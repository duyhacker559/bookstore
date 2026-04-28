#!/usr/bin/env python3
"""
Automatic MySQL Table Rename
Uses credentials from .env.example
"""
import mysql.connector
import sys

# Credentials from .env.example
MYSQL_PASSWORD = "987choithoi"
MYSQL_USER = "root"
MYSQL_HOST = "127.0.0.1"
MYSQL_PORT = 3306
MYSQL_DATABASE = "store"

# SQL commands to rename tables
rename_commands = [
    "ALTER TABLE store_book RENAME TO store_product;",
    "ALTER TABLE store_book_categories_m2m RENAME TO store_product_categories_m2m;",
    "ALTER TABLE store_bookdetail RENAME TO store_productdetail;",
    "ALTER TABLE store_bookimage RENAME TO store_productimage;",
]

print("\n" + "="*70)
print("MySQL Table Rename - Automatic Execution")
print("="*70 + "\n")

try:
    print(f"[*] Connecting to MySQL at {MYSQL_HOST}:{MYSQL_PORT}...")
    connection = mysql.connector.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DATABASE
    )
    print(f"[✓] Successfully connected as {MYSQL_USER}@{MYSQL_HOST}\n")
    
    cursor = connection.cursor()
    
    print("[*] Executing table rename commands...")
    for i, cmd in enumerate(rename_commands, 1):
        try:
            cursor.execute(cmd)
            table_name = cmd.split()[2]
            new_name = cmd.split()[-2]
            print(f"[✓] {i}. Renamed: {table_name} → {new_name}")
        except mysql.connector.Error as err:
            if err.errno == 1146:  # Table doesn't exist
                print(f"[!] {i}. Table already renamed or doesn't exist")
            else:
                print(f"[✗] {i}. Error: {err}")
                raise
    
    connection.commit()
    print("\n[✓] All rename commands executed successfully!\n")
    
    # Verify
    print("[*] Verifying rename...")
    verification_queries = [
        ("SELECT COUNT(*) FROM store_product;", "store_product"),
        ("SELECT COUNT(*) FROM store_productdetail;", "store_productdetail"),
        ("SELECT COUNT(*) FROM store_productimage;", "store_productimage"),
        ("SELECT COUNT(*) FROM store_product_categories_m2m;", "store_product_categories_m2m"),
    ]
    
    for query, table_name in verification_queries:
        cursor.execute(query)
        count = cursor.fetchone()[0]
        print(f"[✓] {table_name}: {count:,} rows")
    
    print("\n" + "="*70)
    print("[✓] SUCCESS! All tables renamed from store_book* to store_product*")
    print("="*70 + "\n")
    
except mysql.connector.Error as err:
    print(f"\n[✗] MySQL Error: {err}")
    sys.exit(1)
except Exception as err:
    print(f"\n[✗] Error: {err}")
    sys.exit(1)
finally:
    if 'cursor' in locals():
        cursor.close()
    if 'connection' in locals():
        connection.close()
