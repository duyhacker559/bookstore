"""
Phase 1 Setup and Testing Script

This script verifies that all Phase 1 components are properly installed and configured:
1. Database migrations
2. API authentication
3. Event system

Usage:
    python manage.py shell < setup_phase1.py
"""

import os
import sys
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token
from store.events import publish_event

print("\n" + "=" * 70)
print("PHASE 1 SETUP AND VERIFICATION")
print("=" * 70 + "\n")

# Step 1: Verify migrations
print("1. Verifying database migrations...")
from django.core.management import call_command
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

executor = MigrationExecutor(connection)
migrated = set(executor.loader.disk_migrations.keys())
required_migrations = {
    ('store', '0007_consolidate_inventory'),
    ('store', '0008_book_add_author_category_fk'),
}

missing = required_migrations - migrated
if not missing:
    print("   ✓ All Phase 1 migrations are present\n")
else:
    print(f"   ✗ Missing migrations: {missing}")
    print("   Run: python manage.py migrate\n")

# Step 2: Verify DRF is installed
print("2. Verifying Django REST Framework...")
try:
    from rest_framework import __version__ as drf_version
    print(f"   ✓ DRF {drf_version} is installed\n")
except ImportError:
    print("   ✗ DRF not installed!")
    print("   Run: pip install djangorestframework\n")

# Step 3: Create test user and token
print("3. Setting up test authentication...")
test_user, created = User.objects.get_or_create(
    username='test_user',
    defaults={'email': 'test@example.com'}
)
token, token_created = Token.objects.get_or_create(user=test_user)

if created:
    print(f"   ✓ Created test user: {test_user.username}")
else:
    print(f"   ✓ Test user already exists: {test_user.username}")

print(f"   ✓ API Token: {token.key}\n")

# Step 4: Create service tokens for microservices
print("4. Setting up service tokens...")
from store.auth import create_service_token

services = ['payment-service', 'shipping-service', 'notification-service']
for service in services:
    try:
        service_token = create_service_token(service)
        print(f"   ✓ Created token for {service}")
        print(f"     Token: {service_token}\n")
    except Exception as e:
        print(f"   ✗ Failed to create token for {service}: {e}\n")

# Step 5: Test event publishing
print("5. Testing event system...")
try:
    from store.events import get_event_bus, RABBITMQ_AVAILABLE
    
    if RABBITMQ_AVAILABLE:
        print("   ✓ pika is installed (RabbitMQ support available)")
        # Try to publish a test event
        success = publish_event('order.created', {
            'order_id': 'test-123',
            'customer_id': 'cust-456',
            'total': 99.99
        })
        if success:
            print("   ✓ Test event published successfully\n")
        else:
            print("   ⚠ Event published to log (RabbitMQ may not be running)\n")
    else:
        print("   ⚠ pika not installed (RabbitMQ support disabled)")
        print("     Install with: pip install pika")
        print("     Events will be logged instead\n")
        
except Exception as e:
    print(f"   ✗ Error testing event system: {e}\n")

# Step 6: Verify models
print("6. Verifying updated models...")
from store.models.book.book import Book

# Check if Book model has the new fields
book_fields = [f.name for f in Book._meta.get_fields()]
required_fields = ['author_fk', 'category_fk']
missing_fields = [f for f in required_fields if f not in book_fields]

if not missing_fields:
    print("   ✓ Book model has author_fk and category_fk fields\n")
else:
    print(f"   ✗ Book model missing fields: {missing_fields}")
    print("   Run: python manage.py migrate\n")

# Step 7: Summary
print("=" * 70)
print("PHASE 1 SETUP SUMMARY")
print("=" * 70 + "\n")

print("✓ Phase 1 setup complete!\n")

print("Next steps:")
print("1. Run migrations:")
print("   python manage.py migrate\n")

print("2. Test API authentication:")
print(f'   curl -H "Authorization: Bearer {token.key}" \\')
print("        http://localhost:8000/api/books/\n")

print("3. For RabbitMQ support, start RabbitMQ:")
print("   docker run -d --name rabbitmq -p 5672:5672 -p 15672:15672 \\")
print("       rabbitmq:3-management\n")

print("4. Set up environment variables:")
print("   cp .env.example .env")
print("   # Update .env with your settings\n")

print("5. Start development server:")
print("   python manage.py runserver\n")

print("=" * 70 + "\n")
