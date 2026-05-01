"""Kafka producer for loan application events."""
import json
import logging
from confluent_kafka import Producer
from backend.core.config import settings

logger = logging.getLogger(__name__)


class LoanEventProducer:
    def __init__(self):
        self._producer = Producer({
            "bootstrap.servers": settings.kafka_bootstrap_servers,
            "client.id": "bfsi-credit-producer",
            "acks": "all",           # Wait for all replicas
            "retries": 3,
            "linger.ms": 5,          # Micro-batching for efficiency
            "compression.type": "snappy",
        })

    def _delivery_callback(self, err, msg):
        if err:
            logger.error(f"Kafka delivery failed: {err}")
        else:
            logger.debug(f"Delivered to {msg.topic()}[{msg.partition()}]@{msg.offset()}")

    async def publish_document_received(self, application_id: str, document_type: str, s3_path: str):
        """Publish event when loan document is received."""
        event = {
            "event_type": "DOCUMENT_RECEIVED",
            "application_id": application_id,
            "document_type": document_type,
            "s3_path": s3_path,
            "timestamp": __import__("time").time(),
        }
        self._producer.produce(
            topic=settings.kafka_topic_documents,
            key=application_id,
            value=json.dumps(event),
            callback=self._delivery_callback,
        )
        self._producer.poll(0)

    async def publish_decision(self, application_id: str, decision: str, amount: float, reason: str):
        """Publish final underwriting decision event."""
        event = {
            "event_type": "UNDERWRITING_DECISION",
            "application_id": application_id,
            "decision": decision,
            "approved_amount": amount,
            "reason": reason,
            "timestamp": __import__("time").time(),
        }
        self._producer.produce(
            topic=settings.kafka_topic_decisions,
            key=application_id,
            value=json.dumps(event),
            callback=self._delivery_callback,
        )
        self._producer.flush(timeout=5)
        logger.info(f"Published decision event: {decision} for {application_id}")


_producer = None
def get_producer() -> LoanEventProducer:
    global _producer
    if _producer is None:
        _producer = LoanEventProducer()
    return _producer
