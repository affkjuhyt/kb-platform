# 🐳 Docker Compose Unified

## Tổng Quan

File `docker-compose.unified.yml` merge từ 2 file cũ:
- `docker-compose.yml` - Services chính
- `docker-compose.dev.yml` - Development override

Và thêm các tính năng mới:
- ✅ Health checks cho tất cả services
- ✅ Logging configuration
- ✅ Restart policies
- ✅ Service dependencies rõ ràng
- ✅ Resource limits (cho rerank service)

## Cấu Trúc Services

### 1. Database & Storage
| Service | Port | Health Check | Mô tả |
|---------|------|--------------|-------|
| postgres | 5432 | pg_isready | PostgreSQL database |
| redis | 6379 | redis ping | Redis cache |

### 2. Vector & Search
| Service | Port | Health Check | Mô tả |
|---------|------|--------------|-------|
| qdrant | 6333, 6334 | /healthz | Vector database (gRPC + HTTP) |
| opensearch | 9200 | /_cluster/health | Full-text search |

### 3. File Storage
| Service | Port | Health Check | Mô tả |
|---------|------|--------------|-------|
| minio | 9000, 9001 | /minio/health/live | Object storage |

### 4. Message Queue
| Service | Port | Health Check | Mô tả |
|---------|------|--------------|-------|
| kafka | 9092 | broker-api-versions | Message queue |

### 5. Application Services
| Service | Port | Depends On | Mô tả |
|---------|------|------------|-------|
| ingestion | 8002 | postgres, minio, kafka | Document ingestion |
| indexer | 8003 | postgres, minio, kafka, qdrant, opensearch | Document indexer |
| indexer-consumer | N/A | All above | Kafka consumer |
| query-api | 8001 | postgres, qdrant, opensearch, rerank | Search & RAG |
| llm-gateway | 8004 | None | LLM provider (mock mode) |
| rerank | 8005 | None | Cross-encoder reranking |
| api-gateway | 8080 | query-api, ingestion, llm-gateway | Nginx proxy |

## 🚀 Quick Start

### Bước 1: Khởi động tất cả services

```bash
cd /Users/thiennlinh/Documents/New\ project/infra/docker-compose

# Khởi động tất cả services
docker-compose -f docker-compose.unified.yml up -d

# Hoặc dùng shorthand (nếu set COMPOSE_FILE)
export COMPOSE_FILE=docker-compose.unified.yml
docker-compose up -d
```

### Bước 2: Kiểm tra trạng thái

```bash
# Kiểm tra tất cả services
./check-services.sh

# Hoặc dùng docker-compose
docker-compose ps

# Xem logs
docker-compose logs -f
```

### Bước 3: Test services

```bash
# Test health endpoints
curl http://localhost:8001/healthz  # Query API
curl http://localhost:8002/healthz  # Ingestion
curl http://localhost:8003/healthz  # Indexer
curl http://localhost:8004/healthz  # LLM Gateway
curl http://localhost:8005/healthz  # Rerank
```

## 🔍 Kiểm Tra Node Nào Không Chạy

### Script check-services.sh

```bash
./check-services.sh
```

Output ví dụ:
```
postgres              ✅ RUNNING & HEALTHY
redis                 ✅ RUNNING & HEALTHY
qdrant                ✅ RUNNING & HEALTHY
opensearch            🔄 STARTING
minio                 ✅ RUNNING & HEALTHY
kafka                 ✅ RUNNING & HEALTHY
ingestion             ❌ STOPPED (exit code: 1)
indexer               ✅ RUNNING & HEALTHY
...

🔍 Issue Detection:
----------------------------------------
❌ kb-ingestion is stopped
   Last 5 lines of logs:
   ModuleNotFoundError: No module named 'requests'
   ...
```

### Manual Check

```bash
# Xem tất cả containers
docker ps -a | grep kb-

# Xem container nào unhealthy
docker ps --format "table {{.Names}}\t{{.Status}}" | grep kb-

# Xem logs của service bị lỗi
docker logs -f kb-ingestion
```

## 🛠️ Troubleshooting

### Service không khởi động được

