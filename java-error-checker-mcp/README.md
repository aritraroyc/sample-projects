# Java Error Checker MCP Service

A Python-based Model Context Protocol (MCP) server that provides Java compilation error checking using the Eclipse JDT Language Server (JDTLS) or javac compiler.

## Features

- **Session Management**: Create isolated workspace sessions for each client
- **Project Structure Replication**: Automatically maintains standard Java project structure
- **Compilation Error Checking**: Detects and reports Java compilation errors
- **Error Recommendations**: Provides intelligent suggestions for fixing common errors
- **Multi-file Support**: Handle complex projects with multiple Java source files
- **File Operations**: Read, write, and list Java files in session workspaces

## Architecture

```
┌─────────────┐                    ┌──────────────────┐
│ MCP Client  │◄──────────────────►│   MCP Server     │
│             │   JSON-RPC/stdio   │                  │
└─────────────┘                    └──────────────────┘
                                            │
                                            ▼
                                   ┌──────────────────┐
                                   │ Session Manager  │
                                   │ - Workspaces     │
                                   │ - File Ops       │
                                   └──────────────────┘
                                            │
                                            ▼
                                   ┌──────────────────┐
                                   │  JDTLS Client    │
                                   │  - Compilation   │
                                   │  - Error Check   │
                                   └──────────────────┘
```

## Prerequisites

- Python 3.10 or higher
- Java Development Kit (JDK) 11 or higher
- Eclipse JDT Language Server (JDTLS) - optional, falls back to javac

## Installation

### 1. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 2. Install Java JDK

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install openjdk-17-jdk
```

**macOS:**
```bash
brew install openjdk@17
```

**Verify installation:**
```bash
java -version
javac -version
```

### 3. Install Eclipse JDTLS (Optional)

For enhanced language server features, install JDTLS:

```bash
# Download JDTLS
mkdir -p ~/.local/share/jdtls
cd ~/.local/share/jdtls

# Download the latest release
wget https://download.eclipse.org/jdtls/milestones/1.9.0/jdt-language-server-1.9.0-202203031534.tar.gz
tar -xzf jdt-language-server-*.tar.gz

# Verify installation
ls -la ~/.local/share/jdtls
```

**Note:** The server will work with just `javac` if JDTLS is not installed.

## Usage

### Starting the Server

#### Stdio Transport (Default)

```bash
python server.py
```

The server communicates via stdin/stdout using the MCP protocol.

### Available Tools

#### 1. `create_session`

Create a new isolated Java project session.

**Parameters:**
- `project_name` (optional): Name of the Java project

**Example:**
```json
{
  "project_name": "my-java-project"
}
```

**Returns:**
```json
{
  "session_id": "uuid-string",
  "project_name": "my-java-project",
  "status": "created"
}
```

#### 2. `write_java_file`

Write a Java source file to the session workspace.

**Parameters:**
- `session_id` (required): Session ID from `create_session`
- `file_path` (required): Relative path (e.g., "com/example/Main.java")
- `content` (required): Java source code

**Example:**
```json
{
  "session_id": "uuid-string",
  "file_path": "com/example/Main.java",
  "content": "package com.example;\n\npublic class Main {\n    public static void main(String[] args) {\n        System.out.println(\"Hello World\");\n    }\n}"
}
```

#### 3. `check_errors`

Check for compilation errors in the Java project.

**Parameters:**
- `session_id` (required): Session ID

**Returns:**
```json
{
  "status": "success",
  "session_id": "uuid-string",
  "error_count": 2,
  "errors": [
    {
      "file": "src/main/java/com/example/Main.java",
      "line": 5,
      "column": 8,
      "severity": "error",
      "message": "cannot find symbol",
      "code": "System.out.prinln(\"Hello\");"
    }
  ]
}
```

#### 4. `list_files`

List all Java files in the session workspace.

**Parameters:**
- `session_id` (required): Session ID

#### 5. `read_file`

Read a Java file from the session workspace.

**Parameters:**
- `session_id` (required): Session ID
- `file_path` (required): Relative path to the file

#### 6. `delete_session`

Delete a session and clean up its workspace.

**Parameters:**
- `session_id` (required): Session ID

#### 7. `get_recommendations`

Get recommendations for fixing a specific compilation error.

**Parameters:**
- `session_id` (required): Session ID
- `error` (required): Error object from `check_errors`

## Example Workflow

```python
# 1. Create a session
response = client.call_tool("create_session", {
    "project_name": "hello-world"
})
session_id = response["session_id"]

