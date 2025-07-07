# Analytics Notification Flow

**Status:** Active, Locked  
**Purpose:** Processes embeddings completion notifications and triggers analytics service

## Flow Diagram
```
HTTP POST /embeddings-ready → Get Embedding Data → Split Records → Prepare Analytics Request → Call Analytics
                                      ↓                                       ↓                    ↓
                                Debug Output                            Debug Output        Update Processed + Debug
```

## Nodes Description

### 1. **embeddings-ready** (HTTP Input)
- **Purpose:** Receives notifications when embeddings are ready for analytics
- **URL:** `/embeddings-ready`
- **Method:** POST
- **Trigger:** Called by embeddings processing flow

### 2. **Get Embedding Data** (PostgreSQL)
- **Purpose:** Retrieves fresh embeddings data for analytics processing
- **Query:** 
  ```sql
  SELECT ... FROM embeddings_history eh
  JOIN aggregated_logs al ON al.id = eh.source_id
  WHERE eh.processed = false
  ORDER BY eh.created_at ASC
  LIMIT 10
  ```
- **Note:** Query appears truncated in flow data, likely selects embedding vectors and metadata
- **Output:** Unprocessed embedding records

### 3. **Split** (Split Node)
- **Purpose:** Processes embedding records individually
- **Configuration:** Array split by 1 item per message
- **Output:** Individual embedding records

### 4. **Prepare Analytics Request** (Function)
- **Purpose:** Formats embedding data for analytics service
- **Functionality:**
  - Extracts embedding data from database result
  - Builds analytics request with text, vector, and metadata
  - Includes embedding_id, source_id, log details
  - Sets Content-Type header
- **Expected Input:** Database record with embedding data
- **Output:** Analytics service request

### 5. **Call Analytics** (HTTP Request)
- **Purpose:** Sends embedding data to analytics service
- **Method:** POST
- **URL:** `http://analytics-node:8002/analyze/pre-storage`
- **Input:** Formatted embedding and metadata
- **Output:** Analytics processing results

### 6. **Update - processed** (PostgreSQL)
- **Purpose:** Marks embeddings as processed after analytics
- **Query:**
  ```sql
  UPDATE embeddings_history
  SET processed = true
  WHERE processed = false
  AND created_at <= NOW() - INTERVAL '1 minute'
  ```
- **Note:** Updates records older than 1 minute to avoid race conditions

### 7. **Multiple Debug Nodes**
- **Purpose:** Monitoring at each processing stage
- **Locations:** 
  - After database query (debug 2)
  - After analytics request prep (debug 3)  
  - After analytics call (debug 4)
  - After database update (debug 1)
- **Active:** Yes for pipeline monitoring

## Data Flow

### Input (Notification)
```json
{} // Empty POST body, triggers processing
```

### Database Query Result (Expected)
```json
[
  {
    "embedding_id": 123,
    "source_id": 456,
    "original_text": "info: User login successful [auth_service]",
    "embedding_array": [0.123, -0.456, 0.789],
    "level": "info",
    "source": "auth_service", 
    "aggregation_count": 5,
    "log_metadata": {"user_id": 789}
  }
]
```

### Analytics Service Request
```json
{
  "text": "info: User login successful [auth_service]",
  "vector": [0.123, -0.456, 0.789],
  "metadata": {
    "embedding_id": 123,
    "source_id": 456,
    "log_level": "info",
    "log_source": "auth_service",
    "aggregation_count": 5,
    "log_metadata": {"user_id": 789}
  }
}
```

## Integration Points
- **Triggered by:** Embeddings processing flow completion
- **Queries:** `embeddings_history` joined with `aggregated_logs`
- **Calls:** Analytics service `/analyze/pre-storage` endpoint
- **Updates:** `embeddings_history.processed` flag

## Database Dependencies
- **embeddings_history:** Source of embedding vectors
- **aggregated_logs:** Source of original log metadata
- **JOIN:** Combines embedding with original log context

## Processing Logic
1. Receive embeddings-ready notification
2. Query for unprocessed embeddings (max 10)
3. Split into individual records for processing
4. Format each record for analytics service
5. Send to analytics for pre-storage analysis
6. Mark records as processed (with 1-minute delay)

## Error Handling
- Debug outputs at each step for troubleshooting
- Handles empty result sets gracefully
- Time-based processing flag updates prevent race conditions

## Performance Notes
- Processes max 10 records per trigger
- Individual analytics calls for granular processing
- 1-minute delay on processed flag prevents premature updates
- Split processing allows parallel analytics calls

## Analytics Integration
- Sends both vector and text data to analytics
- Includes rich metadata for analysis context
- Pre-storage analysis allows analytics service to prepare optimizations