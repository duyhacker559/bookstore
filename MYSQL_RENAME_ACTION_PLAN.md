# MySQL Table Rename - Complete Status & Action Plan

## 📋 Executive Summary

**Problem:** Your local MySQL database contains old table names (`store_book*`) but Django ORM expects new names (`store_product*`).

**Status:** 
- ✅ SQLite: Fully migrated (137 products confirmed)
- ✅ Django code: All configured for new names
- ✅ Migrations created: 0018_rename_book_table_to_product.py ready
- ⏳ MySQL schema: Awaiting manual table rename

**Your Action:** Execute 4 SQL ALTER TABLE commands in your MySQL client (5 minutes)

---

## 📁 Resources Created for You

### 1. **MYSQL_TABLE_RENAME.sql** 
SQL commands ready to copy-paste into MySQL GUI
- Simplest option for quick execution
- Just copy all and paste into your client

### 2. **MANUAL_MYSQL_RENAME_GUIDE.md**
Detailed step-by-step guide with screenshots placeholders
- For those who prefer detailed instructions
- Includes troubleshooting section
- Shows how to verify in Django

### 3. **verify_mysql_rename.py**
Python script to verify rename success
```bash
python verify_mysql_rename.py
```
- Checks if rename was successful
- Validates all 4 tables exist
- Shows row counts
- Confirms no old tables remain

### 4. **display_sql_commands.py**
Display SQL commands in terminal with formatting
```bash
python display_sql_commands.py
```
- Pretty-prints all SQL commands
- Shows 3-step process
- Includes verification queries

---

## 🚀 Quick Start (Choose One Method)

### Method 1: Manual (Recommended for Beginners)
1. Read [MANUAL_MYSQL_RENAME_GUIDE.md](MANUAL_MYSQL_RENAME_GUIDE.md)
2. Open your MySQL GUI client
3. Copy commands one-by-one and execute
4. Run `python verify_mysql_rename.py`

### Method 2: Copy-Paste All at Once (Fastest)
1. Open [MYSQL_TABLE_RENAME.sql](MYSQL_TABLE_RENAME.sql)
2. Copy all content
3. Paste into MySQL client
4. Execute
5. Run `python verify_mysql_rename.py`

### Method 3: Display in Terminal
1. Run `python display_sql_commands.py`
2. Copy commands from terminal
3. Paste into MySQL client
4. Execute
5. Run `python verify_mysql_rename.py`

---

## 📊 What Gets Changed

| Component | From | To | Status |
|-----------|------|-----|--------|
| Main table | `store_book` | `store_product` | ⏳ Pending |
| Details table | `store_bookdetail` | `store_productdetail` | ⏳ Pending |
| Images table | `store_bookimage` | `store_productimage` | ⏳ Pending |
| M2M table | `store_book_categories_m2m` | `store_product_categories_m2m` | ⏳ Pending |
| Total records | 137 products | 137 products | ✅ Verified |

---

## 🔍 Database State

### SQLite (db.sqlite3)
```
✅ All tables renamed
✅ 137 products migrated with attributes JSONField
✅ All relationships updated
✅ Data integrity verified
```

### MySQL (Local on port 3306)
```
⏳ Table structure: Old names (store_book) still in schema
⚠️  Django ORM: Configured for new names (store_product)
⚠️  Data: 137 products waiting for table rename
```

### Docker MySQL (docker-compose)
```
⚠️  Will need to run migrations after user renames local MySQL
🔧 Credentials: store/store_password (from docker-compose.yml)
```

---

## ✅ Verification Checklist

After running SQL commands, verify with:

```bash
# Check Python script success
python verify_mysql_rename.py
```

Expected output:
```
[✓] Connected as store
[✓] No old tables found
[✓] store_product: 137 rows - Products table
[✓] store_productdetail: [count] rows - Product details table
[✓] store_productimage: [count] rows - Product images table
[✓] store_product_categories_m2m: [count] rows - Product-category relationships
[✓] SUCCESS! All tables renamed correctly!
```

Then test Django:
```bash
python manage.py shell -c "from store.models import Book; print(f'Products: {Book.objects.count()}'); print(f'Table: {Book._meta.db_table}')"
```

Expected output:
```
Products: 137
Table: store_product
```

---

## 🛠️ Troubleshooting

### "Access Denied" Error
**Problem:** Cannot connect to MySQL
**Solution:** 
- Check MySQL is running: `Get-Process mysqld`
- Verify port 3306 is available
- Update credentials in scripts if different
- Try connecting manually with your GUI client first

### "Table doesn't exist" During Rename
**Problem:** `Error 1051: Unknown table 'store_book'`
**Reason:** Table already renamed or doesn't exist
**Solution:** Continue with next rename command - it's OK if table doesn't exist

### Foreign Key Constraint Error
**Problem:** `Error 1025: Error on rename`
**Solution:** 
1. Check constraints: `SHOW CREATE TABLE store_book;`
2. Temporarily disable checks: `SET FOREIGN_KEY_CHECKS=0;`
3. Run renames
4. Re-enable: `SET FOREIGN_KEY_CHECKS=1;`

### Verification Script Won't Connect
**Problem:** `[✗] Could not connect to MySQL!`
**Solutions:**
- Make sure MySQL is running
- Edit `verify_mysql_rename.py` to add your actual credentials
- Test with: `mysql -uroot -p -h 127.0.0.1`

---

## 📞 Support

**Files Provided:**
- [README_MYSQL_RENAME.md](README_MYSQL_RENAME.md) - Quick start overview
- [MYSQL_TABLE_RENAME.sql](MYSQL_TABLE_RENAME.sql) - Ready-to-copy SQL
- [MANUAL_MYSQL_RENAME_GUIDE.md](MANUAL_MYSQL_RENAME_GUIDE.md) - Detailed steps
- [verify_mysql_rename.py](verify_mysql_rename.py) - Verification script
- [display_sql_commands.py](display_sql_commands.py) - Terminal display

**Next Steps After Rename:**
1. ✅ Complete: Run `python verify_mysql_rename.py`
2. ✅ Confirm: Django can access new table names
3. 🔄 Deploy: Update production MySQL with same renames
4. 📚 Reference: See [PRODUCT_CATEGORY_ARCHITECTURE.md](PRODUCT_CATEGORY_ARCHITECTURE.md) for full system details

---

**Current Time:** Ready for execution
**Estimated Duration:** 5-10 minutes
**Complexity:** Low (copy-paste SQL commands)

Next action: Open your MySQL client and execute the SQL commands from MYSQL_TABLE_RENAME.sql
