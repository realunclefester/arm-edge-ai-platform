#!/usr/bin/env python3
"""
Claude Webhook MCP Server - Autonomous event processor
Receives events from Node-RED and can wake up Claude when needed
"""

import asyncio
import json
import logging
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
import psycopg2
from mcp.server import Server
from mcp.types import TextContent, Tool
from psycopg2.extras import RealDictCursor

# Load .env file if it exists
env_path = Path(".env")
if env_path.exists():
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ[key] = value

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
POSTGRES_CONFIG = {
    "host": os.getenv("POSTGRES_HOST", "localhost"),
    "port": int(os.getenv("POSTGRES_PORT", "5432")),
    "database": os.getenv("POSTGRES_DB", "ai_platform_db"),
    "user": os.getenv("POSTGRES_USER", "postgres"),
    "password": os.getenv("POSTGRES_PASSWORD"),
}

if not POSTGRES_CONFIG["password"]:
    raise ValueError("POSTGRES_PASSWORD environment variable is required")

# Create server instance
server = Server("claude-webhook")

# Event queue
event_queue = asyncio.Queue()


class EventProcessor:
    def __init__(self):
        self.db_conn = None
        self.processing = False

    def connect_db(self):
        """Connect to PostgreSQL"""
        try:
            self.db_conn = psycopg2.connect(**POSTGRES_CONFIG)
            return True
        except Exception as e:
            logger.error(f"DB connection failed: {e}")
            return False

    def create_tables(self):
        """Create event tables if not exist"""
        try:
            with self.db_conn.cursor() as cur:
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS claude_events (
                        id SERIAL PRIMARY KEY,
                        event_type VARCHAR(100) NOT NULL,
                        flow_id VARCHAR(100),
                        payload JSONB,
                        priority INTEGER DEFAULT 5,
                        status VARCHAR(50) DEFAULT 'pending',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        processed_at TIMESTAMP
                    );
                    
                    CREATE INDEX IF NOT EXISTS idx_status ON claude_events(status);
                    CREATE INDEX IF NOT EXISTS idx_priority ON claude_events(priority DESC);
                """
                )
                self.db_conn.commit()
                logger.info("Event tables ready")
        except Exception as e:
            logger.error(f"Failed to create tables: {e}")

    async def process_event(self, event: Dict[str, Any]):
        """Process incoming event and decide if Claude should be woken"""
        event_type = event.get("type", "unknown")
        priority = event.get("priority", 5)

        # High priority events (1-3) wake Claude immediately
        if priority <= 3:
            await self.wake_claude(event)

        # Store in database
        self.store_event(event)

        # Check for patterns that need Claude's attention
        if await self.needs_claude_attention(event):
            await self.wake_claude(event)

    def store_event(self, event: Dict[str, Any]):
        """Store event in PostgreSQL"""
        try:
            with self.db_conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO claude_events (event_type, flow_id, payload, priority)
                    VALUES (%s, %s, %s, %s)
                """,
                    (
                        event.get("type"),
                        event.get("flow_id"),
                        json.dumps(event.get("payload", {})),
                        event.get("priority", 5),
                    ),
                )
                self.db_conn.commit()
        except Exception as e:
            logger.error(f"Failed to store event: {e}")

    async def needs_claude_attention(self, event: Dict[str, Any]) -> bool:
        """Analyze if event needs Claude's attention"""
        # Error events
        if (
            event.get("type") == "error"
            and event.get("payload", {}).get("error_rate", 0) > 0.1
        ):
            return True

        # Performance degradation
        if event.get("type") == "metrics":
            metrics = event.get("payload", {})
            if metrics.get("response_time", 0) > 5000:  # 5 seconds
                return True
            if metrics.get("error_count", 0) > 10:
                return True

        # Explicit requests
        if event.get("type") == "help_request":
            return True

        return False

    async def wake_claude(self, event: Dict[str, Any]):
        """Wake Claude by sending event to stderr and simulating Enter"""
        try:
            # Format message for Claude
            message = f"\n🔔 [Claude Webhook] {event.get('type', 'Event')}: "
            if event.get("flow_id"):
                message += f"Flow {event['flow_id']} "
            message += json.dumps(event.get("payload", {}), indent=2)

            # Write to stderr (Claude will see this)
            sys.stderr.write(message + "\n")
            sys.stderr.flush()

            # Simulate Enter key to wake Claude (platform specific)
            # This is conceptual - actual implementation would depend on terminal
            logger.info(f"Claude notified about {event.get('type')} event")

        except Exception as e:
            logger.error(f"Failed to wake Claude: {e}")

    def get_pending_events(self) -> List[Dict[str, Any]]:
        """Get pending events from database"""
        try:
            with self.db_conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT * FROM claude_events 
                    WHERE status = 'pending' 
                    ORDER BY priority ASC, created_at ASC 
                    LIMIT 10
                """
                )
                return cur.fetchall()
        except Exception as e:
            logger.error(f"Failed to get pending events: {e}")
            return []


# Global event processor
processor = EventProcessor()


@server.list_tools()
async def list_tools() -> List[Tool]:
    """List available webhook tools"""
    return [
        Tool(
            name="webhook_receive_event",
            description="Receive event from Node-RED or other source",
            inputSchema={
                "type": "object",
                "properties": {
                    "type": {
                        "type": "string",
                        "description": "Event type (error, metrics, help_request, etc.)",
                    },
                    "flow_id": {
                        "type": "string",
                        "description": "Optional Node-RED flow ID",
                    },
                    "payload": {"type": "object", "description": "Event payload data"},
                    "priority": {
                        "type": "integer",
                        "description": "Priority 1-10 (1=highest)",
                        "default": 5,
                    },
                },
                "required": ["type", "payload"],
            },
        ),
        Tool(
            name="webhook_get_events",
            description="Get pending events from queue",
            inputSchema={
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "enum": ["pending", "processed", "all"],
                        "default": "pending",
                    },
                    "limit": {"type": "integer", "default": 10},
                },
            },
        ),
        Tool(
            name="webhook_process_event",
            description="Mark event as processed",
            inputSchema={
                "type": "object",
                "properties": {
                    "event_id": {
                        "type": "integer",
                        "description": "Event ID to mark as processed",
                    }
                },
                "required": ["event_id"],
            },
        ),
        Tool(
            name="webhook_create_http_endpoint",
            description="Create HTTP endpoint for receiving webhooks",
            inputSchema={
                "type": "object",
                "properties": {
                    "port": {
                        "type": "integer",
                        "default": 8888,
                        "description": "Port for HTTP server",
                    }
                },
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """Handle tool calls"""
    try:
        if name == "webhook_receive_event":
            # Process event
            event = {
                "type": arguments["type"],
                "flow_id": arguments.get("flow_id"),
                "payload": arguments["payload"],
                "priority": arguments.get("priority", 5),
                "timestamp": datetime.now().isoformat(),
            }
            await processor.process_event(event)
            return [
                TextContent(
                    type="text",
                    text=json.dumps({"status": "received", "event": event}, indent=2),
                )
            ]

        elif name == "webhook_get_events":
            events = processor.get_pending_events()
            return [
                TextContent(
                    type="text",
                    text=json.dumps(
                        {"events": [dict(e) for e in events], "count": len(events)},
                        indent=2,
                        default=str,
                    ),
                )
            ]

        elif name == "webhook_process_event":
            try:
                with processor.db_conn.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE claude_events 
                        SET status = 'processed', processed_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                    """,
                        (arguments["event_id"],),
                    )
                    processor.db_conn.commit()
                return [
                    TextContent(
                        type="text",
                        text=json.dumps(
                            {"status": "processed", "event_id": arguments["event_id"]}
                        ),
                    )
                ]
            except Exception as e:
                return [TextContent(type="text", text=json.dumps({"error": str(e)}))]

        elif name == "webhook_create_http_endpoint":
            # Start HTTP server for webhooks
            port = arguments.get("port", 8888)
            asyncio.create_task(start_http_server(port))
            return [
                TextContent(
                    type="text",
                    text=json.dumps(
                        {
                            "status": "started",
                            "port": port,
                            "endpoint": f"http://localhost:{port}/webhook",
                        }
                    ),
                )
            ]

        else:
            return [
                TextContent(
                    type="text", text=json.dumps({"error": f"Unknown tool: {name}"})
                )
            ]

    except Exception as e:
        logger.error(f"Error in {name}: {e}")
        return [TextContent(type="text", text=json.dumps({"error": str(e)}))]


async def start_http_server(port: int):
    """Start HTTP server for receiving webhooks"""
    from aiohttp import web

    async def handle_webhook(request):
        try:
            data = await request.json()
            event = {
                "type": data.get("type", "webhook"),
                "flow_id": data.get("flow_id"),
                "payload": data.get("payload", data),
                "priority": data.get("priority", 5),
                "timestamp": datetime.now().isoformat(),
            }
            await processor.process_event(event)
            return web.json_response(
                {"status": "received", "event_id": event["timestamp"]}
            )
        except Exception as e:
            return web.json_response({"error": str(e)}, status=400)

    app = web.Application()
    app.router.add_post("/webhook", handle_webhook)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info(f"Webhook server started on port {port}")


# REMOVED: start_notify_listener() - using polling instead of stderr notifications


async def main():
    """Main entry point"""
    # Initialize database
    if processor.connect_db():
        processor.create_tables()
    else:
        logger.error("Failed to initialize database")

    # Polling system - no need for LISTEN daemon
    logger.info("Claude webhook MCP server ready (polling mode)")

    # Run the MCP server
    from mcp.server.stdio import stdio_server

    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream, write_stream, server.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
