# Agentic Workflow Guide

## Overview

This guide explains how to use the Java Error Checker MCP service in agentic workflows that generate Java code incrementally across multiple stages.

## What is an Agentic Workflow?

An agentic workflow is a multi-stage process where an AI agent or LLM generates code incrementally, often across multiple passes or iterations. Key characteristics:

- **Multi-stage generation**: Code is generated in phases (models → services → controllers → main)
- **Incremental validation**: Each stage is validated before proceeding
- **Session persistence**: The same workspace is maintained across all stages
- **Batch operations**: Multiple files are often generated per stage
- **Long-running**: Workflow may take minutes or hours to complete

## Key Features for Agentic Workflows

The MCP service provides specialized tools for agentic workflows:

### 1. Persistent Sessions

Sessions remain active across multiple tool calls, allowing you to build up a project incrementally.

```python
# Stage 1: Create session
session_id = create_session(project_name="my-project")

# Stage 2: Add models (session persists)
write_multiple_files(session_id, model_files)

# Stage 3: Add services (same session)
write_multiple_files(session_id, service_files)

# Stage 4: Add main class (same session)
write_multiple_files(session_id, main_files)

# Only cleanup when done
delete_session(session_id)
```

### 2. Batch File Writing

Write multiple Java files in a single operation - perfect for generating related classes together.

```python
# Generate multiple model classes at once
files = [
    {
        "file_path": "com/example/model/User.java",
        "content": "..."
    },
    {
        "file_path": "com/example/model/Product.java",
        "content": "..."
    },
    {
        "file_path": "com/example/model/Order.java",
        "content": "..."
    }
]

result = write_multiple_files(
    session_id=session_id,
    files=files
)

# Returns:
# {
#   "status": "success",
#   "written": 3,
#   "failed": 0,
#   "total": 3
# }
```

### 3. Session Refresh

Extend session timeout for long-running workflows to prevent automatic cleanup.

```python
# After each stage, refresh the session
refresh_session(session_id=session_id)

# Session timeout is reset, preventing cleanup
```

### 4. Session Info

Track session state and progress throughout your workflow.

```python
info = get_session_info(session_id=session_id)

# Returns:
# {
#   "session_id": "...",
#   "project_name": "my-project",
#   "age_seconds": 45.2,
#   "idle_seconds": 2.1,
#   "file_count": 7,
#   "files": [...]
# }
```

## Complete MCP Tool Reference

### Session Management

#### create_session
Create a new isolated Java project session.

**Input:**
```json
{
  "project_name": "my-project"
}
```

**Output:**
```json
{
  "session_id": "uuid-string",
  "project_name": "my-project",
  "status": "created"
}
```

#### refresh_session
Extend session timeout (prevents automatic cleanup).

**Input:**
```json
{
  "session_id": "uuid-string"
}
```

**Output:**
```json
{
  "status": "success",
  "message": "Session timeout refreshed successfully"
}
```

#### get_session_info
Get detailed session information.

**Input:**
```json
{
  "session_id": "uuid-string"
}
```

**Output:**
```json
{
  "status": "success",
  "session_id": "uuid-string",
  "project_name": "my-project",
  "age_seconds": 120.5,
  "idle_seconds": 5.2,
  "file_count": 5,
  "files": ["com/example/Main.java", ...]
}
```

#### delete_session
Delete session and cleanup workspace.

**Input:**
```json
{
  "session_id": "uuid-string"
}
```

### File Operations

#### write_java_file
Write a single Java file.

**Input:**
```json
{
  "session_id": "uuid-string",
  "file_path": "com/example/Main.java",
  "content": "package com.example; ..."
}
```

#### write_multiple_files
Write multiple Java files in batch (recommended for agentic workflows).

**Input:**
```json
{
  "session_id": "uuid-string",
  "files": [
    {
      "file_path": "com/example/User.java",
      "content": "..."
    },
    {
      "file_path": "com/example/Product.java",
      "content": "..."
    }
  ]
}
```

**Output:**
```json
{
  "status": "success",
  "written": 2,
  "failed": 0,
  "total": 2
}
```

#### list_files
List all Java files in the workspace.

**Input:**
```json
{
  "session_id": "uuid-string"
}
```

#### read_file
Read a specific Java file.

**Input:**
```json
{
  "session_id": "uuid-string",
  "file_path": "com/example/Main.java"
}
```

### Error Checking

#### check_errors
Check for compilation errors in all files.

**Input:**
```json
{
  "session_id": "uuid-string"
}
```

