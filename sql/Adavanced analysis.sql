-- ============================================
-- ADVANCED SQL ANALYSIS
-- ============================================


-- 1. Most expensive product in each category
-- Business Insight:
-- Identify premium products across categories

WITH ranked_products AS (

    SELECT
        category,
        name,
        mrp,

        RANK() OVER(
            PARTITION BY category
            ORDER BY mrp DESC
        ) AS product_rank

    FROM zepto

)

SELECT
    category,
    name,
    mrp
FROM ranked_products
WHERE product_rank = 1;



-- 2. Top products contributing highest inventory value
-- Business Insight:
-- Products contributing maximum stock value

SELECT
    name,
    category,

    ROUND(
        (discountedSellingPrice * availableQuantity)::numeric,
        2
    ) AS inventory_value

FROM zepto
ORDER BY inventory_value DESC
LIMIT 10;



-- 3. Revenue contribution percentage by category
-- Business Insight:
-- Understand category contribution to total business revenue

WITH category_sales AS (

    SELECT
        category,

        SUM(
            discountedSellingPrice * availableQuantity
        ) AS revenue

    FROM zepto
    GROUP BY category

),

total_sales AS (

    SELECT
        SUM(revenue) AS total_revenue
    FROM category_sales

)

SELECT
    c.category,

    ROUND(c.revenue::numeric, 2) AS revenue,

    ROUND(
        ((c.revenue / t.total_revenue) * 100)::numeric,
        2
    ) AS revenue_percentage

FROM category_sales c
CROSS JOIN total_sales t
ORDER BY revenue_percentage DESC;



-- 4. High discount but low inventory products
-- Business Insight:
-- Products likely to sell out quickly during offers

SELECT
    name,
    category,
    discountPercent,
    availableQuantity

FROM zepto

WHERE discountPercent > 40
AND availableQuantity < 20

ORDER BY discountPercent DESC;



-- 5. Inventory risk segmentation
-- Business Insight:
-- Identify inventory health status

SELECT
    name,
    availableQuantity,

    CASE
        WHEN availableQuantity = 0 THEN 'Out of Stock'
        WHEN availableQuantity < 10 THEN 'Critical Stock'
        WHEN availableQuantity < 30 THEN 'Low Stock'
        ELSE 'Healthy Stock'
    END AS inventory_status

FROM zepto
ORDER BY availableQuantity ASC;