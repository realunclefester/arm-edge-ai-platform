# Embeddings Service

ARM-optimized sentence transformer service for generating vector embeddings using SentenceTransformers library.

## 🎯 Purpose

Provides high-performance text embeddings for:
- Semantic search in documents and logs
- Text similarity calculations
- Vector storage and retrieval
- Machine learning pipelines
- Content recommendation systems

## 🚀 Features

- **ARM Optimization**: Specifically tuned for ARM64 processors
- **Fast Inference**: ~5ms per embedding on Raspberry Pi 5
- **Batch Processing**: Handle up to 100 texts in single request
- **Database Integration**: Direct PostgreSQL storage with pgvector
- **Health Monitoring**: Comprehensive health checks
- **Async Processing**: Non-blocking FastAPI implementation

## 📋 Specifications

- **Model**: `sentence-transformers/all-MiniLM-L6-v2`
- **Dimensions**: 384-dimensional vectors
- **Max Text Length**: 512 tokens
- **Memory Usage**: ~500MB during operation
- **Startup Time**: ~30 seconds (model loading)

## 🔌 API Endpoints

### Health Check
```bash
GET /health
```
Returns service and database connection status.

### Model Information
```bash
GET /model/info
```
Returns model specifications and capabilities.

### Single Text Embedding
```bash
POST /embed/single
Content-Type: application/json

{
  "text": "Your text here",
  "normalize": true
}
```

### Batch Text Embeddings
```bash
POST /embed
Content-Type: application/json

{
  "texts": ["Text 1", "Text 2", "Text 3"],
  "normalize": true
}
```

### Text Similarity
```bash
POST /similarity
Content-Type: application/json

{
  "text1": "First text",
  "text2": "Second text"
}
```

### Store Embedding
```bash
POST /embed/store
Content-Type: application/json

{
  "text": "Text to embed and store",
  "source_type": "api",
  "metadata": {"key": "value"}
}
```

## 🐳 Docker Usage

### Build
```bash
docker build -t arm-embeddings-service .
```

### Run Standalone
```bash
docker run -p 8001:8001 \
  -e DATABASE_URL=postgresql://user:pass@host:5432/db \
  arm-embeddings-service
```

### Environment Variables
- `DATABASE_URL`: PostgreSQL connection string (optional)
- `LOG_LEVEL`: Logging level (default: INFO)
- `MODEL_CACHE_DIR`: Model cache directory (default: /app/models)

## 📊 Performance

### Raspberry Pi 5 Benchmarks
- **Single embedding**: 5ms average
- **Batch (10 texts)**: 15ms average
- **Batch (100 texts)**: 150ms average
- **Throughput**: ~200 requests/second
- **Memory**: 500MB steady state

### Optimization Features
- **Model Pre-caching**: Model loaded during Docker build
- **Connection Pooling**: Efficient database connections
- **Vector Normalization**: Optional L2 normalization
- **Batch Vectorization**: Optimized batch processing

## 🔧 Development

### Local Development
```bash
# Install dependencies
pip install -r requirements.txt

# Run development server
uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

### Testing
```bash
# Test health endpoint
curl http://localhost:8001/health

# Test embedding generation
curl -X POST http://localhost:8001/embed/single \
  -H "Content-Type: application/json" \
  -d '{"text": "test", "normalize": true}'
```

## 🗄️ Database Schema

When using PostgreSQL integration, the service expects these tables:

```sql
-- Embeddings storage
CREATE TABLE embeddings_history (
    id SERIAL PRIMARY KEY,
    original_text TEXT NOT NULL,
    embedding vector(384),  -- pgvector extension required
    source_type VARCHAR(50),
    source_id INTEGER,
    metadata JSONB,
    processing_time_ms INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create vector index for similarity search
CREATE INDEX embeddings_vector_idx ON embeddings_history 
USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
```

## 🔗 Integration Examples

### Python Client
```python
import requests

# Generate embedding
response = requests.post(
    "http://localhost:8001/embed/single",
    json={"text": "Hello world", "normalize": True}
)
embedding = response.json()["embedding"]

# Calculate similarity
response = requests.post(
    "http://localhost:8001/similarity",
    json={"text1": "cat", "text2": "kitten"}
)
similarity = response.json()["similarity_percentage"]
```

### JavaScript/Node.js
```javascript
const axios = require('axios');

async function getEmbedding(text) {
    const response = await axios.post('http://localhost:8001/embed/single', {
        text: text,
        normalize: true
    });
    return response.data.embedding;
}
```

## ⚠️ Limitations

- **Batch Size**: Maximum 100 texts per request
- **Text Length**: Maximum 512 tokens per text
- **Language**: Optimized for English text
- **Model Size**: 80MB model download on first run
- **ARM Only**: Optimized specifically for ARM architecture

## 🛠️ Troubleshooting

### Service Won't Start
```bash
# Check Docker logs
docker logs embeddings

# Check system resources
docker stats embeddings
```

### Slow Performance
- Verify ARM64 architecture
- Check available memory (minimum 1GB)
- Monitor CPU usage during inference
- Ensure model is cached (check startup logs)

### Database Connection Issues
```bash
# Test database connectivity
docker exec postgres pg_isready -U username

# Check environment variables
docker exec embeddings env | grep DATABASE_URL
```

## 📈 Monitoring

### Health Metrics
- Service health status
- Database connection status
- Model loading status
- Memory usage
- Response times

### Custom Metrics (Future)
- Embeddings generated per minute
- Average processing time
- Error rates
- Queue length

## 🔮 Roadmap

- [ ] Support for multiple models
- [ ] Redis caching for embeddings
- [ ] Streaming embeddings for large texts
- [ ] Custom model fine-tuning support
- [ ] Prometheus metrics integration