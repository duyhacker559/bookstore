# 🎯 MySQL Table Rename - START HERE

## Your Task: Rename 4 Tables in MySQL (5 minutes)

Your Django app expects table names like `store_product` but your MySQL database has old names like `store_book`. 

**This must be fixed.**

---

## ✅ Quick Start (Choose One)

### 🚀 Fastest Way (Copy-Paste)
1. Open your MySQL GUI client (Workbench, DBeaver, HeidiSQL, etc.)
2. Open file: [MYSQL_TABLE_RENAME.sql](MYSQL_TABLE_RENAME.sql)
3. Copy all content → Paste into MySQL client → Execute
4. Run verification:
   ```bash
   python verify_mysql_rename.py
   ```
5. Done! ✅

### 📖 Step-by-Step Way
1. Read: [MANUAL_MYSQL_RENAME_GUIDE.md](MANUAL_MYSQL_RENAME_GUIDE.md)
2. Follow instructions step-by-step
3. Run verification:
   ```bash
   python verify_mysql_rename.py
   ```
4. Done! ✅

### 📚 Full Details
Start here: [README_MYSQL_RENAME.md](README_MYSQL_RENAME.md)

---

## 📁 What You'll Need

| File | Purpose |
|------|---------|
| [MYSQL_TABLE_RENAME.sql](MYSQL_TABLE_RENAME.sql) | **← Copy this SQL** |
| [verify_mysql_rename.py](verify_mysql_rename.py) | **← Run after rename** |
| [MANUAL_MYSQL_RENAME_GUIDE.md](MANUAL_MYSQL_RENAME_GUIDE.md) | Step-by-step guide |
| [README_MYSQL_RENAME.md](README_MYSQL_RENAME.md) | Quick reference |
| [MYSQL_RENAME_RESOURCES.md](MYSQL_RENAME_RESOURCES.md) | Complete package overview |

---

## 📋 The SQL (Just 4 Commands)

```sql
USE store;
ALTER TABLE store_book RENAME TO store_product;
ALTER TABLE store_book_categories_m2m RENAME TO store_product_categories_m2m;
ALTER TABLE store_bookdetail RENAME TO store_productdetail;
ALTER TABLE store_bookimage RENAME TO store_productimage;
```

---

## ⏱️ Timeline
- **Step 1 (Read this):** 30 seconds
- **Step 2 (Open MySQL):** 1 minute
- **Step 3 (Execute SQL):** 1 minute
- **Step 4 (Verify):** 2 minutes
- **Total:** ~5 minutes

---

## 🎯 After You Complete This

1. ✅ MySQL table names match Django ORM
2. ✅ No more "table not found" errors
3. ✅ Can proceed with deployment
4. ✅ System is ready for production

---

## 🆘 Issues?

**Can't connect to MySQL?**
→ See [MANUAL_MYSQL_RENAME_GUIDE.md](MANUAL_MYSQL_RENAME_GUIDE.md) troubleshooting

**Verification script fails?**
→ Check MySQL is running on port 3306

**What if a table already exists?**
→ That's OK - it means it was already renamed

---

## 📌 Remember
- ✅ Safe: Only renaming, not deleting
- ✅ Reversible: Can rename back if needed
- ✅ Required: Django won't work without this
- ✅ Quick: Takes 5 minutes

---

## 🚀 Ready?

### Option 1: Copy-Paste (Fastest)
→ Open [MYSQL_TABLE_RENAME.sql](MYSQL_TABLE_RENAME.sql) and copy the SQL

### Option 2: Step-by-Step (Safest)  
→ Read [MANUAL_MYSQL_RENAME_GUIDE.md](MANUAL_MYSQL_RENAME_GUIDE.md)

### Option 3: Get All Details
→ Read [README_MYSQL_RENAME.md](README_MYSQL_RENAME.md)

---

**Next Action:** Open [MYSQL_TABLE_RENAME.sql](MYSQL_TABLE_RENAME.sql) →  Copy → Paste into MySQL → Execute → Run `python verify_mysql_rename.py`

That's it! 🎉
