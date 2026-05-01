"""Kafka consumer for document ingestion pipeline."""
import json
import asyncio
import logging
from confluent_kafka import Consumer, KafkaException
from backend.core.config import settings

logger = logging.getLogger(__name__)


class DocumentConsumer:
    """Consumes loan document events and triggers processing pipeline."""

    def __init__(self, group_id: str = "bfsi-document-processor"):
        self._consumer = Consumer({
            "bootstrap.servers": settings.kafka_bootstrap_servers,
            "group.id": group_id,
            "auto.offset.reset": "earliest",
            "enable.auto.commit": False,    # Manual commit for exactly-once
            "max.poll.interval.ms": 300000,
        })
        self._running = False

    async def start(self, topics: list[str]):
        self._consumer.subscribe(topics)
        self._running = True
        logger.info(f"Kafka consumer started. Subscribed to: {topics}")
        await self._consume_loop()

    async def _consume_loop(self):
        while self._running:
            msg = self._consumer.poll(timeout=1.0)
            if msg is None:
                await asyncio.sleep(0.1)
                continue
            if msg.error():
                logger.error(f"Kafka error: {msg.error()}")
                continue

            try:
                event = json.loads(msg.value().decode("utf-8"))
                await self._handle_event(event)
                self._consumer.commit(msg)
            except Exception as e:
                logger.error(f"Failed to process event: {e}")

    async def _handle_event(self, event: dict):
        event_type = event.get("event_type")
        if event_type == "DOCUMENT_RECEIVED":
            logger.info(f"Processing document: {event['document_type']} for {event['application_id']}")
            # Trigger OCR + extraction pipeline
            from backend.document_processing.ocr_pipeline import OCRPipeline
            ocr = OCRPipeline()
            text = await ocr.extract_text(event.get("s3_path", ""))
            logger.info(f"Extracted {len(text)} chars from {event['document_type']}")

    def stop(self):
        self._running = False
        self._consumer.close()
        logger.info("Kafka consumer stopped")
