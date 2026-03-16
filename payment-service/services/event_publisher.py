"""
Event Publishing Service for Payment Service
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


class EventPublisher:
    """Publish payment events to RabbitMQ"""
    
    EXCHANGE = 'bookstore.events'
    EXCHANGE_TYPE = 'topic'
    
    def __init__(self, host: str, port: int, username: str, password: str):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self._connection = None
        self._channel = None
    
    def _get_connection(self):
        """Get or create RabbitMQ connection"""
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
                return None
        return self._connection
    
    def _get_channel(self):
        """Get or create RabbitMQ channel"""
        conn = self._get_connection()
        if conn is None:
            return None
            
        if self._channel is None or self._channel.is_closed:
            self._channel = conn.channel()
            self._channel.exchange_declare(
                exchange=self.EXCHANGE,
                exchange_type=self.EXCHANGE_TYPE,
                durable=True
            )
        return self._channel
    
    def publish_payment_completed(
        self,
        order_id: str,
        transaction_id: str,
        amount: float,
        customer_email: str = None,
        correlation_id: Optional[str] = None
    ) -> bool:
        """Publish payment completed event"""
        event_data = {
            'order_id': order_id,
            'transaction_id': transaction_id,
            'amount': amount,
            'timestamp': datetime.utcnow().isoformat(),
        }
        if customer_email:
            event_data['customer_email'] = customer_email
            
        return self._publish_event(
            'order.paid',
            event_data,
            correlation_id
        )
    
    def publish_payment_failed(
        self,
        order_id: str,
        error_message: str,
        correlation_id: Optional[str] = None
    ) -> bool:
        """Publish payment failed event"""
        return self._publish_event(
            'payment.failed',
            {
                'order_id': order_id,
                'error_message': error_message,
                'timestamp': datetime.utcnow().isoformat(),
            },
            correlation_id
        )
    
    def _publish_event(
        self,
        event_type: str,
        data: Dict[str, Any],
        correlation_id: Optional[str] = None
    ) -> bool:
        """Publish event to RabbitMQ"""
        if not RABBITMQ_AVAILABLE:
            logger.warning(f"RabbitMQ not available. Event {event_type} logged instead.")
            logger.info(f"[EVENT] {event_type}: {json.dumps(data, default=str)}")
            return False
        
        try:
            channel = self._get_channel()
            if channel is None:
                logger.warning(f"Could not get RabbitMQ channel. Event {event_type} logged.")
                logger.info(f"[EVENT] {event_type}: {json.dumps(data, default=str)}")
                return False
            
            event_data = {
                'event_type': event_type,
                'timestamp': datetime.utcnow().isoformat(),
                'correlation_id': correlation_id,
                'data': data,
            }
            
            channel.basic_publish(
                exchange=self.EXCHANGE,
                routing_key=event_type,
                body=json.dumps(event_data),
                properties=pika.BasicProperties(
                    content_type='application/json',
                    delivery_mode=2,
                    correlation_id=correlation_id,
                )
            )
            
            logger.info(f"Event published: {event_type}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to publish event: {e}")
            logger.info(f"[FALLBACK] {event_type}: {json.dumps(data, default=str)}")
            return False
    
    def close(self):
        """Close RabbitMQ connection"""
        try:
            if self._channel and not self._channel.is_closed:
                self._channel.close()
            if self._connection and not self._connection.is_closed:
                self._connection.close()
        except Exception as e:
            logger.error(f"Error closing RabbitMQ connection: {e}")
