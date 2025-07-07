# Analytics Service

A FastAPI-based service for vector analysis, clustering, and similarity computations optimized for ARM architecture.

## Overview

The Analytics Service provides advanced data analysis capabilities for the ARM Edge AI Platform, focusing on vector operations, clustering algorithms, and similarity analysis. It integrates directly with PostgreSQL+pgvector for efficient vector storage and retrieval.

## Features

### Core Analytics
- **Vector Similarity**: Cosine similarity and Euclidean distance calculations
- **Clustering**: DBSCAN clustering for vector groupings
- **Batch Processing**: Efficient processing of large vector datasets
- **Statistical Analysis**: Comprehensive metrics and insights

### Database Integration
- **PostgreSQL + pgvector**: Direct integration for vector operations
- **Connection Pooling**: Optimized database connections
- **Async Operations**: Non-blocking database queries

### ARM Optimization
- **scikit-learn**: ARM-optimized machine learning algorithms
- **NumPy**: Efficient numerical computations
- **Memory Efficient**: Designed for Raspberry Pi constraints

## API Endpoints

### Health Check
- `GET /health` - Service health status with database connectivity

### Analytics Operations
- `POST /pre_storage_analytics` - Analyze vectors before storage
- `POST /post_storage_analytics` - Analyze vectors after storage
- `POST /similarity_analysis` - Compute vector similarities
- `POST /cluster_analysis` - Perform DBSCAN clustering

## Configuration

### Environment Variables
```bash
DATABASE_URL=postgresql://user:password@postgres:5432/database
LOG_LEVEL=INFO
```

### Docker Configuration
```dockerfile
FROM python:3.11-slim
# ARM-optimized dependencies
# FastAPI + scikit-learn + NumPy
```

## Usage Examples

### Basic Similarity Analysis
```bash
curl -X POST http://localhost:8002/similarity_analysis \
  -H "Content-Type: application/json" \
  -d '{
    "vectors": [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]],
    "method": "cosine"
  }'
```

### Clustering Analysis
```bash
curl -X POST http://localhost:8002/cluster_analysis \
  -H "Content-Type: application/json" \
  -d '{
    "vectors": [[0.1, 0.2], [0.15, 0.25], [0.8, 0.9]],
    "eps": 0.3,
    "min_samples": 2
  }'
```

## Database Schema

The service works with the following PostgreSQL tables:

```sql
-- Vector storage with metadata
CREATE TABLE vectors (
    id UUID PRIMARY KEY,
    embedding vector(384),
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Analytics results
CREATE TABLE analytics_results (
    id UUID PRIMARY KEY,
    analysis_type VARCHAR(50),
    results JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);
```

## Performance

### Benchmarks (Raspberry Pi 5)
- **Similarity Calculation**: ~2ms for 100 vector pairs
- **DBSCAN Clustering**: ~15ms for 1000 vectors
- **Database Query**: <5ms average response time
- **Memory Usage**: ~150MB under load

### Optimization Features
- Connection pooling for database efficiency
- Vectorized NumPy operations
- Batch processing capabilities
- Async/await for non-blocking operations

## Integration

### With Other Services
- **Embeddings Service**: Receives vectors for analysis
- **PostgreSQL**: Stores and retrieves vector data
- **Log Aggregator**: Sends analysis results
- **Plotly Viz**: Provides data for visualization

### MCP Integration
Accessible via the system monitor MCP server for:
- Service health monitoring
- Performance metrics
- Error tracking
- Resource utilization

## Development

### Local Testing
```bash
# Install dependencies
pip install -r requirements.txt

# Set environment
export DATABASE_URL="postgresql://user:pass@localhost:5432/db"

# Run service
python main.py
```

### Docker Development
```bash
# Build image
docker build -t analytics-service .

# Run container
docker run -p 8002:8002 \
  -e DATABASE_URL="postgresql://user:pass@db:5432/db" \
  analytics-service
```

## Monitoring

### Health Checks
The service provides comprehensive health checking:
- Database connectivity
- Memory usage
- Processing queue status
- Error rates

### Logging
Structured logging with:
- Request/response tracking
- Performance metrics
- Error details
- Database operation logs

## Error Handling

### Database Errors
- Connection failures with retry logic
- Query timeout handling
- Transaction rollback on errors

### Computation Errors
- Invalid vector dimension handling
- Memory overflow protection
- Graceful degradation

## Security

### Input Validation
- Vector dimension validation
- Parameter range checking
- SQL injection prevention
- Request size limits

### Network Security
- Container network isolation
- No external dependencies
- Local database connections only

---

**Port**: 8002  
**Technology**: FastAPI + scikit-learn + PostgreSQL  
**Optimization**: ARM64 architecture  
**Status**: Production Ready