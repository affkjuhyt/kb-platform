# 🔧 Ingestion Service - Troubleshooting Guide

## ❌ Tình Trạng Hiện Tại

Service đang **KHÔNG CHẠY** với các lỗi sau:

### 1. Lỗi Import Dependencies (ModuleNotFoundError)

```
ModuleNotFoundError: No module named 'requests'
ModuleNotFoundError: No module named 'pydantic_settings'
```

**Nguyên nhân**: Python dependencies chưa được cài đặt

### 2. Dependencies Thiếu

Ingestion service cần các packages sau:
- `fastapi` - Web framework
- `uvicorn` - ASGI server
- `pydantic-settings` - Configuration management
- `sqlalchemy` - ORM cho PostgreSQL
- `psycopg2-binary` - PostgreSQL driver
- `boto3` - AWS SDK (cho MinIO)
- `requests` - HTTP client
- `kafka-python` - Kafka client

### 3. Infrastructure Dependencies

Service cần các external services:
- ✅ PostgreSQL (port 5432)
- ✅ MinIO (port 9000)
- ✅ Kafka (port 9092)

## 🚀 Cách Khắc Phục

### Bước 1: Cài Đặt Dependencies

```bash
cd "/Users/thiennlinh/Documents/New project/services/ingestion"

# Tạo virtual environment
python3 -m venv venv
source venv/bin/activate  # Mac/Linux
# hoặc: venv\Scripts\activate  # Windows

# Cài đặt dependencies
pip install fastapi uvicorn pydantic-settings sqlalchemy psycopg2-binary boto3 requests kafka-python

# Hoặc nếu có requirements.txt
pip install -r requirements.txt
```

### Bước 2: Tạo Requirements.txt

```bash
cat > "/Users/thiennlinh/Documents/New project/services/ingestion/requirements.txt" << 'EOF'
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic-settings==2.0.3
sqlalchemy==2.0.23
psycopg2-binary==2.9.9
boto3==1.34.0
requests==2.31.0
kafka-python==2.0.2
EOF
```

### Bước 3: Kiểm Tra Infrastructure

```bash
# Check PostgreSQL
curl http://localhost:5432 || echo "PostgreSQL not running"

# Check MinIO
curl http://localhost:9000/minio/health/live || echo "MinIO not running"

# Check Kafka (simplified)
telnet localhost 9092 || echo "Kafka not running"
```

### Bước 4: Khởi Động Services

**Cách 1: Sử dụng Docker Compose (Khuyến nghị)**

```bash
cd "/Users/thiennlinh/Documents/New project"

# Start all infrastructure services
docker-compose up -d postgres minio kafka

# Đợi services khởi động
sleep 10

# Chạy migrations
cd services/ingestion
python3 migrations.py

# Khởi động ingestion service
python3 -m uvicorn app:app --host 0.0.0.0 --port 8002 --reload
```

**Cách 2: Chạy trực tiếp (Development)**

```bash
cd "/Users/thiennlinh/Documents/New project/services/ingestion"
source venv/bin/activate

# Set environment variables
export RAG_POSTGRES_DSN="postgresql://rag:rag@localhost:5432/rag"
export RAG_MINIO_ENDPOINT="localhost:9000"
export RAG_MINIO_ACCESS_KEY="minio"
export RAG_MINIO_SECRET_KEY="minio123"
export RAG_KAFKA_BROKERS="localhost:9092"

# Chạy service
python3 -m uvicorn app:app --host 0.0.0.0 --port 8002 --reload
```

## 🔍 Kiểm Tra Sau Khi Khởi Động

```bash
# 1. Health check
curl http://localhost:8002/healthz

# Expected response:
# {"status": "ok", "time": "2026-02-..."}

# 2. Test webhook ingestion
curl -X POST http://localhost:8002/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "test-tenant",
    "source": "test",
    "source_id": "doc-001",
    "content": "This is a test document.",
    "content_type": "text/plain"
  }'

# Expected response:
# {"doc_id": "...", "version": 1, "duplicate": false, "raw_object_key": "..."}
```

## 🐛 Xử Lý Lỗi Thường Gặp

### Lỗi 1: "ModuleNotFoundError: No module named 'requests'"

**Fix**:
```bash
pip install requests
```

### Lỗi 2: "ModuleNotFoundError: No module named 'pydantic_settings'"

**Fix**:
```bash
pip install pydantic-settings
```

### Lỗi 3: "psycopg2.OperationalError: connection refused"

**Nguyên nhân**: PostgreSQL chưa chạy