**Output:**
```json
{
  "status": "success",
  "error_count": 1,
  "errors": [
    {
      "file": "com/example/Main.java",
      "line": 10,
      "column": 8,
      "severity": "error",
      "message": "cannot find symbol",
      "code": "System.out.prinln(\"test\");"
    }
  ]
}
```

#### get_recommendations
Get fix suggestions for errors.

**Input:**
```json
{
  "session_id": "uuid-string",
  "error": {
    "file": "Main.java",
    "line": 10,
    "message": "cannot find symbol"
  }
}
```

**Output:**
```json
{
  "status": "success",
  "recommendations": [
    "Check that the class name is spelled correctly",
    "Ensure the required import statement is present",
    "Verify that the variable is declared before use"
  ]
}
```

## Example Agentic Workflow

### Pattern 1: Multi-Stage Generation

```python
# Stage 0: Initialize
session_id = create_session("e-commerce")

# Stage 1: Generate models
model_files = generate_model_classes()  # Your LLM generates these
write_multiple_files(session_id, model_files)
check_errors(session_id)
refresh_session(session_id)

# Stage 2: Generate services
service_files = generate_service_classes()  # LLM generates based on models
write_multiple_files(session_id, service_files)
check_errors(session_id)
refresh_session(session_id)

# Stage 3: Generate controllers
controller_files = generate_controller_classes()
write_multiple_files(session_id, controller_files)
check_errors(session_id)
refresh_session(session_id)

# Stage 4: Generate main
main_file = generate_main_class()
write_multiple_files(session_id, [main_file])
errors = check_errors(session_id)

if errors["error_count"] == 0:
    print("✓ Project generated successfully!")
else:
    # Get recommendations and iterate
    for error in errors["errors"]:
        recs = get_recommendations(session_id, error)
        # Feed recommendations back to LLM for fixes

# Cleanup when done
delete_session(session_id)
```

### Pattern 2: Iterative Refinement

```python
session_id = create_session("my-app")

while not project_complete:
    # Generate next batch of classes
    files = llm_generate_next_batch()

    # Write files
    result = write_multiple_files(session_id, files)

    # Check for errors
    errors = check_errors(session_id)

    if errors["error_count"] > 0:
        # Get recommendations
        recommendations = []
        for error in errors["errors"]:
            recs = get_recommendations(session_id, error)
            recommendations.append(recs)

        # Feed back to LLM for corrections
        corrected_files = llm_fix_errors(files, recommendations)
        write_multiple_files(session_id, corrected_files)

    # Refresh session to prevent timeout
    refresh_session(session_id)

    # Check if project is complete
    info = get_session_info(session_id)
    project_complete = check_completion_criteria(info)

delete_session(session_id)
```

### Pattern 3: Dependency-Aware Generation

```python
session_id = create_session("layered-app")

# Generate in dependency order
layers = [
    "models",      # No dependencies
    "repositories", # Depends on models
    "services",    # Depends on models + repositories
    "controllers", # Depends on services
    "main"         # Depends on everything
]

for layer in layers:
    print(f"Generating {layer}...")

    # Get context from existing files
    existing_files = list_files(session_id)
    context = build_context(existing_files)

    # Generate layer with awareness of dependencies
    layer_files = llm_generate_layer(layer, context)

    # Write and validate
    write_multiple_files(session_id, layer_files)
    errors = check_errors(session_id)

    if errors["error_count"] > 0:
        print(f"⚠ Errors in {layer}, fixing...")
        # Fix errors before proceeding to next layer
        fixed_files = fix_layer_errors(layer_files, errors)
        write_multiple_files(session_id, fixed_files)

    refresh_session(session_id)
    print(f"✓ {layer} complete")

delete_session(session_id)
```

## Best Practices

### 1. Always Refresh Long-Running Sessions

```python
# After each major operation
write_multiple_files(session_id, files)
check_errors(session_id)
refresh_session(session_id)  # ← Prevent timeout
```

### 2. Use Batch Writes for Related Classes

```python
# Good: Write related classes together
write_multiple_files(session_id, [
    user_model,
    product_model,
    order_model
])

# Less efficient: Multiple individual writes
write_java_file(session_id, "User.java", user_content)
write_java_file(session_id, "Product.java", product_content)
write_java_file(session_id, "Order.java", order_content)
```

### 3. Check Errors After Each Stage

```python
# After writing files, always check
write_multiple_files(session_id, files)
errors = check_errors(session_id)  # ← Don't skip this

if errors["error_count"] > 0:
    # Handle errors before proceeding
    handle_compilation_errors(errors)
```

