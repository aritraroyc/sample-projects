# Remote Deployment Quick Start

Quick guide to deploying the Java Error Checker MCP service for remote access from LangGraph agents.

## Overview

This guide shows you how to:
1. Deploy the MCP server with HTTP/SSE transport
2. Connect from a remote LangGraph agent
3. Verify everything works

## 5-Minute Setup

### Step 1: Start the MCP Server

**Option A: Local Development**

```bash
# Install dependencies
pip install -r requirements.txt

# Start SSE server
python server_sse.py --host 0.0.0.0 --port 8000
```

**Option B: Docker**

```bash
# Build and run
docker-compose up -d

# Check logs
docker-compose logs -f
```

Server will be available at:
- SSE endpoint: `http://localhost:8000/sse`
- Health check: `http://localhost:8000/health`

### Step 2: Verify Server

```bash
# Health check
curl http://localhost:8000/health

# Expected response:
# {
#   "status": "healthy",
#   "service": "java-error-checker-mcp",
#   "transport": "sse"
# }
```

### Step 3: Connect from Remote Agent

**Simple Python Client:**

```python
import asyncio
from langgraph_integration import JavaErrorCheckerClient

async def main():
    # Connect to remote server
    client = JavaErrorCheckerClient(base_url="http://your-server:8000")

    # Verify connection
    health = await client.health_check()
    print(f"Connected to: {health['service']}")

    # Create session
    session_id = await client.create_session("test-project")
    print(f"Session: {session_id}")

    # Write Java code
    await client.write_file(
        "com/example/Main.java",
        """package com.example;

public class Main {
    public static void main(String[] args) {
        System.out.println("Hello from remote MCP!");
    }
}
"""
    )

    # Check for errors
    errors = await client.check_errors()
    print(f"Errors: {errors['error_count']}")

    # Cleanup
    await client.delete_session()

asyncio.run(main())
```

**LangGraph Agent:**

```python
import asyncio
from langgraph_integration import JavaErrorCheckerClient

# Create client pointing to your deployed server
client = JavaErrorCheckerClient(base_url="http://your-server:8000")

# Use in your LangGraph workflow
# ... (see LANGGRAPH_INTEGRATION.md for full examples)
```

### Step 4: Test End-to-End

```bash
# Run the example
python langgraph_agent_example.py --mode simple --server http://localhost:8000

# Expected output:
# ✓ Connected to MCP server: java-error-checker-mcp
#   Transport: sse
# ✓ Session created
# ✓ Wrote 2 files
# ✓ No compilation errors! Code is valid.
# ✓ Session cleaned up automatically
```

## Deployment Options

### Option 1: Single Server (Development)

```bash
# Start on default port
python server_sse.py

# Agent connects to
# http://localhost:8000
```

**Use Case:** Local development, testing

### Option 2: Remote Server (Production)

**Server Side:**

```bash
# On your remote server
git clone <repo-url>
cd java-error-checker-mcp
pip install -r requirements.txt

# Start with public access
python server_sse.py --host 0.0.0.0 --port 8000

# Configure firewall
sudo ufw allow 8000
```

**Client Side:**

```python
# In your LangGraph agent (running anywhere)
client = JavaErrorCheckerClient(
    base_url="http://your-remote-server.com:8000"
)
```

**Use Case:** Remote agents, cloud deployment

### Option 3: Docker Deployment

**Build:**

```bash
docker build -t java-error-checker-mcp .
```

**Run:**

```bash
# Single container
docker run -d \
  -p 8000:8000 \
  --name java-mcp \
  java-error-checker-mcp

# With docker-compose
docker-compose up -d
```

**Client:**

```python
client = JavaErrorCheckerClient(
    base_url="http://docker-host:8000"
)
```

**Use Case:** Containerized deployment, easy scaling

### Option 4: Cloud Deployment (AWS/GCP/Azure)

**Deploy to Cloud VM:**

```bash
# 1. Create VM instance
# 2. SSH to instance
ssh user@vm-ip

# 3. Install dependencies
sudo apt update
sudo apt install -y python3-pip openjdk-17-jdk
pip3 install -r requirements.txt

# 4. Run server
python3 server_sse.py --host 0.0.0.0 --port 8000

# 5. Configure security group to allow port 8000
```

**Client:**

```python
client = JavaErrorCheckerClient(
    base_url=f"http://{vm_public_ip}:8000"
)
```

**Use Case:** Production deployment, high availability

### Option 5: Kubernetes

**Deploy:**

```bash
# See LANGGRAPH_INTEGRATION.md for full Kubernetes manifests
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml

# Get service URL
kubectl get service java-error-checker-mcp
```

**Client:**

```python
# Inside cluster
client = JavaErrorCheckerClient(
    base_url="http://java-error-checker-mcp:8000"
)

# Outside cluster (LoadBalancer)
client = JavaErrorCheckerClient(
    base_url="http://<external-ip>:8000"
)
```