**Fix**:
```bash
# Start PostgreSQL
docker run -d \
  --name postgres \
  -e POSTGRES_USER=rag \
  -e POSTGRES_PASSWORD=rag \
  -e POSTGRES_DB=rag \
  -p 5432:5432 \
  postgres:14

# Or with docker-compose
docker-compose up -d postgres
```

### Lỗi 4: "botocore.exceptions.EndpointConnectionError" (MinIO)

**Nguyên nhân**: MinIO chưa chạy

**Fix**:
```bash
# Start MinIO
docker run -d \
  --name minio \
  -p 9000:9000 \
  -p 9001:9001 \
  -e MINIO_ROOT_USER=minio \
  -e MINIO_ROOT_PASSWORD=minio123 \
  minio/minio server /data --console-address ":9001"
```

### Lỗi 5: "NoBrokersAvailable" (Kafka)

**Nguyên nhân**: Kafka chưa chạy

**Fix**:
```bash
# Start Kafka (simplified setup)
docker run -d \
  --name kafka \
  -p 9092:9092 \
  -e KAFKA_ADVERTISED_LISTENERS=PLAINTEXT://localhost:9092 \
  confluentinc/cp-kafka:latest
```

## 📝 Startup Script

Tạo file `start_ingestion.sh`:

```bash
#!/bin/bash
cd "/Users/thiennlinh/Documents/New project/services/ingestion"

# Activate virtual environment
source venv/bin/activate

# Set environment
export RAG_SERVICE_PORT=8002
export RAG_POSTGRES_DSN="postgresql://rag:rag@localhost:5432/rag"
export RAG_MINIO_ENDPOINT="localhost:9000"
export RAG_MINIO_ACCESS_KEY="minio"
export RAG_MINIO_SECRET_KEY="minio123"
export RAG_KAFKA_BROKERS="localhost:9092"

# Run migrations
python3 -c "from migrations import run_migrations; run_migrations()"

# Ensure MinIO bucket exists
python3 -c "from storage import storage_service_factory; storage_service_factory().ensure_bucket()"

# Start service
echo "Starting Ingestion Service on port 8002..."
python3 -m uvicorn app:app --host 0.0.0.0 --port 8002 --reload
```

Make it executable:
```bash
chmod +x start_ingestion.sh
```

## 🎯 Test Sau Khi Khởi Động

```bash
# 1. Quick smoke test
python3 << 'EOF'
import requests
import sys

# Test health
try:
    r = requests.get("http://localhost:8002/healthz", timeout=5)
    if r.status_code == 200:
        print("✅ Ingestion service is running")
        print(f"Response: {r.json()}")
    else:
        print(f"❌ Health check failed: {r.status_code}")
        sys.exit(1)
except Exception as e:
    print(f"❌ Cannot connect to ingestion service: {e}")
    sys.exit(1)
EOF

# 2. Test ingestion
python3 << 'EOF'
import requests

data = {
    "tenant_id": "test-tenant",
    "source": "webhook",
    "source_id": "test-doc-001",
    "content": "This is a test document for machine learning.",
    "content_type": "text/plain"
}

r = requests.post("http://localhost:8002/webhook", json=data)
print(f"Status: {r.status_code}")
print(f"Response: {r.json()}")
EOF
```

## 📊 Kiểm Tra Logs

```bash
# Xem logs real-time
tail -f /path/to/ingestion.log

# Hoặc nếu chạy với Docker
docker logs -f ingestion-service
```

## ✅ Checklist Khởi Động

- [ ] Dependencies đã cài đặt
- [ ] PostgreSQL đang chạy (port 5432)
- [ ] MinIO đang chạy (port 9000)
- [ ] Kafka đang chạy (port 9092)
- [ ] Migrations đã chạy
- [ ] MinIO bucket đã tạo
- [ ] Service chạy trên port 8002
- [ ] Health check thành công
- [ ] Test ingestion thành công

## 🆘 Vẫn Không Chạy?

1. **Kiểm tra logs chi tiết**:
```bash
python3 -c "from app import app; print('Import OK')" 2>&1
```

2. **Kiểm tra port conflict**:
```bash
lsof -i :8002  # Xem process nào đang dùng port 8002
```

3. **Kill process và restart**:
```bash
kill $(lsof -t -i:8002)
./start_ingestion.sh
```

4. **Full reset**:
```bash
# Stop all services
docker-compose down

# Start fresh
docker-compose up -d postgres minio kafka
sleep 10
./start_ingestion.sh
```

## 📞 Cần Hỗ Trợ?

Kiểm tra các logs sau:
1. Logs ingestion service
2. Logs PostgreSQL: `docker logs postgres`
3. Logs MinIO: `docker logs minio`
4. Logs Kafka: `docker logs kafka`
