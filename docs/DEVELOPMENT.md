# Development Guide

Complete guide for developing with the Tesote Odoo Connector in localhost.

## 🚀 Quick Start

### 1. Install Dependencies

```bash
# Install all dependencies (including dev tools and debugger)
uv sync --dev

# Activate virtual environment
source .venv/bin/activate
```

### 2. Start Development Environment

```bash
# Enable development mode with hot reloading and debugging
./bin/toggle-log-mode dev

# Start Docker containers
docker compose up -d

# View logs in real-time
./bin/view-logs follow
```

## 🐛 Debugging

### VSCode Debugging Setup

1. **Start Odoo** with debugger enabled (already configured in `docker-compose.yml`)
2. **Set breakpoints** in VSCode by clicking in the gutter
3. **Attach debugger**: Press `F5` or use "Run and Debug" → "Python: Attach to Odoo (Docker)"

### Debugging Features

- **Remote debugging**: Attach VSCode to running Odoo container
- **Breakpoints**: Set breakpoints anywhere in the code
- **Hot reload**: Code changes reload automatically with `--dev=all`
- **Port**: Debugger listens on `localhost:5678`

### Using Breakpoints in Code

```python
from ..utils.debugger import breakpoint_here, log_debug_info

def my_function(data):
    # Set a breakpoint programmatically
    breakpoint_here()

    # Log detailed debug info
    log_debug_info(data, "API Response")
```

### Python Debugger (ipdb)

For interactive debugging in the terminal:

```python
import ipdb
ipdb.set_trace()  # Execution pauses here
```

## 📋 Logging

### Colored Logs

The module uses `colorlog` for enhanced readability in development mode:

- **DEBUG**: Cyan
- **INFO**: Green
- **WARNING**: Yellow
- **ERROR**: Red
- **CRITICAL**: Red with white background

### Log Levels

Development mode shows all logs:

```bash
# In docker-compose.yml (already configured)
ODOO_ENV=development
LOG_LEVEL=debug
```

### Viewing Logs

```bash
# Show all logs
./bin/view-logs all

# Show only HTTP requests/responses
./bin/view-logs http

# Show only errors
./bin/view-logs errors

# Show sync operations
./bin/view-logs sync

# Follow logs in real-time
./bin/view-logs follow

# Show last N lines
./bin/view-logs last 100
```

### HTTP Request Logging

In **development mode**, you get detailed HTTP logs:

```
================================================================================
📤 HTTP REQUEST: POST https://staging.tesote.com/api/v2/accounts/123/transactions/sync
================================================================================
🔍 DEBUG MODE - Full Request Details:
Method: POST
URL: https://staging.tesote.com/api/v2/accounts/123/transactions/sync
Timeout: 30s

📋 Headers:
  Authorization: Bearer abc123...xyz
  Accept: application/json
  Content-Type: application/json

📦 Request Body:
{
  "count": 100
}

🔧 cURL Equivalent:
curl -X POST 'https://staging.tesote.com/api/v2/accounts/123/transactions/sync' \
  -H 'Authorization: Bearer YOUR_TOKEN_HERE' \
  -H 'Accept: application/json' \
  -d '{"count": 100}'
================================================================================
📥 HTTP RESPONSE: 200 (342ms)
================================================================================

📋 Response Headers:
  content-type: application/json
  x-ratelimit-remaining: 198

📦 Response Body:
{
  "added": [...],
  "modified": [],
  "removed": []
}
================================================================================
```

## 🔄 Hot Code Reloading

With `--dev=all` enabled, Odoo automatically reloads when you change:

- Python files (`.py`)
- XML views (`.xml`)
- JavaScript files (`.js`)
- CSS files (`.css`)

**Important**: After changing models or adding fields, you must:

```bash
# Restart Odoo to reload model definitions
docker compose restart odoo

# Or upgrade the module
docker compose exec odoo odoo -u tesote_connector -d tesote_dev --stop-after-init
docker compose restart odoo
```

