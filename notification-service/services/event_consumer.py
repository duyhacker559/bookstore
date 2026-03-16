"""RabbitMQ event consumer for Notification Service."""

import json
import logging
import threading
from datetime import datetime
from typing import Callable

try:
    import pika
except ImportError:
    pika = None

from sqlalchemy.orm import Session

from config import get_settings
from database import SessionLocal
from models import Notification, NotificationStatus, NotificationType
from services.email_service import (
    EmailService,
    compose_order_paid_email,
    compose_shipment_created_email,
    compose_shipment_updated_email,
)

logger = logging.getLogger(__name__)
settings = get_settings()


class EventConsumer:
    def __init__(self):
        self.settings = settings
        self.email_service = EmailService()
        self.connection = None
        self.channel = None
        self.consumer_thread = None
        self.should_stop = False

    def start(self):
        """Start consuming events in a background thread."""
        if pika is None:
            logger.warning("pika not available, event consumer disabled")
            return

        self.consumer_thread = threading.Thread(target=self._consume_loop, daemon=True)
        self.consumer_thread.start()
        logger.info("Event consumer started in background thread")

    def stop(self):
        """Stop consuming events."""
        self.should_stop = True
        if self.connection and not self.connection.is_closed:
            self.connection.close()

    def _consume_loop(self):
        """Main event consumption loop."""
        try:
            credentials = pika.PlainCredentials(self.settings.RABBITMQ_USER, self.settings.RABBITMQ_PASSWORD)
            params = pika.ConnectionParameters(
                host=self.settings.RABBITMQ_HOST,
                port=self.settings.RABBITMQ_PORT,
                credentials=credentials,
                heartbeat=600,
                blocked_connection_timeout=300,
            )

            self.connection = pika.BlockingConnection(params)
            self.channel = self.connection.channel()

            # Declare exchange
            self.channel.exchange_declare(
                exchange="bookstore.events",
                exchange_type="topic",
                durable=True,
            )

            # Create queue for notification service
            queue_name = "notification_service_queue"
            self.channel.queue_declare(queue=queue_name, durable=True)

            # Bind to events we care about
            self.channel.queue_bind(exchange="bookstore.events", queue=queue_name, routing_key="order.paid")
            self.channel.queue_bind(exchange="bookstore.events", queue=queue_name, routing_key="shipment.created")
            self.channel.queue_bind(exchange="bookstore.events", queue=queue_name, routing_key="shipment.updated")

            logger.info(f"Listening for events on queue: {queue_name}")

            self.channel.basic_consume(queue=queue_name, on_message_callback=self._handle_event, auto_ack=False)
            self.channel.start_consuming()

        except Exception as exc:
            logger.error(f"Event consumer error: {exc}")
            if not self.should_stop:
                logger.info("Restarting consumer in 5 seconds...")
                import time
                time.sleep(5)
                if not self.should_stop:
                    self._consume_loop()

    def _handle_event(self, ch, method, properties, body):
        """Handle incoming event."""
        try:
            event = json.loads(body)
            event_type = event.get("event_type")
            data = event.get("data", {})

            logger.info(f"Received event: {event_type}")

            db = SessionLocal()
            try:
                if event_type == "order.paid":
                    self._handle_order_paid(db, data)
                elif event_type == "shipment.created":
                    self._handle_shipment_created(db, data)
                elif event_type == "shipment.updated":
                    self._handle_shipment_updated(db, data)
                else:
                    logger.debug(f"Ignoring event type: {event_type}")

                db.commit()
                ch.basic_ack(delivery_tag=method.delivery_tag)

            except Exception as exc:
                logger.error(f"Error handling event {event_type}: {exc}")
                db.rollback()
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
            finally:
                db.close()

        except Exception as exc:
            logger.error(f"Error processing message: {exc}")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

    def _handle_order_paid(self, db: Session, data: dict):
        """Handle order.paid event."""
        order_id = data.get("order_id")
        amount = data.get("amount", 0)
        customer_email = data.get("customer_email", "customer@example.com")

        subject, body = compose_order_paid_email(order_id, amount)

        notification = Notification(
            notification_type=NotificationType.EMAIL,
            recipient=customer_email,
            subject=subject,
            message=body,
            event_type="order.paid",
            order_id=str(order_id),
            status=NotificationStatus.PENDING,
        )

        # Try to send email
        success = self.email_service.send_email(customer_email, subject, body)
        if success:
            notification.status = NotificationStatus.SENT
            notification.sent_at = datetime.utcnow()
        else:
            notification.status = NotificationStatus.FAILED
            notification.error_message = "Email sending failed"

        db.add(notification)
        logger.info(f"Order paid notification: {notification.status.value}")

    def _handle_shipment_created(self, db: Session, data: dict):
        """Handle shipment.created event."""
        order_id = data.get("order_id")
        method_name = data.get("method_name", "Standard Shipping")
        # In real system, we'd fetch customer email from order service
        customer_email = "customer@example.com"

        subject, body = compose_shipment_created_email(order_id, method_name)

        notification = Notification(
            notification_type=NotificationType.EMAIL,
            recipient=customer_email,
            subject=subject,
            message=body,
            event_type="shipment.created",
            order_id=str(order_id),
            status=NotificationStatus.PENDING,
        )

        success = self.email_service.send_email(customer_email, subject, body)
        if success:
            notification.status = NotificationStatus.SENT
            notification.sent_at = datetime.utcnow()
        else:
            notification.status = NotificationStatus.FAILED
            notification.error_message = "Email sending failed"

        db.add(notification)
        logger.info(f"Shipment created notification: {notification.status.value}")

    def _handle_shipment_updated(self, db: Session, data: dict):
        """Handle shipment.updated event."""
        order_id = data.get("order_id")
        current_status = data.get("current_status", "unknown")
        customer_email = "customer@example.com"

        # Only notify on significant status changes
        if current_status.lower() in ["shipped", "delivered"]:
            subject, body = compose_shipment_updated_email(order_id, current_status)

            notification = Notification(
                notification_type=NotificationType.EMAIL,
                recipient=customer_email,
                subject=subject,
                message=body,
                event_type="shipment.updated",
                order_id=str(order_id),
                status=NotificationStatus.PENDING,
            )

            success = self.email_service.send_email(customer_email, subject, body)
            if success:
                notification.status = NotificationStatus.SENT
                notification.sent_at = datetime.utcnow()
            else:
                notification.status = NotificationStatus.FAILED
                notification.error_message = "Email sending failed"

            db.add(notification)
            logger.info(f"Shipment updated notification: {notification.status.value}")
