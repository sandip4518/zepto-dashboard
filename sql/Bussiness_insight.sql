-- ============================================
-- BUSINESS ANALYSIS
-- ============================================

-- 1. Top 10 products with highest discounts
-- Business Insight:
-- Identify products heavily discounted to attract customers

SELECT 
    name,
    category,
    mrp,
    discountPercent
FROM zepto
ORDER BY discountPercent DESC
LIMIT 10;


-- 2. High-value products currently out of stock
-- Business Insight:
-- Potential revenue loss because premium products are unavailable

SELECT 
    name,
    category,
    mrp
FROM zepto
WHERE outOfStock = TRUE
ORDER BY mrp DESC;


-- 3. Total inventory value by category
-- Business Insight:
-- Identify categories holding maximum inventory investment

SELECT 
    category,
    ROUND(
        SUM(discountedSellingPrice * availableQuantity),
        2
    ) AS inventory_value
FROM zepto
GROUP BY category
ORDER BY inventory_value DESC;


-- 4. Premium products with low discounts
-- Business Insight:
-- Premium products where promotional offers can improve sales

SELECT 
    name,
    category,
    mrp,
    discountPercent
FROM zepto
WHERE mrp > 500
AND discountPercent < 10
ORDER BY mrp DESC;


-- 5. Categories with highest average discounts
-- Business Insight:
-- Understand discount strategy across categories

SELECT 
    category,
    ROUND(AVG(discountPercent),2) AS average_discount
FROM zepto
GROUP BY category
ORDER BY average_discount DESC
LIMIT 5;


-- 6. Price per gram analysis
-- Business Insight:
-- Compare product cost efficiency based on weight

SELECT 
    name,
    category,
    weightInGms,
    discountedSellingPrice,
    ROUND(
        discountedSellingPrice / weightInGms,
        2
    ) AS price_per_gram
FROM zepto
WHERE weightInGms >= 100
ORDER BY price_per_gram;


-- 7. Product segmentation based on weight
-- Business Insight:
-- Useful for warehouse handling and logistics

SELECT 
    name,
    weightInGms,

    CASE
        WHEN weightInGms < 1000 THEN 'Low Weight'
        WHEN weightInGms < 5000 THEN 'Medium Weight'
        ELSE 'Bulk Product'
    END AS weight_category

FROM zepto;


-- 8. Total inventory weight per category
-- Business Insight:
-- Analyze warehouse load distribution

SELECT 
    category,
    SUM(weightInGms) AS weight_per_category
FROM zepto
GROUP BY category
ORDER BY weight_per_category DESC;


-- 9. Low stock products
-- Business Insight:
-- Products at risk of going out of stock soon

SELECT 
    name,
    category,
    availableQuantity
FROM zepto
WHERE availableQuantity < 10
AND outOfStock = FALSE
ORDER BY availableQuantity ASC;


-- 10. Estimated revenue by category
-- Business Insight:
-- Categories with highest revenue potential

SELECT 
    category,

    ROUND(
        SUM(discountedSellingPrice * availableQuantity),
        2
    ) AS estimated_revenue

FROM zepto
GROUP BY category
ORDER BY estimated_revenue DESC;