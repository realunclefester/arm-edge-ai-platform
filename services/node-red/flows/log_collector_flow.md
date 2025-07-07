# Log Collector Flow

**Status:** Active, Locked  
**Purpose:** Collects generated logs from global context and sends them to log aggregator

## Flow Diagram
```
[Global Context] → Read Generated Logs → Split Log Array → Send to Log Aggregator → Aggregator Response
                                                                      ↓
                                                               Error Handler → Collection Error
```

## Nodes Description

### 1. **Read Generated Logs** (Function)
- **Purpose:** Reads logs from global context shared between flows
- **Functionality:**
  - Retrieves `generated_logs` from global context
  - Tracks processed count with `last_processed_count`
  - Resets counter when all logs processed
  - Returns only new logs since last processing
- **Output:** Array of log objects

### 2. **Split Log Array** (Split)
- **Purpose:** Converts log array into individual messages
- **Configuration:** Array split by 1 item per message
- **Output:** Individual log objects

### 3. **Send to Log Aggregator** (HTTP Request)
- **Purpose:** Posts logs to log aggregation service
- **Method:** POST
- **URL:** `http://log-aggregator:8004/logs/ingest`
- **Headers:** `Content-Type: application/json`
- **Input:** Individual log object
- **Output:** Response from aggregator

### 4. **Aggregator Response** (Debug)
- **Purpose:** Displays aggregator response for monitoring
- **Active:** Yes
- **Output:** Sidebar debug panel

### 5. **Error Handler** (Catch)
- **Purpose:** Catches any errors in the flow
- **Scope:** All nodes in flow
- **Output:** Error messages to debug node

### 6. **Collection Error** (Debug)
- **Purpose:** Displays collection errors
- **Target:** Error object
- **Active:** Yes

## Data Flow

### Input Format (from Global Context)
```json
{
  "message": "User authentication successful",
  "source": "test_generator", 
  "level": "info",
  "timestamp": "2025-07-07T...",
  "metadata": {
    "test_run": true,
    "random_id": 123
  }
}
```

### Output Format (to Log Aggregator)
```json
{
  "message": "User authentication successful",
  "source": "test_generator",
  "level": "info", 
  "metadata": {
    "test_run": true,
    "random_id": 123
  }
}
```

## Integration Points
- **Reads from:** Global context `generated_logs`
- **Writes to:** Log Aggregator service `/logs/ingest`
- **Dependencies:** Test Log Generator flow (for data source)

## Error Handling
- Global catch node captures all flow errors
- Debug outputs for monitoring responses and errors
- Graceful handling of empty global context

## Performance Notes
- Processes logs in batches from global context
- Splits arrays to avoid overwhelming aggregator
- Tracks processing state to avoid duplicates