import json
import logging
import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional

import asyncpg
import numpy as np
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sklearn.cluster import DBSCAN
from sklearn.metrics.pairwise import cosine_similarity, euclidean_distances

# import aiohttp  # No longer needed - removed embeddings and Qdrant


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    app.state.db_pool = await asyncpg.create_pool(DATABASE_URL)
    await init_db()

    yield

    # Shutdown
    await app.state.db_pool.close()


app = FastAPI(title="Analytics Node", version="1.0.0", lifespan=lifespan)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is required")
# QDRANT_URL = os.environ.get("QDRANT_URL", "http://qdrant:6333")  # Replaced by pgvector
# EMBEDDINGS_URL = os.environ.get("EMBEDDINGS_URL", "http://embeddings:8001")  # Removed - no embeddings


class PreStorageRequest(BaseModel):
    text: str
    vector: Optional[List[float]] = None
    metadata: Dict[str, Any] = {}


class PostStorageRequest(BaseModel):
    vector_id: str
    vector: List[float]
    storage_result: Dict[str, Any] = {}


class AnalyticsResponse(BaseModel):
    metrics: Dict[str, Any]
    decisions: Dict[str, Any]
    timestamp: datetime


async def init_db():
    async with app.state.db_pool.acquire() as conn:
        # vector_analytics table already exists with proper pgvector structure
        # Just ensure space_evolution exists
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS space_evolution (
                id SERIAL PRIMARY KEY,
                timestamp TIMESTAMPTZ DEFAULT NOW(),
                cluster_count INT,
                total_vectors INT,
                avg_distance FLOAT,
                density_map JSONB,
                significant_changes JSONB
            )
        """
        )


def calculate_vector_metrics(vector: np.ndarray) -> Dict[str, float]:
    """Calculate quality metrics for a single vector"""
    # Calculate entropy safely
    entropy = -np.sum(np.abs(vector) * np.log(np.abs(vector) + 1e-10))

    metrics = {
        "magnitude": float(np.linalg.norm(vector)),
        "sparsity": float(np.sum(np.abs(vector) < 0.01) / len(vector)),
        "entropy": float(entropy if not np.isnan(entropy) else 0.0),
        "mean": float(np.mean(vector)),
        "std": float(np.std(vector)),
        "max": float(np.max(vector)),
        "min": float(np.min(vector)),
    }

    # Replace any NaN/inf values with 0
    for key, value in metrics.items():
        if np.isnan(value) or np.isinf(value):
            metrics[key] = 0.0

    return metrics


# generate_embedding_from_text() function removed - no embeddings service
# Analytics now expects vectors to be provided in requests


async def get_similar_vectors(vector: np.ndarray, limit: int = 10) -> List[Dict]:
    """Query pgvector for similar vectors"""
    async with app.state.db_pool.acquire() as conn:
        try:
            # Convert numpy array to pgvector format
            vector_str = f"[{','.join(map(str, vector.tolist()))}]"

            # pgvector similarity search using cosine distance
            query = """
                SELECT 
                    vector_id::text as id,
                    embedding <=> $1::vector as distance,
                    embedding,
                    original_text as text,
                    metrics,
                    decisions,
                    timestamp
                FROM vector_analytics 
                WHERE embedding IS NOT NULL
                ORDER BY embedding <=> $1::vector
                LIMIT $2
            """

            rows = await conn.fetch(query, vector_str, limit)

            # Convert to Qdrant-compatible format
            results = []
            for row in rows:
                # Convert pgvector embedding directly to list
                embedding_values = list(row["embedding"]) if row["embedding"] else []

                results.append(
                    {
                        "id": row["id"],
                        "score": 1
                        - row["distance"],  # Convert distance to similarity score
                        "payload": {
                            "text": row["text"],
                            "metrics": row["metrics"],
                            "decisions": row["decisions"],
                            "timestamp": (
                                row["timestamp"].isoformat()
                                if row["timestamp"]
                                else None
                            ),
                        },
                        "vector": embedding_values,  # Return the actual stored vector
                    }
                )

            return results

        except Exception as e:
            logger.error(f"Error querying similar vectors: {e}")
            return []


# NOTE: This function is no longer used - storage happens directly in analyze_pre_storage()
# Keeping it commented for reference
'''
async def store_vector_to_pgvector(vector: np.ndarray, text: str, metadata: Dict) -> str:
    """Store vector to pgvector and return point ID"""
    point_id = str(uuid.uuid4())
    
    async with app.state.db_pool.acquire() as conn:
        try:
            # Convert numpy array to pgvector format
            vector_str = f"[{','.join(map(str, vector.tolist()))}]"
            
            # Insert new record with embedding, text and metadata all at once
            query = """
                INSERT INTO vector_analytics (
                    vector_id, 
                    embedding, 
                    original_text,
                    analytics_type,
                    vector_dimension,
                    timestamp
                ) VALUES ($1::uuid, $2::vector, $3, $4, $5, NOW())
                RETURNING id
            """
            
            # Insert the record
            result_id = await conn.fetchval(
                query, 
                point_id,  # vector_id as UUID string
                vector_str,  # embedding as pgvector string
                text,  # original text
                'storage',  # analytics_type
                len(vector)  # vector dimension
            )
            
            if result_id:
                logger.info(f"Vector stored to pgvector with ID: {point_id}, row ID: {result_id}")
            else:
                logger.error(f"Failed to store vector - no ID returned")
                return f"failed_{point_id}"
            
            return point_id
            
        except Exception as e:
            logger.error(f"Failed to store vector to pgvector: {e}")
            return f"failed_{point_id}"
'''


def detect_anomaly(vector: np.ndarray, neighbors: List[np.ndarray]) -> float:
    """Calculate anomaly score based on distance to neighbors"""
    if not neighbors:
        return 0.0

    distances = [np.linalg.norm(vector - n) for n in neighbors]
    avg_distance = np.mean(distances)
    std_distance = np.std(distances)

    # Z-score based anomaly
    if std_distance > 0:
        z_score = (avg_distance - np.mean(distances)) / std_distance
        return float(min(abs(z_score), 5.0) / 5.0)  # Normalize to 0-1
    return 0.0


@app.post("/analyze/pre-storage", response_model=AnalyticsResponse)
async def analyze_pre_storage(request: PreStorageRequest):
    """Analyze vector before storage"""

    # Vector must be provided - no embeddings generation
    if not request.vector or len(request.vector) == 0:
        raise HTTPException(
            status_code=400,
            detail="Vector is required - no embeddings service available",
        )

    vector = np.array(request.vector)

    # Get similar vectors from Qdrant
    similar = await get_similar_vectors(vector)

    # Calculate metrics
    quality_metrics = calculate_vector_metrics(vector)

    # Check for near-duplicates
    duplicate_threshold = 0.95
    is_duplicate = False
    closest_match = None

    if similar:
        similarities = []
        for item in similar:
            other_vector = np.array(item["vector"])
            sim = cosine_similarity([vector], [other_vector])[0][0]
            similarities.append(sim)

            if sim > duplicate_threshold:
                is_duplicate = True
                closest_match = {
                    "id": item["id"],
                    "similarity": float(sim),
                    "payload": item.get("payload", {}),
                }
                break

        quality_metrics["max_similarity"] = float(max(similarities))
        quality_metrics["avg_similarity"] = float(np.mean(similarities))

    # Calculate anomaly score
    if similar:
        neighbor_vectors = [np.array(item["vector"]) for item in similar[:5]]
        anomaly_score = detect_anomaly(vector, neighbor_vectors)
    else:
        anomaly_score = 0.0

    # Make storage decision
    should_store = not is_duplicate and quality_metrics["magnitude"] > 0.1

    metrics = {
        **quality_metrics,
        "anomaly_score": anomaly_score,
        "neighbor_count": len(similar),
    }

    decisions = {
        "should_store": should_store,
        "is_duplicate": is_duplicate,
        "closest_match": closest_match,
        "quality_pass": quality_metrics["magnitude"] > 0.1,
    }

    # Generate vector_id for this analysis
    vector_id = str(uuid.uuid4())
    decisions["vector_id"] = vector_id

    # Store everything in one transaction
    async with app.state.db_pool.acquire() as conn:
        if should_store:
            # Store with embedding
            vector_str = f"[{','.join(map(str, vector.tolist()))}]"
            await conn.execute(
                """INSERT INTO vector_analytics 
                   (vector_id, embedding, original_text, analytics_type, 
                    vector_dimension, metrics, decisions) 
                   VALUES ($1, $2, $3, $4, $5, $6, $7)""",
                vector_id,
                vector_str,  # Convert to pgvector format
                request.text,
                "pre_storage",
                len(vector),
                json.dumps(metrics),
                json.dumps(decisions),
            )
            decisions["stored_vector_id"] = vector_id
            logger.info(f"Stored vector with analytics: {vector_id}")
        else:
            # Store only analytics without embedding
            await conn.execute(
                """INSERT INTO vector_analytics 
                   (vector_id, analytics_type, metrics, decisions, original_text) 
                   VALUES ($1, $2, $3, $4, $5)""",
                vector_id,
                "pre_storage",
                json.dumps(metrics),
                json.dumps(decisions),
                request.text,
            )
            logger.info(f"Stored analytics only (no vector): {vector_id}")

    return AnalyticsResponse(
        metrics=metrics, decisions=decisions, timestamp=datetime.utcnow()
    )


@app.post("/analyze/post-storage", response_model=AnalyticsResponse)
async def analyze_post_storage(request: PostStorageRequest):
    """Analyze vector after storage"""
    vector = np.array(request.vector)

    # Get updated neighbors
    neighbors = await get_similar_vectors(vector, limit=20)

    # Calculate impact metrics
    if neighbors:
        # Remove self from neighbors
        neighbors = [n for n in neighbors if n["id"] != request.vector_id]

        # Calculate how this vector changed the local neighborhood
        distances = []
        for neighbor in neighbors[:10]:
            other_vector = np.array(neighbor["vector"])
            dist = float(np.linalg.norm(vector - other_vector))
            distances.append(dist)

        avg_distance = np.mean(distances) if distances else 0

        metrics = {
            "impact_radius": float(np.max(distances)) if distances else 0,
            "avg_neighbor_distance": float(avg_distance),
            "neighbor_count": len(neighbors),
            "local_density": 1.0 / (avg_distance + 0.1) if avg_distance > 0 else 0,
        }
    else:
        metrics = {
            "impact_radius": 0,
            "avg_neighbor_distance": 0,
            "neighbor_count": 0,
            "local_density": 0,
        }

    decisions = {
        "created_new_cluster": metrics["neighbor_count"] < 3,
        "high_impact": metrics["impact_radius"] > 1.0,
        "dense_area": metrics["local_density"] > 5.0,
    }

    # Store analytics
    async with app.state.db_pool.acquire() as conn:
        await conn.execute(
            """INSERT INTO vector_analytics 
               (vector_id, analytics_type, metrics, decisions) 
               VALUES ($1, $2, $3, $4)""",
            request.vector_id,
            "post_storage",
            json.dumps(metrics),
            json.dumps(decisions),
        )

    return AnalyticsResponse(
        metrics=metrics, decisions=decisions, timestamp=datetime.utcnow()
    )


@app.get("/analyze/space")
async def analyze_space():
    """Analyze overall vector space"""
    # This would need access to all vectors in Qdrant
    # For now, return basic stats from our analytics

    async with app.state.db_pool.acquire() as conn:
        recent_analytics = await conn.fetch(
            """SELECT metrics, decisions 
               FROM vector_analytics 
               WHERE timestamp > NOW() - INTERVAL '1 hour'
               ORDER BY timestamp DESC 
               LIMIT 100"""
        )

        total_vectors = await conn.fetchval(
            "SELECT COUNT(DISTINCT vector_id) FROM vector_analytics"
        )

    if recent_analytics:
        anomaly_scores = []
        similarities = []

        for record in recent_analytics:
            metrics = json.loads(record["metrics"])
            if "anomaly_score" in metrics:
                anomaly_scores.append(metrics["anomaly_score"])
            if "avg_similarity" in metrics:
                similarities.append(metrics["avg_similarity"])

        space_metrics = {
            "total_vectors_analyzed": total_vectors,
            "recent_samples": len(recent_analytics),
            "avg_anomaly_score": (
                float(np.mean(anomaly_scores)) if anomaly_scores else 0
            ),
            "avg_similarity": float(np.mean(similarities)) if similarities else 0,
            "anomaly_trend": (
                "increasing"
                if anomaly_scores and anomaly_scores[-1] > anomaly_scores[0]
                else "stable"
            ),
        }
    else:
        space_metrics = {
            "total_vectors_analyzed": 0,
            "recent_samples": 0,
            "avg_anomaly_score": 0,
            "avg_similarity": 0,
            "anomaly_trend": "unknown",
        }

    return {"space_metrics": space_metrics, "timestamp": datetime.utcnow()}


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "analytics-node"}
