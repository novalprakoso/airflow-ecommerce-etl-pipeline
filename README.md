# FakeStore E-Commerce ETL Pipeline

**End-to-End Data Engineering & Business Analytics Project**

**FakeStore API → Apache Airflow → MySQL Star Schema → SQL Business Analysis → Power BI**

<img width="1536" height="1024" alt="ETL pipeline for business intelligence" src="https://github.com/user-attachments/assets/5ee78116-646e-4844-947c-6617ddba5555" />

## 📌 Project Overview

This project demonstrates an end-to-end **ETL pipeline for E-Commerce analytics**, starting from data extraction through business analysis and visualization.

The pipeline extracts data from the **FakeStore API**, validates and transforms the raw JSON data into a **Star Schema data warehouse**, and loads the resulting datasets into MySQL using Apache Airflow.

The resulting warehouse is then used for:

* SQL-based business analysis
* Business KPI calculation
* Customer and product analysis
* Power BI visualization

The project was developed to demonstrate practical skills in **Data Engineering, Data Analytics, and Business Analysis**.

---

## 🏗️ Data Architecture

```text
                    FakeStore API
                         │
                         ▼
                ┌─────────────────┐
                │     EXTRACT     │
                │                 │
                │ Users           │
                │ Products        │
                │ Carts           │
                └────────┬────────┘
                         │
                         ▼
                ┌─────────────────┐
                │    TRANSFORM    │
                │                 │
                │ Validation      │
                │ Business Keys   │
                │ Date Dimension  │
                │ Sales Amount    │
                └────────┬────────┘
                         │
                         ▼
                ┌─────────────────┐
                │      LOAD       │
                │      MySQL      │
                │                 │
                │ dim_users       │
                │ dim_products    │
                │ dim_date        │
                │ fact_sales      │
                └────────┬────────┘
                         │
              ┌──────────┴──────────┐
              ▼                     ▼
      SQL Business Analysis     Power BI
```

---

# 🔄 ETL Pipeline

The ETL pipeline is orchestrated using **Apache Airflow**.

### DAG Workflow

```text
START
  │
  ▼
Create Star Schema
  │
  ├──────────────┐
  ▼              ▼
Extract Users  Extract Products
  │              │
  └──────┬───────┘
         │
         ▼
    Extract Carts
         │
         ▼
   Transform Data
         │
         ▼
    Load to MySQL
         │
         ▼
        END
```

### Airflow Tasks

| Task                 | Description                               |
| -------------------- | ----------------------------------------- |
| `start`              | Starts the DAG workflow                   |
| `create_star_schema` | Creates MySQL dimensional tables          |
| `extract_users`      | Extracts customer data from FakeStore API |
| `extract_products`   | Extracts product master data              |
| `extract_carts`      | Extracts cart transaction data            |
| `transform_data`     | Validates and transforms API data         |
| `load_to_mysql`      | Loads dimensions and fact data into MySQL |
| `end`                | Completes the pipeline                    |

---

# 📦 Source Data

The project uses the **FakeStore API** as the source system.

The successfully extracted dataset contains:

| Dataset       | Records |
| ------------- | ------: |
| Users         |      10 |
| Products      |      20 |
| Carts         |       7 |
| Product Lines |      14 |

A cart can contain multiple products. Therefore, the grain of the fact table is:

> **One row represents one product line within one cart transaction.**

For example:

```text
Cart 1
├── Product A → Quantity 4
├── Product B → Quantity 1
└── Product C → Quantity 6
```

This produces **3 fact rows** for Cart 1.

---

# 🗃️ Data Warehouse

The transformed data is stored in MySQL using a **Star Schema**.

## Fact Table

### `fact_sales`

| Column         | Description                   |
| -------------- | ----------------------------- |
| `sales_key`    | Surrogate key                 |
| `cart_id`      | Business key of the cart      |
| `user_key`     | Foreign key to `dim_users`    |
| `product_key`  | Foreign key to `dim_products` |
| `date_key`     | Foreign key to `dim_date`     |
| `quantity`     | Quantity purchased            |
| `sales_amount` | Calculated sales value        |

### Grain

```text
1 row = 1 product line within 1 cart
```

---

## Dimension Tables

### `dim_users`

Contains customer information:

```text
user_key
user_id
email
username
city
```

### `dim_products`

Contains product master information:

```text
product_key
product_id
title
category
price
```

### `dim_date`

Contains calendar attributes:

```text
date_key
full_date
day
month
year
```

The current dataset generates **62 calendar dates** covering the minimum and maximum transaction dates.

---

# 🔑 Data Modeling

The warehouse uses **surrogate keys** for dimensional relationships while preserving API IDs as business keys.

```text
                 dim_users
                    │
                    │ user_key
                    ▼
               fact_sales
              ▲    ▲    ▲
              │    │    │
       product_key │ date_key
              │    │    │
              │    │    │
      dim_products  │ dim_date
```