### 4. Track Session Info for Progress

```python
# Use session info to track progress
info = get_session_info(session_id)
print(f"Progress: {info['file_count']} files generated")
print(f"Running for: {info['age_seconds']:.1f}s")
```

### 5. Always Cleanup

```python
try:
    # Your workflow
    session_id = create_session("project")
    # ... generate code ...
finally:
    # Always cleanup, even if errors occur
    delete_session(session_id)
```

## Error Handling

### Handle Batch Write Failures

```python
result = write_multiple_files(session_id, files)

if result["failed"] > 0:
    print(f"⚠ {result['failed']} files failed to write")
    for failed_file in result.get("failed_files", []):
        print(f"  - {failed_file['file_path']}: {failed_file['error']}")
        # Retry or handle individually
```

### Handle Compilation Errors

```python
errors = check_errors(session_id)

if errors["error_count"] > 0:
    # Group errors by file
    errors_by_file = group_errors_by_file(errors["errors"])

    # Get recommendations for each file
    for file_path, file_errors in errors_by_file.items():
        for error in file_errors:
            recs = get_recommendations(session_id, error)
            # Apply fixes
            apply_recommendations(file_path, error, recs)
```

## Performance Tips

### 1. Batch Operations
- Use `write_multiple_files` instead of multiple `write_java_file` calls
- Reduces round-trips to server
- More efficient for generating 5+ files at once

### 2. Session Reuse
- Don't create new sessions for each stage
- Reuse the same session throughout your workflow
- Only delete when completely done

### 3. Selective Error Checking
- Check errors after logical stages, not after every file
- Group related classes and check once

```python
# Good: Check after logical group
write_multiple_files(session_id, all_model_files)
check_errors(session_id)

write_multiple_files(session_id, all_service_files)
check_errors(session_id)

# Overkill: Checking after every file
for file in model_files:
    write_java_file(session_id, file)
    check_errors(session_id)  # Too frequent
```

## Complete Example

See `agentic_workflow_example.py` for a complete working example that demonstrates:

- Multi-stage incremental generation
- Batch file writing
- Session persistence
- Error checking after each stage
- Session refresh
- Session info tracking
- Proper cleanup

Run it with:
```bash
python3 agentic_workflow_example.py
```

## Troubleshooting

### Session Timeout During Long Workflow

**Problem:** Session gets cleaned up during long-running workflow

**Solution:** Call `refresh_session` periodically
```python
# After each stage
refresh_session(session_id)
```

### Batch Write Partial Failures

**Problem:** Some files in batch fail to write

**Solution:** Check the response for failed files
```python
result = write_multiple_files(session_id, files)
if result["failed"] > 0:
    # Retry failed files individually
    for failed in result["failed_files"]:
        retry_write(failed)
```

### Memory Usage with Large Projects

**Problem:** Large number of files in one session

**Solution:**
- Delete session when done to free resources
- Consider splitting very large projects into multiple sessions
- Use `get_session_info` to monitor file count

## Integration with LLMs

### Example with Claude/GPT

```python
async def llm_generate_java_code(prompt, context):
    """Use LLM to generate Java code."""
    # Call your LLM
    response = await llm_api.generate(
        prompt=f"{context}\n\n{prompt}",
        system="You are a Java code generator"
    )
    return parse_java_files(response)

async def agentic_workflow():
    session_id = create_session("llm-project")

    # Stage 1: Models
    model_files = await llm_generate_java_code(
        "Generate User and Product model classes",
        context=""
    )
    write_multiple_files(session_id, model_files)

    # Stage 2: Services (with context)
    existing = list_files(session_id)
    context = build_context(existing)

    service_files = await llm_generate_java_code(
        "Generate UserService and ProductService classes",
        context=context
    )
    write_multiple_files(session_id, service_files)

    # Check and fix errors
    errors = check_errors(session_id)
    if errors["error_count"] > 0:
        fixed_files = await llm_fix_errors(service_files, errors)
        write_multiple_files(session_id, fixed_files)

    delete_session(session_id)
```

## Summary

The Java Error Checker MCP service is designed for agentic workflows:

✅ **Persistent sessions** - Build projects incrementally
✅ **Batch operations** - Write multiple files efficiently
✅ **Session refresh** - Handle long-running workflows
✅ **Session tracking** - Monitor progress and state
✅ **Error validation** - Check after each stage
✅ **Smart recommendations** - Get fix suggestions

Use these tools to build robust agentic code generation systems that can create complex Java projects iteratively and reliably.
