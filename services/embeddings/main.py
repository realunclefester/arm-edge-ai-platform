import json
import logging
import os
import time
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

import asyncpg
import numpy as np
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global variables
model = None
db_pool = None

# Database configuration
DATABASE_URL = os.environ.get("DATABASE_URL")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global model, db_pool

    # Load model
    logger.info("Loading sentence transformer model...")
    start_time = time.time()
    model = SentenceTransformer(
        "sentence-transformers/all-MiniLM-L6-v2", cache_folder="/app/models"
    )
    load_time = time.time() - start_time
    logger.info(f"Model loaded in {load_time:.2f} seconds")

    # Initialize database connection
    try:
        db_pool = await asyncpg.create_pool(DATABASE_URL, min_size=2, max_size=10)
        logger.info("Connected to PostgreSQL")
    except Exception as e:
        logger.error(f"Failed to connect to PostgreSQL: {e}")

    yield

    # Shutdown
    if db_pool:
        await db_pool.close()
        logger.info("Closed database connections")
    logger.info("Shutting down...")


# Create FastAPI app
app = FastAPI(
    title="Embeddings Service",
    description="Sentence transformer embeddings for Claude OS",
    version="1.0.0",
    lifespan=lifespan,
)


# Request/Response models
class EmbedRequest(BaseModel):
    texts: List[str]
    normalize: bool = True


class EmbedSingleRequest(BaseModel):
    text: str
    normalize: bool = True


class EmbedResponse(BaseModel):
    embeddings: List[List[float]]
    model: str
    dimension: int
    processing_time: float


class EmbedSingleResponse(BaseModel):
    embedding: List[float]
    model: str
    dimension: int
    processing_time: float


class ModelInfo(BaseModel):
    model_name: str
    embedding_dimension: int
    max_sequence_length: int


class StoreRequest(BaseModel):
    text: str
    source_type: str = "manual"
    source_id: Optional[int] = None
    metadata: Dict[str, Any] = {}
    normalize: bool = True


class StoreResponse(BaseModel):
    id: int
    embedding_id: str
    processing_time: float
    dimension: int


# Endpoints
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    db_status = "connected" if db_pool and not db_pool._closed else "disconnected"
    return {
        "status": (
            "healthy" if model is not None and db_status == "connected" else "partial"
        ),
        "model_loaded": model is not None,
        "database": db_status,
    }


@app.get("/model/info", response_model=ModelInfo)
async def get_model_info():
    """Get information about the loaded model"""
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")

    return ModelInfo(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        embedding_dimension=model.get_sentence_embedding_dimension(),
        max_sequence_length=model.max_seq_length,
    )


@app.post("/embed", response_model=EmbedResponse)
async def embed_batch(request: EmbedRequest):
    """Generate embeddings for multiple texts"""
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")

    if not request.texts:
        raise HTTPException(status_code=400, detail="No texts provided")

    if len(request.texts) > 100:
        raise HTTPException(status_code=400, detail="Maximum 100 texts per request")

    start_time = time.time()

    try:
        # Generate embeddings
        embeddings = model.encode(
            request.texts,
            normalize_embeddings=request.normalize,
            show_progress_bar=False,
        )

        processing_time = time.time() - start_time

        return EmbedResponse(
            embeddings=embeddings.tolist(),
            model="all-MiniLM-L6-v2",
            dimension=model.get_sentence_embedding_dimension(),
            processing_time=processing_time,
        )
    except Exception as e:
        logger.error(f"Error generating embeddings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/embed/single", response_model=EmbedSingleResponse)
async def embed_single(request: EmbedSingleRequest):
    """Generate embedding for a single text"""
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")

    if not request.text:
        raise HTTPException(status_code=400, detail="No text provided")

    start_time = time.time()

    try:
        # Generate embedding
        embedding = model.encode(
            [request.text],
            normalize_embeddings=request.normalize,
            show_progress_bar=False,
        )[0]

        processing_time = time.time() - start_time

        return EmbedSingleResponse(
            embedding=embedding.tolist(),
            model="all-MiniLM-L6-v2",
            dimension=model.get_sentence_embedding_dimension(),
            processing_time=processing_time,
        )
    except Exception as e:
        logger.error(f"Error generating embedding: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/similarity")
async def calculate_similarity(text1: str, text2: str):
    """Calculate cosine similarity between two texts"""
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")

    try:
        embeddings = model.encode([text1, text2], normalize_embeddings=True)
        similarity = np.dot(embeddings[0], embeddings[1])

        return {
            "text1": text1,
            "text2": text2,
            "similarity": float(similarity),
            "similarity_percentage": float(similarity * 100),
        }
    except Exception as e:
        logger.error(f"Error calculating similarity: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/embed/store", response_model=StoreResponse)
async def embed_and_store(request: StoreRequest):
    """Generate embedding and store to database"""
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    if db_pool is None:
        raise HTTPException(status_code=503, detail="Database not connected")

    if not request.text:
        raise HTTPException(status_code=400, detail="No text provided")

    start_time = time.time()

    try:
        # Generate embedding
        embedding = model.encode(
            [request.text],
            normalize_embeddings=request.normalize,
            show_progress_bar=False,
        )[0]

        # Store to database
        async with db_pool.acquire() as conn:
            embedding_id = await conn.fetchval(
                """
                INSERT INTO embeddings_history 
                (original_text, embedding, source_type, source_id, metadata, processing_time_ms)
                VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING id
                """,
                request.text,
                embedding.tolist(),
                request.source_type,
                request.source_id,
                json.dumps(request.metadata),
                int((time.time() - start_time) * 1000),
            )

        processing_time = time.time() - start_time

        return StoreResponse(
            id=embedding_id,
            embedding_id=str(embedding_id),
            processing_time=processing_time,
            dimension=model.get_sentence_embedding_dimension(),
        )

    except Exception as e:
        logger.error(f"Error storing embedding: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/")
async def root():
    """Root endpoint with service info"""
    return {
        "service": "Embeddings Service",
        "version": "2.0.0",
        "endpoints": [
            "/health",
            "/model/info",
            "/embed",
            "/embed/single",
            "/embed/store",
            "/similarity",
            "/docs",
        ],
    }
