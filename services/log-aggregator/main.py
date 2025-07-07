import asyncio
import json
import logging
import os
from collections import defaultdict
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import aiohttp
import asyncpg
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field


@asynccontextmanager
async def lifespan(app: FastAPI):
    global db_pool
    # Startup
    try:
        db_pool = await asyncpg.create_pool(
            DATABASE_URL,
            min_size=2,
            max_size=10,
        )
        logger.info("Connected to PostgreSQL")
    except Exception as e:
        logger.error(f"Failed to connect to PostgreSQL: {e}")

    # Start background aggregation task
    asyncio.create_task(periodic_aggregation())

    yield

    # Shutdown
    await flush_aggregated_logs()
    if db_pool:
        await db_pool.close()
        logger.info("Closed PostgreSQL connection pool")


app = FastAPI(title="Log Aggregator", version="1.0.0", lifespan=lifespan)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
ANALYTICS_NODE_URL = os.environ.get("ANALYTICS_NODE_URL", "http://analytics-node:8002")
AGGREGATION_WINDOW = int(os.environ.get("AGGREGATION_WINDOW", "30"))  # seconds
BATCH_SIZE = int(os.environ.get("BATCH_SIZE", "10"))

# PostgreSQL configuration
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://ai_platform_user:ai_platform_secure_2025@postgres:5432/ai_platform_db",
)

# In-memory storage for aggregation
log_buffer = defaultdict(list)
last_flush = datetime.now()
db_pool = None


class LogEntry(BaseModel):
    message: str
    source: str
    timestamp: Optional[str] = None
    level: Optional[str] = "info"
    metadata: Dict[str, Any] = Field(default_factory=dict)


class WorkflowLogEntry(BaseModel):
    workflow_id: str
    node_id: Optional[str] = None
    message: str
    level: str = "info"
    duration_ms: Optional[int] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AggregatedLog(BaseModel):
    text: str
    metadata: Dict[str, Any]


async def periodic_aggregation():
    """Background task to periodically aggregate and send logs"""
    while True:
        await asyncio.sleep(AGGREGATION_WINDOW)
        await flush_aggregated_logs()


