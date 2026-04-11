# airflow-ecommerce-etl-pipeline
End-to-End Data Engineering Project: API → Airflow ETL → MySQL Data Warehouse → Power BI Dashboard

<img width="1536" height="1024" alt="ETL pipeline for business intelligence" src="https://github.com/user-attachments/assets/5ee78116-646e-4844-947c-6617ddba5555" />


This project demonstrates how to build a production-style ETL pipeline that extracts data from an E-Commerce API, transforms it into a Star Schema Data Warehouse, and delivers business insights through a BI dashboard.

📌 Project Overview

This project simulates a real-world Data Engineering workflow:

Extract data from public E-Commerce API
Transform raw JSON into Star Schema Data Warehouse
Load data into MySQL using Apache Airflow
Export data for analytics
Build interactive Power BI dashboard

The goal is to showcase end-to-end data engineering skills including orchestration, data modeling, and data visualization.

🏗️ Data Architecture
🔹 ETL Pipeline

The pipeline extracts raw data from the FakeStore API, transforms it, and loads it into a MySQL Data Warehouse using Apache Airflow.

Pipeline flow:

API → Airflow DAG → Transform → MySQL Star Schema → Power BI Dashboard

⭐ Star Schema Design

The warehouse uses a dimensional model optimized for analytics.

Fact Table

fact_sales

quantity,
total_price,
user_key,
product_key,
date_key

dim_users

user_id,
username,
email,
city

dim_products

product_id,
title,
category,
price

dim_date

full_date,
day,
month,
year

This schema enables fast analytical queries and BI reporting.

⚠️ Data Limitation

The FakeStore API provides a very small dataset:

Table	Rows
Users	10
Products	20

To simulate real analytics scenarios, synthetic sales transactions were generated.

During development, an attempt was made to scale the dataset to ~1200 transactions using retry logic and alternative API mirrors. However, the FakeStore API frequently returned SSL and HTTP 526 errors and became unavailable during development.

Because of this limitation, the project currently uses the stable dataset that was successfully extracted earlier.
Future improvement would include integrating a more reliable API or data source.

⚙️ Tech Stack
Layer	Tools
Orchestration	Apache Airflow (Astronomer)
Database	MySQL
Language	Python
Data Modeling	Star Schema
Visualization	Power BI
Containerization	Docker
🔄 Airflow DAG Workflow

Pipeline tasks:

1️⃣ Create Star Schema tables
2️⃣ Extract Users from API
3️⃣ Extract Products from API
4️⃣ Transform into dimensions + facts
5️⃣ Load into MySQL

The DAG is fully rerunnable and automatically truncates tables before loading.

📊 Dashboard Overview


<img width="551" height="298" alt="Dashboard E-Commerce FakeStore" src="https://github.com/user-attachments/assets/1d5c0412-bdbc-4c70-a1cf-edb55cfc8bb1" />

The Power BI dashboard answers key business questions:

Revenue Performance
Total Revenue KPI
Revenue trend over time
Monthly performance
Product Analytics
Revenue by category
Top selling products
Customer Insights
Revenue by city
Customer purchase distribution

💡 Business Insights
The dashboard enables stakeholders to answer questions such as:
🛍️ Which product categories generate the most revenue?
Identify high-performing product segments to prioritize marketing and inventory.

🌍 Which cities contribute the most sales?
Understand geographical demand patterns and target marketing campaigns.

📈 How does revenue evolve over time?
Track business growth and detect seasonal trends.

🧑‍💻 Who are the most valuable customers?
Identify high-value customers and analyze purchasing behavior.

🖥️ Power BI Data Model
The dashboard uses a Star Schema relationship model:

<img width="677" height="251" alt="image" src="https://github.com/user-attachments/assets/c5e07ac3-4669-4f84-af07-1d0230636527" />

This model ensures:

Fast filtering
Accurate aggregations
Scalable analytics

🚀 How to Run This Project

Follow the steps below to run the full ETL pipeline locally.
🔐 1. Environment Setup & Secrets
This project does not store credentials in the repository.
Create your own environment configuration before running the pipeline.

Create .env file

Create a file in the project root:

MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_DB=ecommerce_db
MYSQL_USER=your_username
MYSQL_PASSWORD=your_password

Add .env to .gitignore:

.env

🗄️ 2. Create MySQL Database
Open MySQL and create a new database:

CREATE DATABASE ecommerce_db;

🌬️ 3. Start Apache Airflow
Run Airflow locally:

airflow standalone

Open Airflow UI:

http://localhost:8080

🔗 4. Create Airflow MySQL Connection
Inside Airflow UI:

Admin → Connections → Add Connection

Use this configuration:

Field	Value
Conn Id	mysql_conn
Conn Type	MySQL
Host	localhost
Schema	ecommerce_db
Login	<your-username>
Password	<your-password>
Port	3306

⚙️ 5. Add DAG to Airflow
Copy DAG file into Airflow DAG folder:

cp dags/fakestore_etl.py ~/airflow/dags/

Restart Airflow if needed.

▶️ 6. Run the Pipeline
In Airflow UI:

Turn ON the DAG
Click Trigger DAG

The pipeline will:

Extract data from FakeStore API
Transform data into star schema
Load data into MySQL warehouse

📊 7. Open Power BI Dashboard

Export tables from MySQL → CSV

Open Power BI file in /dashboard folder
Refresh data source

🎯 Future Improvements

1. Integrate reliable production API
2. Add incremental loading
3. Add data quality checks
4. Deploy Airflow to cloud environment
5. Automate dashboard refresh


👨‍💻 Author

Noval

Aspiring Data Engineer
