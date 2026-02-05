# 🧪 Testing Guide cho Solo Dev

> **Nguyên tắc**: Test nhỏ → Test nhanh → Test rõ ràng

## 📁 Cấu trúc Tests

```
tests/
├── conftest.py              # Pytest fixtures
├── requirements.txt         # Test dependencies
├── smoke_test.py           # ✅ Quick health check
├── e2e/
│   └── test_pipeline.py    # 🔄 Full E2E tests
└── postman/
    └── rag-platform.json   # 📮 Postman collection
```

## 🚀 Quick Start

### 1. Smoke Test (30 giây)

```bash
# Check tất cả services healthy
python tests/smoke_test.py

# Hoặc dùng curl
curl http://localhost:8000/health
curl http://localhost:8001/healthz
curl http://localhost:8003/healthz
```

### 2. Postman/Newman (Manual + Automated)

```bash
# Import vào Postman
tests/postman/rag-platform.json

# Chạy bằng Newman (CLI)
npm install -g newman

newman run tests/postman/rag-platform.json \
  --env-var "base_url=http://localhost:8000"
```

### 3. E2E Tests (Automated)

```bash
# Install dependencies
cd tests
pip install -r requirements.txt

# Run smoke tests
pytest smoke_test.py -v

# Run specific test
pytest e2e/test_pipeline.py::TestPipeline::test_health_all_services -v

# Run full pipeline test
pytest e2e/test_pipeline.py::TestPipeline::test_full_document_pipeline -v -s

# Run all E2E tests
pytest e2e/ -v --tb=short
```

## 📋 Test Scenarios

### Phase 1: Health Checks
- [x] Gateway healthy
- [x] All services healthy
- [x] API availability

### Phase 2: Ingestion
- [x] Webhook ingestion
- [x] Pull from URL
- [x] Document metadata

### Phase 3: Search & RAG
- [x] Semantic search
- [x] Hybrid search (BM25 + Vector)
- [x] RAG query với citations
- [x] Reranking

### Phase 4: Extraction
- [x] Sync extraction
- [x] Async extraction job
- [x] Schema validation

### Phase 5: Tenant Isolation
- [x] Multi-tenant data separation
- [x] Cross-tenant access denied

## 🔧 Tips cho Solo Dev

### 1. Chạy test nhanh khi dev

```bash
# Alias trong ~/.zshrc hoặc ~/.bashrc
alias rag-smoke='python ~/projects/rag/tests/smoke_test.py'
alias rag-test='cd ~/projects/rag/tests && pytest e2e/ -v'
```

### 2. Test song song với dev

```bash
# Terminal 1: Chạy services
docker-compose up

# Terminal 2: Watch và auto-test
watch -n 10 'python tests/smoke_test.py'
```

### 3. Debug khi fail

```bash
# Xem chi tiết lỗi
pytest e2e/test_pipeline.py -v --tb=long

# Chạy với logging
pytest e2e/test_pipeline.py -v -s --log-cli-level=DEBUG
```

### 4. Test data riêng biệt

Mỗi test tự động tạo tenant ID unique → Không conflict data

## 🎯 Demo Checklist

Trước khi demo cho stakeholder:

```bash
# 1. Smoke test (30s)
python tests/smoke_test.py

# 2. Full pipeline test (2 phút)
pytest e2e/test_pipeline.py::TestPipeline::test_full_document_pipeline -v

# 3. Manual test với Postman
# Import collection → Run từng folder
```

## 🚨 Troubleshooting

| Lỗi | Nguyên nhân | Fix |
|-----|-------------|-----|
| Connection refused | Service chưa start | `docker-compose up -d` |
| 401 Unauthorized | Thiếu tenant header | Thêm `X-Tenant-ID: demo` |
| 400 Bad Request | Payload sai format | Check JSON schema |
| Timeout | Service chậm | Tăng timeout trong test |

## 📊 Observability trong Test

Tests đã tích hợp observability:
- Clear error messages
- Tenant isolation verification
- Response validation
- Pipeline timing logs

## 🔄 CI/CD Integration

```yaml
# .github/workflows/test.yml
test:
  steps:
    - name: Smoke Test
      run: python tests/smoke_test.py
    
    - name: E2E Tests
      run: pytest tests/e2e/ -v
    
    - name: Postman Tests
      run: newman run tests/postman/rag-platform.json
```

## 💡 Lợi ích

1. **Không burnout**: Mỗi test chạy < 30 giây
2. **Dễ debug**: Clear error messages, tenant isolation
3. **Dễ demo**: Postman collection sẵn có
4. **Tự động**: Chạy trong CI/CD
5. **Solo friendly**: Không cần team để maintain
