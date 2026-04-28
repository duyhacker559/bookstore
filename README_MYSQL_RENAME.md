# MySQL Table Rename - Quick Start Guide

## Problem
Your local MySQL database contains old table names (`store_book`, `store_bookdetail`, etc.) but Django ORM is configured to use new table names (`store_product`, `store_productdetail`, etc.).

## Solution
You need to rename 4 tables in your MySQL database to match Django's ORM mapping.

## Quick Start (2 Steps)

### Step 1: Execute SQL Rename Commands
Open your MySQL GUI client and run the SQL commands from one of these files:
- **Easiest**: Use [MYSQL_TABLE_RENAME.sql](MYSQL_TABLE_RENAME.sql) - copy everything and paste into your client
- **With Details**: Read [MANUAL_MYSQL_RENAME_GUIDE.md](MANUAL_MYSQL_RENAME_GUIDE.md) for step-by-step instructions

### Step 2: Verify Success
After running SQL commands, execute this Python script to verify:
```bash
python verify_mysql_rename.py
```

## Files Provided

| File | Purpose |
|------|---------|
| [MYSQL_TABLE_RENAME.sql](MYSQL_TABLE_RENAME.sql) | Ready-to-copy SQL commands for table rename |
| [MANUAL_MYSQL_RENAME_GUIDE.md](MANUAL_MYSQL_RENAME_GUIDE.md) | Detailed step-by-step guide with troubleshooting |
| [verify_mysql_rename.py](verify_mysql_rename.py) | Verification script to confirm rename success |

## What Tables Get Renamed

| Old Name | New Name |
|----------|----------|
| `store_book` | `store_product` |
| `store_bookdetail` | `store_productdetail` |
| `store_bookimage` | `store_productimage` |
| `store_book_categories_m2m` | `store_product_categories_m2m` |

## Background
- **SQLite** (db.sqlite3): ✓ Already renamed successfully  
- **MySQL** (local): ⚠ Pending rename
- **Django ORM**: ✓ Already configured to use new names
- **Migrations**: ✓ Already created (0018_rename_book_table_to_product.py)

## Why This Matters
Django's ORM is mapped to the new table names. If MySQL still has old table names, there will be a mismatch between what Django expects and what exists in the database. This causes "table not found" errors.

## Troubleshooting

### "Access Denied" when running verify script
- Make sure MySQL is running
- Update the credentials in `verify_mysql_rename.py` if your MySQL password is different

### "Table already exists" error during rename
- The table might already be renamed
- Run verification script to check current state

### Need manual SQL execution?
See [MANUAL_MYSQL_RENAME_GUIDE.md](MANUAL_MYSQL_RENAME_GUIDE.md) for complete instructions and troubleshooting

---

**Questions about the migration?** Check [PRODUCT_CATEGORY_ARCHITECTURE.md](PRODUCT_CATEGORY_ARCHITECTURE.md) for full technical details about the product refactoring.
