# Node-RED Service

Node-RED provides visual workflow automation for the AI platform using the official `nodered/node-red:latest` Docker image.

## Quick Start

1. **Start the service:**
   ```bash
   docker compose up -d node-red
   ```

2. **Access Node-RED:**
   Open `http://localhost:1880` in your browser

3. **Install PostgreSQL nodes:**
   - Menu (☰) → Manage palette → Install
   - Search and install: `node-red-contrib-postgresql`

## Database Connection

Configure PostgreSQL nodes with these settings:
- **Host:** `postgres`
- **Port:** `5432`
- **Database:** `ai_platform_db`
- **User:** `ai_platform_user`
- **Password:** From your `.env` file

## Environment Variables

The service receives:
- `DATABASE_URL` - PostgreSQL connection string
- `LOG_LEVEL` - Logging level (INFO, DEBUG, etc.)

## Common Workflow Patterns

### 1. Log Processing
```
HTTP Input → Function (transform) → PostgreSQL Output
```

### 2. Database Events
```
PostgreSQL Listen → Function (process) → HTTP Request
```

### 3. Service Integration
```
HTTP Input → Embeddings API → Store Results → Response
```

## Volumes

- `node_red_data:/data` - Persistent storage for flows and settings

## Integration with AI Platform

Node-RED can integrate with other platform services:
- **Embeddings Service:** `http://embeddings:8001`
- **Analytics Service:** `http://analytics-node:8002`
- **Log Aggregator:** `http://log-aggregator:8004`

For specific flow configurations, refer to your production Node-RED instance flows.