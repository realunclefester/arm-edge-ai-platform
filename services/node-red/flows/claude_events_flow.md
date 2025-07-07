# Claude Events Flow

**Status:** Active, Locked  
**Purpose:** HTTP endpoint for receiving Claude events and storing them in PostgreSQL

## Flow Diagram
```
HTTP POST /claude-events → Prepare Claude Event → Insert Claude Event → Success Response
                                                         ↓
                                                  Event Debug
```

## Nodes Description

### 1. **Claude Events Endpoint** (HTTP Input)
- **Purpose:** Receives HTTP POST requests with Claude events
- **URL:** `/claude-events`
- **Method:** POST
- **Input:** JSON payload with event data

### 2. **Prepare Claude Event** (Function)
- **Purpose:** Validates and prepares event data for database storage
- **Functionality:**
  - Sets default `event_type` to "webhook" if not provided
  - Extracts event fields: `event_type`, `flow_id`, `payload`, `priority`
  - Serializes payload to JSON string
  - Sets default priority to 5
  - Prepares SQL parameters array
- **Output:** Message with prepared SQL parameters

### 3. **Insert Claude Event** (PostgreSQL)
- **Purpose:** Stores event in `claude_events` table
- **Database:** `claude_ai_db` on postgres:5432
- **User:** `postgres`
- **Query:**
  ```sql
  INSERT INTO claude_events (event_type, flow_id, payload, priority)
  VALUES ($1, $2, $3, $4)
  RETURNING id, event_type, status
  ```
- **Output:** Inserted record with ID and status

### 4. **Success Response** (HTTP Response)
- **Purpose:** Sends HTTP 200 response to client
- **Status Code:** 200
- **Content:** Database response

### 5. **Event Debug** (Debug)
- **Purpose:** Logs event details for monitoring
- **Active:** Yes
- **Target:** Full payload
- **Output:** Sidebar debug panel

## Data Flow

### Input Format (HTTP Request)
```json
{
  "event_type": "embeddings_decision_required",
  "flow_id": "notify_log_embedding",
  "payload": {
    "batch_size": 10,
    "log_ids": [1, 2, 3],
    "action_required": "approve_embeddings_batch"
  },
  "priority": 3
}
```

### Database Storage
```sql
-- Table: claude_events
event_type: "embeddings_decision_required"
flow_id: "notify_log_embedding" 
payload: JSON string of payload object
priority: 3
created_at: auto-generated timestamp
```

### Output Response
```json
{
  "id": 123,
  "event_type": "embeddings_decision_required", 
  "status": "pending"
}
```

## Integration Points
- **Receives from:** Any service posting to `/claude-events`
- **Stores in:** PostgreSQL `claude_events` table
- **Used by:** Claude MCP webhook system for notifications

## Database Configuration
- **Host:** postgres:5432
- **Database:** claude_ai_db
- **User:** postgres
- **Connection Pool:** Max 10 connections
- **SSL:** Disabled

## Error Handling
- Validates required fields with defaults
- PostgreSQL errors returned in HTTP response
- Debug logging for troubleshooting

## Usage Examples
```bash
# Send embeddings decision event
curl -X POST http://localhost:1880/claude-events \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "embeddings_decision_required",
    "payload": {"batch_size": 5},
    "priority": 3
  }'
```