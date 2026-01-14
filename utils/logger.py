"""Structured logging utility for the backend."""
import logging
import sys
from pathlib import Path
from datetime import datetime

# Create logs directory if it doesn't exist (backend-relative)
backend_root = Path(__file__).parent.parent
logs_dir = backend_root / 'logs'
logs_dir.mkdir(exist_ok=True)

# Configure backend logger
backend_logger = logging.getLogger('backend')
backend_logger.setLevel(logging.INFO)

# Remove existing handlers to avoid duplicates
backend_logger.handlers.clear()

# Console handler
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)

# File handler
log_file = logs_dir / 'backend.log'
file_handler = logging.FileHandler(log_file)
file_handler.setLevel(logging.DEBUG)

# Formatter
class BackendFormatter(logging.Formatter):
    """Custom formatter for backend logs."""
    
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
        'RESET': '\033[0m'
    }
    
    def format(self, record):
        # Add color for console
        if hasattr(record, 'color') and record.color:
            color = self.COLORS.get(record.levelname, '')
            reset = self.COLORS['RESET']
            record.levelname = f"{color}{record.levelname}{reset}"
        
        # Format message
        timestamp = datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S')
        return f"[{timestamp}] [{record.name}] {record.levelname}: {record.getMessage()}"

console_formatter = BackendFormatter()
file_formatter = logging.Formatter(
    '%(asctime)s [%(name)s] %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

console_handler.setFormatter(console_formatter)
file_handler.setFormatter(file_formatter)

backend_logger.addHandler(console_handler)
backend_logger.addHandler(file_handler)

# Prevent propagation to root logger
backend_logger.propagate = False


def log_api_request(endpoint: str, method: str, details: dict = None):
    """Log API request."""
    details = details or {}
    message = f"📥 API Request | {method} {endpoint}"
    if details:
        details_str = " | ".join([f"{k}={v}" for k, v in details.items()])
        message += f" | {details_str}"
    backend_logger.info(message, extra={'color': True})


def log_agent_api_call(url: str, message: str, response_time: float = None):
    """Log agent API call."""
    message_log = f"🤖 Agent API Call | URL={url} | Message={message[:100]}"
    if response_time:
        message_log += f" | Time={response_time:.2f}s"
    backend_logger.info(message_log, extra={'color': True})


def log_agent_response(response: str, success: bool = True):
    """Log agent API response."""
    status = "✅ Success" if success else "❌ Error"
    message = f"{status} | Agent Response: {response[:200]}"
    backend_logger.info(message, extra={'color': True})


def log_error(error: Exception, context: str = None):
    """Log errors with context."""
    message = f"❌ Error"
    if context:
        message += f" | Context={context}"
    message += f" | {type(error).__name__}: {str(error)}"
    backend_logger.error(message, extra={'color': True}, exc_info=True)
