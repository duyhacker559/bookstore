#!/usr/bin/env python3
"""
Verify MySQL table rename from store_book* to store_product*
Run this script AFTER you've executed the SQL rename commands in MySQL

Usage:
    python verify_mysql_rename.py
"""
import mysql.connector
import sys
from datetime import datetime

# Credentials (from .env.example)
CREDENTIALS = [
    {"user": "store", "password": "987choithoi"},
    {"user": "root", "password": "987choithoi"},
    {"user": "store", "password": "store_password"},
    {"user": "root", "password": "root_password"},
]

def verify_rename():
    """Try to connect and verify table rename"""
    connection = None
    
    print(f"\n{'='*60}")
    print(f"MySQL Table Rename Verification")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")
    
    # Try connecting
    for cred in CREDENTIALS:
        try:
            print(f"[*] Attempting connection: {cred['user']}...")
            connection = mysql.connector.connect(
                host="127.0.0.1",
                port=3306,
                user=cred["user"],
                password=cred["password"],
                database="store"
            )
            print(f"[✓] Connected as {cred['user']}\n")
            break
        except mysql.connector.Error:
            continue
    
    if not connection:
        print("[✗] Could not connect to MySQL!")
        print("    Please ensure:")
        print("    - MySQL is running on port 3306")
        print("    - Database 'store' exists")
        print("    - Credentials are correct")
        return False
    
    try:
        cursor = connection.cursor()
        
        # Check old tables don't exist
        print("[*] Checking old table names (should be empty)...")
        old_tables = ['store_book', 'store_bookdetail', 'store_bookimage', 'store_book_categories_m2m']
        old_found = []
        
        for table in old_tables:
            cursor.execute(f"SELECT COUNT(*) FROM information_schema.TABLES WHERE TABLE_SCHEMA='store' AND TABLE_NAME='{table}'")
            if cursor.fetchone()[0] > 0:
                old_found.append(table)
        
        if old_found:
            print(f"[✗] Old tables still exist: {', '.join(old_found)}")
            print("    Please run the SQL rename commands first!")
            return False
        else:
            print("[✓] No old tables found\n")
        
        # Check new tables exist
        print("[*] Checking new table names...")
        new_tables = {
            'store_product': 'Products table',
            'store_productdetail': 'Product details table',
            'store_productimage': 'Product images table',
            'store_product_categories_m2m': 'Product-category relationships'
        }
        
        all_exist = True
        for table, desc in new_tables.items():
            cursor.execute(f"SELECT COUNT(*) FROM information_schema.TABLES WHERE TABLE_SCHEMA='store' AND TABLE_NAME='{table}'")
            exists = cursor.fetchone()[0] > 0
            
            if exists:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                print(f"[✓] {table}: {count:,} rows - {desc}")
            else:
                print(f"[✗] {table}: NOT FOUND")
                all_exist = False
        
        if not all_exist:
            print("\n[✗] Some new tables are missing!")
            return False
        
        print("\n" + "="*60)
        print("[✓] SUCCESS! All tables renamed correctly!")
        print("="*60)
        
        # Additional checks
        print("\n[*] Additional Verification:")
        
        # Check migration history
        cursor.execute("SELECT COUNT(*) FROM django_migrations WHERE app='store' AND name='0018_rename_book_table_to_product'")
        if cursor.fetchone()[0] > 0:
            print("[✓] Migration 0018 is recorded in django_migrations")
        
        # Check for any remaining old column references
        cursor.execute("""
            SELECT COLUMN_NAME FROM information_schema.COLUMNS 
            WHERE TABLE_SCHEMA='store' AND TABLE_NAME='store_product' 
            AND COLUMN_NAME LIKE '%book%'
        """)
        old_columns = cursor.fetchall()
        if old_columns:
            print(f"[!] Warning: Found old column names in store_product: {[c[0] for c in old_columns]}")
        else:
            print("[✓] No old 'book' column names found")
        
        return True
        
    except mysql.connector.Error as err:
        print(f"[✗] Error: {err}")
        return False
    finally:
        cursor.close()
        connection.close()

if __name__ == "__main__":
    success = verify_rename()
    sys.exit(0 if success else 1)