This design separates:

* Customer attributes
* Product attributes
* Calendar attributes
* Transaction measures

and allows analytical queries to aggregate sales across different business dimensions.

---

# 🛡️ Data Quality & Validation

The transformation layer includes several validation checks before data reaches the warehouse.

### User validation

The pipeline checks that:

* User dataset is not empty
* User IDs are not NULL
* Cart transactions reference existing users

### Product validation

The pipeline checks that:

* Product dataset is not empty
* Product IDs are not NULL
* Product prices are not NULL
* Cart transactions reference existing products

### Transaction validation

The pipeline checks that:

* Cart dataset is not empty
* Product quantities are greater than zero
* Product references are valid
* Transaction dates can be converted into valid dates

Invalid records cause the transformation task to fail rather than silently loading inconsistent data.

---

# ♻️ Idempotency

The pipeline was designed to be **rerunnable without creating duplicate business records**.

The `fact_sales` table uses:

```text
UNIQUE(cart_id, product_key)
```

and the load process uses:

```sql
ON DUPLICATE KEY UPDATE
```

for fact records.

Dimension tables also use duplicate-safe loading logic.

This allows the DAG to be executed repeatedly while maintaining the expected warehouse state.

---

# 📊 Monitoring & Logging

The pipeline includes operational logging during the load process.

Examples include:

```text
dim_users loaded: X records
dim_products loaded: X records
dim_date loaded: X records
fact_sales loaded: X records
```

A load summary is also logged after the warehouse loading process.

This provides basic observability into:

* Number of records processed
* Successful loading of each table
* Pipeline execution status
* Failed database operations

---

# 📈 SQL Business Analysis

After the ETL process completes, SQL queries are used to analyze the resulting warehouse.

Business analysis is available in:

```text
dags/business_analysis.sql
```

The analysis covers:

### 1. Sales by Category

Measures:

* Total quantity
* Total sales

### 2. Top Products

Measures:

* Total quantity sold
* Total sales by product

### 3. Sales by Customer

Measures:

* Number of orders
* Total quantity
* Total sales

### 4. Sales by Date

Measures:

* Total quantity
* Total sales by transaction date

---

# 💡 Key Business Insights

Based on the current dataset:

## Sales Performance

Total sales:

```text
Rp4,691.27
```

Total product-line transactions:

```text
14
```

Total quantity sold:

```text
42
```

---

## 🥇 Sales by Category

| Category         | Quantity |      Sales |
| ---------------- | -------: | ---------: |
| Men's clothing   |       31 | Rp2,646.44 |
| Jewelery         |        4 | Rp1,410.98 |
| Electronics      |        6 |   Rp624.00 |
| Women's clothing |        1 |     Rp9.85 |

**Men's clothing generates the highest sales**, contributing approximately 56% of total sales.

Jewelry ranks second in sales despite having a much lower quantity because of its higher-value products.

---

## 🏆 Top Products

The highest-selling product is:

**Fjallraven - Foldsack No. 1 Backpack**

```text
Quantity: 20
Sales: Rp2,199.00
```

The product alone contributes almost half of total sales.

This indicates that product-level sales concentration is relatively high in the current dataset.

---

## 👤 Customer Analysis

| Customer  | Orders | Quantity |      Sales |
| --------- | -----: | -------: | ---------: |
| johnd     |      2 |       27 | Rp3,376.74 |
| donero    |      1 |        5 |   Rp560.00 |
| kevinryan |      2 |        6 |   Rp460.78 |
| mor_2314  |      1 |        3 |   Rp283.90 |
| hopkins   |      1 |        1 |     Rp9.85 |

`johnd` is the highest-value customer with:

```text
2 orders
27 units
Rp3,376.74 sales
```

This customer contributes approximately 72% of total sales in the current dataset.

---

## 📅 Sales by Date

| Date     | Quantity |      Sales |
| -------- | -------: | ---------: |
| 1/1/2020 |        4 |   Rp439.80 |
| 1/2/2020 |       16 | Rp2,578.70 |
| 3/1/2020 |       11 |   Rp874.73 |
| 3/2/2020 |       11 |   Rp798.04 |

The highest sales date is:

**January 2, 2020 — Rp2,578.70**

---

# 📊 Power BI Dashboard

The existing Power BI dashboard is retained as the visualization layer.

<img width="551" height="298" alt="Dashboard E-Commerce FakeStore" src="https://github.com/user-attachments/assets/1d5c0412-bdbc-4c70-a1cf-edb55cfc8bb1" />

The dashboard provides analysis such as:

* Revenue performance
* Sales by category
* Top products
* Customer analysis
* Sales trends
* Geographic/customer analysis

The Power BI model follows a Star Schema approach.

<img width="677" height="251" alt="Power BI Data Model" src="https://github.com/user-attachments/assets/c5e07ac3-4669-4f84-af07-1d0230636527" />

