# Java Error Checker MCP Service - Architecture Overview

## Table of Contents
1. [Executive Summary](#executive-summary)
2. [High-Level Architecture](#high-level-architecture)
3. [Core Components](#core-components)
4. [Data Flow](#data-flow)
5. [Key Features](#key-features)
6. [Use Cases](#use-cases)
7. [Technical Deep Dive](#technical-deep-dive)

## Executive Summary

The Java Error Checker MCP Service is a **remote validation service** that allows AI agents (particularly LangGraph agents) to generate Java code and validate it for compilation errors in real-time.

### What Problem Does It Solve?

When AI agents generate Java code:
- ❌ **Problem**: No way to verify the code compiles
- ❌ **Problem**: No immediate feedback on errors
- ❌ **Problem**: Multi-file projects are hard to validate
- ❌ **Problem**: Long-running workflows lose context

### Our Solution

✅ **Remote MCP Service** that provides:
- Java code validation via JDTLS/javac
- Session-based workspace management
- Batch file operations
- Error analysis and recommendations
- Remote access via HTTP/SSE
- LangGraph integration

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLIENT LAYER                            │
│                                                                 │
│  ┌────────────────┐  ┌────────────────┐  ┌──────────────────┐ │
│  │  LangGraph     │  │  Custom Agent  │  │  Claude Desktop  │ │
│  │  Agent         │  │                │  │  / MCP Client    │ │
│  └────────┬───────┘  └────────┬───────┘  └────────┬─────────┘ │
│           │                   │                    │           │
└───────────┼───────────────────┼────────────────────┼───────────┘
            │                   │                    │
            │  HTTP/SSE         │  HTTP/SSE         │  stdio
            │                   │                    │
┌───────────▼───────────────────▼────────────────────▼───────────┐
│                      TRANSPORT LAYER                            │
│                                                                 │
│  ┌──────────────────────────┐   ┌──────────────────────────┐  │
│  │   SSE Server             │   │   Stdio Server           │  │
│  │   (server_sse.py)        │   │   (server.py)            │  │
│  │   - HTTP endpoint        │   │   - stdin/stdout         │  │
│  │   - Remote access        │   │   - Local only           │  │
│  │   - Port 8000            │   │   - Direct pipe          │  │
│  └───────────┬──────────────┘   └───────────┬──────────────┘  │
│              │                               │                 │
└──────────────┼───────────────────────────────┼─────────────────┘
               │                               │
               └───────────┬───────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│                      MCP PROTOCOL LAYER                         │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  MCP Server (from mcp.server)                            │  │
│  │  - Tool registration                                     │  │
│  │  - JSON-RPC protocol                                     │  │
│  │  - Request routing                                       │  │
│  │  - Response formatting                                   │  │
│  └───────────────────────────┬──────────────────────────────┘  │
│                              │                                 │
└──────────────────────────────┼─────────────────────────────────┘
                               │
┌──────────────────────────────▼─────────────────────────────────┐
│                      BUSINESS LOGIC LAYER                      │
│                                                                │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │  JavaErrorCheckerServer                                 │  │
│  │  - 10 MCP tool handlers                                 │  │
│  │  - Error recommendation engine                          │  │
│  │  - Request orchestration                                │  │
│  └──────────────┬──────────────────────────┬───────────────┘  │
│                 │                          │                  │
│                 ▼                          ▼                  │
│  ┌──────────────────────┐   ┌──────────────────────────────┐ │
│  │  SessionManager      │   │  JDTLSClient                 │ │
│  │  - Create sessions   │   │  - Compile Java code         │ │
│  │  - Manage workspaces │   │  - Parse errors              │ │
│  │  - File operations   │   │  - Run javac                 │ │
│  │  - Cleanup           │   │  - Extract diagnostics       │ │
│  └──────────┬───────────┘   └───────────┬──────────────────┘ │
│             │                           │                    │
└─────────────┼───────────────────────────┼────────────────────┘
              │                           │
┌─────────────▼───────────────────────────▼────────────────────┐
│                      STORAGE & EXECUTION LAYER               │
│                                                              │
│  ┌──────────────────────┐   ┌──────────────────────────┐   │
│  │  File System         │   │  Java Compiler           │   │
│  │  /tmp/jdtls-         │   │  - javac                 │   │
│  │  workspaces/         │   │  - JDTLS (optional)      │   │
│  │  └─ session-uuid/    │   │  - Error output          │   │
│  │     └─ src/          │   │  - Diagnostics           │   │
│  │        └─ main/      │   │                          │   │
│  │           └─ java/   │   │                          │   │
│  └──────────────────────┘   └──────────────────────────┘   │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

## Core Components

### 1. Transport Layer

**Purpose**: Enable different access methods (remote vs local)

#### A. SSE Server (`server_sse.py`)
```python
# Remote access via HTTP/SSE
# Use case: LangGraph agents, cloud deployments

app = Starlette(routes=[
    Route("/sse", handle_sse),      # MCP endpoint
    Route("/health", handle_health)  # Health check
])

# Start: python server_sse.py --host 0.0.0.0 --port 8000
# Access: http://your-server:8000/sse
```

**Features:**
- Remote access from anywhere
- Multiple concurrent clients
- CORS support
- Health monitoring
- Production-ready (uvicorn)

#### B. Stdio Server (`server.py`)
```python
# Local access via stdin/stdout
# Use case: Claude Desktop, local MCP clients

async with stdio_server() as (read_stream, write_stream):
    await server.run(read_stream, write_stream, ...)

# Start: python server.py
# Access: Via stdin/stdout pipe
```

**Features:**
- Local-only access
- Direct process communication
- Lower overhead
- Claude Desktop compatible

### 2. Business Logic Layer

#### A. JavaErrorCheckerServer (Main Server Class)

**Responsibilities:**
1. Register MCP tools
2. Route tool calls
3. Orchestrate operations
4. Format responses
5. Handle errors

**10 MCP Tools Provided:**

| Tool | Purpose | Input | Output |
|------|---------|-------|--------|
| `create_session` | Create isolated workspace | `project_name` | `session_id` |
| `write_java_file` | Write single file | `session_id, file_path, content` | `success/error` |
| `write_multiple_files` | Batch write files | `session_id, files[]` | `written, failed, total` |
| `check_errors` | Validate compilation | `session_id` | `errors[]` |
| `list_files` | List all Java files | `session_id` | `files[]` |
| `read_file` | Read file content | `session_id, file_path` | `content` |
| `delete_session` | Cleanup workspace | `session_id` | `success/error` |
| `get_recommendations` | Get fix suggestions | `session_id, error` | `recommendations[]` |
| `refresh_session` | Extend timeout | `session_id` | `success/error` |
| `get_session_info` | Get session details | `session_id` | `metadata` |

#### B. SessionManager (`session_manager.py`)

**Responsibilities:**
1. Create isolated workspaces
2. Manage session lifecycle
3. Handle file operations
4. Track session metadata
5. Cleanup old sessions

**Key Concepts:**

```python
# Session Object
@dataclass
class Session:
    session_id: str           # Unique UUID
    workspace_path: Path      # /tmp/jdtls-workspaces/{uuid}
    project_name: str         # User-provided name
    created_at: float         # Timestamp
    last_accessed: float      # For timeout management

# Workspace Structure Created
/tmp/jdtls-workspaces/{session_id}/
├── src/
│   ├── main/
│   │   └── java/          # Main source files here
│   └── test/
│       └── java/          # Test files here
```

**Session Isolation:**
- Each client gets unique workspace
- No interference between sessions
- Automatic cleanup after timeout
- File system isolation

#### C. JDTLSClient (`jdtls_client.py`)

**Responsibilities:**
1. Compile Java code
2. Parse compiler errors
3. Extract error details
4. Format diagnostics

**Compilation Process:**

```python
# 1. Find all .java files in workspace
java_files = workspace.rglob("*.java")

# 2. Run javac for each file
javac -d /tmp -cp src/main/java MyFile.java

# 3. Parse stderr for errors
# Error format: File.java:10: error: ';' expected
#                return a + b
#                            ^

# 4. Extract structured data
{
    "file": "com/example/Main.java",
    "line": 10,
    "column": 20,
    "severity": "error",
    "message": "';' expected",
    "code": "return a + b"
}
```

**Error Recommendation Engine:**

```python
# Pattern matching for common errors
if "cannot find symbol" in error_message:
    recommendations = [
        "Check that the class name is spelled correctly",
        "Ensure the required import statement is present",
        "Verify that the variable is declared before use"
    ]

# Returns context-aware suggestions
```

### 3. Integration Layer

#### A. LangGraph Integration (`langgraph_integration.py`)

**Purpose:** Bridge between MCP service and LangGraph agents

**Components:**

1. **JavaErrorCheckerClient** - Python HTTP client
```python
client = JavaErrorCheckerClient(base_url="http://server:8000")

# Simple async API
session_id = await client.create_session("project")
await client.write_multiple_files(files)
errors = await client.check_errors()
```

2. **JavaProjectSession** - Context manager
```python
async with JavaProjectSession(client, "project") as session:
    # Work with session
    await session.write_multiple_files(files)
    # Automatic cleanup on exit
```

3. **create_langgraph_tools()** - LangGraph tool factory
```python
tools = create_langgraph_tools(client)
# Returns list of @tool decorated functions
# Ready to use with LangGraph agents
```

## Data Flow

### Typical Request Flow

```
1. CLIENT REQUEST
   ┌─────────────────────────────────────────┐
   │ LangGraph Agent calls tool:             │
   │ write_multiple_files(session_id, files) │
   └────────────────┬────────────────────────┘
                    │
                    ▼
2. TRANSPORT LAYER
   ┌─────────────────────────────────────────┐
   │ HTTP POST to /sse                       │
   │ {                                       │
   │   "method": "tools/call",               │
   │   "params": {                           │
   │     "name": "write_multiple_files",     │
   │     "arguments": {...}                  │
   │   }                                     │
   │ }                                       │
   └────────────────┬────────────────────────┘
                    │
                    ▼
3. MCP PROTOCOL LAYER
   ┌─────────────────────────────────────────┐
   │ MCP Server routes to handler:           │
   │ _handle_write_multiple_files(arguments) │
   └────────────────┬────────────────────────┘
                    │
                    ▼
4. BUSINESS LOGIC
   ┌─────────────────────────────────────────┐
   │ SessionManager.write_multiple_files()   │
   │ For each file:                          │
   │   - Validate session exists             │
   │   - Create directory structure          │
   │   - Write file to disk                  │
   │   - Track success/failure               │
   └────────────────┬────────────────────────┘
                    │
                    ▼
5. FILE SYSTEM
   ┌─────────────────────────────────────────┐
   │ Write to:                               │
   │ /tmp/jdtls-workspaces/{uuid}/          │
   │   src/main/java/com/example/Main.java  │
   └────────────────┬────────────────────────┘
                    │
                    ▼
6. RESPONSE
   ┌─────────────────────────────────────────┐
   │ {                                       │
   │   "status": "success",                  │
   │   "written": 2,                         │
   │   "failed": 0,                          │
   │   "total": 2                            │
   │ }                                       │
   └────────────────┬────────────────────────┘
                    │
                    ▼
7. CLIENT RECEIVES
   ┌─────────────────────────────────────────┐
   │ LangGraph agent processes result        │
   │ Decides next action based on response   │
   └─────────────────────────────────────────┘
```

### Compilation Error Check Flow

```
1. CLIENT: check_errors(session_id)
   │
   ▼
2. SessionManager: get_workspace_path(session_id)
   │ Returns: /tmp/jdtls-workspaces/{uuid}/
   ▼
3. JDTLSClient: check_compilation_errors(workspace_path)
   │
   ├─► Find all *.java files
   │   └─► [Main.java, User.java, Product.java]
   │
   ├─► For each file:
   │   └─► Run: javac -d /tmp -cp src/main/java File.java
   │
   ├─► Capture stderr output
   │   └─► "Main.java:10: error: ';' expected"
   │
   ├─► Parse errors with regex
   │   └─► Extract: file, line, column, message, code
   │
   └─► Return structured errors
       └─► [{file: "Main.java", line: 10, ...}]
   │
   ▼
4. Return to client
   {
     "error_count": 1,
     "errors": [...]
   }
```

## Key Features

### 1. Session-Based Isolation

**Why it matters:**
- Multiple agents can work simultaneously
- No interference between projects
- Clean separation of concerns
- Automatic resource management

**How it works:**
```python
# Agent 1
session1 = create_session("project-A")
write_files(session1, files_A)  # Goes to /tmp/.../session1/

# Agent 2 (concurrent)
session2 = create_session("project-B")
write_files(session2, files_B)  # Goes to /tmp/.../session2/

# Completely isolated - no conflicts
```

### 2. Batch Operations

**Why it matters:**
- Efficient for multi-file projects
- Reduces network round-trips
- Atomic-like operations
- Better for agentic workflows

**Example:**
```python
# Instead of:
write_file("User.java", content1)      # 3 API calls
write_file("Product.java", content2)   # 3 round-trips
write_file("Order.java", content3)

# Do this:
write_multiple_files([                 # 1 API call
    {"file_path": "User.java", "content": content1},
    {"file_path": "Product.java", "content": content2},
    {"file_path": "Order.java", "content": content3}
])  # 1 round-trip, all files written together
```

### 3. Session Timeout Management

**Why it matters:**
- Long-running agentic workflows
- Prevent premature cleanup
- Resource management

**How it works:**
```python
# Session created
session = create_session()  # last_accessed = now()

# 30 minutes later...
write_files(session, files)  # last_accessed updated automatically

# After intensive stage
refresh_session(session)     # Explicitly extend timeout

# Automatic cleanup if idle > SESSION_TIMEOUT
# Default: 1 hour (3600 seconds)
```

### 4. Error Analysis & Recommendations

**Why it matters:**
- Helps agents fix errors automatically
- Provides context-aware suggestions
- Reduces trial-and-error

**Example:**
```python
# Check errors
errors = check_errors(session)
# [{
#   "message": "cannot find symbol: variable user",
#   "line": 15,
#   ...
# }]

# Get recommendations
recs = get_recommendations(session, errors[0])
# {
#   "recommendations": [
#     "Check that the variable name is spelled correctly",
#     "Ensure the variable is declared before use",
#     "Verify the variable is in scope"
#   ]
# }

# Agent uses recommendations to fix code
```

### 5. Remote Access

**Why it matters:**
- Deploy service separately from agents
- Scale independently
- Cloud deployment
- Multiple agent access

**Architecture:**
```
┌────────────┐        ┌────────────┐        ┌────────────┐
│ LangGraph  │───────►│    MCP     │◄───────│ LangGraph  │
│ Agent 1    │  HTTP  │   Server   │  HTTP  │ Agent 2    │
│ (Cloud A)  │        │  (Cloud B) │        │ (Cloud C)  │
└────────────┘        └────────────┘        └────────────┘
                             │
                             ▼
                      ┌────────────┐
                      │  JDTLS +   │
                      │  javac     │
                      └────────────┘
```

## Use Cases

### Use Case 1: Simple Code Validation

**Scenario:** LLM generates a single Java class, needs validation

```python
# Agent generates code
code = llm.generate("Create a Calculator class")

# Validate via MCP
client = JavaErrorCheckerClient("http://mcp:8000")
session = await client.create_session("validation")
await client.write_file("Calculator.java", code)
errors = await client.check_errors()

if errors["error_count"] == 0:
    print("✓ Code is valid!")
else:
    print(f"✗ Found {errors['error_count']} errors")
    # Show errors to LLM for fixing
```

### Use Case 2: Multi-Stage Project Generation

**Scenario:** LangGraph agent builds complete project incrementally

```python
async def generate_project():
    client = JavaErrorCheckerClient("http://mcp:8000")
    session = await client.create_session("e-commerce")

    # Stage 1: Models
    models = llm.generate_models()
    await client.write_multiple_files(models)
    await client.check_errors()
    await client.refresh_session()  # Prevent timeout

    # Stage 2: Services (depends on models)
    services = llm.generate_services(context=models)
    await client.write_multiple_files(services)
    await client.check_errors()
    await client.refresh_session()

    # Stage 3: Controllers
    controllers = llm.generate_controllers(context=services)
    await client.write_multiple_files(controllers)
    await client.check_errors()
    await client.refresh_session()

    # Stage 4: Main
    main = llm.generate_main()
    await client.write_multiple_files([main])

    # Final validation
    errors = await client.check_errors()

    await client.delete_session()
    return errors
```

### Use Case 3: Iterative Error Fixing

**Scenario:** Agent generates code, finds errors, fixes them automatically

```python
async def generate_with_retry(requirements, max_retries=3):
    client = JavaErrorCheckerClient("http://mcp:8000")
    session = await client.create_session("retry-project")

    for iteration in range(max_retries):
        # Generate code
        code = llm.generate(requirements)

        # Write and validate
        await client.write_multiple_files(code)
        errors = await client.check_errors()

        if errors["error_count"] == 0:
            print(f"✓ Success on iteration {iteration + 1}")
            break

        # Get recommendations for each error
        recommendations = []
        for error in errors["errors"]:
            recs = await client.get_recommendations(error)
            recommendations.append(recs)

        # Feed back to LLM
        requirements = f"""
        Previous code had errors. Fix them:

        Errors: {errors}
        Recommendations: {recommendations}

        Original requirements: {requirements}
        """

        await client.refresh_session()

    await client.delete_session()
```

### Use Case 4: Multi-Agent Collaboration

**Scenario:** Multiple agents work on different parts of a project

```python
# Agent 1: Backend specialist
async def backend_agent():
    client = JavaErrorCheckerClient("http://mcp:8000")
    session = await client.create_session("backend")

    # Generate backend code
    models = generate_models()
    services = generate_services()

    await client.write_multiple_files(models + services)
    await client.check_errors()

    return session  # Pass to agent 2

# Agent 2: Frontend specialist
async def frontend_agent(backend_session):
    client = JavaErrorCheckerClient("http://mcp:8000")

    # Continue in same session
    client.session_id = backend_session

    # Add frontend code
    controllers = generate_controllers()
    views = generate_views()

    await client.write_multiple_files(controllers + views)
    await client.check_errors()

    await client.delete_session()
```

## Technical Deep Dive

### MCP Protocol Communication

**JSON-RPC Format:**

```json
// Request
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "write_multiple_files",
    "arguments": {
      "session_id": "uuid-here",
      "files": [
        {"file_path": "Main.java", "content": "..."},
        {"file_path": "User.java", "content": "..."}
      ]
    }
  },
  "id": 1
}

// Response
{
  "jsonrpc": "2.0",
  "result": {
    "content": [
      {
        "type": "text",
        "text": "{\"status\":\"success\",\"written\":2,\"failed\":0}"
      }
    ]
  },
  "id": 1
}
```

### Session Lifecycle

```python
# 1. Creation
session_id = str(uuid.uuid4())  # e.g., "a1b2c3d4-..."
workspace = Path(f"/tmp/jdtls-workspaces/{session_id}")
workspace.mkdir(parents=True)

# Create structure
(workspace / "src/main/java").mkdir(parents=True)
(workspace / "src/test/java").mkdir(parents=True)

session = Session(
    session_id=session_id,
    workspace_path=workspace,
    created_at=time.time(),
    last_accessed=time.time()
)
sessions[session_id] = session

# 2. Active Use
# Every operation updates last_accessed
session.last_accessed = time.time()

# 3. Timeout Check (periodic background task)
current_time = time.time()
if current_time - session.last_accessed > SESSION_TIMEOUT:
    delete_session(session_id)

# 4. Explicit Deletion
shutil.rmtree(workspace_path)
del sessions[session_id]
```

### File Path Handling

```python
# Input: "com/example/Main.java"
# Output: "/tmp/jdtls-workspaces/{uuid}/src/main/java/com/example/Main.java"

def resolve_file_path(session_id, file_path):
    workspace = sessions[session_id].workspace_path

    if file_path.startswith("src/"):
        # Already has src/ prefix
        full_path = workspace / file_path
    else:
        # Add src/main/java prefix
        full_path = workspace / "src/main/java" / file_path

    # Create parent directories
    full_path.parent.mkdir(parents=True, exist_ok=True)

    return full_path
```

### Error Parsing

```python
# javac error format:
# File.java:line: severity: message
#     code line
#     ^

def parse_javac_errors(stderr_output, workspace_path):
    errors = []
    lines = stderr_output.split('\n')

    i = 0
    while i < len(lines):
        line = lines[i]

        # Match: "File.java:10: error: message"
        match = re.match(r'(.+\.java):(\d+): (error|warning): (.+)', line)

        if match:
            file_path, line_num, severity, message = match.groups()

            error = {
                "file": make_relative(file_path, workspace_path),
                "line": int(line_num),
                "severity": severity,
                "message": message
            }

            # Next line might be code
            if i + 1 < len(lines):
                error["code"] = lines[i + 1].strip()

            # Next line might have column indicator (^)
            if i + 2 < len(lines) and '^' in lines[i + 2]:
                error["column"] = lines[i + 2].index('^')

            errors.append(error)

        i += 1

    return errors
```

### Concurrency Handling

```python
# Thread-safe session management
import threading

class SessionManager:
    def __init__(self):
        self.sessions = {}
        self.lock = threading.Lock()

    def create_session(self, project_name):
        with self.lock:
            session_id = str(uuid.uuid4())
            # ... create session
            self.sessions[session_id] = session
            return session_id

    def get_session(self, session_id):
        # No lock needed for reads (dict lookups are atomic in Python)
        return self.sessions.get(session_id)

    def delete_session(self, session_id):
        with self.lock:
            if session_id in self.sessions:
                session = self.sessions[session_id]
                # ... cleanup
                del self.sessions[session_id]
```

## Summary

### What We Built

A **comprehensive remote validation service** for Java code that:

1. **Accepts** Java code from AI agents
2. **Validates** compilation using javac/JDTLS
3. **Reports** detailed error information
4. **Suggests** fixes based on error patterns
5. **Manages** isolated workspaces for each client
6. **Supports** remote access via HTTP/SSE
7. **Integrates** seamlessly with LangGraph
8. **Scales** for production deployment

### Key Innovations

✅ **Session Isolation** - Multiple concurrent agents
✅ **Batch Operations** - Efficient multi-file handling
✅ **Timeout Management** - Long-running workflow support
✅ **Remote Access** - Deploy anywhere, access from anywhere
✅ **Error Intelligence** - Context-aware recommendations
✅ **LangGraph Ready** - Drop-in tools for agents
✅ **Production Ready** - Logging, monitoring, scaling

### Technology Stack

- **Protocol**: Model Context Protocol (MCP)
- **Transport**: HTTP/SSE or stdio
- **Server**: Python with Starlette/Uvicorn
- **Validation**: javac / Eclipse JDTLS
- **Client**: Python async (httpx)
- **Integration**: LangGraph tools

### File Structure

```
java-error-checker-mcp/
├── server.py                      # Stdio transport server
├── server_sse.py                  # HTTP/SSE transport server
├── session_manager.py             # Session lifecycle management
├── jdtls_client.py               # Java compilation & error parsing
├── langgraph_integration.py      # LangGraph client & tools
├── config.py                     # Configuration
├── requirements.txt              # Dependencies
├── setup.py                      # Package installation
├── Dockerfile                    # Container image
├── docker-compose.yml            # Container orchestration
├── example_client.py             # Simple MCP client example
├── agentic_workflow_example.py   # Multi-stage workflow example
├── langgraph_agent_example.py    # LangGraph agent example
├── test_server.py                # Unit tests
├── README.md                     # Main documentation
├── AGENTIC_WORKFLOWS.md          # Agentic workflow guide
├── LANGGRAPH_INTEGRATION.md      # LangGraph integration guide
├── REMOTE_DEPLOYMENT.md          # Deployment quick start
├── QUICKSTART.md                 # 5-minute setup
└── PROJECT_OVERVIEW.md           # This file
```

This architecture provides a robust, scalable solution for validating AI-generated Java code in real-time, whether running locally or deployed in the cloud.
