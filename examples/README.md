# Examples

This directory contains practical examples demonstrating how to use the ARM Edge AI Platform.

## Available Examples

### 1. Basic Usage (`basic_usage.py`)
Simple synchronous examples showing core functionality:
- Service health checks
- Text embedding generation
- Similarity calculations
- Clustering analysis
- Log data processing
- Statistics retrieval

**Run the example:**
```bash
cd examples
python basic_usage.py
```

### 2. API Examples (`api_examples.py`)
Advanced asynchronous examples for production use:
- Document similarity search
- Text clustering analysis
- Log processing workflows
- Performance benchmarking
- Async API client wrapper

**Run the example:**
```bash
cd examples
pip install aiohttp  # If not already installed
python api_examples.py
```

## Prerequisites

Before running examples, ensure:

1. **Services are running:**
   ```bash
   docker compose up -d
   ```

2. **Services are healthy:**
   ```bash
   curl http://localhost:8001/health  # Embeddings
   curl http://localhost:8002/health  # Analytics
   curl http://localhost:8004/health  # Log Aggregator
   curl http://localhost:8003/        # Plotly Viz
   ```

3. **Python dependencies:**
   ```bash
   pip install requests aiohttp numpy
   ```

## Example Output

### Basic Usage Example
```
🚀 ARM Edge AI Platform - Basic Usage Examples
==================================================
🔍 Checking service health...
  Embeddings: ✅ Healthy
  Analytics: ✅ Healthy
  Log Aggregator: ✅ Healthy
  Plotly Viz: ✅ Healthy

🧠 Generating embeddings for 8 texts...
  ✅ Generated 8 embeddings (384 dimensions)

🔬 Performing clustering analysis...
  ✅ Found 3 clusters

📊 Calculating similarity between texts...
  ✅ Similarity: 0.7234

📝 Sending 3 log entries...
  ✅ Logs successfully processed

📈 Getting log aggregation statistics...
  ✅ Retrieved statistics
  📊 Total logs processed: 156
  📊 Aggregation ratio: 0.68

🎉 Example completed! Visit http://localhost:8003 to see visualizations
```

### API Examples Output
```
🚀 ARM Edge AI Platform - API Examples
======================================
📄 Document Similarity Search Example
----------------------------------------
Processing 8 documents...

Query: 'ARM-based edge computing solutions'
Most similar documents:
  1. [0.856] ARM processors are designed for energy efficiency
  2. [0.742] Raspberry Pi is a popular ARM-based single board computer
  3. [0.681] Machine learning models can run on edge devices

🔬 Text Clustering Analysis Example
----------------------------------------
Clustering 12 texts...

Found 4 clusters:
🏷️  Cluster 0 (3 items):
    • Neural networks for image recognition
    • Deep learning model optimization
    • Machine learning inference on edge

🏷️  Cluster 1 (3 items):
    • ARM Cortex-A78 processor architecture
    • Raspberry Pi GPIO programming
    • Edge computing hardware selection
```

## Integration Patterns

### 1. Semantic Search Application
```python
# Generate embeddings for document collection
documents = ["doc1", "doc2", "doc3"]
embeddings = await client.generate_embeddings_batch(documents)

# Store in database with metadata
for doc, embedding in zip(documents, embeddings):
    store_document(doc, embedding, metadata)

# Search similar documents
query_embedding = await client.generate_embedding(user_query)
similar_docs = find_similar(query_embedding, threshold=0.7)
```

### 2. Log Analysis Pipeline
```python
# Collect logs from multiple sources
logs = collect_system_logs()

# Send for intelligent aggregation
await client.ingest_logs(logs)

# Monitor aggregation statistics
stats = await client.get_aggregation_stats()
alert_if_anomaly_detected(stats)
```

### 3. Content Clustering
```python
# Generate embeddings for content
content_embeddings = await client.generate_embeddings_batch(content_list)

# Perform clustering analysis
clusters = await client.perform_vector_clustering(content_embeddings)

# Group content by clusters for organization
organized_content = group_by_clusters(content_list, clusters)
```

## Performance Notes

### ARM Optimization
- Examples are optimized for Raspberry Pi performance
- Batch operations reduce API overhead
- Async patterns maximize throughput
- Memory usage is monitored and optimized

### Typical Performance (Raspberry Pi 5)
- Single embedding: ~10-15ms
- Batch embedding (50 texts): ~200-300ms
- Similarity calculation: ~5ms
- Clustering (100 vectors): ~50ms
- Log processing: ~10ms per batch

## Troubleshooting

### Service Connection Issues
```bash
# Check service status
docker compose ps

# View service logs
docker compose logs embeddings
docker compose logs analytics
```

### Performance Issues
```bash
# Monitor system resources
docker stats

# Check service health endpoints
curl -v http://localhost:8001/health
```

### Database Issues
```bash
# Check PostgreSQL connection
docker exec ai_platform_postgres pg_isready -U ai_platform_user

# View database logs
docker logs ai_platform_postgres
```

## Next Steps

1. **Explore Visualizations**: Visit `http://localhost:8003` for interactive dashboards
2. **API Documentation**: Check `http://localhost:800X/docs` for detailed API specs
3. **Custom Integration**: Use the examples as templates for your applications
4. **Performance Tuning**: Adjust parameters based on your hardware and requirements

For more information, see the main [README](../README.md) and [documentation](../docs/).