# Almighty AI Assistant - Deployment Guide

## 🚀 Quick Start Deployment

### Prerequisites
- Docker and Docker Compose installed
- Google API Key for Gemini AI
- At least 4GB RAM and 2 CPU cores

### 1. Clone Repository
```bash
git clone https://github.com/tanloifmc/Almighty-AI-assistant.git
cd Almighty-AI-assistant
```

### 2. Environment Setup
```bash
# Create environment file
cp .env.example .env

# Edit .env file with your API keys
nano .env
```

Required environment variables:
```env
GOOGLE_API_KEY=your_gemini_api_key_here
REDIS_URL=redis://redis:6379
FLASK_ENV=production
```

### 3. Deploy with Docker Compose
```bash
# Build and start all services
docker-compose up -d

# Check service status
docker-compose ps

# View logs
docker-compose logs -f
```

### 4. Access Applications
- **Main Web App**: http://localhost:3000
- **Mobile App**: http://localhost:3001
- **API Gateway**: http://localhost:80
- **Backend API**: http://localhost:5000
- **Redis**: localhost:6379

## 🔧 Individual Service Deployment

### Backend APIs
```bash
# Backend API
docker-compose up -d backend-api

# Multilingual API
docker-compose up -d multilingual-api

# Voice API
docker-compose up -d voice-api

# Collaboration API
docker-compose up -d collaboration-api

# Analytics API
docker-compose up -d analytics-api

# Training API
docker-compose up -d training-api

# Background Worker
docker-compose up -d background-worker
```

### Frontend Applications
```bash
# Web Frontend
docker-compose up -d frontend

# Mobile App
docker-compose up -d mobile-app
```

## 🌐 Production Deployment

### 1. Cloud Deployment (AWS/GCP/Azure)

#### AWS ECS Deployment
```bash
# Install AWS CLI and configure
aws configure

# Create ECS cluster
aws ecs create-cluster --cluster-name almighty-ai-cluster

# Deploy services
./deploy/aws-ecs-deploy.sh
```

#### Google Cloud Run Deployment
```bash
# Install gcloud CLI
gcloud auth login

# Deploy to Cloud Run
./deploy/gcp-cloudrun-deploy.sh
```

#### Azure Container Instances
```bash
# Install Azure CLI
az login

# Deploy to ACI
./deploy/azure-aci-deploy.sh
```

### 2. Kubernetes Deployment
```bash
# Apply Kubernetes manifests
kubectl apply -f k8s/

# Check deployment status
kubectl get pods -n almighty-ai

# Access via LoadBalancer
kubectl get services -n almighty-ai
```

### 3. VPS/Dedicated Server
```bash
# Install Docker and Docker Compose
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Clone and deploy
git clone https://github.com/tanloifmc/Almighty-AI-assistant.git
cd Almighty-AI-assistant
docker-compose up -d
```

## 🔒 Security Configuration

### 1. SSL/TLS Setup
```bash
# Generate SSL certificates
./scripts/generate-ssl.sh

# Update nginx configuration
cp nginx/nginx-ssl.conf nginx/nginx.conf

# Restart nginx
docker-compose restart nginx
```

### 2. Environment Security
```bash
# Set secure environment variables
export GOOGLE_API_KEY="your_secure_api_key"
export JWT_SECRET_KEY="your_jwt_secret"
export ENCRYPTION_KEY="your_encryption_key"

# Use Docker secrets (recommended)
echo "your_api_key" | docker secret create google_api_key -
```

### 3. Firewall Configuration
```bash
# Allow only necessary ports
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow 22/tcp
ufw enable
```

## 📊 Monitoring and Logging

### 1. Health Checks
```bash
# Check all service health
curl http://localhost/health

# Individual service health
curl http://localhost:5000/api/health
curl http://localhost:5001/api/multilingual/health
curl http://localhost:5002/api/voice/health
curl http://localhost:5003/api/collaboration/health
curl http://localhost:5004/api/analytics/health
curl http://localhost:5005/api/training/health
```