Power BI files included in the repository:

```text
Dashboard E-Commerce FakeStore.pbix
Dashboard E-Commerce FakeStore.pbit
```

---

# 🛠️ Technology Stack

| Layer             | Technology     |
| ----------------- | -------------- |
| Source            | FakeStore API  |
| Programming       | Python         |
| Orchestration     | Apache Airflow |
| Containerization  | Docker         |
| Data Warehouse    | MySQL          |
| Data Modeling     | Star Schema    |
| Business Analysis | SQL            |
| Visualization     | Power BI       |
| Version Control   | Git & GitHub   |

---

# 📁 Project Structure

```text
airflow-ecommerce-etl-pipeline/
│
├── dags/
│   ├── etl_fakestore_api.py
│   └── business_analysis.sql
│
├── Dashboard E-Commerce FakeStore.pbix
├── Dashboard E-Commerce FakeStore.pbit
│
├── RAW Data Postman.png
├── Raw Data.png
├── Tampilan Airflow UI refactor v2.png
│
├── docker-compose.yml
├── .gitignore
└── README.md
```

---

# 🚀 How to Run

## 1. Clone the repository

```bash
git clone https://github.com/novalprakoso/airflow-ecommerce-etl-pipeline.git
cd airflow-ecommerce-etl-pipeline
```

For the current V2 implementation:

```bash
git checkout refactor-v2
```

---

## 2. Configure environment variables

Create a local `.env` file in the project root.

Example:

```env
AIRFLOW_SECRET_KEY=airflow_secret_local
POSTGRES_PASSWORD=postgres_local
AIRFLOW_ADMIN_PASSWORD=admin_local
```

The `.env` file is intentionally excluded from Git through `.gitignore`.

---

## 3. Start Docker services

Run:

```bash
docker compose up -d
```

Check running containers:

```bash
docker compose ps
```

---

## 4. Open Airflow

Open:

```text
http://localhost:8080
```

Log in using the local Airflow credentials configured through `.env`.

---

## 5. Configure MySQL Connection

Create an Airflow connection with:

| Field     | Value                 |
| --------- | --------------------- |
| Conn ID   | `mysql_conn`          |
| Conn Type | `MySQL`               |
| Host      | Your local MySQL host |
| Schema    | `fakestore_api`       |
| Login     | Your MySQL username   |
| Password  | Your MySQL password   |
| Port      | `3306`                |

The DAG accesses this connection using:

```python
MySqlHook(mysql_conn_id="mysql_conn")
```

---

## 6. Run the DAG

From Airflow UI:

```text
etl_fakestore_api
        ↓
Trigger DAG
```

The expected workflow is:

```text
Create Star Schema
        ↓
Extract Users
Extract Products
Extract Carts
        ↓
Transform Data
        ↓
Load to MySQL
        ↓
Success
```

---

# 🔍 Validate the Warehouse

After the DAG completes, verify the warehouse using SQL:

```sql
SELECT COUNT(*) FROM dim_users;

SELECT COUNT(*) FROM dim_products;

SELECT COUNT(*) FROM dim_date;

SELECT COUNT(*) FROM fact_sales;
```

Expected current dataset:

```text
dim_users     = 10
dim_products  = 20
dim_date      = 62
fact_sales    = 14
```

Total sales can be checked with:

```sql
SELECT
    COUNT(*) AS total_product_lines,
    SUM(quantity) AS total_quantity,
    SUM(sales_amount) AS total_sales
FROM fact_sales;
```

Expected result:

```text
product lines : 14
quantity      : 42
total sales   : Rp4,691.27
```

---

# ⚠️ Data Limitation

FakeStore API is a demonstration API with a relatively small dataset.

The current successful extraction contains only:

```text
10 users
20 products
7 carts
14 product lines
```

Therefore, the business insights in this project should be interpreted as **demonstration analytics**, not as statistically representative E-Commerce performance.

The purpose of the project is primarily to demonstrate:

* ETL pipeline design
* Data orchestration
* Data validation
* Dimensional modeling
* Idempotent loading
* SQL analytics
* BI integration

For a production implementation, the pipeline could be connected to a larger and more reliable transactional data source.

---

# 🚧 Future Improvements

Potential improvements include:

1. Incremental data loading
2. Automated data quality reporting
3. More comprehensive pipeline monitoring
4. Historical dimension management
5. Cloud deployment
6. Automated Power BI dataset refresh
7. Integration with a larger production-scale E-Commerce dataset
8. CI/CD pipeline for Airflow DAG testing

---

# 👨‍💻 Author

**Noval Prakoso**

Aspiring Data Engineer | Data Analyst | Business Analyst

Background in Electrical Engineering with hands-on experience in:

* Python
* SQL
* MySQL
* Apache Airflow
* Docker
* Power BI
* Data Modeling
* ETL Development
* Business Analysis
