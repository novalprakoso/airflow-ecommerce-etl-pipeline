# =====================================================
# FAKESTORE API → MYSQL STAR SCHEMA
# ETL PIPELINE - V2
# =====================================================

from datetime import datetime, timedelta
import logging
logger = logging.getLogger(__name__)

import requests
from airflow import DAG
from airflow.providers.mysql.hooks.mysql import MySqlHook
from airflow.providers.standard.operators.empty import EmptyOperator
from airflow.providers.standard.operators.python import PythonOperator


DAG_ID = "etl_fakestore_api"
BASE_URL = "https://fakestoreapi.com"


# =====================================================
# API
# =====================================================

def call_api(endpoint):
    """
    Extract data from FakeStore API.
    """

    url = f"{BASE_URL}{endpoint}"

    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        data = response.json()

        if not data:
            raise ValueError(f"API returned empty data: {endpoint}")

        return data

    except requests.RequestException as exc:
        raise RuntimeError(
            f"Failed to extract data from {url}: {exc}"
        ) from exc


# =====================================================
# DATABASE SCHEMA
# =====================================================

def create_star_schema():
    """
    Create dimensional model used by the analytical warehouse.
    """

    mysql = MySqlHook(mysql_conn_id="mysql_conn")
    conn = mysql.get_conn()
    cursor = conn.cursor()

    ddl_statements = [

        # -------------------------------------------------
        # DIMENSION: USERS
        # -------------------------------------------------

        """
        CREATE TABLE IF NOT EXISTS dim_users (
            user_key INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL UNIQUE,
            email VARCHAR(255),
            username VARCHAR(100),
            city VARCHAR(100)
        )
        """,

        # -------------------------------------------------
        # DIMENSION: PRODUCTS
        # -------------------------------------------------

        """
        CREATE TABLE IF NOT EXISTS dim_products (
            product_key INT AUTO_INCREMENT PRIMARY KEY,
            product_id INT NOT NULL UNIQUE,
            title VARCHAR(255),
            category VARCHAR(100),
            price DECIMAL(10,2)
        )
        """,

        # -------------------------------------------------
        # DIMENSION: DATE
        # -------------------------------------------------

        """
        CREATE TABLE IF NOT EXISTS dim_date (
            date_key INT PRIMARY KEY,
            full_date DATE NOT NULL,
            day INT,
            month INT,
            year INT
        )
        """,

        # -------------------------------------------------
        # FACT: SALES
        #
        # Grain:
        # One row represents one product line
        # within one cart transaction.
        # -------------------------------------------------

        """
        CREATE TABLE IF NOT EXISTS fact_sales (
            sales_key INT AUTO_INCREMENT PRIMARY KEY,

            cart_id INT NOT NULL,

            user_key INT NOT NULL,
            product_key INT NOT NULL,
            date_key INT NOT NULL,

            quantity INT NOT NULL,
            sales_amount DECIMAL(10,2) NOT NULL,

            CONSTRAINT uq_cart_product
                UNIQUE (cart_id, product_key),

            CONSTRAINT fk_sales_user
                FOREIGN KEY (user_key)
                REFERENCES dim_users(user_key),

            CONSTRAINT fk_sales_product
                FOREIGN KEY (product_key)
                REFERENCES dim_products(product_key),

            CONSTRAINT fk_sales_date
                FOREIGN KEY (date_key)
                REFERENCES dim_date(date_key)
        )
        """
    ]

    try:

        for statement in ddl_statements:
            cursor.execute(statement)

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        cursor.close()
        conn.close()


# =====================================================
# EXTRACT
# =====================================================

def extract_users(ti):
    """
    Extract customer data from API.
    """

    users = call_api("/users")

    logger.info(
        "Extract users completed: %d records",
        len(users)
    )

    ti.xcom_push(
        key="raw_users",
        value=users
    )


def extract_products(ti):
    """
    Extract product master data from API.
    """

    products = call_api("/products")

    logger.info(
        "Extract products completed: %d records",
        len(products)
    )

    ti.xcom_push(
        key="raw_products",
        value=products
    )


def extract_carts(ti):
    """
    Extract cart transaction data from API.
    """

    carts = call_api("/carts")

    logger.info(
        "Extract carts completed: %d records",
        len(carts)
    )

    ti.xcom_push(
        key="raw_carts",
        value=carts
    )


# =====================================================
# TRANSFORM
# =====================================================

