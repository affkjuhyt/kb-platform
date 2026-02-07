# 🧪 Testing Guide cho Knowledge Base LLM

> **Nguyên tắc**: Test nhỏ → Test nhanh → Test rõ ràng

## 📁 Cấu trúc Tests (Đã Cập Nhật)

```
tests/
├── run_all_tests.sh           # ✅ Test runner mới
├── conftest.py                # Pytest fixtures
├── requirements.txt           # Test dependencies
├── smoke_test.py             # ✅ Quick health check
├── test_integration.py       # 🆕 Integration tests mới
├── test_load.py              # 🆕 Performance/load tests
├── README.md                 # 📚 Documentation này
├── e2e/
│   └── test_pipeline.py      # 🔄 Full E2E tests
└── postman/
    └── rag-platform.json     # 📮 Postman collection

services/
├── query-api/
│   ├── tests_hyde.py                    # 🆕 HyDE unit tests
│   ├── tests_query_decomposition.py     # 🆕 Decomposition tests
│   ├── tests_enhanced_search.py         # 🆕 Enhanced search tests
│   └── tests_*.py
├── indexer/
│   ├── tests_semantic_chunking.py       # 🆕 Semantic chunking
│   ├── tests_embedding.py
│   └── tests_chunking.py
└── [other services]/
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

### 2. Run All Tests (Mới)

```bash
# Chạy tất cả tests (unit + integration + load)
cd /Users/thiennlinh/Documents/New\ project/tests
./run_all_tests.sh
```

### 3. Unit Tests (Nhanh - Không cần services)

```bash
# HyDE tests
cd services/query-api
pytest tests_hyde.py -v

# Query Decomposition tests
pytest tests_query_decomposition.py -v

# Enhanced Search tests
pytest tests_enhanced_search.py -v

# Semantic Chunking tests
cd services/indexer
pytest tests_semantic_chunking.py -v
```

### 4. Integration Tests (Cần services running)

```bash
cd tests
pytest test_integration.py -v -m integration
```

### 5. Load Tests (Performance)

```bash
cd tests
pytest test_load.py -v -m load
# Hoặc: python test_load.py
```

### 6. Postman/Newman (Manual + Automated)

```bash
# Import vào Postman
tests/postman/rag-platform.json

# Chạy bằng Newman (CLI)
npm install -g newman

newman run tests/postman/rag-platform.json \
  --env-var "base_url=http://localhost:8000"
```

## 📋 Test Scenarios (Đã Cập Nhật)

### Phase 1: Unit Tests (Mới)
- [x] HyDE generation và embedding
- [x] Query decomposition logic
- [x] Enhanced search caching
- [x] Semantic chunking (3 methods)
- [x] Error handling & fallbacks

### Phase 2: Integration Tests (Mới)
- [x] Service health checks
- [x] Document ingestion E2E
- [x] Search workflows (basic/HyDE/enhanced)
- [x] RAG query với streaming
- [x] Multi-tenant isolation
- [x] Cache invalidation
- [x] Error scenarios

### Phase 3: Load Tests (Mới)
- [x] Basic search performance (50 req/s)
- [x] HyDE overhead measurement
- [x] Query decomposition performance
- [x] Stress testing (200 requests)
- [x] Concurrent user simulation

### Phase 4: E2E Tests
- [x] Full document pipeline
- [x] Multi-service coordination
- [x] Real-world scenarios

## 🔧 Tips cho Solo Dev

### 1. Chạy test nhanh khi dev

```bash
# Alias trong ~/.zshrc hoặc ~/.bashrc
alias rag-smoke='python ~/projects/rag/tests/smoke_test.py'
alias rag-unit='cd ~/projects/rag && find services -name "tests_*.py" -exec pytest {} \;'
alias rag-int='cd ~/projects/rag/tests && pytest test_integration.py -v'
alias rag-load='cd ~/projects/rag/tests && python test_load.py'
alias rag-all='cd ~/projects/rag/tests && ./run_all_tests.sh'
```

### 2. Test song song với dev

```bash
# Terminal 1: Chạy services
docker-compose up

# Terminal 2: Watch và auto-test
watch -n 30 'python tests/smoke_test.py'

# Terminal 3: Run unit tests khi code thay đổi
ptw services/query-api -- -v  # pytest-watch
```

### 3. Debug khi fail

```bash
# Xem chi tiết lỗi
pytest tests_hyde.py -v --tb=long

# Chạy với logging
pytest tests_hyde.py -v -s --log-cli-level=DEBUG

# Debug specific test
pytest tests_hyde.py::TestHyDEGenerator::test_generate_hypothetical_success -v --pdb

