"""Test script to publish events to RabbitMQ and verify notification service consumption."""

import json
import pika
import time

def publish_order_paid_event():
    """Publish an order.paid event to test notification service."""
    credentials = pika.PlainCredentials('guest', 'guest')
    params = pika.ConnectionParameters(
        host='localhost',
        port=5672,
        credentials=credentials
    )
    
    connection = pika.BlockingConnection(params)
    channel = connection.channel()
    
    # Declare exchange
    channel.exchange_declare(
        exchange='bookstore.events',
        exchange_type='topic',
        durable=True
    )
    
    # Create test event
    test_event = {
        "event_type": "order.paid",
        "data": {
            "order_id": "TEST-001",
            "amount": 99.99,
            "customer_email": "test@example.com"
        }
    }
    
    # Publish event
    channel.basic_publish(
        exchange='bookstore.events',
        routing_key='order.paid',
        body=json.dumps(test_event),
        properties=pika.BasicProperties(
            delivery_mode=2,  # make message persistent
        )
    )
    
    print(f"✓ Published order.paid event for order TEST-001")
    connection.close()


def publish_shipment_created_event():
    """Publish a shipment.created event to test notification service."""
    credentials = pika.PlainCredentials('guest', 'guest')
    params = pika.ConnectionParameters(
        host='localhost',
        port=5672,
        credentials=credentials
    )
    
    connection = pika.BlockingConnection(params)
    channel = connection.channel()
    
    channel.exchange_declare(
        exchange='bookstore.events',
        exchange_type='topic',
        durable=True
    )
    
    test_event = {
        "event_type": "shipment.created",
        "data": {
            "order_id": "TEST-002",
            "method_name": "Express Shipping",
            "method_code": "express"
        }
    }
    
    channel.basic_publish(
        exchange='bookstore.events',
        routing_key='shipment.created',
        body=json.dumps(test_event),
        properties=pika.BasicProperties(
            delivery_mode=2,
        )
    )
    
    print(f"✓ Published shipment.created event for order TEST-002")
    connection.close()


def publish_shipment_updated_event():
    """Publish a shipment.updated event to test notification service."""
    credentials = pika.PlainCredentials('guest', 'guest')
    params = pika.ConnectionParameters(
        host='localhost',
        port=5672,
        credentials=credentials
    )
    
    connection = pika.BlockingConnection(params)
    channel = connection.channel()
    
    channel.exchange_declare(
        exchange='bookstore.events',
        exchange_type='topic',
        durable=True
    )
    
    test_event = {
        "event_type": "shipment.updated",
        "data": {
            "order_id": "TEST-003",
            "previous_status": "processing",
            "current_status": "shipped"
        }
    }
    
    channel.basic_publish(
        exchange='bookstore.events',
        routing_key='shipment.updated',
        body=json.dumps(test_event),
        properties=pika.BasicProperties(
            delivery_mode=2,
        )
    )
    
    print(f"✓ Published shipment.updated event for order TEST-003")
    connection.close()


if __name__ == "__main__":
    print("\n=== Testing Notification Service Event Consumption ===\n")
    
    try:
        print("Publishing test events...")
        publish_order_paid_event()
        time.sleep(1)
        
        publish_shipment_created_event()
        time.sleep(1)
        
        publish_shipment_updated_event()
        time.sleep(1)
        
        print("\n✓ All events published successfully!")
        print("\nCheck notification service logs with:")
        print("  docker compose logs notification-service --tail=30")
        print("\nVerify notifications in database with:")
        print("  docker compose exec postgres psql -U bookstore -d notification_service -c 'SELECT id, notification_type, recipient, event_type, status, order_id FROM notifications;'")
        
    except Exception as e:
        print(f"\n✗ Error publishing events: {e}")
