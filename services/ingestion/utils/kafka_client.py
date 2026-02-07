import json
import logging

from typing import TYPE_CHECKING

from config import settings

if TYPE_CHECKING:
    from kafka import KafkaProducer


logger = logging.getLogger(__name__)


class KafkaProducerFactory:
    def create_producer(self):
        if not settings.kafka_brokers:
            return None

        return KafkaProducer(
            bootstrap_servers=settings.kafka_brokers.split(","),
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        )


class EventPublisher:
    def __init__(self, producer_factory: KafkaProducerFactory):
        self._factory = producer_factory

    def publish(self, event: dict) -> None:
        producer = self._factory.create_producer()
        if producer is None:
            logger.warning("Kafka brokers not configured; skipping publish")
            return
        try:
            producer.send(settings.kafka_topic, event)
            producer.flush(5)
        except Exception as exc:
            logger.warning("Failed to publish event: %s", exc)


def event_publisher_factory() -> EventPublisher:
    return EventPublisher(KafkaProducerFactory())