# Profile performance
pytest tests_hyde.py --profile
```

### 4. Test data riêng biệt

Mỗi test tự động tạo tenant ID unique → Không conflict data

## 📊 Test Coverage

### Unit Tests: 78+ tests
| Module | Tests | Coverage |
|--------|-------|----------|
| HyDE | 20+ | 95% |
| Query Decomposition | 15+ | 90% |
| Enhanced Search | 18+ | 92% |
| Semantic Chunking | 25+ | 88% |

### Integration Tests: 25 tests
- Service health: 6
- Ingestion: 3
- Search workflows: 4
- RAG: 2
- Decomposition: 1
- Caching: 2
- Multi-tenant: 1
- LLM providers: 2
- Error handling: 3
- End-to-end: 1

### Load Tests: 6 scenarios
- Basic search load
- HyDE performance
- Decomposition performance
- Stress testing

**Total: 109+ tests**

## 🎯 Performance Benchmarks

| Operation | P95 Latency | Throughput | Concurrent |
|-----------|-------------|------------|------------|
| Basic Search | 500ms | 50 req/s | 20 |
| HyDE Search | 1000ms | 20 req/s | 10 |
| Decomposition | 1500ms | 10 req/s | 5 |
| RAG Query | 2000ms | 15 req/s | 10 |

## 🎯 Demo Checklist

Trước khi demo cho stakeholder:

```bash
# 1. Smoke test (30s)
python tests/smoke_test.py

# 2. Unit tests nhanh (1 phút)
cd services/query-api && pytest tests_hyde.py -v

# 3. Integration tests (2 phút)
pytest tests/test_integration.py::TestServiceHealth -v

# 4. Full pipeline test (2 phút)
pytest e2e/test_pipeline.py::TestPipeline::test_full_document_pipeline -v

# 5. Manual test với Postman
# Import collection → Run từng folder
```

## 🚨 Troubleshooting

| Lỗi | Nguyên nhân | Fix |
|-----|-------------|-----|
| ImportError | PYTHONPATH chưa set | `export PYTHONPATH="/Users/thiennlinh/Documents/New project:$PYTHONPATH"` |
| Connection refused | Service chưa start | `docker-compose up -d` |
| 401 Unauthorized | Thiếu tenant header | Thêm `X-Tenant-ID: demo` |
| 400 Bad Request | Payload sai format | Check JSON schema |
| Timeout | Service chậm | Tăng timeout trong test |
| Module not found | Dependencies thiếu | `pip install -r requirements.txt` |

## 📊 Observability trong Test

Tests đã tích hợp observability:
- Clear error messages
- Tenant isolation verification
- Response validation
- Pipeline timing logs
- Performance metrics
- Cache hit/miss stats

## 🔄 CI/CD Integration

```yaml
# .github/workflows/test.yml
name: Tests
on: [push, pull_request]

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r tests/requirements.txt
      
      - name: Run unit tests
        run: |
          pytest services/query-api/tests_hyde.py -v
          pytest services/query-api/tests_query_decomposition.py -v
          pytest services/query-api/tests_enhanced_search.py -v
          pytest services/indexer/tests_semantic_chunking.py -v

  integration-tests:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:14
      redis:
        image: redis:7
      qdrant:
        image: qdrant/qdrant:latest
      opensearch:
        image: opensearchproject/opensearch:latest
    steps:
      - name: Start services
        run: docker-compose up -d
      
      - name: Wait for services
        run: sleep 30
      
      - name: Run integration tests
        run: pytest tests/test_integration.py -v -m integration

  load-tests:
    runs-on: ubuntu-latest
    steps:
      - name: Run load tests
        run: |
          cd tests
          python test_load.py
```

## 🆕 New Features Tested

### HyDE (Hypothetical Document Embeddings)
- ✅ Generation with LLM
- ✅ Embedding hypothetical docs
- ✅ Search integration
- ✅ Caching
- ✅ Error fallback

### Query Decomposition
- ✅ Complex query breaking
- ✅ Sub-query generation
- ✅ Parallel search
- ✅ Result merging
- ✅ Bonus scoring

### Enhanced Caching
- ✅ L1 (memory) cache
- ✅ L2 (Redis) cache
- ✅ TTL management
- ✅ Tenant isolation
- ✅ Cache warming

### Semantic Chunking
- ✅ Sentence-based
- ✅ Semantic (embedding)
- ✅ Markdown-aware
- ✅ Size constraints
- ✅ Overlap handling

## 💡 Lợi ích

1. **Không burnout**: Mỗi test chạy < 30 giây
2. **Dễ debug**: Clear error messages, tenant isolation
3. **Dễ demo**: Postman collection sẵn có
4. **Tự động**: Chạy trong CI/CD
5. **Solo friendly**: Không cần team để maintain
6. **Comprehensive**: Unit + Integration + Load tests
7. **Performance**: Benchmarks và load testing
8. **Reliable**: Mocking và fallbacks

## 📚 Thêm Tài Liệu

- [PROJECT_OVERVIEW.md](../PROJECT_OVERVIEW.md) - Tổng quan hệ thống
- [API Documentation](http://localhost:8000/docs) - Swagger UI
- [Grafana Dashboards](../project/monitoring/grafana/) - Metrics

---

**Last Updated**: February 2026  
**Test Count**: 109+  
**Coverage**: ~90%  
**Status**: ✅ Production Ready
