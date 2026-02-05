import json
import logging
from typing import TYPE_CHECKING

from config import settings

if TYPE_CHECKING:
    from kafka import KafkaConsumer, KafkaProducer

logger = logging.getLogger(__name__)


class KafkaConsumerFactory:
    def create_consumer(self) -> "KafkaConsumer":
        from kafka import KafkaConsumer

        return KafkaConsumer(
            settings.kafka_ingestion_topic,
            bootstrap_servers=settings.kafka_brokers.split(","),
            value_deserializer=lambda v: json.loads(v.decode("utf-8")),
            auto_offset_reset="earliest",
            enable_auto_commit=True,
            group_id="indexer-consumer",
        )


class KafkaProducerFactory:
    def create_producer(self) -> "KafkaProducer":
        from kafka import KafkaProducer

        return KafkaProducer(
            bootstrap_servers=settings.kafka_brokers.split(","),
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        )


class ChunkPublisher:
    def __init__(self, producer_factory: KafkaProducerFactory):
        self._factory = producer_factory

    def publish(self, payload: dict) -> None:
        try:
            producer = self._factory.create_producer()
            producer.send(settings.kafka_chunk_topic, payload)
            producer.flush(5)
        except Exception as exc:
            logger.warning("Failed to publish chunk event: %s", exc)


def consumer_factory() -> KafkaConsumerFactory:
    return KafkaConsumerFactory()


def publisher_factory() -> ChunkPublisher:
    return ChunkPublisher(KafkaProducerFactory())
