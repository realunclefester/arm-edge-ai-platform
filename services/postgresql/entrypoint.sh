#!/bin/bash
# PostgreSQL entrypoint script for ARM Edge AI Platform
set -e

# Execute the original PostgreSQL entrypoint with all arguments
exec /usr/local/bin/docker-entrypoint.sh "$@"