#### 1. Kiểm tra dependencies
```bash
# Xem service dependencies
docker-compose config | grep -A 5 "depends_on"

# Đảm bảo dependencies healthy trước
docker-compose ps
```

#### 2. Restart service cụ thể
```bash
# Restart một service
docker-compose restart ingestion

# Hoặc stop/start
docker-compose stop ingestion
docker-compose start ingestion

# Hoặc rebuild
docker-compose up -d --build ingestion
```

#### 3. Xem logs chi tiết
```bash
# Logs real-time
docker-compose logs -f ingestion

# Logs 100 dòng cuối
docker-compose logs --tail=100 ingestion

# Tất cả logs
docker-compose logs > all-logs.txt
```

### Lỗi thường gặp

#### " unhealthy" status

**Nguyên nhân**: Health check fail liên tục

**Fix**:
```bash
# Kiểm tra health check
docker inspect --format='{{.State.Health}}' kb-ingestion

# Xem lỗi chi tiết
docker logs kb-ingestion --tail 20
```

#### "Restarting" status

**Nguyên nhân**: Container crash và đang restart

**Fix**:
```bash
# Xem lý do crash
docker logs kb-ingestion --tail 50

# Stop restart loop
docker-compose stop ingestion

# Fix lỗi rồi start lại
docker-compose start ingestion
```

#### Port conflict

**Nguyên nhân**: Port đã được sử dụng

**Fix**:
```bash
# Tìm process đang dùng port
lsof -i :8002

# Kill process hoặc đổi port trong docker-compose
```

## ⚙️ Configuration

### Environment Variables

Copy file `.env` từ project root hoặc set trực tiếp:

```bash
export RAG_POSTGRES_DSN="postgresql://rag:rag@postgres:5432/rag"
export RAG_MINIO_ENDPOINT="minio:9000"
export RAG_KAFKA_BROKERS="kafka:9092"
```

### Resource Limits

Chỉ `rerank` service có resource limits:
- Memory limit: 2GB
- Memory reservation: 512MB

Thêm limits cho services khác:
```yaml
services:
  query-api:
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: '1'
```

### Logging

Tất cả services đã cấu hình logging:
- Driver: json-file
- Max size: 50-200MB (tùy service)
- Max files: 3-5 files

Xem logs:
```bash
# Tất cả logs
docker-compose logs

# Specific service
docker-compose logs query-api

# Theo thứ gian
docker-compose logs --since=5m
```

## 🔄 Lifecycle Management

### Start
```bash
docker-compose up -d
```

### Stop
```bash
docker-compose stop
# Hoặc: docker-compose down (xóa containers)
```

### Restart
```bash
# Tất cả
docker-compose restart

# Một service
docker-compose restart ingestion

# Rebuild + restart
docker-compose up -d --build ingestion
```

### Clean up
```bash
# Stop và xóa containers
docker-compose down

# Xóa cả volumes (CẨN THẬN - mất dữ liệu!)
docker-compose down -v

# Xóa images
docker-compose down --rmi all
```

## 📊 Monitoring

### Resource Usage
```bash
# Real-time stats
docker stats

# Hoặc
docker-compose stats
```

### Health Dashboard
```bash
# Script tự động check
./check-services.sh

# Hoặc dùng curl để check từng service
curl http://localhost:8001/healthz
curl http://localhost:8002/healthz
```

## 🎯 Production Tips

1. **Dùng reverse proxy**: Nginx (đã có api-gateway)
2. **SSL/TLS**: Thêm certbot hoặc Cloudflare
3. **Backup**: Backup volumes regularly
4. **Monitoring**: Prometheus + Grafana
5. **Logs**: Centralized logging (ELK hoặc Loki)

## 📁 Files

- `docker-compose.unified.yml` - File chính
- `check-services.sh` - Script kiểm tra health
- `nginx.conf` - Nginx configuration (nếu có)

## 🔗 Liên kết

- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [Health Checks](https://docs.docker.com/compose/compose-file/compose-file-v3/#healthcheck)
- [Project Overview](../../PROJECT_OVERVIEW.md)
