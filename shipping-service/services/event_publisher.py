"""RabbitMQ event publishing for Shipping Service."""

import json
import logging
from datetime import datetime

try:
    import pika
except ImportError:  # pragma: no cover
    pika = None

logger = logging.getLogger(__name__)


class EventPublisher:
    def __init__(self, host: str, port: int, username: str, password: str):
        self.host = host
        self.port = port
        self.username = username
        self.password = password

    def _publish(self, event_type: str, payload: dict) -> bool:
        body = {
            "event_type": event_type,
            "timestamp": datetime.utcnow().isoformat(),
            "data": payload,
        }
        if pika is None:
            logger.info("RabbitMQ not available; event logged: %s", body)
            return False

        try:
            credentials = pika.PlainCredentials(self.username, self.password)
            params = pika.ConnectionParameters(host=self.host, port=self.port, credentials=credentials)
            connection = pika.BlockingConnection(params)
            channel = connection.channel()
            channel.exchange_declare(exchange="bookstore.events", exchange_type="topic", durable=True)
            channel.basic_publish(
                exchange="bookstore.events",
                routing_key=event_type,
                body=json.dumps(body),
                properties=pika.BasicProperties(delivery_mode=2, content_type="application/json"),
            )
            connection.close()
            return True
        except Exception as exc:  # pragma: no cover
            logger.warning("Failed to publish event %s: %s", event_type, exc)
            return False

    def shipment_created(self, order_id: str, shipment_id: int, method_name: str) -> bool:
        return self._publish(
            "shipment.created",
            {
                "order_id": order_id,
                "shipment_id": shipment_id,
                "method_name": method_name,
            },
        )

    def shipment_updated(self, order_id: str, previous_status: str, current_status: str) -> bool:
        return self._publish(
            "shipment.updated",
            {
                "order_id": order_id,
                "previous_status": previous_status,
                "current_status": current_status,
            },
        )
