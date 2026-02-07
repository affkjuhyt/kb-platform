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
    def __init__(self, factory: StorageClientFactory):
        self._factory = factory

    def get_object(self, key: str) -> tuple[bytes | None, str | None]:
        client = self._factory.create_s3_client()
        try:
            obj = client.get_object(Bucket=settings.minio_bucket, Key=key)
            data = obj["Body"].read()
            content_type = obj.get("ContentType", "application/octet-stream")
            return data, content_type
        except client.exceptions.NoSuchKey:
            return None, None
        except Exception as e:
            print(f"⚠ Error fetching object {key}: {e}")
            raise


def storage_service_factory() -> StorageService:
    return StorageService(StorageClientFactory())