# 2. Write Java files
client.call_tool("write_java_file", {
    "session_id": session_id,
    "file_path": "com/example/Main.java",
    "content": """
package com.example;

public class Main {
    public static void main(String[] args) {
        System.out.println("Hello World");
    }
}
"""
})

# 3. Check for errors
errors = client.call_tool("check_errors", {
    "session_id": session_id
})

# 4. Get recommendations if errors exist
if errors["error_count"] > 0:
    recommendations = client.call_tool("get_recommendations", {
        "session_id": session_id,
        "error": errors["errors"][0]
    })

# 5. Clean up
client.call_tool("delete_session", {
    "session_id": session_id
})
```

## Configuration

### Environment Variables

- `JAVA_HOME`: Path to Java JDK installation
- `JDTLS_PATH`: Path to JDTLS installation (optional)

### Custom Configuration

Create a `config.py` file to customize settings:

```python
# Workspace configuration
WORKSPACE_BASE_DIR = "/tmp/jdtls-workspaces"

# Session timeout (seconds)
SESSION_TIMEOUT = 3600

# JDTLS configuration
JDTLS_PATH = "/opt/jdtls"
JDTLS_MEMORY = "1G"
```

## MCP Client Integration

### Using with Claude Desktop

Add to your Claude Desktop MCP configuration (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

```json
{
  "mcpServers": {
    "java-error-checker": {
      "command": "python",
      "args": ["/path/to/java-error-checker-mcp/server.py"]
    }
  }
}
```

### Using with Custom MCP Client

```python
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    server_params = StdioServerParameters(
        command="python",
        args=["server.py"]
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Use the session
            tools = await session.list_tools()
            result = await session.call_tool("create_session", {
                "project_name": "test"
            })
```

## Logging

Logs are written to:
- `/tmp/java-error-checker-mcp.log`
- stderr (for real-time monitoring)

## Error Handling

The server handles various error conditions:

- **Session not found**: Returns error message
- **File write errors**: Returns error with details
- **Compilation errors**: Returns structured error information
- **Missing dependencies**: Returns helpful error messages

## Common Compilation Errors

The service can detect and provide recommendations for:

- Cannot find symbol
- Missing semicolons
- Type mismatches
- Method signature mismatches
- Duplicate declarations
- Unreachable statements
- Package/import errors
- Syntax errors

## Performance Considerations

- **Session Cleanup**: Old sessions are automatically cleaned up after timeout
- **Workspace Isolation**: Each session has its own isolated workspace
- **Concurrent Sessions**: Supports multiple concurrent client sessions
- **Memory Usage**: Configure JDTLS memory based on project size

## Troubleshooting

### JDTLS Not Found

If JDTLS is not found, the server falls back to using `javac` directly. To use JDTLS:

1. Install JDTLS in a standard location
2. Set `JDTLS_PATH` environment variable
3. Verify installation: `ls $JDTLS_PATH/plugins/org.eclipse.equinox.launcher_*.jar`

### Java Not Found

Ensure Java is installed and in PATH:
```bash
which java
which javac
echo $JAVA_HOME
```

### Permission Errors

Ensure the workspace directory is writable:
```bash
chmod 755 /tmp/jdtls-workspaces
```

## Contributing

Contributions are welcome! Areas for improvement:

- Full JDTLS LSP implementation
- Code completion support
- Quick fix suggestions
- Maven/Gradle project support
- Enhanced error parsing
- Unit tests

## License

MIT License

## Related Projects

- [MCP (Model Context Protocol)](https://github.com/anthropics/mcp)
- [Eclipse JDT Language Server](https://github.com/eclipse/eclipse.jdt.ls)
- [Language Server Protocol](https://microsoft.github.io/language-server-protocol/)
