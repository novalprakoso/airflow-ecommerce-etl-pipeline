-- =====================================================
-- FAKESTORE E-COMMERCE BUSINESS ANALYSIS
-- MySQL Star Schema
-- =====================================================

USE fakestore_api;


-- =====================================================
-- 1. OVERALL SALES PERFORMANCE
-- =====================================================

SELECT
    COUNT(*) AS total_product_lines,
    SUM(quantity) AS total_quantity,
    ROUND(SUM(sales_amount), 2) AS total_sales,
    ROUND(AVG(sales_amount), 2) AS avg_sales_per_line
FROM fact_sales;


-- =====================================================
-- 2. SALES BY CATEGORY
-- =====================================================

SELECT
    p.category,
    SUM(f.quantity) AS total_quantity,
    ROUND(SUM(f.sales_amount), 2) AS total_sales
FROM fact_sales f
JOIN dim_products p
    ON f.product_key = p.product_key
GROUP BY p.category
ORDER BY total_sales DESC;


-- =====================================================
-- 3. TOP PRODUCTS BY SALES
-- =====================================================

SELECT
    p.title,
    SUM(f.quantity) AS total_quantity,
    ROUND(SUM(f.sales_amount), 2) AS total_sales
FROM fact_sales f
JOIN dim_products p
    ON f.product_key = p.product_key
GROUP BY p.product_key, p.title
ORDER BY total_sales DESC
LIMIT 10;


-- =====================================================
-- 4. SALES BY CUSTOMER
-- =====================================================

SELECT
    u.username,
    COUNT(DISTINCT f.cart_id) AS total_orders,
    SUM(f.quantity) AS total_quantity,
    ROUND(SUM(f.sales_amount), 2) AS total_sales
FROM fact_sales f
JOIN dim_users u
    ON f.user_key = u.user_key
GROUP BY u.user_key, u.username
ORDER BY total_sales DESC;


-- =====================================================
-- 5. SALES TREND BY DATE
-- =====================================================

SELECT
    d.full_date,
    SUM(f.quantity) AS total_quantity,
    ROUND(SUM(f.sales_amount), 2) AS total_sales
FROM fact_sales f
JOIN dim_date d
    ON f.date_key = d.date_key
GROUP BY d.date_key, d.full_date
ORDER BY d.full_date;


-- =====================================================
-- 6. SALES BY MONTH
-- =====================================================

SELECT
    d.year,
    d.month,
    SUM(f.quantity) AS total_quantity,
    ROUND(SUM(f.sales_amount), 2) AS total_sales
FROM fact_sales f
JOIN dim_date d
    ON f.date_key = d.date_key
GROUP BY d.year, d.month
ORDER BY d.year, d.month;


-- =====================================================
-- 7. CATEGORY SALES CONTRIBUTION
-- =====================================================

SELECT
    p.category,
    ROUND(SUM(f.sales_amount), 2) AS total_sales,
    ROUND(
        SUM(f.sales_amount) /
        (SELECT SUM(sales_amount) FROM fact_sales) * 100,
        2
    ) AS sales_contribution_pct
FROM fact_sales f
JOIN dim_products p
    ON f.product_key = p.product_key
GROUP BY p.category
ORDER BY total_sales DESC;


-- =====================================================
-- 8. TOP CUSTOMERS BY REVENUE
-- =====================================================

SELECT
    u.username,
    COUNT(DISTINCT f.cart_id) AS total_orders,
    ROUND(SUM(f.sales_amount), 2) AS total_sales,
    ROUND(
        SUM(f.sales_amount) /
        (SELECT SUM(sales_amount) FROM fact_sales) * 100,
        2
    ) AS revenue_contribution_pct
FROM fact_sales f
JOIN dim_users u
    ON f.user_key = u.user_key
GROUP BY u.user_key, u.username
ORDER BY total_sales DESC;


-- =====================================================
-- 9. AVERAGE ORDER VALUE
-- =====================================================

SELECT
    ROUND(
        SUM(sales_amount) / COUNT(DISTINCT cart_id),
        2
    ) AS average_order_value
FROM fact_sales;


-- =====================================================
-- 10. ORDER VALUE BY CUSTOMER
-- =====================================================

SELECT
    u.username,
    COUNT(DISTINCT f.cart_id) AS total_orders,
    ROUND(SUM(f.sales_amount), 2) AS total_sales,
    ROUND(
        SUM(f.sales_amount) /
        COUNT(DISTINCT f.cart_id),
        2
    ) AS average_order_value
FROM fact_sales f
JOIN dim_users u
    ON f.user_key = u.user_key
GROUP BY u.user_key, u.username
ORDER BY average_order_value DESC;


-- =====================================================
-- 11. PRODUCT PERFORMANCE BY CATEGORY
-- =====================================================

SELECT
    p.category,
    p.title,
    SUM(f.quantity) AS total_quantity,
    ROUND(SUM(f.sales_amount), 2) AS total_sales
FROM fact_sales f
JOIN dim_products p
    ON f.product_key = p.product_key
GROUP BY
    p.category,
    p.product_key,
    p.title
ORDER BY
    p.category,
    total_sales DESC;


-- =====================================================
-- 12. DATA QUALITY CHECK
-- =====================================================

SELECT
    COUNT(*) AS fact_rows,
    COUNT(DISTINCT cart_id) AS distinct_orders,
    COUNT(DISTINCT user_key) AS distinct_customers,
    COUNT(DISTINCT product_key) AS distinct_products,
    COUNT(DISTINCT date_key) AS distinct_dates
FROM fact_sales;