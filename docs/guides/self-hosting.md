# Self-Hosting Guide

This guide covers deploying SpotDL on your own infrastructure for personal or organizational use.

## Overview

A complete SpotDL deployment consists of:

- **Backend API**: FastAPI application handling matching and data
- **Frontend**: React web interface
- **Database**: PostgreSQL (production) or SQLite (development)
- **Cache**: Redis (optional, improves performance)
- **Reverse Proxy**: Nginx for SSL and routing

## Quick Start with Docker Compose

### Prerequisites

- Docker and Docker Compose installed
- Domain name (optional, for SSL)
- At least 1GB RAM available

### Basic Setup

1. Clone the repository:

```bash
git clone https://github.com/spotDL/spotify-downloader.git
cd spotify-downloader
```

2. Create environment file:

```bash
cp .env.example .env
```

3. Edit `.env` with your settings:

```bash
# Required - generate with: openssl rand -hex 32
SECRET_KEY=your-generated-secret-key

# Required - database password
DB_PASSWORD=your-secure-password

# Optional - your domain
CORS_ORIGINS=https://spotdl.yourdomain.com
```

4. Start the production stack:

```bash
docker compose -f docker-compose.prod.yml up -d
```

5. Verify all services are running:

```bash
docker compose -f docker-compose.prod.yml ps
```

## Docker Compose Configuration

### Production Stack

The `docker-compose.prod.yml` includes:

```yaml
services:
  api:
    # Backend API on port 8000 (internal)

  frontend:
    # React frontend on port 80 (internal)

  nginx:
    # Reverse proxy on ports 80/443 (external)

  db:
    # PostgreSQL database

  redis:
    # Redis cache
```

### Service Configuration

#### API Service

```yaml
api:
  image: ghcr.io/spotdl/spotify-downloader-backend:latest
  environment:
    - DATABASE_URL=postgresql+asyncpg://spotdl:${DB_PASSWORD}@db:5432/spotdl
    - REDIS_URL=redis://redis:6379
    - ENVIRONMENT=production
    - SECRET_KEY=${SECRET_KEY}
    - CORS_ORIGINS=${CORS_ORIGINS}
```

#### Database Service

```yaml
db:
  image: postgres:16-alpine
  environment:
    - POSTGRES_USER=spotdl
    - POSTGRES_PASSWORD=${DB_PASSWORD}
    - POSTGRES_DB=spotdl
  volumes:
    - postgres_data:/var/lib/postgresql/data
```

#### Redis Service

```yaml
redis:
  image: redis:7-alpine
  command: redis-server --appendonly yes
  volumes:
    - redis_data:/data
```

### Custom Build

To build images locally instead of pulling from registry:

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

## SSL Certificates

### Option 1: Let's Encrypt with Certbot

1. Install certbot on your host:

```bash
sudo apt install certbot
```

2. Generate certificates:

```bash
sudo certbot certonly --standalone -d spotdl.yourdomain.com
```

3. Copy certificates to nginx directory:

```bash
sudo cp /etc/letsencrypt/live/spotdl.yourdomain.com/fullchain.pem nginx/certs/cert.pem
sudo cp /etc/letsencrypt/live/spotdl.yourdomain.com/privkey.pem nginx/certs/key.pem
```

4. Set up auto-renewal:

```bash
sudo crontab -e
# Add: 0 0 * * * certbot renew --quiet && docker compose -f docker-compose.prod.yml restart nginx
```

### Option 2: Self-Signed Certificates

For testing or internal use:

```bash
mkdir -p nginx/certs
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout nginx/certs/key.pem \
  -out nginx/certs/cert.pem \
  -subj "/CN=spotdl.local"
```

### Option 3: Bring Your Own Certificates

Place your certificate files in `nginx/certs/`:
- `cert.pem` - Certificate chain
- `key.pem` - Private key

## Reverse Proxy Configuration

### Default Nginx Configuration

The included `nginx/nginx.conf` handles:

- HTTP to HTTPS redirect
- SSL termination
- API routing (`/api/*`)
- WebSocket support (`/api/v1/ws`)
- Frontend serving
- Static asset caching
- Security headers
- Rate limiting

### Key Configuration Sections

```nginx
# Rate limiting zones
limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
limit_req_zone $binary_remote_addr zone=general:10m rate=30r/s;

# API proxy
location /api/ {
    limit_req zone=api burst=20 nodelay;
    proxy_pass http://api;
}

# Frontend
location / {
    limit_req zone=general burst=50 nodelay;
    proxy_pass http://frontend;
}
```

### Using External Reverse Proxy

If you have an existing reverse proxy (Traefik, Caddy, etc.), disable the nginx service:

```yaml
# docker-compose.override.yml
services:
  nginx:
    deploy:
      replicas: 0
  api:
    ports:
      - "8000:8000"
  frontend:
    ports:
      - "3000:80"
```

#### Traefik Example

