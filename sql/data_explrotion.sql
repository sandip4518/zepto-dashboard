-- ============================================
-- DATA EXPLORATION
-- ============================================

-- Total number of products

SELECT COUNT(*) AS total_products
FROM zepto;


-- Display sample records

SELECT *
FROM zepto
LIMIT 10;


-- Find NULL values

SELECT *
FROM zepto
WHERE
    name IS NULL
    OR mrp IS NULL
    OR discountPercent IS NULL
    OR availableQuantity IS NULL
    OR discountedSellingPrice IS NULL
    OR weightInGms IS NULL
    OR outOfStock IS NULL
    OR quantity IS NULL
    OR category IS NULL;


-- Distinct product categories

SELECT DISTINCT category
FROM zepto
ORDER BY category;


-- Product stock availability overview

SELECT 
    outOfStock,
    COUNT(sku_id) AS total_products
FROM zepto
GROUP BY outOfStock;


-- Products appearing multiple times

SELECT 
    name,
    COUNT(sku_id) AS "Number of SKUs"
FROM zepto
GROUP BY name
HAVING COUNT(sku_id) > 1
ORDER BY COUNT(sku_id) DESC;