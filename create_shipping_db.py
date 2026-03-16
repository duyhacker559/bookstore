"""Create shipping_service database in PostgreSQL."""
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# Connect to PostgreSQL server
conn = psycopg2.connect(
    host='localhost',
    port=5432,
    user='bookstore',
    password='bookstore_password',
    database='postgres'
)

conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
cursor = conn.cursor()

# Check if database exists
cursor.execute("SELECT 1 FROM pg_database WHERE datname='shipping_service'")
exists = cursor.fetchone()

if exists:
    print("✓ Database 'shipping_service' already exists")
else:
    # Create database
    cursor.execute("CREATE DATABASE shipping_service")
    print("✓ Database 'shipping_service' created successfully")

cursor.close()
conn.close()
