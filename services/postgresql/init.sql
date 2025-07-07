-- PostgreSQL initialization script for ARM Edge AI Platform
-- Creates necessary extensions and tables for vector operations

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_net;

-- Create embedding history table
CREATE TABLE IF NOT EXISTS embeddings_history (
    id SERIAL PRIMARY KEY,
    original_text TEXT NOT NULL,
    embedding vector(384),
    source_type VARCHAR(50),
    source_id VARCHAR(100),
    metadata JSONB,
    processing_time_ms INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create analytics table
CREATE TABLE IF NOT EXISTS vector_analytics (
    id SERIAL PRIMARY KEY,
    vector_id VARCHAR(100) NOT NULL,
    analytics_type VARCHAR(50) NOT NULL,
    metrics JSONB NOT NULL,
    decisions JSONB NOT NULL,
    text_sample TEXT,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create aggregated logs table
CREATE TABLE IF NOT EXISTS aggregated_logs (
    id SERIAL PRIMARY KEY,
    source VARCHAR(100) NOT NULL,
    message TEXT NOT NULL,
    aggregation_count INTEGER DEFAULT 1,
    error_count INTEGER DEFAULT 0,
    info_count INTEGER DEFAULT 0,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create Claude events table for webhook system
CREATE TABLE IF NOT EXISTS claude_events (
    id SERIAL PRIMARY KEY,
    event_type VARCHAR(50) NOT NULL,
    flow_id VARCHAR(100),
    payload JSONB NOT NULL,
    priority INTEGER DEFAULT 5,
    status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP WITH TIME ZONE
);

-- Create memory table for pgvector memory MCP server
CREATE TABLE IF NOT EXISTS ai_platform_memory (
    id VARCHAR(100) PRIMARY KEY,
    text TEXT NOT NULL,
    type VARCHAR(50) NOT NULL,
    category VARCHAR(50) DEFAULT 'system_memory',
    priority VARCHAR(20) DEFAULT 'medium',
    embedding vector(384),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_embeddings_embedding ON embeddings_history 
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

CREATE INDEX IF NOT EXISTS idx_memory_embedding ON ai_platform_memory 
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

CREATE INDEX IF NOT EXISTS idx_analytics_vector_id ON vector_analytics(vector_id);
CREATE INDEX IF NOT EXISTS idx_analytics_timestamp ON vector_analytics(timestamp);
CREATE INDEX IF NOT EXISTS idx_logs_source ON aggregated_logs(source);
CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON aggregated_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_events_status ON claude_events(status);
CREATE INDEX IF NOT EXISTS idx_events_type ON claude_events(event_type);

-- Create function for log batch notifications
CREATE OR REPLACE FUNCTION notify_new_logs() 
RETURNS TRIGGER AS $$
BEGIN
    -- Notify every 50 new logs for batch processing
    IF (NEW.id % 50) = 0 THEN
        PERFORM pg_notify('new_logs_batch', NEW.id::text);
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger for log notifications
DROP TRIGGER IF EXISTS logs_notify_trigger ON aggregated_logs;
CREATE TRIGGER logs_notify_trigger
    AFTER INSERT ON aggregated_logs
    FOR EACH ROW
    EXECUTE FUNCTION notify_new_logs();

-- Create application user if it doesn't exist
-- User creation is handled by docker-compose environment variables
-- Only grant permissions here as user should already exist

-- Grant permissions to application user (check both possible usernames)
DO $$
BEGIN
    -- Check for production user
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'ai_platform_user') THEN
        GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO ai_platform_user;
        GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO ai_platform_user;
        GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO ai_platform_user;
    END IF;
END
$$;

-- Insert initial system memory entries
INSERT INTO ai_platform_memory (id, text, type, category, priority, embedding) VALUES
('system_init_001', 'ARM Edge AI Platform initialized with PostgreSQL pgvector, embeddings service, analytics engine, and Node-RED automation', 'system', 'system_memory', 'high', NULL)
ON CONFLICT (id) DO NOTHING;

-- Log initialization completion
INSERT INTO aggregated_logs (source, message, metadata) VALUES
('postgresql_init', 'Database initialized successfully with all tables, indexes, and triggers', 
 ('{"initialization": true, "timestamp": "' || CURRENT_TIMESTAMP || '"}')::jsonb);