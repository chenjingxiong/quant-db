# Quant DB Deployment Guide

## Table of Contents

1. [Deployment Options](#deployment-options)
2. [Docker Deployment](#docker-deployment)
3. [Kubernetes Deployment](#kubernetes-deployment)
4. [Cloud Deployment](#cloud-deployment)
5. [Monitoring Setup](#monitoring-setup)
6. [Backup & Recovery](#backup--recovery)
7. [Security Hardening](#security-hardening)
8. [Troubleshooting](#troubleshooting)

---

## Deployment Options

### Supported Deployments

| Method | Complexity | Scalability | Recommended For |
|--------|------------|-------------|-----------------|
| Docker Compose | Low | Limited | Development, Small Production |
| Kubernetes | Medium-High | High | Medium-Large Production |
| Cloud Platform | Low-Medium | High | Rapid Deployment |

---

## Docker Deployment

### Prerequisites

- Docker 20.10+
- Docker Compose 2.0+
- 4GB+ RAM
- 20GB+ disk space

### Quick Start

1. **Clone repository:**
   ```bash
   git clone https://github.com/your-org/quant-db.git
   cd quant-db
   ```

2. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Start services:**
   ```bash
   docker-compose up -d
   ```

4. **Check status:**
   ```bash
   docker-compose ps
   ```

### Using Deployment Scripts

```bash
# Initialize (build and start)
./scripts/deploy.sh init

# Start services
./scripts/deploy.sh up

# Stop services
./scripts/deploy.sh down

# Restart services
./scripts/deploy.sh restart

# View logs
./scripts/deploy.sh logs

# Check status
./scripts/deploy.sh status

# Clean up
./scripts/deploy.sh clean
```

### Environment Configuration

Create `.env` file:

```bash
# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=4
LOG_LEVEL=INFO

# Database
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=quant_db
POSTGRES_USER=quant_user
POSTGRES_PASSWORD=secure_password_here

# Redis
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=

# RabbitMQ
RABBITMQ_HOST=rabbitmq
RABBITMQ_PORT=5672
RABBITMQ_USER=admin
RABBITMQ_PASS=secure_password_here

# TDengine (optional)
TDENGINE_AVAILABLE=false
TDENGINE_HOST=tdengine
TDENGINE_PORT=6041

# Security
SECRET_KEY=generate-secure-secret-key
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

### Production Docker Compose

For production, use `docker-compose.prod.yml`:

```bash
docker-compose -f docker-compose.prod.yml up -d
```

Key differences:
- Multiple API replicas
- Persistent volumes
- Resource limits
- Health checks
- Auto-restart policies

---

## Kubernetes Deployment

### Prerequisites

- Kubernetes cluster (v1.24+)
- kubectl configured
- Helm 3+ (optional)
- Ingress controller

### Namespace Setup

```bash
# Create namespace
kubectl create namespace quant-db

# Set default namespace
kubectl config set-context --current --namespace=quant-db
```

### Secrets Management

```bash
# Create secret for environment variables
kubectl create secret generic quant-db-secrets \\
  --from-literal=secret-key=$(openssl rand -hex 32) \\
  --from-literal=postgres-password=$(openssl rand -hex 16) \\
  --from-literal=redis-password=$(openssl rand -hex 16)

# Create TLS secret
kubectl create secret tls quant-db-tls \\
  --cert=path/to/cert.crt \\
  --key=path/to/cert.key
```

### Deploy with Manifests

```bash
# Deploy PostgreSQL
kubectl apply -f k8s/postgres/

# Deploy Redis
kubectl apply -f k8s/redis/

# Deploy RabbitMQ
kubectl apply -f k8s/rabbitmq/

# Deploy API
kubectl apply -f k8s/api/

# Deploy Ingress
kubectl apply -f k8s/ingress/
```

### Deploy with Helm

```bash
# Add Helm repository
helm repo add quant-db https://charts.quantdb.example.com

# Install
helm install quant-db quant-db/quant-db \\
  --set image.tag=latest \\
  --set replicas=3 \\
  --set resources.requests.memory=512Mi \\
  --set secrets.existingSecret=quant-db-secrets

# Upgrade
helm upgrade quant-db quant-db/quant-db

# Uninstall
helm uninstall quant-db
```

### Example Kubernetes Manifest

```yaml
# k8s/api/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: quant-db-api
  labels:
    app: quant-db
    component: api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: quant-db
      component: api
  template:
    metadata:
      labels:
        app: quant-db
        component: api
    spec:
      containers:
      - name: api
        image: quant-db/api:latest
        ports:
        - containerPort: 8000
        env:
        - name: POSTGRES_HOST
          value: postgres-service
        - name: REDIS_HOST
          value: redis-service
        - name: SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: quant-db-secrets
              key: secret-key
        resources:
          requests:
            memory: 512Mi
            cpu: 250m
          limits:
            memory: 1Gi
            cpu: 500m
        livenessProbe:
          httpGet:
            path: /health/ping
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: quant-db-api-service
spec:
  selector:
    app: quant-db
    component: api
  ports:
  - port: 80
    targetPort: 8000
  type: ClusterIP
```

---

## Cloud Deployment

### AWS Deployment

#### Using ECS

```bash
# Create ECR repository
aws ecr create-repository --repository-name quant-db

# Push image
aws ecr get-login-password | docker login --username AWS --password-stdin <account>.dkr.ecr.<region>.amazonaws.com
docker tag quant-db:latest <account>.dkr.ecr.<region>.amazonaws.com/quant-db:latest
docker push <account>.dkr.ecr.<region>.amazonaws.com/quant-db:latest

# Deploy with ECS
aws ecs create-service \\
  --cluster quant-db-cluster \\
  --service-name quant-db-api \\
  --task-definition quant-db-task \\
  --desired-count 3 \\
  --launch-type FARGATE
```

#### Using EKS

```bash
# Create EKS cluster
eksctl create cluster \\
  --name quant-db \\
  --region us-west-2 \\
  --nodes 3 \\
  --node-type t3.medium

# Deploy
kubectl apply -f k8s/
```

### GCP Deployment

#### Using Cloud Run

```bash
# Build and push
gcloud builds submit --tag gcr.io/PROJECT_ID/quant-db

# Deploy
gcloud run deploy quant-db \\
  --image gcr.io/PROJECT_ID/quant-db \\
  --platform managed \\
  --region us-central1 \\
  --allow-unauthenticated
```

#### Using GKE

```bash
# Create cluster
gcloud container clusters create quant-db \\
  --num-nodes 3 \\
  --zone us-central1-a

# Get credentials
gcloud container clusters get-credentials quant-db

# Deploy
kubectl apply -f k8s/
```

### Azure Deployment

#### Using Container Instances

```bash
# Create resource group
az group create --name quant-db-rg --location eastus

# Create container
az container create \\
  --resource-group quant-db-rg \\
  --name quant-db \\
  --image quant-db:latest \\
  --cpu 2 \\
  --memory 4 \\
  --ports 8000
```

---

## Monitoring Setup

### Prometheus & Grafana

1. **Deploy Prometheus:**
   ```bash
   kubectl apply -f k8s/monitoring/prometheus/
   ```

2. **Deploy Grafana:**
   ```bash
   kubectl apply -f k8s/monitoring/grafana/
   ```

3. **Import Dashboards:**
   - API Performance
   - System Metrics
   - Business Metrics

### Metrics Configuration

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'quant-db-api'
    kubernetes_sd_configs:
      - role: pod
    relabel_configs:
      - source_labels: [__meta_kubernetes_pod_label_app]
        regex: quant-db
        action: keep
```

### Alerting Rules

```yaml
# alerting_rules.yml
groups:
  - name: quant-db
    rules:
      - alert: HighErrorRate
        expr: rate(api_errors_total[5m]) > 0.05
        for: 5m
        annotations:
          summary: "High API error rate"
          description: "{{ $value }} errors/sec"

      - alert: HighResponseTime
        expr: histogram_quantile(0.95, api_response_time) > 1
        for: 5m
        annotations:
          summary: "High API response time"
```

---

## Backup & Recovery

### Database Backups

```bash
# Automated backup script
./scripts/backup.sh backup postgres

# Manual backup
docker exec postgres-container pg_dump -U quant_user quant_db > backup.sql

# Restore
docker exec -i postgres-container psql -U quant_user quant_db < backup.sql
```

### Backup Configuration

```bash
# /etc/cron.d/quant-db-backups
0 2 * * * root /path/to/scripts/backup.sh backup postgres
0 3 * * * root /path/to/scripts/backup.sh backup redis
0 4 * * * root /path/to/scripts/backup.sh backup tdengine
```

### Recovery Procedures

1. **Stop services:**
   ```bash
   docker-compose stop
   ```

2. **Restore from backup:**
   ```bash
   ./scripts/backup.sh restore postgres /backups/postgres/latest.sql
   ```

3. **Verify data:**
   ```bash
   docker-compose start
   ./scripts/deploy.sh status
   ```

---

## Security Hardening

### TLS/SSL Configuration

```nginx
# nginx.conf
server {
    listen 443 ssl http2;
    server_name api.quantdb.example.com;

    ssl_certificate /etc/nginx/certs/fullchain.pem;
    ssl_certificate_key /etc/nginx/certs/privkey.pem;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    location / {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Firewall Rules

```bash
# Allow only necessary ports
ufw allow 22/tcp    # SSH
ufw allow 80/tcp    # HTTP
ufw allow 443/tcp   # HTTPS
ufw deny 8000/tcp   # Block direct API access
ufw enable
```

### Secrets Management

```bash
# Use environment variables for secrets
export SECRET_KEY=$(openssl rand -hex 32)

# Or use HashiCorp Vault
vault kv put secret/quant-db \\
  secret-key=$(openssl rand -hex 32) \\
  postgres-password=$(openssl rand -hex 16)
```

---

## Troubleshooting

### Common Issues

#### Container won't start

```bash
# Check logs
docker-compose logs backend

# Check resource usage
docker stats

# Verify configuration
docker-compose config
```

#### Database connection errors

```bash
# Check PostgreSQL status
docker-compose ps postgres

# Test connection
docker exec -it postgres-container psql -U quant_user -d quant_db

# Check network
docker network inspect quant-db_default
```

#### High memory usage

```bash
# Check container stats
docker stats --no-stream

# Add resource limits
# In docker-compose.yml:
services:
  backend:
    deploy:
      resources:
        limits:
          memory: 1G
```

### Health Checks

```bash
# Manual health check
curl http://localhost:8000/health

# Detailed health check
curl http://localhost:8000/health/detailed

# Component checks
curl http://localhost:8000/health/ping
```

### Log Analysis

```bash
# View logs
docker-compose logs -f backend

# Filter errors
docker-compose logs backend | grep ERROR

# Export logs
docker-compose logs backend > backend.log
```

---

## Performance Tuning

### API Workers

```bash
# Calculate workers: (2 x CPU cores) + 1
API_WORKERS=9  # For 4 CPU cores
```

### Connection Pools

```python
# postgres_client.py
pool = await asyncpg.create_pool(
    min_size=10,
    max_size=50,
    max_queries=50000,
    max_inactive_connection_lifetime=300.0
)
```

### Redis Configuration

```conf
# redis.conf
maxmemory 256mb
maxmemory-policy allkeys-lru
save 900 1
save 300 10
```

---

## Maintenance

### Rolling Updates

```bash
# Update with zero downtime
docker-compose up -d --no-deps --build backend

# Kubernetes rolling update
kubectl rollout restart deployment/quant-db-api
```

### Monitoring

```bash
# Check service status
watch -n 5 'docker-compose ps'

# Monitor resources
htop

# Check disk usage
df -h
```

---

## Support

- **Documentation:** https://docs.quantdb.example.com
- **Issues:** https://github.com/your-org/quant-db/issues
- **Email:** support@quantdb.example.com