def transform_data(ti):
    """
    Transform raw API data into dimensional model.

    Grain of fact_sales:
    One row = one product line within one cart transaction.
    """

    users = ti.xcom_pull(
        key="raw_users",
        task_ids="extract_users"
    )

    products = ti.xcom_pull(
        key="raw_products",
        task_ids="extract_products"
    )

    carts = ti.xcom_pull(
        key="raw_carts",
        task_ids="extract_carts"
    )

    # -------------------------------------------------
    # DATA VALIDATION
    # -------------------------------------------------

    if not users:
        raise ValueError("Users dataset is empty")

    if not products:
        raise ValueError("Products dataset is empty")

    if not carts:
        raise ValueError("Carts dataset is empty")

    # -------------------------------------------------
    # BUSINESS KEY SETS
    # -------------------------------------------------

    user_ids = {
        user["id"]
        for user in users
    }

    product_ids = {
        product["id"]
        for product in products
    }

    # -------------------------------------------------
    # DIM USERS
    # -------------------------------------------------

    dim_users = []

    for user in users:

        if user["id"] is None:
            raise ValueError("User ID cannot be NULL")

        dim_users.append(
            (
                user["id"],
                user["email"],
                user["username"],
                user["address"]["city"]
            )
        )

    # -------------------------------------------------
    # DIM PRODUCTS
    # -------------------------------------------------

    dim_products = []

    product_price_map = {
        product["id"]: product["price"]
        for product in products
    }

    for product in products:

        if product["id"] is None:
            raise ValueError("Product ID cannot be NULL")

        if product["price"] is None:
            raise ValueError(
                f"Product {product['id']} has NULL price"
            )

        dim_products.append(
            (
                product["id"],
                product["title"],
                product["category"],
                product["price"]
            )
        )

    # -------------------------------------------------
    # DIM DATE
    # -------------------------------------------------

    dim_dates = {}

    cart_dates = [
        datetime.fromisoformat(
            cart["date"][:10]
        ).date()
        for cart in carts
    ]

    min_date = min(cart_dates)
    max_date = max(cart_dates)

    current_date = min_date

    while current_date <= max_date:

        date_key = int(
            current_date.strftime("%Y%m%d")
        )

        dim_dates[date_key] = (
            date_key,
            current_date,
            current_date.day,
            current_date.month,
            current_date.year
        )

        current_date += timedelta(days=1)

    # -------------------------------------------------
    # FACT SALES
    # -------------------------------------------------

    fact_sales = []

    for cart in carts:

        cart_id = cart["id"]
        user_id = cart["userId"]

        # Validate user reference

        if user_id not in user_ids:
            raise ValueError(
                f"Cart {cart_id} references "
                f"unknown user {user_id}"
            )

        # Convert API datetime to date

        date = cart["date"][:10]

        dt = datetime.fromisoformat(date)

        date_key = int(
            dt.strftime("%Y%m%d")
        )

        # -------------------------------------------------
        # PRODUCT LINES
        # -------------------------------------------------

        for item in cart["products"]:

            product_id = item["productId"]
            quantity = item["quantity"]

            # Validate product reference

            if product_id not in product_ids:
                raise ValueError(
                    f"Cart {cart_id} references "
                    f"unknown product {product_id}"
                )

            if quantity <= 0:
                raise ValueError(
                    f"Invalid quantity {quantity} "
                    f"for cart {cart_id}, "
                    f"product {product_id}"
                )

            price = product_price_map[product_id]

            sales_amount = price * quantity

            fact_sales.append(
                (
                    cart_id,
                    user_id,
                    product_id,
                    date_key,
                    quantity,
                    sales_amount
                )
            )

    # -------------------------------------------------
    # VALIDATE TRANSFORM RESULT
    # -------------------------------------------------

    if not fact_sales:
        raise ValueError(
            "fact_sales transformation produced no rows"
        )

    # -------------------------------------------------
    # PUSH TRANSFORMED DATA
    # -------------------------------------------------

    ti.xcom_push(
        key="dim_users",
        value=dim_users
    )

    ti.xcom_push(
        key="dim_products",
        value=dim_products
    )

    ti.xcom_push(
        key="dim_dates",
        value=list(dim_dates.values())
    )

    ti.xcom_push(
        key="fact_sales",
        value=fact_sales
    )

# =====================================================
# MONITORING
# =====================================================

    logger.info(
        "Transform completed successfully"
    )

    logger.info(
        "dim_users: %d records",
        len(dim_users)
    )

    logger.info(
        "dim_products: %d records",
        len(dim_products)
    )

    logger.info(
        "dim_date: %d records",
        len(dim_dates)
    )   

    logger.info(
        "fact_sales: %d records",
        len(fact_sales)
    )

# =====================================================
# LOAD
# =====================================================

