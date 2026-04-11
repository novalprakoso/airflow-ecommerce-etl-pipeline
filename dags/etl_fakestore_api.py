# =====================================================
# FAKESTORE API → MYSQL STAR SCHEMA (ETL PIPELINE)
# =====================================================

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.empty import EmptyOperator
from airflow.providers.mysql.hooks.mysql import MySqlHook
from datetime import datetime
import requests

DAG_ID = "etl_fakestore_api"
BASE_URL = "https://fakestoreapi.com"

# =====================================================
# GENERIC API CALL
# =====================================================
def call_api(endpoint):
    response = requests.get(f"{BASE_URL}{endpoint}", timeout=30)
    response.raise_for_status()
    return response.json()

# =====================================================
# CREATE STAR SCHEMA
# =====================================================
def create_star_schema():
    mysql = MySqlHook(mysql_conn_id="mysql_conn")
    conn = mysql.get_conn()
    cursor = conn.cursor()

    ddl_sql = """
    CREATE TABLE IF NOT EXISTS dim_users (
        user_key INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT UNIQUE,
        email VARCHAR(255),
        username VARCHAR(100),
        city VARCHAR(100)
    );

    CREATE TABLE IF NOT EXISTS dim_products (
        product_key INT AUTO_INCREMENT PRIMARY KEY,
        product_id INT UNIQUE,
        title VARCHAR(255),
        category VARCHAR(100),
        price DECIMAL(10,2)
    );

    CREATE TABLE IF NOT EXISTS dim_date (
        date_key INT PRIMARY KEY,
        full_date DATE,
        day INT,
        month INT,
        year INT
    );

    CREATE TABLE IF NOT EXISTS fact_sales (
        sales_key INT AUTO_INCREMENT PRIMARY KEY,
        user_key INT,
        product_key INT,
        date_key INT,
        quantity INT,
        total_price DECIMAL(10,2)
    );
    """

    for statement in ddl_sql.split(";"):
        if statement.strip():
            cursor.execute(statement)

    conn.commit()
    cursor.close()
    conn.close()

# =====================================================
# EXTRACT
# =====================================================
def extract_users(ti):
    ti.xcom_push(key="raw_users", value=call_api("/users"))

def extract_products(ti):
    ti.xcom_push(key="raw_products", value=call_api("/products"))

def extract_carts(ti):
    ti.xcom_push(key="raw_carts", value=call_api("/carts"))

# =====================================================
# TRANSFORM → BUILD STAR SCHEMA DATA
# =====================================================
def transform_data(ti):
    users = ti.xcom_pull(key="raw_users", task_ids="extract_users")
    products = ti.xcom_pull(key="raw_products", task_ids="extract_products")
    carts = ti.xcom_pull(key="raw_carts", task_ids="extract_carts")

    # ---------- DIM USERS ----------
    dim_users = []
    for u in users:
        dim_users.append((
            u["id"],
            u["email"],
            u["username"],
            u["address"]["city"]
        ))

    # ---------- DIM PRODUCTS ----------
    dim_products = []
    for p in products:
        dim_products.append((
            p["id"],
            p["title"],
            p["category"],
            p["price"]
        ))

    # ---------- DIM DATE + FACT ----------
    dim_dates = {}
    fact_sales = []

    for cart in carts:
        date = cart["date"][:10]  # yyyy-mm-dd
        dt = datetime.fromisoformat(date)
        date_key = int(dt.strftime("%Y%m%d"))

        dim_dates[date_key] = (
            date_key, date, dt.day, dt.month, dt.year
        )

        user_id = cart["userId"]

        for item in cart["products"]:
            product_id = item["productId"]
            qty = item["quantity"]

            price = next(p["price"] for p in products if p["id"] == product_id)
            total_price = price * qty

            fact_sales.append((
                user_id,
                product_id,
                date_key,
                qty,
                total_price
            ))

    ti.xcom_push(key="dim_users", value=dim_users)
    ti.xcom_push(key="dim_products", value=dim_products)
    ti.xcom_push(key="dim_dates", value=list(dim_dates.values()))
    ti.xcom_push(key="fact_sales", value=fact_sales)

# =====================================================
# LOAD → INSERT INTO MYSQL
# =====================================================
def load_to_mysql(ti):
    mysql = MySqlHook(mysql_conn_id="mysql_conn")
    conn = mysql.get_conn()
    cursor = conn.cursor()

    dim_users = ti.xcom_pull(key="dim_users", task_ids="transform_data")
    dim_products = ti.xcom_pull(key="dim_products", task_ids="transform_data")
    dim_dates = ti.xcom_pull(key="dim_dates", task_ids="transform_data")
    fact_sales = ti.xcom_pull(key="fact_sales", task_ids="transform_data")

    # ---------- LOAD DIM USERS ----------
    cursor.executemany("""
        INSERT INTO dim_users (user_id,email,username,city)
        VALUES (%s,%s,%s,%s)
        ON DUPLICATE KEY UPDATE
        email=VALUES(email), username=VALUES(username), city=VALUES(city)
    """, dim_users)

    # ---------- LOAD DIM PRODUCTS ----------
    cursor.executemany("""
        INSERT INTO dim_products (product_id,title,category,price)
        VALUES (%s,%s,%s,%s)
        ON DUPLICATE KEY UPDATE
        title=VALUES(title), category=VALUES(category), price=VALUES(price)
    """, dim_products)

    # ---------- LOAD DIM DATE ----------
    cursor.executemany("""
        INSERT IGNORE INTO dim_date (date_key,full_date,day,month,year)
        VALUES (%s,%s,%s,%s,%s)
    """, dim_dates)

    # ---------- LOAD FACT SALES ----------
    for row in fact_sales:
        user_id, product_id, date_key, qty, total_price = row

        cursor.execute("SELECT user_key FROM dim_users WHERE user_id=%s", (user_id,))
        user_key = cursor.fetchone()[0]

        cursor.execute("SELECT product_key FROM dim_products WHERE product_id=%s", (product_id,))
        product_key = cursor.fetchone()[0]

        cursor.execute("""
            INSERT INTO fact_sales (user_key,product_key,date_key,quantity,total_price)
            VALUES (%s,%s,%s,%s,%s)
        """, (user_key, product_key, date_key, qty, total_price))

    conn.commit()
    cursor.close()
    conn.close()

# =====================================================
# DAG
# =====================================================
with DAG(
    dag_id=DAG_ID,
    start_date=datetime(2024,1,1),
    schedule=None,
    catchup=False,
    tags=["portfolio","etl","star_schema"]
) as dag:

    start = EmptyOperator(task_id="start")
    end = EmptyOperator(task_id="end")

    create_tables = PythonOperator(
        task_id="create_star_schema",
        python_callable=create_star_schema
    )

    extract_users_task = PythonOperator(task_id="extract_users", python_callable=extract_users)
    extract_products_task = PythonOperator(task_id="extract_products", python_callable=extract_products)
    extract_carts_task = PythonOperator(task_id="extract_carts", python_callable=extract_carts)

    transform_task = PythonOperator(task_id="transform_data", python_callable=transform_data)
    load_task = PythonOperator(task_id="load_to_mysql", python_callable=load_to_mysql)

    start >> create_tables >> [extract_users_task, extract_products_task, extract_carts_task] >> transform_task >> load_task >> end