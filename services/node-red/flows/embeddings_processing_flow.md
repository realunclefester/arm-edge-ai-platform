# Embeddings Processing Flow

**Status:** Active, Locked  
**Purpose:** Processes approved embeddings requests and stores results in database

## Flow Diagram
```
HTTP POST /process-embeddings → Prepare Embeddings Request → Call Embeddings Service → Prepare for Storage
                                                                         ↓
Split Individual Items → Prepare SQL Params → Store Embedding → Join Results → Process Response
                                    ↓                                    ↓
                              Multiple Debug Nodes                Notify Analytics + Debug
```

## Nodes Description

### 1. **postgres post** (HTTP Input)
- **Purpose:** Receives requests to process embeddings
- **URL:** `/process-embeddings`
- **Method:** POST
- **Trigger:** Called by Claude or automation systems

### 2. **Prepare Embeddings Request** (Function)
- **Purpose:** Prepares request for embeddings service
- **Functionality:**
  - Retrieves `pending_logs` from flow context (set by notification flow)
  - Combines log message with metadata for better context
  - Creates text array: `"level: message [source]"`
  - Builds metadata array with log details
  - Sets Content-Type header
- **Output:** Request payload for embeddings service

### 3. **Call Embeddings Service** (HTTP Request)
- **Purpose:** Generates embeddings for log texts
- **Method:** POST
- **URL:** `http://embeddings:8001/embed`
- **Input:** Array of texts and metadata
- **Output:** Embeddings array

### 4. **Prepare Embeddings for Storage** (Function)
- **Purpose:** Matches embeddings with original logs
- **Functionality:**
  - Validates embeddings response
  - Matches log count with embeddings count
  - Creates insert objects with log_id, text, embedding, metadata
- **Output:** Array of embedding records for storage

### 5. **Split** (Split Node)
- **Purpose:** Splits embedding array into individual records
- **Configuration:** Array split by 1 item per message
- **Output:** Individual embedding objects

### 6. **Prepare SQL Params** (Function)
- **Purpose:** Formats data for PostgreSQL insertion
- **Functionality:**
  - Converts embedding array to PostgreSQL format
  - Ensures numeric values in embedding vector
  - Creates parameter array for SQL query
  - Formats embedding as string: `"[1.5,2.3,4.1]"`
- **Output:** SQL parameters array

### 7. **Store Embedding** (PostgreSQL)
- **Purpose:** Stores embedding in database
- **Queries:**
  ```sql
  INSERT INTO embeddings_history
  (source_id, original_text, embedding, source_type, metadata, processing_time_ms)
  VALUES ($1, $2, $3, 'aggregated_logs', $4, 100)
  RETURNING id;
  
  UPDATE aggregated_logs
  SET processed = true
  WHERE id = $1;
  ```
- **Output:** Inserted record ID

### 8. **Join** (Join Node)
- **Purpose:** Recombines individual results into complete response
- **Mode:** Auto-join based on message parts
- **Output:** Complete processing results

### 9. **Process Embeddings Response** (Function)
- **Purpose:** Validates and reports processing results
- **Functionality:**
  - Checks HTTP status code
  - Updates node status with success indicator
  - Logs processing count
- **Output:** Final response

### 10. **Multiple Debug Nodes**
- **Purpose:** Various debug outputs for monitoring
- **Locations:** After each major processing step
- **Active:** Yes for monitoring pipeline

### 11. **notify analytics node** (HTTP Request)
- **Purpose:** Triggers analytics processing
- **Method:** POST
- **URL:** `http://node-red:1880/embeddings-ready`
- **Trigger:** After successful embeddings storage

## Data Flow

### Input Format
```json
{} // Empty POST body, uses flow context for data
```

### Embeddings Service Request
```json
{
  "texts": [
    "info: User login successful [auth_service]",
    "error: Database timeout [db_service]"
  ],
  "metadata": [
    {
      "log_id": 123,
      "source": "auth_service", 
      "level": "info",
      "timestamp": "2025-07-07T...",
      "original_metadata": {"user_id": 456}
    }
  ]
}
```

### Database Storage Format
```sql
-- embeddings_history table
source_id: 123
original_text: "info: User login successful [auth_service]"
embedding: "[0.123, -0.456, 0.789, ...]"
source_type: "aggregated_logs"
metadata: JSON string
processing_time_ms: 100

-- aggregated_logs update
processed: true (for log ID 123)
```

## Integration Points
- **Reads from:** Flow context `pending_logs` (set by notification flow)
- **Calls:** Embeddings service `/embed` endpoint
- **Stores in:** `embeddings_history` table
- **Updates:** `aggregated_logs.processed` flag
- **Triggers:** Analytics processing via notification

## Flow Context Dependencies
- **Requires:** `pending_logs` from embeddings notification flow
- **Critical:** Flow must be triggered after notification flow sets context

## Database Schema
```sql
-- embeddings_history table structure
id: SERIAL PRIMARY KEY
source_id: INTEGER (references aggregated_logs.id)
original_text: TEXT
embedding: TEXT (JSON array as string)
source_type: VARCHAR (always 'aggregated_logs')
metadata: JSONB
processing_time_ms: INTEGER
created_at: TIMESTAMP DEFAULT NOW()
```

## Error Handling
- Validates embeddings service response
- Checks array length matching
- Multiple debug nodes for troubleshooting
- Status code validation for HTTP requests

## Performance Notes
- Processes in batches from flow context
- Splits for individual database insertions
- Joins results for atomic response
- Updates processed flags to prevent reprocessing