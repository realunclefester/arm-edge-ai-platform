# Deployment Guide

Complete guide for deploying the ARM Edge AI Platform on Raspberry Pi and other ARM-based systems.

## Prerequisites

### Hardware Requirements
- **CPU**: ARM64 processor (Raspberry Pi 4/5 recommended)
- **RAM**: 4GB minimum, 8GB recommended
- **Storage**: 32GB minimum, 64GB+ recommended for production
- **Network**: Ethernet or WiFi connectivity
- **Optional**: External SSD for better performance

### Software Requirements
- **OS**: Raspberry Pi OS (64-bit) or Ubuntu Server ARM64
- **Docker**: Version 20.10+ with Docker Compose
- **Git**: For repository management
- **SSH**: For remote access and key management

### Network Configuration
- **SSH Access**: Port 22 (configure SSH keys)
- **Service Ports**: 1880, 5432, 8001-8004
- **Optional**: Tailscale for VPN access

## Installation Steps

### 1. System Preparation

```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Install required packages
sudo apt install -y git docker.io docker-compose curl wget

# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker

# Enable Docker service
sudo systemctl enable docker
sudo systemctl start docker
```

### 2. Repository Setup

```bash
# Clone the repository
git clone https://github.com/realunclefester/ARM-Edge-AI-Platform.git
cd ARM-Edge-AI-Platform

# Set up SSH keys (if not already configured)
ssh-keygen -t ed25519 -C "your-email@example.com"
# Add public key to GitHub: ~/.ssh/id_ed25519.pub
```

### 3. Environment Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit environment variables
nano .env
```

#### Environment Variables Configuration

```bash
# Database Configuration
POSTGRES_DB=ai_platform_db
POSTGRES_USER=ai_platform_user
POSTGRES_PASSWORD=your_secure_password_here
DATABASE_URL=postgresql://ai_platform_user:your_secure_password_here@postgres:5432/ai_platform_db

# Service Configuration
LOG_LEVEL=INFO
MAX_BATCH_SIZE=100
MODEL_CACHE_DIR=/app/models

# Network Configuration
COMPOSE_PROJECT_NAME=arm_edge_ai
DOCKER_NETWORK=ai_platform_network

# Optional: External API Keys
GITHUB_TOKEN=your_github_token_here
OPENAI_API_KEY=your_openai_key_here
```

### 4. Database Initialization

```bash
# Start PostgreSQL first
docker compose up -d postgres

# Wait for PostgreSQL to be ready
sleep 30

# Note: Database initialization and pgvector extension are handled automatically
# by the PostgreSQL container during first startup
```

### 5. Service Deployment

```bash
# Deploy all services
docker compose up -d

# Verify deployment
docker compose ps
docker compose logs
```

### 6. Health Verification

```bash
# Check service health
curl http://localhost:8001/health  # Embeddings
curl http://localhost:8002/health  # Analytics
curl http://localhost:8004/health  # Log Aggregator
curl http://localhost:8003/        # Plotly Viz

# Check Node-RED
curl http://localhost:1880/

# Check PostgreSQL
docker exec ai_platform_postgres pg_isready -U ai_platform_user
```

## Production Configuration

### 1. Security Hardening

#### SSH Configuration
```bash
# Edit SSH configuration
sudo nano /etc/ssh/sshd_config

# Recommended settings:
PasswordAuthentication no
PubkeyAuthentication yes
PermitRootLogin no
Port 22
AllowUsers your_username

# Restart SSH service
sudo systemctl restart ssh
```

#### Firewall Configuration
```bash
# Install and configure UFW
sudo apt install ufw

# Default policies
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Allow SSH
sudo ufw allow 22/tcp

# Allow service ports (adjust as needed)
sudo ufw allow 1880/tcp  # Node-RED
sudo ufw allow 5432/tcp  # PostgreSQL (if external access needed)
sudo ufw allow 8001/tcp  # Embeddings
sudo ufw allow 8002/tcp  # Analytics
sudo ufw allow 8003/tcp  # Plotly
sudo ufw allow 8004/tcp  # Log Aggregator

# Enable firewall
sudo ufw enable
```

### 2. Performance Optimization

#### Docker Configuration
```bash
# Create Docker daemon configuration
sudo nano /etc/docker/daemon.json

{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  },
  "storage-driver": "overlay2",
  "default-ulimits": {
    "nofile": {
      "Hard": 64000,
      "Name": "nofile",
      "Soft": 64000
    }
  }
}

# Restart Docker
sudo systemctl restart docker
```

#### System Optimization
```bash
# Increase file limits
echo "* soft nofile 64000" | sudo tee -a /etc/security/limits.conf
echo "* hard nofile 64000" | sudo tee -a /etc/security/limits.conf

# Optimize PostgreSQL for ARM
# Edit postgresql.conf in the container or mount custom config
```

### 3. Monitoring Setup

#### Health Check Script
```bash
# Create health check script
cat > /home/pi/health_check.sh << 'EOF'
#!/bin/bash

SERVICES=("embeddings:8001" "analytics:8002" "log-aggregator:8004" "plotly:8003" "node-red:1880")
FAILED=0

