# PostgreSQL Service

Custom PostgreSQL 16.9 container with pgvector extension and pg_net for vector storage and optional HTTP capabilities, optimized for ARM architecture.

## Overview

The PostgreSQL service forms the core data layer of the ARM Edge AI Platform. Built on PostgreSQL 16.9 with the pgvector extension for efficient vector operations and pg_net extension for potential HTTP functionality, it provides robust, scalable data storage optimized for edge computing environments.

## Features

### Core Database
- **PostgreSQL 16.9**: Latest stable version with ARM64 support
- **pgvector 0.8.0**: Vector similarity search and storage
- **pg_net**: HTTP extension (installed but not actively used)
- **Custom Configuration**: Optimized for Raspberry Pi performance

### Vector Capabilities
- **384-Dimensional Vectors**: Optimized for SentenceTransformer embeddings
- **Similarity Search**: Cosine similarity and L2 distance operations
- **Vector Indexing**: HNSW and IVFFlat indexing for performance
- **Batch Operations**: Efficient bulk vector operations

### ARM Optimization
- **Memory Tuning**: Configured for Raspberry Pi memory constraints
- **CPU Settings**: Optimized for ARM64 processors
- **Connection Pooling**: Efficient connection management
- **Storage Optimization**: SSD-optimized I/O settings

## Docker Configuration

### Base Image
```dockerfile
FROM pgvector/pgvector:pg16
# Includes PostgreSQL 16.9 + pgvector 0.8.0
```

### Extensions Installed
1. **pgvector**: Vector operations and indexing
2. **pg_net**: HTTP client functionality (available for future use)

### Build Process
```bash
# Install pg_net from source
git clone https://github.com/supabase/pg_net.git
make && make install

# Configure shared libraries
shared_preload_libraries = 'pg_net'
```

## Database Schema

### Core Tables
```sql
-- Vector embeddings storage
CREATE TABLE vectors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    embedding vector(384) NOT NULL,
    metadata JSONB,
    content TEXT,
    source VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Analytics results
CREATE TABLE analytics_results (
    id SERIAL PRIMARY KEY,
    analysis_type VARCHAR(50) NOT NULL,
    results JSONB NOT NULL,
    vector_count INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Aggregated logs
CREATE TABLE aggregated_logs (
    id SERIAL PRIMARY KEY,
    message_pattern TEXT NOT NULL,
    count INTEGER DEFAULT 1,
    level VARCHAR(10),
    source VARCHAR(100),
    first_seen TIMESTAMP DEFAULT NOW(),
    last_seen TIMESTAMP DEFAULT NOW(),
    metadata JSONB,
    sample_messages JSONB
);

-- Claude events (webhook system)
CREATE TABLE claude_events (
    id SERIAL PRIMARY KEY,
    event_type VARCHAR(50) NOT NULL,
    payload JSONB NOT NULL,
    priority INTEGER DEFAULT 5,
    status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT NOW(),
    processed_at TIMESTAMP
);
```

### Indexes for Performance
```sql
-- Vector similarity indexes
CREATE INDEX ON vectors USING hnsw (embedding vector_cosine_ops);
CREATE INDEX ON vectors USING ivfflat (embedding vector_l2_ops) WITH (lists = 100);

-- Metadata and text search
CREATE INDEX idx_vectors_source ON vectors(source);
CREATE INDEX idx_vectors_created_at ON vectors(created_at);
CREATE INDEX idx_vectors_metadata ON vectors USING gin(metadata);

-- Analytics indexes
CREATE INDEX idx_analytics_type ON analytics_results(analysis_type);
CREATE INDEX idx_analytics_created_at ON analytics_results(created_at);

-- Log aggregation indexes
CREATE INDEX idx_logs_source ON aggregated_logs(source);
CREATE INDEX idx_logs_level ON aggregated_logs(level);
CREATE INDEX idx_logs_last_seen ON aggregated_logs(last_seen);

-- Event system indexes
CREATE INDEX idx_events_status ON claude_events(status);
CREATE INDEX idx_events_type ON claude_events(event_type);
CREATE INDEX idx_events_created_at ON claude_events(created_at);
```

## Configuration

### Environment Variables
```bash
POSTGRES_USER=ai_platform_user
POSTGRES_PASSWORD=your_secure_password
POSTGRES_DB=ai_platform_db
POSTGRES_PORT=5432
```

### PostgreSQL Configuration
```ini
# postgresql.conf optimizations for ARM/Raspberry Pi

# Memory settings
shared_buffers = 512MB              # 25% of available RAM
effective_cache_size = 2GB          # 75% of available RAM
work_mem = 16MB                     # Per operation memory
maintenance_work_mem = 128MB        # Maintenance operations

# Connection settings
max_connections = 100               # Reasonable for edge device
shared_preload_libraries = 'pg_net' # Load pg_net extension

# Logging
log_min_duration_statement = 1000   # Log slow queries (1s+)
log_statement = 'ddl'               # Log schema changes
logging_collector = on
log_directory = 'pg_log'

# Checkpoints and WAL
checkpoint_timeout = 5min
max_wal_size = 1GB
min_wal_size = 80MB
wal_compression = on                # Compress WAL files

# ARM-specific optimizations
random_page_cost = 1.1              # SSD optimization
effective_io_concurrency = 200      # SSD concurrent I/O
```

## Vector Operations

### Similarity Search
```sql
-- Find similar vectors (cosine similarity)
SELECT id, content, metadata,
       1 - (embedding <=> target_vector) AS similarity
FROM vectors
WHERE 1 - (embedding <=> target_vector) > 0.7
ORDER BY embedding <=> target_vector
LIMIT 10;

-- L2 distance search
SELECT id, content, metadata,
       embedding <-> target_vector AS distance
FROM vectors
ORDER BY embedding <-> target_vector
LIMIT 10;
```