```yaml
services:
  api:
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.spotdl-api.rule=Host(`spotdl.yourdomain.com`) && PathPrefix(`/api`)"
      - "traefik.http.services.spotdl-api.loadbalancer.server.port=8000"
```

#### Caddy Example

```
spotdl.yourdomain.com {
    handle /api/* {
        reverse_proxy api:8000
    }
    handle {
        reverse_proxy frontend:80
    }
}
```

## Database Management

### Migrations

Run database migrations after updates:

```bash
docker compose -f docker-compose.prod.yml exec api alembic upgrade head
```

### Backups

#### Automated Backups

Create a backup script:

```bash
#!/bin/bash
# backup.sh
DATE=$(date +%Y%m%d_%H%M%S)
docker compose -f docker-compose.prod.yml exec -T db \
  pg_dump -U spotdl spotdl > backup_${DATE}.sql
```

Schedule with cron:

```bash
0 2 * * * /path/to/backup.sh
```

#### Restore from Backup

```bash
docker compose -f docker-compose.prod.yml exec -T db \
  psql -U spotdl spotdl < backup_20240101_020000.sql
```

### Database Maintenance

```bash
# Vacuum database
docker compose -f docker-compose.prod.yml exec db \
  vacuumdb -U spotdl -d spotdl -z

# Analyze tables
docker compose -f docker-compose.prod.yml exec db \
  psql -U spotdl -d spotdl -c "ANALYZE;"
```

## Monitoring

### Health Checks

All services include health checks. View status:

```bash
docker compose -f docker-compose.prod.yml ps
```

API health endpoint:

```bash
curl https://spotdl.yourdomain.com/api/v1/health
```

### Logs

View logs:

```bash
# All services
docker compose -f docker-compose.prod.yml logs -f

# Specific service
docker compose -f docker-compose.prod.yml logs -f api

# Last 100 lines
docker compose -f docker-compose.prod.yml logs --tail=100 api
```

### Resource Monitoring

```bash
docker stats
```

## Scaling

### Horizontal Scaling

Scale API workers:

```yaml
# docker-compose.override.yml
services:
  api:
    deploy:
      replicas: 3
```

Update nginx for load balancing:

```nginx
upstream api {
    least_conn;
    server api_1:8000;
    server api_2:8000;
    server api_3:8000;
}
```

### Resource Limits

```yaml
services:
  api:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '0.5'
          memory: 512M
```

## Security Considerations

### Network Isolation

The production compose file uses two networks:
- `internal`: Database and Redis (not exposed)
- `web`: API, frontend, nginx

### Environment Variables

Never commit secrets to version control:

```bash
# Use .env file (gitignored)
SECRET_KEY=$(openssl rand -hex 32)
DB_PASSWORD=$(openssl rand -base64 24)
```

### Firewall Rules

Allow only necessary ports:

```bash
# UFW example
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw deny 5432/tcp  # Block direct database access
sudo ufw deny 6379/tcp  # Block direct Redis access
```

### Rate Limiting

Adjust rate limits in nginx config:

```nginx
# More restrictive for API
limit_req_zone $binary_remote_addr zone=api:10m rate=5r/s;

# Less restrictive for static content
limit_req_zone $binary_remote_addr zone=static:10m rate=50r/s;
```

## Updating

### Update Process

1. Pull latest changes:

```bash
git pull origin master
```

2. Pull new images:

```bash
docker compose -f docker-compose.prod.yml pull
```

3. Restart services:

```bash
docker compose -f docker-compose.prod.yml up -d
```

4. Run migrations:

```bash
docker compose -f docker-compose.prod.yml exec api alembic upgrade head
```

### Rollback

If issues occur:

```bash
# Stop services
docker compose -f docker-compose.prod.yml down

# Checkout previous version
git checkout v5.0.0

# Start with previous images
docker compose -f docker-compose.prod.yml up -d
```

## Troubleshooting

### Common Issues

**API not starting:**
```bash
docker compose -f docker-compose.prod.yml logs api
# Check for database connection issues
```

**Database connection refused:**
```bash
# Ensure db service is healthy
docker compose -f docker-compose.prod.yml exec db pg_isready -U spotdl
```

**502 Bad Gateway:**
```bash
# Check if backend is running
docker compose -f docker-compose.prod.yml ps
# Check nginx logs
docker compose -f docker-compose.prod.yml logs nginx
```

**SSL certificate errors:**
```bash
# Verify certificates exist
ls -la nginx/certs/
# Check certificate validity
openssl x509 -in nginx/certs/cert.pem -text -noout
```

### Useful Commands

```bash
# Restart a specific service
docker compose -f docker-compose.prod.yml restart api

# Rebuild and restart
docker compose -f docker-compose.prod.yml up -d --build api

# Execute command in container
docker compose -f docker-compose.prod.yml exec api python -c "print('test')"

# View real-time logs
docker compose -f docker-compose.prod.yml logs -f --tail=50
```

## See Also

- [Installation Guide](../getting-started/installation.md)
- [Configuration Reference](../getting-started/configuration.md)
- [Architecture Overview](../development/architecture.md)
