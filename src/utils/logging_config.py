"""
Centralized logging configuration for the RAG benchmarking system.
Provides both console and file logging with rotation.
"""

import logging
import logging.handlers
from pathlib import Path
from datetime import datetime
import sys


def setup_logging(
    log_level: str = "INFO",
    log_dir: str = "./logs",
    log_to_file: bool = True,
    log_to_console: bool = True,
    max_bytes: int = 10 * 1024 * 1024,  # 10 MB
    backup_count: int = 5
):
    """
    Configure logging for the application with both file and console handlers.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: Directory to store log files
        log_to_file: Whether to log to files
        log_to_console: Whether to log to console
        max_bytes: Maximum size of each log file before rotation
        backup_count: Number of backup files to keep
    """
    # Create logs directory if it doesn't exist
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Remove existing handlers to avoid duplicates
    root_logger.handlers.clear()
    
    # Create formatter
    detailed_formatter = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    console_formatter = logging.Formatter(
        fmt='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # Console handler
    if log_to_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, log_level.upper()))
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)
    
    # File handlers
    if log_to_file:
        # General application log with rotation
        app_log_file = log_path / "app.log"
        file_handler = logging.handlers.RotatingFileHandler(
            app_log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)  # Capture all levels in file
        file_handler.setFormatter(detailed_formatter)
        root_logger.addHandler(file_handler)
        
        # Error log (errors and above only)
        error_log_file = log_path / "errors.log"
        error_handler = logging.handlers.RotatingFileHandler(
            error_log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(detailed_formatter)
        root_logger.addHandler(error_handler)
        
        # Session-specific log (with timestamp)
        session_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        session_log_file = log_path / f"session_{session_timestamp}.log"
        session_handler = logging.FileHandler(
            session_log_file,
            encoding='utf-8'
        )
        session_handler.setLevel(logging.DEBUG)
        session_handler.setFormatter(detailed_formatter)
        root_logger.addHandler(session_handler)
    
    # Log the initialization
    logging.info(f"Logging configured - Level: {log_level}, File logging: {log_to_file}")
    if log_to_file:
        logging.info(f"Log files location: {log_path.absolute()}")
        logging.info(f"  - General log: app.log")
        logging.info(f"  - Error log: errors.log")
        logging.info(f"  - Session log: session_{session_timestamp}.log")
    
    return root_logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a module.
    
    Args:
        name: Logger name (typically __name__)
    
    Returns:
        Logger instance
    """
    return logging.getLogger(name)


# Configure for specific subsystems
def setup_quiet_loggers():
    """Reduce verbosity of noisy third-party libraries."""
    # Neo4j notifications can be quite verbose
    logging.getLogger('neo4j').setLevel(logging.WARNING)
    logging.getLogger('neo4j.notifications').setLevel(logging.WARNING)
    
    # Asyncio can be noisy in debug mode
    logging.getLogger('asyncio').setLevel(logging.WARNING)
    
    # HTTP clients
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('httpcore').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
