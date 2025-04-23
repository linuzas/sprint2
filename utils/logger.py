import logging
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler
import json
from typing import Dict, Any, Optional
from pathlib import Path

# Constants
DEFAULT_LOG_DIR = "logs"
MAX_BYTES = 10 * 1024 * 1024  # 10MB
BACKUP_COUNT = 5
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

class StructuredLogger:
    """A structured logger that outputs JSON-formatted logs to both file and console.
    
    Attributes:
        name (str): Name of the logger
        log_dir (str): Directory to store log files
        level (int): Logging level (default: logging.INFO)
    """
    
    def __init__(
        self, 
        name: str, 
        log_dir: str = DEFAULT_LOG_DIR,
        level: int = logging.INFO
    ):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        
        # Prevent duplicate handlers
        if not self.logger.handlers:
            self._setup_handlers(log_dir)
    
    def _setup_handlers(self, log_dir: str) -> None:
        """Set up file and console handlers for the logger."""
        # Create logs directory if it doesn't exist
        Path(log_dir).mkdir(parents=True, exist_ok=True)
        
        # File handler with rotation
        log_file = Path(log_dir) / f"{self.logger.name}_{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=MAX_BYTES,
            backupCount=BACKUP_COUNT,
            encoding='utf-8'
        )
        
        # Console handler
        console_handler = logging.StreamHandler()
        
        # Formatter
        formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
    
    def _format_message(self, message: str, extra: Optional[Dict[str, Any]] = None) -> str:
        """Format message with extra context as JSON.
        
        Args:
            message: The log message
            extra: Additional context to include in the log
            
        Returns:
            JSON-formatted string containing the log data
        """
        log_data = {
            "message": message,
            "timestamp": datetime.now().isoformat(),
            **(extra or {})
        }
        return json.dumps(log_data, ensure_ascii=False, default=str)
    
    def info(self, message: str, extra: Optional[Dict[str, Any]] = None) -> None:
        """Log an info message."""
        self.logger.info(self._format_message(message, extra))
    
    def error(self, message: str, extra: Optional[Dict[str, Any]] = None) -> None:
        """Log an error message."""
        self.logger.error(self._format_message(message, extra))
    
    def warning(self, message: str, extra: Optional[Dict[str, Any]] = None) -> None:
        """Log a warning message."""
        self.logger.warning(self._format_message(message, extra))
    
    def debug(self, message: str, extra: Optional[Dict[str, Any]] = None) -> None:
        """Log a debug message."""
        self.logger.debug(self._format_message(message, extra))
    
    def critical(self, message: str, extra: Optional[Dict[str, Any]] = None) -> None:
        """Log a critical message."""
        self.logger.critical(self._format_message(message, extra))

# Create a default logger instance
logger = StructuredLogger("crypto_assistant") 