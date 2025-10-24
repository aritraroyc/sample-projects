

# LangGraph Integration Guide

Complete guide for consuming the Java Error Checker MCP service from LangGraph agents running remotely.

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Setup](#setup)
4. [Quick Start](#quick-start)
5. [LangGraph Integration](#langgraph-integration)
6. [Remote Deployment](#remote-deployment)
7. [Examples](#examples)
8. [Best Practices](#best-practices)
9. [Troubleshooting](#troubleshooting)

## Overview

The Java Error Checker MCP service can be consumed by remote LangGraph agents via HTTP/SSE transport. This enables:

- **Remote Code Generation**: LangGraph agents generate Java code and validate it remotely
- **Multi-Agent Workflows**: Multiple agents can use the service concurrently
- **Cloud Deployment**: Deploy MCP server separately from agents
- **Scalability**: Scale agents and MCP service independently

## Architecture

```
┌─────────────────────┐
│  LangGraph Agent    │
│  (Remote/Cloud)     │
└──────────┬──────────┘
           │ HTTP/SSE
           ▼
┌─────────────────────┐
│  MCP Server (SSE)   │
│  Port: 8000         │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Session Manager    │
│  JDTLS / javac      │
└─────────────────────┘
```

### Communication Flow

1. **LangGraph Agent** sends tool requests via HTTP
2. **MCP Server (SSE)** processes requests and manages sessions
3. **Session Manager** handles workspaces and file operations
4. **JDTLS/javac** validates Java code
5. **Results** returned to agent via HTTP response

## Setup

### 1. Install Dependencies

```bash
# Server dependencies
pip install -r requirements.txt

# Additional for SSE server
pip install uvicorn starlette

# LangGraph agent dependencies
pip install langgraph langchain-openai httpx
```

### 2. Start the MCP Server with SSE Transport

```bash
# Start on localhost
python server_sse.py

# Start on specific host/port
python server_sse.py --host 0.0.0.0 --port 8000

# Start in Docker
docker-compose up -d
```

The server will be available at:
- **SSE Endpoint**: `http://localhost:8000/sse`
- **Health Check**: `http://localhost:8000/health`

### 3. Verify Server is Running

```bash
# Check health
curl http://localhost:8000/health

# Should return:
# {
#   "status": "healthy",
#   "service": "java-error-checker-mcp",
#   "transport": "sse"
# }
```

## Quick Start

### Simple Python Client (No LangGraph)

```python
import asyncio
from langgraph_integration import JavaErrorCheckerClient, JavaProjectSession

async def main():
    client = JavaErrorCheckerClient(base_url="http://localhost:8000")

    # Use context manager for automatic cleanup
    async with JavaProjectSession(client, "my-project") as session:
        # Write Java files
        await session.write_multiple_files([
            {
                "file_path": "com/example/Main.java",
                "content": "package com.example;\n\npublic class Main {...}"
            }
        ])

        # Check errors
        errors = await session.check_errors()
        print(f"Errors: {errors['error_count']}")

    # Session automatically cleaned up

asyncio.run(main())
```

### With LangGraph Tools

```python
from langgraph_integration import JavaErrorCheckerClient, create_langgraph_tools

# Create client
client = JavaErrorCheckerClient(base_url="http://localhost:8000")

# Create LangGraph-compatible tools
tools = create_langgraph_tools(client)

# Use tools in your LangGraph agent
# ... (see full example below)
```

## LangGraph Integration

### Method 1: Using the Integration Module

The `langgraph_integration.py` module provides ready-to-use tools:

```python
from langgraph_integration import JavaErrorCheckerClient, create_langgraph_tools
from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI

# Create MCP client
client = JavaErrorCheckerClient(base_url="http://your-mcp-server:8000")

# Create tools
tools = create_langgraph_tools(client)

# Create LLM
llm = ChatOpenAI(model="gpt-4", temperature=0)

# Create agent
agent = create_react_agent(llm, tools)

# Run agent
response = await agent.ainvoke({
    "messages": [("user", "Create a Java calculator class")]
})
```

### Method 2: Custom Tools

Define custom tools for your specific workflow:

```python
from langchain_core.tools import tool
from langgraph_integration import JavaErrorCheckerClient

client = JavaErrorCheckerClient(base_url="http://localhost:8000")

@tool
async def generate_java_models(requirements: str) -> str:
    """Generate Java model classes based on requirements."""
    # Your LLM generates code here
    files = llm_generate_models(requirements)

    # Write to MCP service
    result = await client.write_multiple_files(files)
    return json.dumps(result)

@tool
async def validate_and_fix_java() -> str:
    """Validate Java code and get fix suggestions."""
    # Check errors
    errors = await client.check_errors()

    if errors["error_count"] > 0:
        # Get recommendations for first error
        error = errors["errors"][0]
        recs = await client.get_recommendations(error)
        return json.dumps({
            "errors": errors,
            "recommendations": recs
        })

    return json.dumps({"status": "valid", "errors": []})

# Use in LangGraph
tools = [generate_java_models, validate_and_fix_java]
```

### Method 3: State-based Workflow

Full state-based LangGraph workflow:

```python
from typing import TypedDict, Sequence
from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage

class CodeGenState(TypedDict):
    messages: Sequence[BaseMessage]
    session_id: str
    files_generated: int
    errors_count: int
    iteration: int

def generate_code_node(state: CodeGenState):
    """Node that generates Java code."""
    # Use LLM to generate code
    files = llm.generate_java_code(state["messages"])

    # Write to MCP service
    result = await client.write_multiple_files(files)

    return {
        "files_generated": result["written"],
        "messages": state["messages"] + [AIMessage(content=f"Generated {result['written']} files")]
    }

def validate_code_node(state: CodeGenState):
    """Node that validates code."""
    errors = await client.check_errors()

    return {
        "errors_count": errors["error_count"],
        "messages": state["messages"] + [AIMessage(content=f"Found {errors['error_count']} errors")]
    }

def should_continue(state: CodeGenState) -> str:
    """Router: continue if errors exist."""
    if state["errors_count"] > 0 and state["iteration"] < 3:
        return "fix_errors"
    return "end"

# Build graph
workflow = StateGraph(CodeGenState)
workflow.add_node("generate", generate_code_node)
workflow.add_node("validate", validate_code_node)
workflow.add_node("fix_errors", fix_errors_node)

workflow.set_entry_point("generate")
workflow.add_edge("generate", "validate")
workflow.add_conditional_edges("validate", should_continue)
workflow.add_edge("fix_errors", "generate")

app = workflow.compile()
```

## Remote Deployment

### Option 1: Docker Deployment

**1. Build and run the MCP server:**

```bash
# Using docker-compose
docker-compose up -d

# Or build manually
docker build -t java-error-checker-mcp .
docker run -p 8000:8000 java-error-checker-mcp
```

**2. Deploy LangGraph agent separately:**

```python
# In your LangGraph agent code (running anywhere)
from langgraph_integration import JavaErrorCheckerClient

# Point to your deployed MCP server
client = JavaErrorCheckerClient(
    base_url="http://your-mcp-server.com:8000"
)
```

### Option 2: Cloud Deployment (AWS/GCP/Azure)

**MCP Server:**

```bash
# Deploy to cloud VM
# 1. SSH to VM
ssh user@your-vm

# 2. Clone repo
git clone https://github.com/your-repo/java-error-checker-mcp
cd java-error-checker-mcp

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run server
python server_sse.py --host 0.0.0.0 --port 8000

# 5. Configure firewall to allow port 8000
```

**LangGraph Agent:**

```python
# In your cloud-deployed agent
import os

MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://mcp-server:8000")
client = JavaErrorCheckerClient(base_url=MCP_SERVER_URL)
```

### Option 3: Kubernetes Deployment

**mcp-server-deployment.yaml:**

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: java-error-checker-mcp
spec:
  replicas: 2
  selector:
    matchLabels:
      app: java-error-checker-mcp
  template:
    metadata:
      labels:
        app: java-error-checker-mcp
    spec:
      containers:
      - name: mcp-server
        image: your-registry/java-error-checker-mcp:latest
        ports:
        - containerPort: 8000
        env:
        - name: SESSION_TIMEOUT
          value: "3600"
---
apiVersion: v1
kind: Service
metadata:
  name: java-error-checker-mcp
spec:
  selector:
    app: java-error-checker-mcp
  ports:
  - port: 8000
    targetPort: 8000
  type: LoadBalancer
```

**Deploy:**

```bash
kubectl apply -f mcp-server-deployment.yaml
kubectl get services  # Get external IP
```

**LangGraph Agent:**

```python
# Use Kubernetes service
client = JavaErrorCheckerClient(
    base_url="http://java-error-checker-mcp:8000"
)
```

## Examples

### Example 1: Simple Code Generation

```python
import asyncio
from langgraph_integration import JavaErrorCheckerClient

async def generate_hello_world():
    client = JavaErrorCheckerClient("http://localhost:8000")

    # Create session
    session_id = await client.create_session("hello-world")

    # Write file
    await client.write_file(
        "com/example/Main.java",
        """package com.example;

public class Main {
    public static void main(String[] args) {
        System.out.println("Hello, World!");
    }
}
"""
    )

    # Validate
    errors = await client.check_errors()
    print(f"Errors: {errors['error_count']}")

    # Cleanup
    await client.delete_session()

asyncio.run(generate_hello_world())
```

### Example 2: Multi-Stage Generation

```python
async def generate_project_in_stages():
    client = JavaErrorCheckerClient("http://localhost:8000")

    # Create session
    await client.create_session("multi-stage-project")

    # Stage 1: Models
    models = [
        {"file_path": "com/example/User.java", "content": "..."},
        {"file_path": "com/example/Product.java", "content": "..."}
    ]
    await client.write_multiple_files(models)
    await client.check_errors()
    await client.refresh_session()  # Extend timeout

    # Stage 2: Services
    services = [
        {"file_path": "com/example/UserService.java", "content": "..."},
        {"file_path": "com/example/ProductService.java", "content": "..."}
    ]
    await client.write_multiple_files(services)
    await client.check_errors()
    await client.refresh_session()

    # Stage 3: Main
    main = [{"file_path": "com/example/Main.java", "content": "..."}]
    await client.write_multiple_files(main)

    # Final validation
    errors = await client.check_errors()

    # Cleanup
    await client.delete_session()
```

### Example 3: Full LangGraph Agent

See `langgraph_agent_example.py` for a complete working example with:
- LangGraph state management
- Tool-based architecture
- Error handling and retry logic
- Multi-stage generation
- Automatic session management

Run it:

```bash
# Simple mode (no LangGraph, no API key needed)
python langgraph_agent_example.py --mode simple --server http://localhost:8000

# Full LangGraph mode (requires OpenAI API key)
export OPENAI_API_KEY=your-key-here
python langgraph_agent_example.py --mode langgraph --server http://localhost:8000
```

## Best Practices

### 1. Session Management

```python
# ✅ Good: Use context manager
async with JavaProjectSession(client, "project") as session:
    await session.write_multiple_files(files)
    # Automatic cleanup

# ✅ Good: Manual cleanup with try/finally
session_id = await client.create_session()
try:
    # Your work
    pass
finally:
    await client.delete_session(session_id)

# ❌ Bad: No cleanup
session_id = await client.create_session()
await client.write_multiple_files(files)
# Session never deleted!
```

### 2. Error Handling

```python
# ✅ Good: Check and handle errors
errors = await client.check_errors()
if errors["error_count"] > 0:
    for error in errors["errors"]:
        recs = await client.get_recommendations(error)
        # Handle or fix errors
        print(f"Error: {error['message']}")
        print(f"Recommendations: {recs['recommendations']}")

# ❌ Bad: Ignore errors
await client.write_multiple_files(files)
# No validation!
```

### 3. Timeout Management

```python
# ✅ Good: Refresh for long workflows
for stage in stages:
    await client.write_multiple_files(stage_files)
    await client.check_errors()
    await client.refresh_session()  # Prevent timeout

# ❌ Bad: Long workflow without refresh
# Session may timeout during processing
```

### 4. Batch Operations

```python
# ✅ Good: Batch write related files
files = [user_model, product_model, order_model]
await client.write_multiple_files(files)

# ❌ Bad: Individual writes
for file in files:
    await client.write_file(file["file_path"], file["content"])
```

### 5. Connection Handling

```python
# ✅ Good: Health check before starting
try:
    health = await client.health_check()
    print(f"Connected to {health['service']}")
except:
    print("MCP server not available")
    exit(1)

# Then proceed with work
```

## Troubleshooting

### Issue: Connection Refused

**Problem:** `Connection refused` when connecting to MCP server

**Solutions:**
```bash
# 1. Verify server is running
curl http://localhost:8000/health

# 2. Check server logs
tail -f /tmp/java-error-checker-mcp-sse.log

# 3. Verify port and host
python server_sse.py --host 0.0.0.0 --port 8000

# 4. Check firewall
sudo ufw allow 8000
```

### Issue: Session Not Found

**Problem:** `Session {id} not found`

**Solutions:**
```python
# 1. Verify session was created
session_id = await client.create_session()
print(f"Created: {session_id}")

# 2. Check session info
info = await client.get_session_info()
print(f"Session exists: {info}")

# 3. Session may have timed out - refresh it
await client.refresh_session()
```

### Issue: Batch Write Failures

**Problem:** Some files fail to write in batch operation

**Solutions:**
```python
# Check the response
result = await client.write_multiple_files(files)
if result["failed"] > 0:
    print(f"Failed files: {result.get('failed_files', [])}")

    # Retry failed files individually
    for failed in result.get("failed_files", []):
        print(f"Retrying: {failed['file_path']}")
        # Retry logic
```

### Issue: Compilation Errors

**Problem:** Unexpected compilation errors

**Solutions:**
```python
# 1. Get detailed error info
errors = await client.check_errors()
for error in errors["errors"]:
    print(f"File: {error['file']}")
    print(f"Line: {error['line']}")
    print(f"Message: {error['message']}")
    if 'code' in error:
        print(f"Code: {error['code']}")

# 2. Get recommendations
recs = await client.get_recommendations(error)
print(f"Suggestions: {recs['recommendations']}")

# 3. List all files to verify structure
files = await client.list_files()
print(f"Files in session: {files['files']}")
```

### Issue: Remote Server Timeout

**Problem:** Requests to remote MCP server timeout

**Solutions:**
```python
# 1. Increase timeout
import httpx
client = JavaErrorCheckerClient(base_url="http://remote:8000")
client.http_timeout = 60.0  # Increase to 60 seconds

# 2. Check network connectivity
curl -v http://remote:8000/health

# 3. Use retry logic
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def write_with_retry(files):
    return await client.write_multiple_files(files)
```

## Performance Considerations

### Concurrent Sessions

The MCP server supports multiple concurrent sessions:

```python
# Multiple agents can use the service simultaneously
agent1_client = JavaErrorCheckerClient("http://server:8000")
agent2_client = JavaErrorCheckerClient("http://server:8000")

# Each gets its own session
session1 = await agent1_client.create_session("agent1-project")
session2 = await agent2_client.create_session("agent2-project")

# Work independently
await agent1_client.write_multiple_files(files1)
await agent2_client.write_multiple_files(files2)
```

### Scaling

For high-load scenarios:

1. **Horizontal Scaling**: Run multiple MCP server instances behind a load balancer
2. **Resource Limits**: Configure memory/CPU limits in Docker/Kubernetes
3. **Session Cleanup**: Configure appropriate SESSION_TIMEOUT
4. **Monitoring**: Monitor server logs and resource usage

## Security

### Production Deployment

```python
# 1. Use HTTPS
client = JavaErrorCheckerClient(base_url="https://mcp-server.com")

# 2. Add authentication
# In server_sse.py, add auth middleware

# 3. Restrict CORS
# In server_sse.py:
# allow_origins=["https://your-agent-domain.com"]

# 4. Use environment variables
import os
MCP_URL = os.getenv("MCP_SERVER_URL")
API_KEY = os.getenv("MCP_API_KEY")
```

## Summary

The Java Error Checker MCP service provides a robust remote API for LangGraph agents to:

✅ Generate and validate Java code remotely
✅ Handle multi-stage agentic workflows
✅ Scale independently from agents
✅ Support concurrent agent sessions
✅ Provide detailed error feedback and recommendations

For more examples, see:
- `langgraph_agent_example.py` - Complete LangGraph agent
- `langgraph_integration.py` - Client library and utilities
- `server_sse.py` - SSE transport server

Happy coding! 🚀
