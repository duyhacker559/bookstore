# MySQL Table Rename - Manual Instructions

## Current Situation
- User's local MySQL on port 3306 has old table names: `store_book`, `store_bookdetail`, `store_bookimage`, `store_book_categories_m2m`
- Django ORM is configured to use new table names: `store_product`, `store_productdetail`, `store_productimage`, `store_product_categories_m2m`
- SQLite database (db.sqlite3) has already been migrated successfully
- MySQL database schema needs to be renamed to match Django ORM mapping

## Step-by-Step Instructions

### 1. Open MySQL Client
Open your MySQL GUI client (MySQL Workbench, DBeaver, HeidiSQL, or command line)

### 2. Select the `store` Database
```sql
USE store;
```

### 3. Rename the Tables
Copy and execute each command one by one. If a table doesn't exist, it's already renamed:

#### Rename Main Table
```sql
ALTER TABLE store_book RENAME TO store_product;
```

#### Rename Categories Mapping Table
```sql
ALTER TABLE store_book_categories_m2m RENAME TO store_product_categories_m2m;
```

#### Rename Detail Table
```sql
ALTER TABLE store_bookdetail RENAME TO store_productdetail;
```

#### Rename Image Table
```sql
ALTER TABLE store_bookimage RENAME TO store_productimage;
```

### 4. Verify the Changes
After renaming, verify the tables were successfully renamed:

```sql
-- Check new table names exist
SHOW TABLES LIKE 'store_product%';

-- Check old table names are gone (should return empty)
SHOW TABLES LIKE 'store_book%';

-- Count records in renamed tables
SELECT 'store_product' as table_name, COUNT(*) as row_count FROM store_product
UNION
SELECT 'store_productdetail', COUNT(*) FROM store_productdetail
UNION
SELECT 'store_productimage', COUNT(*) FROM store_productimage
UNION
SELECT 'store_product_categories_m2m', COUNT(*) FROM store_product_categories_m2m;
```

### 5. Verify in Django
Once SQL rename is complete, test Django can access the tables:

```bash
# Test ORM mapping
python manage.py shell -c "from store.models import Book; print(f'Total products: {Book.objects.count()}'); print(f'DB table: {Book._meta.db_table}')"

# Expected output:
# Total products: 137
# DB table: store_product
```

## Complete SQL Script (Copy All at Once)

If your MySQL client allows multi-statement execution, copy all at once:

```sql
USE store;
ALTER TABLE store_book RENAME TO store_product;
ALTER TABLE store_book_categories_m2m RENAME TO store_product_categories_m2m;
ALTER TABLE store_bookdetail RENAME TO store_productdetail;
ALTER TABLE store_bookimage RENAME TO store_productimage;

-- Verify
SHOW TABLES LIKE 'store_product%';
SELECT COUNT(*) as products FROM store_product;
SELECT COUNT(*) as details FROM store_productdetail;
```

## Troubleshooting

### Table doesn't exist error
- **Error**: `Error 1051: Unknown table 'store_book'`
- **Cause**: Table already renamed or doesn't exist
- **Action**: Skip that command and continue with next one

### Access denied error
- **Error**: `Error 1045: Access denied for user`
- **Cause**: Wrong MySQL credentials
- **Action**: Check your MySQL username and password in your client

### Foreign key constraint error
- **Error**: `Error 1025: Error on rename`
- **Cause**: Foreign key constraints or table relationships
- **Action**: Check foreign keys with `SHOW CREATE TABLE store_book;` and handle constraints

## After Rename Checklist
- [ ] All 4 tables renamed successfully
- [ ] Verification query shows correct row counts
- [ ] Django ORM test shows `store_product` as db_table
- [ ] No error messages during rename

---

**Questions?** Check that:
1. You're connected to the correct database (`USE store;`)
2. You're using the correct MySQL credentials
3. No other processes are locking the tables
