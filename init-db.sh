#!/bin/bash
# Database initialization script for Bookstore microservices
# This script creates the three microservice databases if they don't exist

set -e

echo "Waiting for PostgreSQL to be ready..."
until pg_isready -U bookstore -d postgres; do
  sleep 1
done

echo "PostgreSQL is ready. Initializing databases..."

# Create payment_service database
psql -U bookstore -d postgres -tc "SELECT 1 FROM pg_database WHERE datname = 'payment_service'" | grep -q 1 || \
  psql -U bookstore -d postgres -c "CREATE DATABASE payment_service;"

# Create shipping_service database
psql -U bookstore -d postgres -tc "SELECT 1 FROM pg_database WHERE datname = 'shipping_service'" | grep -q 1 || \
  psql -U bookstore -d postgres -c "CREATE DATABASE shipping_service;"

# Create notification_service database
psql -U bookstore -d postgres -tc "SELECT 1 FROM pg_database WHERE datname = 'notification_service'" | grep -q 1 || \
  psql -U bookstore -d postgres -c "CREATE DATABASE notification_service;"

echo "✓ All databases initialized successfully!"
echo "  - bookstore (main)"
echo "  - payment_service"
echo "  - shipping_service"
echo "  - notification_service"
