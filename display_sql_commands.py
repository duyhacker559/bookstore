#!/usr/bin/env python3
"""
Display MySQL rename SQL commands for easy copy-paste
"""

sql_commands = [
    ("Main products table", "ALTER TABLE store_book RENAME TO store_product;"),
    ("Product categories mapping", "ALTER TABLE store_book_categories_m2m RENAME TO store_product_categories_m2m;"),
    ("Product details table", "ALTER TABLE store_bookdetail RENAME TO store_productdetail;"),
    ("Product images table", "ALTER TABLE store_bookimage RENAME TO store_productimage;"),
]

verify_commands = [
    ("Show new tables", "SHOW TABLES LIKE 'store_product%';"),
    ("Verify old tables removed", "SHOW TABLES LIKE 'store_book%';"),
    ("Count records", """SELECT 'store_product' as table_name, COUNT(*) as row_count FROM store_product
UNION
SELECT 'store_productdetail', COUNT(*) FROM store_productdetail
UNION
SELECT 'store_productimage', COUNT(*) FROM store_productimage
UNION
SELECT 'store_product_categories_m2m', COUNT(*) FROM store_product_categories_m2m;"""),
]

print("\n" + "="*70)
print("MySQL TABLE RENAME COMMANDS - Copy & Paste into MySQL Client")
print("="*70 + "\n")

print("STEP 1: Select the store database")
print("-" * 70)
print("USE store;\n")

print("STEP 2: Execute rename commands (one at a time or all together)")
print("-" * 70)
for desc, cmd in sql_commands:
    print(f"{desc}:")
    print(f"  {cmd}")
    print()

print("STEP 3: Verify the rename was successful")
print("-" * 70)
for desc, cmd in verify_commands:
    print(f"{desc}:")
    for line in cmd.split('\n'):
        print(f"  {line}")
    print()

print("="*70)
print("ALL COMMANDS AT ONCE (for multi-statement MySQL clients):")
print("="*70 + "\n")
print("USE store;")
for _, cmd in sql_commands:
    print(cmd)
print("\n-- Verification queries:")
for _, cmd in verify_commands:
    print(f"-- {cmd}")
print("\n" + "="*70)

try:
    import pyperclip
    print("\nCopying all rename commands to clipboard...")
    all_commands = "USE store;\n" + "\n".join([cmd for _, cmd in sql_commands])
    pyperclip.copy(all_commands)
    print("[✓] Commands copied to clipboard! Paste them into your MySQL client.")
except ImportError:
    print("\n(Note: Install 'pyperclip' for automatic clipboard copy)")
    print("    pip install pyperclip")
