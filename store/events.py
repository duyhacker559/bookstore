"""
Event bus for microservices communication via RabbitMQ.

This module handles publishing domain events that other microservices
can subscribe to and react upon.

Supported events:
- order.created: When a new order is created
- order.paid: When payment is successfully processed
- order.shipped: When order is shipped
- order.cancelled: When order is cancelled
- payment.completed: When payment is processed by payment service
- inventory.reserved: When inventory is reserved for an order
- inventory.released: When inventory reservation is released
"""

import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime

try:
    import pika
    RABBITMQ_AVAILABLE = True
except ImportError:
    RABBITMQ_AVAILABLE = False

logger = logging.getLogger(__name__)


class EventBus:
    """
    RabbitMQ-based event bus for async communication between services.
    
    Usage:
        from store.events import event_bus
        
        event_bus.publish('order.created', {
            'order_id': '123',
            'customer_id': '456',
            'total': 99.99
        })
    """
    
    EXCHANGE_NAME = 'bookstore.events'
    EXCHANGE_TYPE = 'topic'
    
    # Supported event topics
    EVENTS = {
        'order.created': 'order.created',
        'order.paid': 'order.paid',
        'order.shipped': 'order.shipped',
        'order.cancelled': 'order.cancelled',
        'payment.completed': 'payment.completed',
        'shipment.created': 'shipment.created',
        'shipment.updated': 'shipment.updated',
        'inventory.reserved': 'inventory.reserved',
        'inventory.released': 'inventory.released',
        'notification.send_email': 'notification.send_email',
    }
    
    def __init__(self, host: str = 'localhost', port: int = 5672,
                 username: str = 'guest', password: str = 'guest'):
        """Initialize event bus with RabbitMQ connection details."""
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self._connection = None
        self._channel = None
    
    def _get_connection(self):
        """Get or create RabbitMQ connection."""
        if self._connection is None or self._connection.is_closed:
            try:
                credentials = pika.PlainCredentials(self.username, self.password)
                self._connection = pika.BlockingConnection(
                    pika.ConnectionParameters(
                        host=self.host,
                        port=self.port,
                        credentials=credentials,
                        heartbeat=600,
                        blocked_connection_timeout=300,
                    )
                )
            except Exception as e:
                logger.error(f"Failed to connect to RabbitMQ: {e}")
                raise
        return self._connection
    
    def _get_channel(self):
        """Get or create RabbitMQ channel."""
        if self._channel is None or self._channel.is_closed:
            conn = self._get_connection()
            self._channel = conn.channel()
            self._channel.exchange_declare(
                exchange=self.EXCHANGE_NAME,
                exchange_type=self.EXCHANGE_TYPE,
                durable=True
            )
        return self._channel
    
    def publish(self, event_type: str, data: Dict[str, Any], 
                correlation_id: Optional[str] = None) -> bool:
        """
        Publish an event to the message bus.
        
        Args:
            event_type: Type of event (e.g., 'order.created')
            data: Event data as dictionary
            correlation_id: Optional correlation ID for tracing
            
        Returns:
            bool: True if event was published successfully
        """
        if not RABBITMQ_AVAILABLE:
            logger.warning(f"RabbitMQ not available. Event {event_type} not published.")
            return False
        
        if event_type not in self.EVENTS:
            logger.warning(f"Unknown event type: {event_type}")
            return False
        
        try:
            channel = self._get_channel()
            
            # Add metadata
            event_data = {
                'event_type': event_type,
                'timestamp': datetime.utcnow().isoformat(),
                'correlation_id': correlation_id,
                'data': data,
            }
            
            # Publish message
            channel.basic_publish(
                exchange=self.EXCHANGE_NAME,
                routing_key=self.EVENTS[event_type],
                body=json.dumps(event_data),
                properties=pika.BasicProperties(
                    content_type='application/json',
                    delivery_mode=2,  # Persistent message
                    correlation_id=correlation_id,
                )
            )
            
            logger.info(f"Event published: {event_type} (correlation_id: {correlation_id})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to publish event {event_type}: {e}")
            return False
    
    def close(self):
        """Close RabbitMQ connection."""
        try:
            if self._channel and not self._channel.is_closed:
                self._channel.close()
            if self._connection and not self._connection.is_closed:
                self._connection.close()
        except Exception as e:
            logger.error(f"Error closing RabbitMQ connection: {e}")


# Create singleton instance
def get_event_bus(host: str = None, port: int = None, 
                  username: str = None, password: str = None) -> EventBus:
    """
    Get or create event bus instance with Django settings.
    
    Usage:
        from store.events import get_event_bus
        
        event_bus = get_event_bus()
        event_bus.publish('order.created', {'order_id': '123'})
    """
    from django.conf import settings
    
    return EventBus(
        host=host or getattr(settings, 'RABBITMQ_HOST', 'localhost'),
        port=port or getattr(settings, 'RABBITMQ_PORT', 5672),
        username=username or getattr(settings, 'RABBITMQ_USER', 'guest'),
        password=password or getattr(settings, 'RABBITMQ_PASSWORD', 'guest'),
    )


# Convenience function for publishing events
def publish_event(event_type: str, data: Dict[str, Any], 
                  correlation_id: Optional[str] = None) -> bool:
    """
    Convenience function to publish an event.
    
    Args:
        event_type: Type of event
        data: Event payload
        correlation_id: Optional correlation ID
        
    Returns:
        bool: Success status
        
    Example:
        from store.events import publish_event
        
        publish_event('order.created', {
            'order_id': order.id,
            'customer_id': order.customer.id,
        })
    """
    try:
        event_bus = get_event_bus()
        return event_bus.publish(event_type, data, correlation_id)
    except Exception as e:
        logger.error(f"Error publishing event: {e}")
        return False


# For backward compatibility with Docker Compose (when RabbitMQ not available)
# Events will be logged but not published
class LoggingEventBus(EventBus):
    """Fallback event bus that logs events instead of publishing to RabbitMQ."""
    
    def publish(self, event_type: str, data: Dict[str, Any],
                correlation_id: Optional[str] = None) -> bool:
        """Log event instead of publishing."""
        logger.info(f"[EVENT] {event_type}: {json.dumps(data, default=str)}")
        return True