### Batch Operations
```sql
-- Insert multiple vectors efficiently
INSERT INTO vectors (embedding, content, metadata, source) 
VALUES 
  ('[0.1,0.2,0.3,...]'::vector, 'text1', '{"type":"doc"}', 'service1'),
  ('[0.4,0.5,0.6,...]'::vector, 'text2', '{"type":"log"}', 'service2');

-- Batch similarity analysis
WITH target AS (SELECT '[0.1,0.2,0.3,...]'::vector as vec)
SELECT v.id, v.content,
       1 - (v.embedding <=> t.vec) AS similarity
FROM vectors v, target t
WHERE 1 - (v.embedding <=> t.vec) > 0.5;
```

### Index Management
```sql
-- Create vector indexes
CREATE INDEX CONCURRENTLY idx_vectors_hnsw 
ON vectors USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- Monitor index usage
SELECT schemaname, tablename, indexname, idx_tup_read, idx_tup_fetch
FROM pg_stat_user_indexes
WHERE tablename = 'vectors';
```

## Performance Monitoring

### Key Metrics
```sql
-- Database size and growth
SELECT pg_size_pretty(pg_database_size('ai_platform_db')) as db_size;

-- Table sizes
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables 
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Vector index performance
SELECT indexname, 
       idx_tup_read, 
       idx_tup_fetch, 
       idx_scan
FROM pg_stat_user_indexes 
WHERE tablename = 'vectors';

-- Active connections
SELECT count(*) as active_connections,
       state,
       application_name
FROM pg_stat_activity 
GROUP BY state, application_name;
```

### Slow Query Analysis
```sql
-- Enable pg_stat_statements extension
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- Top slow queries
SELECT query,
       calls,
       total_time,
       mean_time,
       rows
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;
```

## Backup and Recovery

### Automated Backups
```bash
# Database dump
pg_dump -h localhost -U ai_platform_user -d ai_platform_db > backup.sql

# Vector data specific backup
pg_dump -h localhost -U ai_platform_user -d ai_platform_db \
  --table=vectors --table=analytics_results > vectors_backup.sql

# Compressed backup
pg_dump -h localhost -U ai_platform_user -d ai_platform_db | gzip > backup.sql.gz
```

### Point-in-Time Recovery
```bash
# Enable WAL archiving in postgresql.conf
archive_mode = on
archive_command = 'cp %p /backup/wal/%f'

# Base backup for PITR
pg_basebackup -h localhost -U ai_platform_user -D /backup/base -Ft -z
```

## Extensions Available

### pgvector (Active)
```sql
-- Create vector column
ALTER TABLE my_table ADD COLUMN embedding vector(384);

-- Vector operations
SELECT embedding <-> '[1,2,3]'::vector AS l2_distance;
SELECT embedding <=> '[1,2,3]'::vector AS cosine_distance;
SELECT embedding <#> '[1,2,3]'::vector AS inner_product;
```

### pg_net (Installed, Not Used)
```sql
-- HTTP GET request (available but not used)
SELECT net.http_get('https://api.example.com/data');

-- HTTP POST request (available but not used)
SELECT net.http_post(
    'https://api.example.com/webhook',
    '{"message": "hello"}'::jsonb,
    'application/json'
);
```

## Maintenance

### Regular Tasks
```sql
-- Update table statistics
ANALYZE vectors;
ANALYZE analytics_results;

-- Reindex for performance
REINDEX INDEX CONCURRENTLY idx_vectors_hnsw;

-- Vacuum for space reclaim
VACUUM ANALYZE vectors;

-- Check database health
SELECT * FROM pg_stat_database WHERE datname = 'ai_platform_db';
```

### ARM-Specific Maintenance
```bash
# Monitor temperature (important for ARM devices)
SELECT name, setting FROM pg_settings WHERE name LIKE '%temp%';

# Check memory usage
SELECT * FROM pg_stat_bgwriter;

# Monitor I/O patterns
SELECT * FROM pg_stat_user_tables WHERE relname = 'vectors';
```

## Security

### Access Control
```sql
-- Create read-only user for analytics
CREATE USER analytics_reader WITH PASSWORD 'secure_password';
GRANT CONNECT ON DATABASE ai_platform_db TO analytics_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO analytics_reader;

-- Service-specific permissions
CREATE USER embeddings_service WITH PASSWORD 'secure_password';
GRANT INSERT, SELECT ON vectors TO embeddings_service;
```

### Data Protection
- Password-protected access only
- No superuser access for applications
- Encrypted connections (TLS)
- Regular security updates

## Troubleshooting

### Common Issues
```sql
-- Check connection limits
SELECT count(*) FROM pg_stat_activity;
SELECT setting FROM pg_settings WHERE name = 'max_connections';

-- Identify blocking queries
SELECT pid, state, query, query_start 
FROM pg_stat_activity 
WHERE state != 'idle';

-- Check vector index health
SELECT indexname, idx_scan, idx_tup_read 
FROM pg_stat_user_indexes 
WHERE tablename = 'vectors';
```

### Performance Tuning
```sql
-- Identify missing indexes
SELECT schemaname, tablename, attname, n_distinct, correlation
FROM pg_stats
WHERE tablename = 'vectors' AND n_distinct > 100;

-- Check query performance
EXPLAIN (ANALYZE, BUFFERS) 
SELECT * FROM vectors 
ORDER BY embedding <=> '[0.1,0.2,0.3]'::vector 
LIMIT 10;
```

---

**Port**: 5432  
**Technology**: PostgreSQL 16.9 + pgvector 0.8.0 + pg_net  
**Optimization**: ARM64 + memory tuned  
**Status**: Production Ready