**Use Case:** Microservices architecture, auto-scaling

## Configuration

### Environment Variables

```bash
# Workspace directory
export JDTLS_WORKSPACE_DIR=/tmp/jdtls-workspaces

# Session timeout (seconds)
export SESSION_TIMEOUT=3600

# Java home
export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64

# Log level
export LOG_LEVEL=INFO
```

### Server Options

```bash
# Custom host and port
python server_sse.py --host 0.0.0.0 --port 9000

# Help
python server_sse.py --help
```

## Testing

### Health Check

```bash
curl http://localhost:8000/health
```

### Create Session

```bash
curl -X POST http://localhost:8000/sse \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "create_session",
      "arguments": {"project_name": "test"}
    },
    "id": 1
  }'
```

### Full Workflow Test

```bash
# Run the example
python langgraph_agent_example.py --mode simple --server http://localhost:8000
```

## Monitoring

### Server Logs

```bash
# Log file
tail -f /tmp/java-error-checker-mcp-sse.log

# Docker logs
docker logs -f java-mcp

# Docker-compose logs
docker-compose logs -f
```

### Health Monitoring

```python
import asyncio
from langgraph_integration import JavaErrorCheckerClient

async def monitor_health():
    client = JavaErrorCheckerClient("http://localhost:8000")

    while True:
        try:
            health = await client.health_check()
            print(f"✓ Server healthy: {health}")
        except Exception as e:
            print(f"✗ Server unhealthy: {e}")

        await asyncio.sleep(30)  # Check every 30 seconds

asyncio.run(monitor_health())
```

## Security

### Production Checklist

- [ ] Use HTTPS instead of HTTP
- [ ] Add authentication/API keys
- [ ] Restrict CORS to specific domains
- [ ] Configure firewall rules
- [ ] Set up monitoring and alerting
- [ ] Use environment variables for secrets
- [ ] Regular security updates
- [ ] Resource limits (CPU/memory)

### HTTPS Setup

**Using Nginx as reverse proxy:**

```nginx
server {
    listen 443 ssl;
    server_name your-domain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

**Client:**

```python
client = JavaErrorCheckerClient(
    base_url="https://your-domain.com"
)
```

## Troubleshooting

### Connection Issues

**Problem:** Cannot connect to server

**Solutions:**

```bash
# 1. Verify server is running
curl http://localhost:8000/health

# 2. Check server logs
tail -f /tmp/java-error-checker-mcp-sse.log

# 3. Verify port is open
netstat -an | grep 8000

# 4. Check firewall
sudo ufw status
sudo ufw allow 8000

# 5. Test from remote machine
curl http://server-ip:8000/health
```

### Java Not Found

**Problem:** javac not found

**Solutions:**

```bash
# Install Java JDK
sudo apt install openjdk-17-jdk

# Verify
java -version
javac -version

# Set JAVA_HOME
export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
```

### Docker Issues

**Problem:** Container not starting

**Solutions:**

```bash
# Check logs
docker logs java-mcp

# Rebuild
docker-compose down
docker-compose build --no-cache
docker-compose up

# Check Java inside container
docker exec -it java-mcp java -version
```

## Performance Tuning

### Concurrent Sessions

```bash
# Increase file descriptor limits
ulimit -n 10000

# Increase session timeout for long workflows
export SESSION_TIMEOUT=7200  # 2 hours
```

### Resource Limits

**Docker:**

```yaml
# docker-compose.yml
services:
  java-error-checker-mcp:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          cpus: '1'
          memory: 2G
```

**Kubernetes:**

```yaml
resources:
  limits:
    cpu: "2"
    memory: "4Gi"
  requests:
    cpu: "1"
    memory: "2Gi"
```

## Next Steps

1. **For detailed LangGraph integration**, see [LANGGRAPH_INTEGRATION.md](LANGGRAPH_INTEGRATION.md)
2. **For agentic workflows**, see [AGENTIC_WORKFLOWS.md](AGENTIC_WORKFLOWS.md)
3. **For complete documentation**, see [README.md](README.md)

## Quick Reference

| Task | Command |
|------|---------|
| Start server | `python server_sse.py` |
| Health check | `curl http://localhost:8000/health` |
| View logs | `tail -f /tmp/java-error-checker-mcp-sse.log` |
| Run example | `python langgraph_agent_example.py --mode simple` |
| Docker build | `docker-compose build` |
| Docker run | `docker-compose up -d` |
| Docker logs | `docker-compose logs -f` |
| Stop server | `Ctrl+C` or `docker-compose down` |

## Support

For issues or questions:
- Check logs: `/tmp/java-error-checker-mcp-sse.log`
- Review documentation: `README.md`, `LANGGRAPH_INTEGRATION.md`
- Run health check: `curl http://localhost:8000/health`
- Test with example: `python langgraph_agent_example.py`

---

**Ready to deploy?** Start with Option 1 (Single Server) for development, then move to Option 4 (Cloud) or Option 5 (Kubernetes) for production.
