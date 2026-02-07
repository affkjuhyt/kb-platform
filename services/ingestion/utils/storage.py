import boto3

from config import settings


class StorageClientFactory:
    def create_s3_client(self):
        return boto3.client(
            "s3",
            endpoint_url=f"http{'s' if settings.minio_secure else ''}://{settings.minio_endpoint}",
            aws_access_key_id=settings.minio_access_key,
            aws_secret_access_key=settings.minio_secret_key,
            region_name="us-east-1",
        )


class StorageService:
    def __init__(self, client_factory: StorageClientFactory):
        self._factory = client_factory

    def ensure_bucket(self) -> None:
        client = self._factory.create_s3_client()
        buckets = client.list_buckets().get("Buckets", [])
        if not any(b["Name"] == settings.minio_bucket for b in buckets):
            client.create_bucket(Bucket=settings.minio_bucket)

    def put_raw_object(self, key: str, data: bytes, content_type: str) -> None:
        client = self._factory.create_s3_client()
        client.put_object(
            Bucket=settings.minio_bucket,
            Key=key,
            Body=data,
            ContentType=content_type,
        )


def storage_service_factory() -> StorageService:
    return StorageService(StorageClientFactory())
