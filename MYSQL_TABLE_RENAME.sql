-- ==============================================================
-- MySQL Table Rename Script
-- Rename store_book* tables to store_product*
-- ==============================================================
-- Execute these commands in your MySQL client to rename the tables
-- ==============================================================

-- Rename main book table to product table
ALTER TABLE store_book RENAME TO store_product;

-- Rename categories many-to-many table
ALTER TABLE store_book_categories_m2m RENAME TO store_product_categories_m2m;

-- Rename book detail table
ALTER TABLE store_bookdetail RENAME TO store_productdetail;

-- Rename book image table
ALTER TABLE store_bookimage RENAME TO store_productimage;

-- Verify the rename was successful
SHOW TABLES LIKE 'store_product%';
SHOW TABLES LIKE 'store_book%';  -- Should return empty result

-- ==============================================================
-- Check data integrity
-- ==============================================================
SELECT COUNT(*) as total_products FROM store_product;
SELECT COUNT(*) as product_details FROM store_productdetail;
SELECT COUNT(*) as product_images FROM store_productimage;
SELECT COUNT(*) as category_mappings FROM store_product_categories_m2m;