for service in "${SERVICES[@]}"; do
    name=${service%:*}
    port=${service#*:}
    
    if ! curl -f -s http://localhost:$port/health > /dev/null 2>&1; then
        echo "$(date): $name service health check failed"
        FAILED=1
    fi
done

if [ $FAILED -eq 1 ]; then
    echo "$(date): Some services are unhealthy"
    exit 1
else
    echo "$(date): All services healthy"
    exit 0
fi
EOF

chmod +x /home/pi/health_check.sh
```

#### Automated Monitoring
```bash
# Add to crontab for regular health checks
crontab -e

# Add this line for 5-minute health checks
*/5 * * * * /home/pi/health_check.sh >> /var/log/health_check.log 2>&1
```

## MCP Server Setup

### 1. MCP Server Installation

```bash
# Install Python dependencies for MCP servers
cd mcp-servers
pip install -r requirements.txt

# Make MCP servers executable
chmod +x *.py
```

### 2. Claude Code Integration

```bash
# Install Claude Code CLI (if not already installed)
# Follow official Claude Code installation instructions

# Configure MCP servers in Claude Code
# Add to your MCP configuration file
```

### 3. MCP Server Management

```bash
# Start individual MCP servers
python mcp-servers/pgvector_memory_mcp.py &
python mcp-servers/system_monitor_mcp.py &
python mcp-servers/github_mcp.py &
python mcp-servers/node_red_mcp.py &
python mcp-servers/claude_webhook_mcp.py &
python mcp-servers/postgres_mcp.py &

# Or use a process manager like systemd or supervisor
```

## Backup and Recovery

### 1. Database Backup

```bash
# Create backup script
cat > /home/pi/backup_db.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/home/pi/backups"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# PostgreSQL backup
docker exec ai_platform_postgres pg_dumpall -U ai_platform_user > $BACKUP_DIR/postgres_backup_$DATE.sql

# Compress backup
gzip $BACKUP_DIR/postgres_backup_$DATE.sql

# Keep only last 7 backups
find $BACKUP_DIR -name "postgres_backup_*.sql.gz" -mtime +7 -delete

echo "Backup completed: postgres_backup_$DATE.sql.gz"
EOF

chmod +x /home/pi/backup_db.sh

# Schedule daily backups
crontab -e
# Add: 0 2 * * * /home/pi/backup_db.sh
```

### 2. Volume Backup

```bash
# Backup Docker volumes
docker run --rm -v arm_edge_ai_postgres_data:/data -v /home/pi/backups:/backup alpine tar czf /backup/volumes_backup_$(date +%Y%m%d).tar.gz -C /data .

# Backup Node-RED flows
docker run --rm -v arm_edge_ai_node_red_data:/data -v /home/pi/backups:/backup alpine tar czf /backup/node_red_backup_$(date +%Y%m%d).tar.gz -C /data .
```

## Troubleshooting

### Common Issues

#### Services Won't Start
```bash
# Check Docker logs
docker compose logs service-name

# Check resource usage
docker stats

# Check disk space
df -h

# Check memory usage
free -h
```

#### Database Connection Issues
```bash
# Check PostgreSQL status
docker exec ai_platform_postgres pg_isready -U ai_platform_user

# Check database logs
docker logs ai_platform_postgres

# Test connection manually
docker exec ai_platform_postgres psql -U ai_platform_user -d ai_platform_db -c "SELECT version();"
```

#### Performance Issues
```bash
# Monitor system resources
htop
iotop
netstat -tuln

# Check Docker resource usage
docker stats

# Monitor PostgreSQL performance
docker exec postgres psql -U ai_user -d ai_platform -c "SELECT * FROM pg_stat_activity;"
```

### Recovery Procedures

#### Service Recovery
```bash
# Restart individual service
docker compose restart service-name

# Restart all services
docker compose restart

# Rebuild and restart
docker compose down
docker compose build --no-cache
docker compose up -d
```

#### Database Recovery
```bash
# Stop services
docker compose down

# Restore from backup
gunzip -c /home/pi/backups/postgres_backup_YYYYMMDD_HHMMSS.sql.gz | docker exec -i postgres psql -U ai_user

# Restart services
docker compose up -d
```

## Maintenance

### Regular Maintenance Tasks

#### Weekly Tasks
- Review service logs for errors
- Check disk space usage
- Verify backup completion
- Update system packages
- Monitor service performance

#### Monthly Tasks
- Update Docker images
- Clean up old logs and backups
- Review security configurations
- Performance optimization review
- Documentation updates

#### Quarterly Tasks
- Full system backup
- Security audit
- Performance benchmarking
- Hardware health check
- Disaster recovery testing

### Update Procedures

#### System Updates
```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Update Docker images
docker compose pull
docker compose down
docker compose up -d
```

#### Application Updates
```bash
# Pull latest code
git pull origin main

# Rebuild containers
docker compose build --no-cache
docker compose down
docker compose up -d
```

## Performance Tuning

### Raspberry Pi Specific Optimizations

#### GPU Memory Split
```bash
# Edit config.txt
sudo nano /boot/config.txt

# Add these lines for headless operation
gpu_mem=16
disable_camera=1
```

#### CPU Governor
```bash
# Set performance governor
echo 'performance' | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor
```

#### Memory Configuration
```bash
# Increase swap (if needed)
sudo dphys-swapfile swapoff
sudo nano /etc/dphys-swapfile
# Set CONF_SWAPSIZE=2048
sudo dphys-swapfile setup
sudo dphys-swapfile swapon
```

### Service-Specific Tuning

#### PostgreSQL Tuning
```sql
-- Connect to PostgreSQL and adjust settings
ALTER SYSTEM SET shared_buffers = '512MB';
ALTER SYSTEM SET effective_cache_size = '2GB';
ALTER SYSTEM SET work_mem = '16MB';
ALTER SYSTEM SET maintenance_work_mem = '128MB';
SELECT pg_reload_conf();
```

#### Docker Resource Limits
```yaml
# In docker-compose.yml, add resource limits
services:
  embeddings:
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: '1.0'
        reservations:
          memory: 512M
          cpus: '0.5'
```

This deployment guide provides comprehensive instructions for setting up the ARM Edge AI Platform in production environments. Follow the security hardening and monitoring recommendations for optimal performance and reliability.