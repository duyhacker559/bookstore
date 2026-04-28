# MySQL Table Rename - Complete Resource Package

## 📦 All Files Created

### Quick Reference
| File | Type | Purpose |
|------|------|---------|
| [README_MYSQL_RENAME.md](README_MYSQL_RENAME.md) | MD | Start here - Quick start guide |
| [MYSQL_RENAME_ACTION_PLAN.md](MYSQL_RENAME_ACTION_PLAN.md) | MD | Executive summary with complete action plan |
| [MANUAL_MYSQL_RENAME_GUIDE.md](MANUAL_MYSQL_RENAME_GUIDE.md) | MD | Detailed step-by-step instructions |
| [MYSQL_TABLE_RENAME.sql](MYSQL_TABLE_RENAME.sql) | SQL | Copy-paste ready SQL commands |
| [verify_mysql_rename.py](verify_mysql_rename.py) | Python | Verification script (run after rename) |
| [display_sql_commands.py](display_sql_commands.py) | Python | Display SQL in terminal |

---

## 🎯 Getting Started (3 Steps)

### Step 1: Understand the Problem
Read: [README_MYSQL_RENAME.md](README_MYSQL_RENAME.md)
- What needs to change
- Why it matters
- Current status

### Step 2: Execute the Rename
Choose ONE method:

**Option A: Copy-Paste Method (Fastest)**
1. Open [MYSQL_TABLE_RENAME.sql](MYSQL_TABLE_RENAME.sql)
2. Copy all content
3. Paste into your MySQL client
4. Execute all at once

**Option B: Step-by-Step Method (Safest)**
1. Read [MANUAL_MYSQL_RENAME_GUIDE.md](MANUAL_MYSQL_RENAME_GUIDE.md)
2. Execute each command one at a time
3. Verify each step

**Option C: Terminal Display Method**
```bash
python display_sql_commands.py
```
Then copy commands from terminal output

### Step 3: Verify Success
```bash
python verify_mysql_rename.py
```

Expected output:
```
[✓] Connected as store
[✓] No old tables found
[✓] store_product: 137 rows - Products table
[✓] SUCCESS! All tables renamed correctly!
```

---

## 📋 SQL Rename Commands

```sql
USE store;
ALTER TABLE store_book RENAME TO store_product;
ALTER TABLE store_book_categories_m2m RENAME TO store_product_categories_m2m;
ALTER TABLE store_bookdetail RENAME TO store_productdetail;
ALTER TABLE store_bookimage RENAME TO store_productimage;
```

---

## ✅ Verification Steps

After rename, verify with:

```bash
# Python verification
python verify_mysql_rename.py

# Django verification
python manage.py shell -c "from store.models import Book; print(f'Products: {Book.objects.count()}'); print(f'DB Table: {Book._meta.db_table}')"
```

---

## 📞 Troubleshooting

### Common Issues:
- **Access Denied**: Check MySQL is running and credentials are correct
- **Table Not Found**: It's already renamed - continue with next table
- **Foreign Key Error**: See [MANUAL_MYSQL_RENAME_GUIDE.md](MANUAL_MYSQL_RENAME_GUIDE.md) troubleshooting section

### Support Resources:
- [MANUAL_MYSQL_RENAME_GUIDE.md](MANUAL_MYSQL_RENAME_GUIDE.md) - Complete troubleshooting
- [MYSQL_RENAME_ACTION_PLAN.md](MYSQL_RENAME_ACTION_PLAN.md) - Detailed reference

---

## 🔄 Before & After

### Before (Current State)
```
MySQL Tables:
├── store_book (137 records)
├── store_bookdetail
├── store_bookimage
└── store_book_categories_m2m

Django ORM expects:
├── store_product ❌ NOT FOUND
├── store_productdetail ❌ NOT FOUND
├── store_productimage ❌ NOT FOUND
└── store_product_categories_m2m ❌ NOT FOUND

Result: "no such table: store_product" errors
```

### After (Target State)
```
MySQL Tables:
├── store_product (137 records) ✅
├── store_productdetail ✅
├── store_productimage ✅
└── store_product_categories_m2m ✅

Django ORM:
├── Finds store_product ✅
├── Finds store_productdetail ✅
├── Finds store_productimage ✅
└── Finds store_product_categories_m2m ✅

Result: Django can access all tables successfully ✅
```

---

## 🚀 Next Steps

1. **Execute SQL** - Use [MYSQL_TABLE_RENAME.sql](MYSQL_TABLE_RENAME.sql)
2. **Verify Success** - Run `python verify_mysql_rename.py`
3. **Test Django** - Run `python manage.py shell -c "from store.models import Book; Book.objects.count()"`
4. **Deploy** - Apply same renames to production MySQL

---

## 📚 Additional Resources

For complete system context:
- [PRODUCT_CATEGORY_ARCHITECTURE.md](PRODUCT_CATEGORY_ARCHITECTURE.md) - Full technical documentation
- [README.md](README.md) - Project overview
- Migration files: [store/migrations/0018_rename_book_table_to_product.py](store/migrations/0018_rename_book_table_to_product.py)

---

## ⏱️ Expected Timeline

| Step | Time | Notes |
|------|------|-------|
| Understand problem | 2 min | Read README_MYSQL_RENAME.md |
| Open MySQL client | 1 min | Use your existing GUI client |
| Execute SQL | 1 min | Copy & paste 4 commands |
| Run verification | 2 min | python verify_mysql_rename.py |
| Test Django | 1 min | Confirm table access |
| **Total** | **~7 minutes** | One-time setup |

---

**Status:** Ready for execution  
**Complexity:** Low (copy-paste SQL)  
**Risk:** Minimal (tables not being deleted, only renamed)  

Start with: [README_MYSQL_RENAME.md](README_MYSQL_RENAME.md)
