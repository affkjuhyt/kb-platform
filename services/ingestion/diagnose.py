#!/usr/bin/env python3
"""
Diagnostic script for Ingestion Service startup issues
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("=" * 60)
print("INGESTION SERVICE - STARTUP DIAGNOSTIC")
print("=" * 60)

# Test 1: Check Python version
print("\n1. Python Version:")
print(f"   {sys.version}")
if sys.version_info < (3, 8):
    print("   ❌ Python 3.8+ required")
else:
    print("   ✅ Python version OK")

# Test 2: Check dependencies
print("\n2. Checking Dependencies:")
dependencies = [
    "fastapi",
    "uvicorn",
    "pydantic_settings",
    "sqlalchemy",
    "boto3",
    "requests",
]

missing = []
for dep in dependencies:
    try:
        __import__(dep.replace("-", "_"))
        print(f"   ✅ {dep}")
    except ImportError:
        print(f"   ❌ {dep} - NOT INSTALLED")
        missing.append(dep)

if missing:
    print(f"\n   ⚠️  Missing dependencies. Run:")
    print(f"   pip install {' '.join(missing)}")

# Test 3: Check environment variables
print("\n3. Environment Variables:")
required_env = [
    "RAG_POSTGRES_DSN",
    "RAG_MINIO_ENDPOINT",
    "RAG_MINIO_ACCESS_KEY",
    "RAG_MINIO_SECRET_KEY",
]

for env_var in required_env:
    value = os.getenv(env_var)
    if value:
        # Mask sensitive info
        if "PASSWORD" in env_var or "SECRET" in env_var:
            display = value[:4] + "****" if len(value) > 4 else "****"
        else:
            display = value
        print(f"   ✅ {env_var}={display}")
    else:
        print(f"   ⚠️  {env_var} not set (will use defaults)")

# Test 4: Check database connection
print("\n4. Database Connection (PostgreSQL):")
try:
    from config import settings

    print(f"   Database URL: {settings.postgres_dsn}")

    from sqlalchemy import create_engine

    engine = create_engine(settings.postgres_dsn, pool_pre_ping=True)
    connection = engine.connect()
    connection.execute("SELECT 1")
    connection.close()
    print("   ✅ PostgreSQL connection OK")
except Exception as e:
    print(f"   ❌ PostgreSQL connection failed: {e}")
    print("   💡 Make sure PostgreSQL is running:")
    print("      docker-compose up -d postgres")

# Test 5: Check MinIO connection
print("\n5. Object Storage (MinIO):")
try:
    from storage import storage_service_factory
    from config import settings

    print(f"   MinIO Endpoint: {settings.minio_endpoint}")
    print(f"   Bucket: {settings.minio_bucket}")

    service = storage_service_factory()

    # Try to list buckets
    import boto3
    from botocore.exceptions import ClientError

    client = boto3.client(
        "s3",
        endpoint_url=f"http{'s' if settings.minio_secure else ''}://{settings.minio_endpoint}",
        aws_access_key_id=settings.minio_access_key,
        aws_secret_access_key=settings.minio_secret_key,
        region_name="us-east-1",
    )

    buckets = client.list_buckets()
    print(f"   ✅ MinIO connection OK")
    print(f"   📦 Existing buckets: {[b['Name'] for b in buckets.get('Buckets', [])]}")

except Exception as e:
    print(f"   ❌ MinIO connection failed: {e}")
    print("   💡 Make sure MinIO is running:")
    print("      docker-compose up -d minio")

# Test 6: Check migrations
print("\n6. Database Migrations:")
try:
    from pathlib import Path

    alembic_ini = Path(__file__).parent.parent.parent / "alembic.ini"

    if alembic_ini.exists():
        print(f"   ✅ alembic.ini found: {alembic_ini}")
    else:
        print(f"   ❌ alembic.ini not found at: {alembic_ini}")
        print(f"   💡 Looking in: {Path(__file__).parent}")

        # List files in current directory
        current_dir = Path(__file__).parent
        files = list(current_dir.glob("*.ini"))
        if files:
            print(f"   📄 Found .ini files: {[f.name for f in files]}")

except Exception as e:
    print(f"   ❌ Error checking migrations: {e}")

# Test 7: Import app
print("\n7. Application Import:")
try:
    from app import app

    print("   ✅ FastAPI app imported successfully")
    print(
        f"   📋 Routes: {[route.path for route in app.routes if hasattr(route, 'path')]}"
    )
except Exception as e:
    print(f"   ❌ Failed to import app: {e}")
    import traceback

    traceback.print_exc()

# Test 8: Check Kafka (optional)
print("\n8. Message Queue (Kafka) - Optional:")
try:
    from kafka_client import event_publisher_factory

    print("   ⚠️  Kafka client available (will test connection on first use)")
except Exception as e:
    print(f"   ⚠️  Kafka not configured: {e}")
    print("   💡 Kafka is optional for basic functionality")

# Summary
print("\n" + "=" * 60)
print("DIAGNOSTIC SUMMARY")
print("=" * 60)

if missing:
    print("\n❌ CRITICAL ISSUES FOUND:")
    print(f"   Install missing dependencies: pip install {' '.join(missing)}")
else:
    print("\n✅ All dependencies installed")
    print("\n🚀 To start the service:")
    print("   ./start.sh")
    print("\nOr manually:")
    print("   python3 -m uvicorn app:app --host 0.0.0.0 --port 8002 --reload")

print("\n📚 For detailed troubleshooting, see: TROUBLESHOOTING.md")
print("=" * 60)
