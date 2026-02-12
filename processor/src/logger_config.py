"""logger_config.py

Structured logging configuration for AURA processor.
Automatically detects Docker vs local environment and configures appropriate formatters.

Jan 2026
"""
import os
import sys
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any


def is_docker_environment() -> bool:
    """
    Detect if running in a Docker container.

    Checks for:
    - /.dockerenv file (standard Docker marker)
    - KUBERNETES_SERVICE_HOST environment variable (Kubernetes)
    - Container-specific cgroup markers

    Returns:
        True if running in Docker/container, False otherwise
    """
    # Check for .dockerenv file
    if os.path.exists('/.dockerenv'):
        return True

    # Check for Kubernetes
    if os.getenv('KUBERNETES_SERVICE_HOST'):
        return True

    # Check cgroup (works for most containers)
    try:
        with open('/proc/1/cgroup', 'r') as f:
            return 'docker' in f.read() or 'kubepods' in f.read()
    except:
        pass

    return False


class JSONFormatter(logging.Formatter):
    """
    JSON formatter for structured logging in Docker environments.

    Outputs logs as single-line JSON objects for easy parsing by log aggregators.
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON"""
        log_data: Dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "module": record.name,
            "message": record.getMessage(),
        }

        # Add extra fields if present
        if hasattr(record, 'arxiv_id'):
            log_data['arxiv_id'] = record.arxiv_id
        if hasattr(record, 'paper_id'):
            log_data['paper_id'] = record.paper_id
        if hasattr(record, 'duration'):
            log_data['duration'] = record.duration

        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)

        return json.dumps(log_data)


class ColoredFormatter(logging.Formatter):
    """
    Colored formatter for human-readable local development logs.

    Adds color coding based on log level for better readability.
    """

    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Green
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[35m',  # Magenta
        'RESET': '\033[0m'       # Reset
    }

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with colors"""
        # Get color for level
        color = self.COLORS.get(record.levelname, '')
        reset = self.COLORS['RESET']

        # Format base message
        formatted = super().format(record)

        # Add color if stdout is a TTY
        if sys.stdout.isatty():
            return f"{color}{formatted}{reset}"
        return formatted


def setup_logging(
    log_level: str = "INFO",
    log_dir: str = "data/logs",
    force_json: bool = False,
    force_local: bool = False
) -> logging.Logger:
    """
    Configure logging for the AURA processor.

    Automatically detects environment and sets up appropriate formatters:
    - Docker: JSON format to stdout only
    - Local: Human-readable format to stdout + file

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: Directory for log files (local mode only)
        force_json: Force JSON format even in local mode
        force_local: Force local format even in Docker mode

    Returns:
        Configured root logger
    """
    # Determine environment
    is_docker = is_docker_environment()
    use_json = (is_docker and not force_local) or force_json

    # Get log level from environment or parameter
    level_str = os.getenv('LOG_LEVEL', log_level).upper()
    level = getattr(logging, level_str, logging.INFO)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Clear any existing handlers
    root_logger.handlers.clear()

    # Console handler (always present)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)

    if use_json:
        # Docker/JSON mode: structured logs to stdout
        console_handler.setFormatter(JSONFormatter())
    else:
        # Local mode: human-readable logs with colors
        fmt = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        console_handler.setFormatter(ColoredFormatter(fmt))

    root_logger.addHandler(console_handler)

    # File handler (local mode only, unless explicitly requested)
    if not is_docker or os.getenv('ENABLE_FILE_LOGGING', '').lower() == 'true':
        try:
            # Create log directory
            Path(log_dir).mkdir(parents=True, exist_ok=True)

            # Log file with date
            today = datetime.now().strftime('%Y-%m-%d')
            log_file = Path(log_dir) / f"processor_{today}.log"

            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(level)

            # Always use plain format for files (easier to read/grep)
            fmt = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            file_handler.setFormatter(logging.Formatter(fmt))

            root_logger.addHandler(file_handler)

            root_logger.info(f"Logging to file: {log_file}")

        except Exception as e:
            root_logger.warning(f"Failed to set up file logging: {e}")

    # Log environment info
    env_type = "Docker (JSON)" if use_json else "Local (Human-readable)"
    root_logger.info(f"Logging initialized: {env_type}, level={level_str}")

    return root_logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger for a specific module.

    Args:
        name: Module name (typically __name__)

    Returns:
        Logger instance for the module
    """
    return logging.getLogger(name)


# Example usage for structured logging with extra fields
def log_with_context(logger: logging.Logger, level: str, message: str, **kwargs):
    """
    Log a message with additional context fields.

    Args:
        logger: Logger instance
        level: Log level (debug, info, warning, error, critical)
        message: Log message
        **kwargs: Additional fields (arxiv_id, paper_id, duration, etc.)

    Example:
        log_with_context(logger, 'info', 'Downloaded PDF', arxiv_id='2401.12345', duration=2.3)
    """
    # Get logging function
    log_func = getattr(logger, level.lower())

    # Add extra fields to the record
    extra_dict = {k: v for k, v in kwargs.items()}

    # Log with extra data
    log_func(message, extra=extra_dict)


if __name__ == "__main__":
    # Test logging configuration
    print("Testing logger configuration...")
    print(f"Detected Docker environment: {is_docker_environment()}")
    print()

    # Set up logging
    setup_logging(log_level="DEBUG")

    # Get test logger
    logger = get_logger(__name__)

    # Test different log levels
    logger.debug("This is a debug message")
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    logger.critical("This is a critical message")

    print("\nTesting structured logging with extra fields:")

    # Test with extra fields (for JSON mode)
    log_with_context(
        logger,
        'info',
        'Downloaded PDF successfully',
        arxiv_id='2401.12345',
        duration=2.3,
        size_mb=3.2
    )

    log_with_context(
        logger,
        'error',
        'Failed to parse definitions',
        paper_id=42,
        arxiv_id='2401.67890',
        error_type='JSON parse error'
    )

    print("\nTesting exception logging:")
    try:
        raise ValueError("Test exception for logging")
    except Exception:
        logger.exception("Caught an exception")

    print("\n✓ Logger configuration test complete")
