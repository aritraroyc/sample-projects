# Quick Start Guide

## 5-Minute Setup

### Prerequisites

1. **Python 3.10+**
   ```bash
   python3 --version
   ```

2. **Java JDK**
   ```bash
   java -version
   javac -version
   ```

### Installation

1. **Clone and navigate to the directory**
   ```bash
   cd java-error-checker-mcp
   ```

2. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Test the installation**
   ```bash
   # Make the server executable
   chmod +x server.py

   # Run the example client
   python3 example_client.py
   ```

   You should see output showing:
   - Session creation
   - File writing
   - Error detection
   - Recommendations
   - Error fixing

### Using with Claude Desktop

1. **Find your Claude Desktop config file**
   - **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
   - **Linux**: `~/.config/Claude/claude_desktop_config.json`

2. **Add the MCP server**
   ```json
   {
     "mcpServers": {
       "java-error-checker": {
         "command": "python3",
         "args": ["/full/path/to/java-error-checker-mcp/server.py"]
       }
     }
   }
   ```

3. **Restart Claude Desktop**

4. **Test it out**
   Ask Claude:
   ```
   Can you check this Java code for errors?

   public class Test {
       public static void main(String[] args) {
           System.out.prinln("Hello")
       }
   }
   ```

   Claude should:
   - Create a session
   - Write the file
   - Detect the errors (missing semicolon, typo in println)
   - Provide recommendations

## Docker Quick Start

1. **Build the Docker image**
   ```bash
   docker-compose build
   ```

2. **Run the container**
   ```bash
   docker-compose up -d
   ```

3. **Test with the client**
   ```bash
   python3 example_client.py
   ```

## Interactive Mode

Try the interactive client:

```bash
python3 example_client.py --interactive
```

Commands:
- `write com/example/Test.java` - Write Java code (end with `END`)
- `check` - Check for errors
- `list` - List all files
- `read com/example/Test.java` - Read a file
- `quit` - Exit

## Example Usage

```python
# In Claude or your MCP client:

1. "Create a new Java session for my calculator project"
   → Creates session with unique ID

2. "Write a Calculator class with add and multiply methods"
   → Writes Java file to session workspace

3. "Check for compilation errors"
   → Runs javac/JDTLS and reports errors

4. "Get recommendations for fixing the errors"
   → Provides context-aware suggestions

5. "Clean up the session"
   → Deletes workspace and frees resources
```

## Troubleshooting

### "javac not found"
```bash
# Install Java JDK
sudo apt install openjdk-17-jdk  # Ubuntu/Debian
brew install openjdk@17          # macOS
```

### "Permission denied" errors
```bash
chmod +x server.py
chmod +x example_client.py
```

### Server not responding
```bash
# Check the logs
tail -f /tmp/java-error-checker-mcp.log
```

### MCP connection issues
```bash
# Test the server directly
python3 server.py
# (Should wait for stdin input)
```

## Next Steps

- Read the full [README.md](README.md) for detailed documentation
- Check out [example_client.py](example_client.py) for usage examples
- Configure environment variables in `.env` (copy from `.env.example`)
- Install JDTLS for enhanced language server features

## Getting Help

- Check logs: `/tmp/java-error-checker-mcp.log`
- Review the README: [README.md](README.md)
- Test with: `python3 example_client.py`