### 2. Logging
```bash
# View all logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f backend-api
docker-compose logs -f redis

# Export logs
docker-compose logs > almighty-ai-logs.txt
```

### 3. Monitoring Setup
```bash
# Deploy monitoring stack
docker-compose -f docker-compose.monitoring.yml up -d

# Access monitoring dashboards
# Grafana: http://localhost:3001
# Prometheus: http://localhost:9090
```

## 🔧 Maintenance

### 1. Updates
```bash
# Pull latest changes
git pull origin main

# Rebuild and restart services
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### 2. Backup
```bash
# Backup Redis data
docker exec almighty-redis redis-cli BGSAVE

# Backup application data
./scripts/backup.sh
```

### 3. Scaling
```bash
# Scale specific services
docker-compose up -d --scale backend-api=3
docker-compose up -d --scale background-worker=2

# Auto-scaling with Docker Swarm
docker swarm init
docker stack deploy -c docker-compose.yml almighty-ai
```

## 🐛 Troubleshooting

### Common Issues

#### 1. Redis Connection Failed
```bash
# Check Redis status
docker-compose logs redis

# Restart Redis
docker-compose restart redis

# Check Redis connectivity
docker exec almighty-redis redis-cli ping
```

#### 2. API Services Not Starting
```bash
# Check service logs
docker-compose logs backend-api

# Verify environment variables
docker-compose config

# Restart specific service
docker-compose restart backend-api
```

#### 3. Frontend Not Loading
```bash
# Check frontend logs
docker-compose logs frontend

# Verify API connectivity
curl http://localhost:5000/api/health

# Rebuild frontend
docker-compose build frontend --no-cache
docker-compose up -d frontend
```

#### 4. Memory Issues
```bash
# Check resource usage
docker stats

# Increase memory limits
# Edit docker-compose.yml and add:
# deploy:
#   resources:
#     limits:
#       memory: 2G
```

### Performance Optimization

#### 1. Redis Optimization
```bash
# Tune Redis configuration
echo "maxmemory 1gb" >> redis.conf
echo "maxmemory-policy allkeys-lru" >> redis.conf
```

#### 2. API Optimization
```bash
# Enable API caching
export ENABLE_CACHING=true

# Increase worker processes
export WORKERS=4
```

#### 3. Database Optimization
```bash
# Optimize Redis persistence
echo "save 900 1" >> redis.conf
echo "save 300 10" >> redis.conf
```

## 📈 Scaling Guide

### Horizontal Scaling
```bash
# Scale backend services
docker-compose up -d --scale backend-api=3
docker-compose up -d --scale multilingual-api=2
docker-compose up -d --scale voice-api=2

# Load balancer configuration
# Update nginx.conf with upstream servers
```

### Vertical Scaling
```bash
# Increase resource limits in docker-compose.yml
deploy:
  resources:
    limits:
      cpus: '2.0'
      memory: 4G
    reservations:
      cpus: '1.0'
      memory: 2G
```

### Database Scaling
```bash
# Redis Cluster setup
docker-compose -f docker-compose.redis-cluster.yml up -d

# Redis Sentinel for high availability
docker-compose -f docker-compose.redis-sentinel.yml up -d
```

## 🔐 Security Best Practices

### 1. API Security
- Use HTTPS in production
- Implement rate limiting
- Validate all inputs
- Use JWT tokens with short expiration
- Enable CORS only for trusted domains

### 2. Container Security
- Use non-root users in containers
- Scan images for vulnerabilities
- Keep base images updated
- Use Docker secrets for sensitive data

### 3. Network Security
- Use private networks for internal communication
- Implement firewall rules
- Monitor network traffic
- Use VPN for remote access

## 📞 Support

For deployment issues or questions:
- GitHub Issues: https://github.com/tanloifmc/Almighty-AI-assistant/issues
- Documentation: https://github.com/tanloifmc/Almighty-AI-assistant/wiki
- Email: support@almighty-ai.com

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

