from datetime import datetime, UTC
import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI

sys.path.insert(0, "/Users/thiennlinh/Documents/New project/shared")

from config import settings
from utils.qdrant_store import QdrantStore, init_qdrant, close_qdrant
from routes.cache import cache_router
from routes.chunks import router as chunks_router
from routes.extract import extract_router
from routes.rag import rag_router
from routes.search import search_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ===== Startup =====
    print("🚀 Starting Query API...")

    # Initialize Qdrant
    await init_qdrant()
    print("✅ Qdrant pool initialized")

    # Ensure collection exists
    try:
        qdrant = QdrantStore()
        from qdrant_client.http.models import Distance, VectorParams

        http_client = qdrant._get_http_client()
        try:
            collections = http_client.get_collections()
            if not any(
                c.name == settings.qdrant_collection for c in collections.collections
            ):
                print(
                    f"⚠️ Collection '{settings.qdrant_collection}' not found, creating..."
                )
                http_client.create_collection(
                    collection_name=settings.qdrant_collection,
                    vectors_config=VectorParams(
                        size=settings.embedding_dim, distance=Distance.COSINE
                    ),
                )
                print(f"✅ Created collection: {settings.qdrant_collection}")
            else:
                print(f"✅ Collection exists: {settings.qdrant_collection}")
        except Exception as e:
            print(f"⚠️ Could not verify collection: {e}")
    except Exception as e:
        print(f"⚠️ Could not ensure collection: {e}")

    # Model warmup: preload embedding model into memory
    print("🔥 Warming up embedding model...")
    try:
        from utils.embedding import embedder_factory

        embedder = embedder_factory()
        _ = embedder.embed_query("warmup query")
        print("✅ Embedding model warmed up")
    except Exception as e:
        print(f"⚠️ Model warmup failed: {e}")

    print("✅ Query API startup complete")

    yield

    # ===== Shutdown =====
    print("🛑 Shutting down Query API...")
    await close_qdrant()
    print("✅ Query API shutdown complete")
    print("🧹 Qdrant pool closed")


app = FastAPI(title="Query API", lifespan=lifespan)
app.include_router(cache_router)
app.include_router(chunks_router)
app.include_router(extract_router)
app.include_router(rag_router)
app.include_router(search_router)


@app.get("/healthz")
def healthz():
    return {"status": "ok", "time": datetime.now(UTC).isoformat()}
