-- ============================================
-- DATA CLEANING
-- ============================================

-- Products with invalid pricing

SELECT *
FROM zepto
WHERE mrp = 0
OR discountedSellingPrice = 0;


-- Remove products with invalid MRP

DELETE FROM zepto
WHERE mrp = 0;


-- Convert paise to rupees

UPDATE zepto
SET 
    mrp = mrp / 100.0,
    discountedSellingPrice = discountedSellingPrice / 100.0;


-- Verify updated pricing

SELECT 
    name,
    mrp,
    discountedSellingPrice
FROM zepto
LIMIT 10;


-- Remove negative stock quantities if any

DELETE FROM zepto
WHERE availableQuantity < 0;


-- Final cleaned dataset count

SELECT COUNT(*) AS cleaned_records
FROM zepto;