def load_to_mysql(ti):
    """
    Load transformed data into MySQL warehouse.
    """

    mysql = MySqlHook(mysql_conn_id="mysql_conn")

    conn = mysql.get_conn()
    cursor = conn.cursor()

    dim_users = ti.xcom_pull(
        key="dim_users",
        task_ids="transform_data"
    )

    dim_products = ti.xcom_pull(
        key="dim_products",
        task_ids="transform_data"
    )

    dim_dates = ti.xcom_pull(
        key="dim_dates",
        task_ids="transform_data"
    )

    fact_sales = ti.xcom_pull(
        key="fact_sales",
        task_ids="transform_data"
    )

    try:

        # =================================================
        # LOAD DIM USERS
        # =================================================

        cursor.executemany(
            """
            INSERT INTO dim_users
                (user_id, email, username, city)

            VALUES
                (%s, %s, %s, %s)

            ON DUPLICATE KEY UPDATE
                email = VALUES(email),
                username = VALUES(username),
                city = VALUES(city)
            """,
            dim_users
        )

        # =================================================
        # LOAD DIM PRODUCTS
        # =================================================

        cursor.executemany(
            """
            INSERT INTO dim_products
                (product_id, title, category, price)

            VALUES
                (%s, %s, %s, %s)

            ON DUPLICATE KEY UPDATE
                title = VALUES(title),
                category = VALUES(category),
                price = VALUES(price)
            """,
            dim_products
        )

        # =================================================
        # LOAD DIM DATE
        # =================================================

        cursor.executemany(
            """
            INSERT IGNORE INTO dim_date
                (date_key, full_date, day, month, year)

            VALUES
                (%s, %s, %s, %s, %s)
            """,
            dim_dates
        )

        # =================================================
        # RESOLVE SURROGATE KEYS
        # =================================================

        user_key_map = {}

        cursor.execute(
            """
            SELECT user_key, user_id
            FROM dim_users
            """
        )

        for user_key, user_id in cursor.fetchall():
            user_key_map[user_id] = user_key

        product_key_map = {}

        cursor.execute(
            """
            SELECT product_key, product_id
            FROM dim_products
            """
        )

        for product_key, product_id in cursor.fetchall():
            product_key_map[product_id] = product_key

        # =================================================
        # LOAD FACT SALES
        # =================================================

        fact_rows = []

        for row in fact_sales:

            (
                cart_id,
                user_id,
                product_id,
                date_key,
                quantity,
                sales_amount
            ) = row

            user_key = user_key_map[user_id]
            product_key = product_key_map[product_id]

            fact_rows.append(
                (
                    cart_id,
                    user_key,
                    product_key,
                    date_key,
                    quantity,
                    sales_amount
                )
            )

        cursor.executemany(
            """
            INSERT INTO fact_sales
                (
                    cart_id,
                    user_key,
                    product_key,
                    date_key,
                    quantity,
                    sales_amount
                )

            VALUES
                (%s, %s, %s, %s, %s, %s)

            ON DUPLICATE KEY UPDATE
                user_key = VALUES(user_key),
                product_key = VALUES(product_key),
                date_key = VALUES(date_key),
                quantity = VALUES(quantity),
                sales_amount = VALUES(sales_amount)
            """,
            fact_rows
        )

        logger.info(
            "fact_sales loaded: %d records",
            len(fact_rows)
        )

        # =================================================
        # COMMIT
        # =================================================

        logger.info(
            "Load summary - dim_users: %d records",
            len(dim_users)
        )

        logger.info(
            "Load summary - dim_products: %d records",
            len(dim_products)
        )

        logger.info(
            "Load summary - dim_date: %d records",
        len(dim_dates)
        )

        logger.info(
            "Load summary - fact_sales: %d records",
            len(fact_rows)
        )

        conn.commit()

        logger.info(
            "MySQL load committed successfully"
        )

        logger.info(
            "MySQL load committed successfully"
        )

    except Exception:
        conn.rollback()
        raise

    finally:
        cursor.close()
        conn.close()


# =====================================================
# DAG
# =====================================================

with DAG(
    dag_id=DAG_ID,
    start_date=datetime(2024, 1, 1),
    schedule=None,
    catchup=False,
    tags=[
        "portfolio",
        "etl",
        "star_schema"
    ],
) as dag:

    start = EmptyOperator(
        task_id="start"
    )

    end = EmptyOperator(
        task_id="end"
    )

    create_tables = PythonOperator(
        task_id="create_star_schema",
        python_callable=create_star_schema
    )

    extract_users_task = PythonOperator(
        task_id="extract_users",
        python_callable=extract_users
    )

    extract_products_task = PythonOperator(
        task_id="extract_products",
        python_callable=extract_products
    )

    extract_carts_task = PythonOperator(
        task_id="extract_carts",
        python_callable=extract_carts
    )

    transform_task = PythonOperator(
        task_id="transform_data",
        python_callable=transform_data
    )

    load_task = PythonOperator(
        task_id="load_to_mysql",
        python_callable=load_to_mysql
    )

    # =================================================
    # DAG DEPENDENCY
    # =================================================

    start >> create_tables

    create_tables >> [
        extract_users_task,
        extract_products_task,
        extract_carts_task
    ]

    [
        extract_users_task,
        extract_products_task,
        extract_carts_task
    ] >> transform_task

    transform_task >> load_task >> end