async def save_to_postgres(aggregated_log: AggregatedLog):
    """Save aggregated log to PostgreSQL"""
    if not db_pool:
        logger.error("No database connection available")
        return False

    try:
        async with db_pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO aggregated_logs 
                   (source, message, aggregation_count, error_count, info_count, metadata)
                   VALUES ($1, $2, $3, $4, $5, $6)""",
                aggregated_log.metadata.get("source", "unknown"),
                aggregated_log.text,
                aggregated_log.metadata.get("total_logs", 1),
                aggregated_log.metadata.get("error_count", 0),
                aggregated_log.metadata.get("info_count", 0),
                json.dumps(aggregated_log.metadata),
            )
            logger.info(f"Successfully saved aggregated log to PostgreSQL")
            return True
    except Exception as e:
        logger.error(f"Error saving to PostgreSQL: {e}")
        return False


async def flush_aggregated_logs():
    """Aggregate buffered logs and send to Analytics Node"""
    global log_buffer, last_flush

    if not log_buffer:
        return

    logger.info(
        f"Flushing {sum(len(logs) for logs in log_buffer.values())} logs from buffer"
    )

    # Group logs by source and create aggregated entries
    for source, logs in log_buffer.items():
        if not logs:
            continue

        # Simple aggregation: combine messages, count occurrences
        message_counts = defaultdict(int)
        error_logs = []
        info_logs = []

        for log in logs:
            message_counts[log["message"]] += 1
            if log.get("level", "info").lower() in ["error", "warning"]:
                error_logs.append(log)
            else:
                info_logs.append(log)

        # Create aggregated message
        if error_logs:
            # Priority to errors
            agg_text = (
                f"[{source}] {len(error_logs)} errors, {len(info_logs)} info messages. "
            )
            agg_text += (
                f"Errors: {'; '.join([log['message'][:100] for log in error_logs[:3]])}"
            )
        else:
            # Just info messages
            top_messages = sorted(
                message_counts.items(), key=lambda x: x[1], reverse=True
            )[:3]
            agg_text = f"[{source}] Activity summary: {'; '.join([f'{msg} ({count}x)' for msg, count in top_messages])}"

        # Create aggregated log entry
        aggregated = AggregatedLog(
            text=agg_text,
            metadata={
                "source": source,
                "aggregation_window": AGGREGATION_WINDOW,
                "total_logs": len(logs),
                "error_count": len(error_logs),
                "info_count": len(info_logs),
                "timestamp": datetime.now().isoformat(),
                "log_sources": list(set([log.get("source", source) for log in logs])),
            },
        )

        # Save to PostgreSQL
        await save_to_postgres(aggregated)

    # Clear buffer
    log_buffer = defaultdict(list)
    last_flush = datetime.now()


@app.post("/logs/ingest")
async def ingest_log(log_entry: LogEntry):
    """Generic log ingestion endpoint"""
    # Add to buffer
    log_data = {
        "message": log_entry.message,
        "source": log_entry.source,
        "level": log_entry.level,
        "timestamp": log_entry.timestamp or datetime.now().isoformat(),
        "metadata": log_entry.metadata,
    }

    log_buffer[log_entry.source].append(log_data)

    # Check if buffer should be flushed early (errors or buffer full)
    if (
        log_entry.level.lower() in ["error", "critical"]
        or sum(len(logs) for logs in log_buffer.values()) >= BATCH_SIZE
    ):
        await flush_aggregated_logs()

    return {"status": "accepted", "buffer_size": len(log_buffer[log_entry.source])}


@app.post("/logs/workflow")
async def ingest_workflow_log(workflow_log: WorkflowLogEntry):
    """Specialized endpoint for workflow logs (Node-RED, N8N, etc.)"""
    # Convert workflow log to standard format
    log_entry = LogEntry(
        message=f"[{workflow_log.workflow_id}] {workflow_log.message}",
        source=f"workflow_{workflow_log.workflow_id}",
        level=workflow_log.level,
        metadata={
            "workflow_id": workflow_log.workflow_id,
            "node_id": workflow_log.node_id,
            "duration_ms": workflow_log.duration_ms,
            **workflow_log.metadata,
        },
    )

    return await ingest_log(log_entry)


@app.post("/logs/http")
async def ingest_http_log(
    method: str,
    url: str,
    status_code: int,
    response_time_ms: int,
    source: str = "http_monitoring",
):
    """Specialized endpoint for HTTP monitoring logs"""
    level = "error" if status_code >= 400 else "info"
    message = f"{method} {url} -> {status_code} ({response_time_ms}ms)"

    log_entry = LogEntry(
        message=message,
        source=source,
        level=level,
        metadata={
            "method": method,
            "url": url,
            "status_code": status_code,
            "response_time_ms": response_time_ms,
            "endpoint_type": "http_monitoring",
        },
    )

    return await ingest_log(log_entry)


@app.get("/health")
async def health_check():
    db_status = "connected" if db_pool and not db_pool._closed else "disconnected"
    return {
        "status": "healthy" if db_status == "connected" else "unhealthy",
        "database": db_status,
        "buffer_size": sum(len(logs) for logs in log_buffer.values()),
        "sources": list(log_buffer.keys()),
        "last_flush": last_flush.isoformat(),
    }


@app.get("/stats")
async def get_stats():
    """Get aggregator statistics"""
    return {
        "total_buffered": sum(len(logs) for logs in log_buffer.values()),
        "sources": {source: len(logs) for source, logs in log_buffer.items()},
        "last_flush": last_flush.isoformat(),
        "config": {
            "aggregation_window": AGGREGATION_WINDOW,
            "batch_size": BATCH_SIZE,
            "analytics_node_url": ANALYTICS_NODE_URL,
        },
    }


@app.post("/flush")
async def manual_flush():
    """Manually trigger log aggregation and flush"""
    await flush_aggregated_logs()
    return {"status": "flushed", "timestamp": datetime.now().isoformat()}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8004)
