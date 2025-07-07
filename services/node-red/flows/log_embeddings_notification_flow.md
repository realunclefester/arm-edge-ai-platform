# Log Embeddings Notification Flow

**Status:** Active, Locked  
**Purpose:** Monitors unprocessed logs and creates Claude events when embeddings are needed

## Flow Diagram
```
HTTP POST /logs-batch-ready → Process Batch Notification → Get Unprocessed Logs → Prepare Claude Event → Send to Claude Events
                                        ↓                          ↓
                                Manual Trigger              Logs to Process (Debug)
```

## Nodes Description

### 1. **logs-batch-ready** (HTTP Input)
- **Purpose:** Receives notifications when log batches are ready for processing
- **URL:** `/logs-batch-ready`
- **Method:** POST
- **Trigger:** Called by log aggregator or other services

### 2. **Manual Trigger** (Inject)
- **Purpose:** Manual testing trigger for the flow
- **Type:** Timestamp injection
- **Usage:** Development and debugging

### 3. **Process Batch Notification** (Function)
- **Purpose:** Processes incoming batch notification
- **Functionality:**
  - Parses notification payload
  - Updates node status with batch size info
  - Prepares empty payload for database query
- **Output:** Empty payload to trigger database query

### 4. **Get Unprocessed Logs** (PostgreSQL)
- **Purpose:** Retrieves logs that haven't been processed for embeddings
- **Query:**
  ```sql
  SELECT id, message, source, level, timestamp, metadata
  FROM aggregated_logs
  WHERE NOT EXISTS (
      SELECT 1 FROM embeddings_history
      WHERE embeddings_history.source_id = aggregated_logs.id
  )
  ORDER BY id
  LIMIT 50
  ```
- **Output:** Array of unprocessed log records

### 5. **Logs to Process** (Debug)
- **Purpose:** Shows unprocessed logs for monitoring
- **Active:** Yes
- **Target:** Full payload

### 6. **Prepare Claude Event** (Function)
- **Purpose:** Creates Claude event for embeddings decision
- **Functionality:**
  - Builds event with type "embeddings_decision_required"
  - Includes batch size, log IDs, timestamp
  - Sets priority to 3 and flow_id
  - Stores pending logs in flow context for later use
- **Output:** Claude event object

### 7. **Send to Claude Events** (HTTP Request)
- **Purpose:** Posts event to Claude events endpoint
- **Method:** POST
- **URL:** `http://node-red:1880/claude-events`
- **Content-Type:** application/json

## Data Flow

### Input (Batch Notification)
```json
{
  "payload": {
    "batch_size": 25,
    "timestamp": "2025-07-07T..."
  }
}
```

### Database Query Result
```json
[
  {
    "id": 123,
    "message": "User login successful",
    "source": "auth_service",
    "level": "info",
    "timestamp": "2025-07-07T...",
    "metadata": {"user_id": 456}
  }
]
```

### Claude Event Output
```json
{
  "event_type": "embeddings_decision_required",
  "payload": {
    "batch_size": 25,
    "log_ids": [123, 124, 125],
    "total_unprocessed": 25,
    "timestamp": "2025-07-07T...",
    "action_required": "approve_embeddings_batch"
  },
  "priority": 3,
  "flow_id": "notify_log_embedding"
}
```

## Integration Points
- **Triggered by:** Log aggregator batch notifications
- **Queries:** `aggregated_logs` and `embeddings_history` tables
- **Notifies:** Claude via events endpoint
- **Used by:** Embeddings processing flow (reads from flow context)

## Flow Context Usage
- **Stores:** `pending_logs` - array of logs awaiting embeddings processing
- **Purpose:** Allows embeddings flow to access the same log batch

## Database Dependencies
- **aggregated_logs:** Source of log data
- **embeddings_history:** Tracks which logs have been processed
- **claude_events:** Target for notifications

## Performance Notes
- Limits query to 50 logs per batch
- Uses EXISTS subquery for efficient unprocessed log detection
- Stores logs in flow context to avoid re-querying

## Error Handling
- Debug outputs for monitoring query results
- HTTP request error handling for Claude events
- Flow context fallback for missing data