## 🧪 Testing

### Run All Tests

```bash
# Run all tests with coverage
uv run pytest --cov=. --cov-report=term-missing

# Run specific test file
uv run pytest tests/test_adapter.py -v

# Run tests matching pattern
uv run pytest -k "webhook" -v
```

### Debug Tests in VSCode

1. Open test file
2. Set breakpoints
3. Press `F5` → "Python: Debug Tests (Current File)"

## 🛠️ Development Tools

### Code Quality

```bash
# Format code
uv run black .
uv run isort .

# Lint code
uv run ruff check --fix .

# Run all checks (pre-commit)
uv run pre-commit run --all-files
```

### Toggle Between Modes

```bash
# Development mode (verbose logging, debugging)
./bin/toggle-log-mode dev
docker compose restart odoo

# Production mode (minimal logging)
./bin/toggle-log-mode prod
docker compose restart odoo
```

## 📊 Environment Variables

Key environment variables for development:

```bash
# docker-compose.yml
ODOO_ENV=development        # Enable dev features
ENABLE_DEBUGPY=true         # Enable remote debugging
PYTHONUNBUFFERED=1          # Real-time log output
LOG_LEVEL=debug             # Detailed Odoo logs
```

## 🔍 Debugging Common Issues

### Debugger Won't Attach

1. Check debugger is listening:
   ```bash
   docker compose logs odoo | grep "Debugger listening"
   ```

2. Verify port is exposed:
   ```bash
   docker compose ps
   # Should show 0.0.0.0:5678->5678/tcp
   ```

3. Check environment variables:
   ```bash
   docker compose exec odoo env | grep DEBUGPY
   # Should show ENABLE_DEBUGPY=true
   ```

### Hot Reload Not Working

1. Check volume mount is read-write (not `:ro`):
   ```bash
   docker compose config | grep tesote_connector
   # Should NOT have :ro flag
   ```

2. Verify `--dev=all` is enabled:
   ```bash
   docker compose exec odoo ps aux | grep odoo
   # Should show --dev=all
   ```

### Logs Not Showing

1. Check log level:
   ```bash
   docker compose logs odoo | grep -i "log level"
   ```

2. Increase verbosity:
   ```bash
   # Edit docker-compose.yml
   command: odoo --dev=all --log-level=debug --workers=0
   ```

## 📚 Additional Resources

- [Odoo Development Docs](https://www.odoo.com/documentation/18.0/developer.html)
- [debugpy Documentation](https://github.com/microsoft/debugpy)
- [pytest Documentation](https://docs.pytest.org/)
- [VSCode Python Debugging](https://code.visualstudio.com/docs/python/debugging)

## 🎯 Quick Commands Reference

```bash
# Development
./bin/toggle-log-mode dev          # Enable dev mode
docker compose up -d                # Start containers
./bin/view-logs follow             # Watch logs

# Debugging
# Press F5 in VSCode                # Attach debugger
docker compose logs -f odoo        # View container logs

# Testing
uv run pytest -v                   # Run tests
uv run pytest --cov=.              # Run with coverage

# Code Quality
uv run ruff check --fix .          # Lint and fix
uv run black .                     # Format code

# Container Management
docker compose restart odoo        # Restart Odoo
docker compose down                # Stop all
docker compose ps                  # Show status
```

## 💡 Pro Tips

1. **Use breakpoint_here()** instead of `breakpoint()` for better team clarity
2. **Keep logs open** in a separate terminal with `./bin/view-logs follow`
3. **Use ipdb** for interactive debugging when breakpoints aren't enough
4. **Test first** - Write tests before implementing features
5. **Check logs** - The enhanced HTTP logging shows exactly what's sent/received
6. **Hot reload** works for most changes, but model changes need restart
7. **Use cURL** - Copy the generated cURL commands to test API directly
