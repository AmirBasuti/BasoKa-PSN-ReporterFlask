# BasoKa Flask Reporter

A professional Flask server for managing and monitoring BasoKa checker processes through Telegram bot integration.

## Features

- **Process Management**: Start, stop, and monitor checker processes
- **Login Tracking**: Track successful and failed login attempts
- **API Endpoints**: RESTful API for Telegram bot integration
- **Logging**: Comprehensive logging with file and console output
- **Error Handling**: Robust error handling and status reporting
- **Health Monitoring**: Built-in health check endpoint

## API Endpoints

### Core Endpoints

- `GET /status` - Get comprehensive system status including login statistics
- `POST /start` - Start the checker process
- `POST /stop` - Stop the checker process  
- `GET /is_running` - Check if the process is currently running
- `GET /log` - Get recent log entries (supports `?lines=N` parameter)
- `GET /health` - Health check endpoint

### Response Format

All endpoints return JSON responses with consistent error handling:

```json
{
  "status": "success|error|already_running|not_running",
  "message": "Optional message",
  "data": "Endpoint-specific data"
}
```

## Installation

1. **Clone the repository:**
   ```bash
   git clone <your-repo-url>
   cd BasoKa_flaskReporter
   ```

2. **Install dependencies:**
   ```bash
   # Using uv (recommended)
   uv sync
   
   # Or using pip
   pip install -e .
   ```

3. **Create environment file (optional):**
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

## Usage

### Starting the Server

**Option 1: Direct execution**
```bash
python main.py
```

**Option 2: Using the startup script**
```bash
python run_server.py
```

**Option 3: Using uv**
```bash
uv run python main.py
```

### Testing the Server

Run the test script to verify all endpoints:
```bash
python test_server.py
```

### Configuration

The server can be configured through:

1. **Environment variables** (`.env` file)
2. **Configuration files** (`config.py`)
3. **Command line arguments**

Key configuration options:
- `FLASK_HOST`: Server host (default: 0.0.0.0)
- `FLASK_PORT`: Server port (default: 8000)
- `FLASK_DEBUG`: Debug mode (default: False)
- `LOG_LEVEL`: Logging level (default: INFO)

## Project Structure

```
BasoKa_flaskReporter/
├── main.py              # Main Flask application
├── config.py            # Configuration management
├── app_factory.py       # Application factory (optional)
├── run_server.py        # Startup script
├── test_server.py       # Testing script
├── pyproject.toml       # Project configuration
├── logs/                # Log files directory
│   ├── .gitkeep
│   ├── flask_app.log    # Flask application logs
│   └── app.log          # Checker process logs
├── successful_logins.json  # Successful login data
├── failed_logins.json      # Failed login data
└── README.md
```

## Architecture

The application is structured with clear separation of concerns:

- **ProcessManager**: Handles checker process lifecycle
- **DataManager**: Manages JSON data files for login tracking  
- **LogManager**: Handles log file operations
- **Config**: Centralized configuration management

## Integration with Telegram Bot

This Flask server is designed to work seamlessly with your Telegram bot. The bot should make HTTP requests to these endpoints:

```python
# Example bot configuration
config = {
    "base_url": "http://your-server:8000",
    "endpoints": {
        "status": "/status",
        "start": "/start", 
        "stop": "/stop",
        "is_running": "/is_running",
        "log": "/log"
    }
}
```

## Error Handling

The server includes comprehensive error handling:

- **Process errors**: Graceful handling of process start/stop failures
- **File errors**: Safe JSON file operations with fallbacks
- **Network errors**: Proper HTTP status codes and error messages
- **Logging**: All errors are logged for debugging

## Logging

Logs are written to:
- `logs/flask_app.log` - Flask application logs
- `logs/app.log` - Checker process logs (if configured)
- Console output (stdout/stderr)

Log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL

## Development

### Running in Development Mode

```bash
export FLASK_ENV=development
export FLASK_DEBUG=true
python main.py
```

### Code Quality

```bash
# Format and lint code
uv run ruff check .
uv run ruff format .
```

### Testing

```bash
# Run the test script
python test_server.py

# Or install dev dependencies and use pytest
uv sync --group dev
uv run pytest
```

## Production Deployment

For production deployment, consider:

1. **Use a WSGI server** (Gunicorn, uWSGI)
2. **Set up reverse proxy** (Nginx, Apache)
3. **Configure logging** properly
4. **Set environment variables** for production
5. **Monitor the application** with health checks

Example with Gunicorn:
```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:8000 main:app
```

## Security Considerations

- Run behind a reverse proxy in production
- Implement authentication if needed
- Validate input parameters
- Monitor for suspicious activity
- Keep dependencies updated

## Troubleshooting

### Common Issues

1. **Port already in use**: Change the port in configuration
2. **Permission errors**: Check file permissions for log directories
3. **Process won't start**: Verify the `MAIN_SCRIPT` path is correct
4. **JSON file errors**: Check file permissions and disk space

### Debug Mode

Enable debug mode for detailed error messages:
```bash
export FLASK_DEBUG=true
python main.py
```

## License

[Add your license information here]

## Contributing

[Add contribution guidelines here]