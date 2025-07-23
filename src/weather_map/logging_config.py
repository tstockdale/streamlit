"""
Logging configuration for Weather Map Application.
"""

import logging
import logging.config
import os
from pathlib import Path
from typing import Dict, Any


def get_logging_config(log_dir: str = "logs") -> Dict[str, Any]:
    """
    Get comprehensive logging configuration.
    
    Args:
        log_dir: Directory to store log files
        
    Returns:
        Dictionary containing logging configuration
    """
    # Ensure log directory exists
    Path(log_dir).mkdir(exist_ok=True)
    
    return {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'detailed': {
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(funcName)s:%(lineno)d - %(message)s',
                'datefmt': '%Y-%m-%d %H:%M:%S'
            },
            'simple': {
                'format': '%(asctime)s - %(levelname)s - %(message)s',
                'datefmt': '%Y-%m-%d %H:%M:%S'
            },
            'json': {
                'format': '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "module": "%(module)s", "function": "%(funcName)s", "line": %(lineno)d, "message": "%(message)s"}',
                'datefmt': '%Y-%m-%d %H:%M:%S'
            }
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'level': 'INFO',
                'formatter': 'simple',
                'stream': 'ext://sys.stdout'
            },
            'console_error': {
                'class': 'logging.StreamHandler',
                'level': 'ERROR',
                'formatter': 'detailed',
                'stream': 'ext://sys.stderr'
            },
            'file_all': {
                'class': 'logging.handlers.RotatingFileHandler',
                'level': 'DEBUG',
                'formatter': 'detailed',
                'filename': f'{log_dir}/app.log',
                'maxBytes': 10 * 1024 * 1024,  # 10MB
                'backupCount': 5,
                'encoding': 'utf8'
            },
            'file_error': {
                'class': 'logging.handlers.RotatingFileHandler',
                'level': 'ERROR',
                'formatter': 'detailed',
                'filename': f'{log_dir}/error.log',
                'maxBytes': 10 * 1024 * 1024,  # 10MB
                'backupCount': 10,
                'encoding': 'utf8'
            },
            'file_api': {
                'class': 'logging.handlers.RotatingFileHandler',
                'level': 'DEBUG',
                'formatter': 'json',
                'filename': f'{log_dir}/api.log',
                'maxBytes': 10 * 1024 * 1024,  # 10MB
                'backupCount': 5,
                'encoding': 'utf8'
            },
            'file_performance': {
                'class': 'logging.handlers.RotatingFileHandler',
                'level': 'INFO',
                'formatter': 'json',
                'filename': f'{log_dir}/performance.log',
                'maxBytes': 5 * 1024 * 1024,  # 5MB
                'backupCount': 3,
                'encoding': 'utf8'
            }
        },
        'loggers': {
            # Root logger
            '': {
                'level': 'DEBUG',
                'handlers': ['console', 'file_all', 'file_error'],
                'propagate': False
            },
            # Application loggers
            'src.weather_map': {
                'level': 'DEBUG',
                'handlers': ['console', 'file_all', 'file_error'],
                'propagate': False
            },
            'src.weather_map.services': {
                'level': 'DEBUG',
                'handlers': ['console', 'file_all', 'file_api'],
                'propagate': False
            },
            'src.weather_map.weather_app': {
                'level': 'INFO',
                'handlers': ['console', 'file_all', 'file_performance'],
                'propagate': False
            },
            # Third-party loggers (reduce noise)
            'requests': {
                'level': 'WARNING',
                'handlers': ['file_all'],
                'propagate': False
            },
            'urllib3': {
                'level': 'WARNING',
                'handlers': ['file_all'],
                'propagate': False
            },
            'streamlit': {
                'level': 'WARNING',
                'handlers': ['console'],
                'propagate': False
            }
        }
    }


def setup_logging(log_level: str = None, log_dir: str = "logs") -> None:
    """
    Setup logging configuration for the application.
    
    Args:
        log_level: Override log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: Directory to store log files
    """
    # Get environment-based log level
    if log_level is None:
        log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
    
    # Get logging configuration
    config = get_logging_config(log_dir)
    
    # Override log level if specified
    if log_level in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']:
        # Update console handler level
        config['handlers']['console']['level'] = log_level
        # Update root logger level
        config['loggers']['']['level'] = log_level
        config['loggers']['src.weather_map']['level'] = log_level
    
    # Apply configuration
    logging.config.dictConfig(config)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the specified name.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)


class PerformanceLogger:
    """Context manager for performance logging."""
    
    def __init__(self, operation: str, logger: logging.Logger = None):
        """
        Initialize performance logger.
        
        Args:
            operation: Name of the operation being timed
            logger: Logger instance to use
        """
        self.operation = operation
        self.logger = logger or get_logger('performance')
        self.start_time = None
    
    def __enter__(self):
        """Start timing the operation."""
        import time
        self.start_time = time.time()
        self.logger.info(f"Starting operation: {self.operation}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """End timing and log the duration."""
        import time
        duration = time.time() - self.start_time
        
        if exc_type is None:
            self.logger.info(f"Completed operation: {self.operation} in {duration:.3f}s")
        else:
            self.logger.error(f"Failed operation: {self.operation} after {duration:.3f}s - {exc_val}")


class APILogger:
    """Specialized logger for API calls."""
    
    def __init__(self, logger: logging.Logger = None):
        """
        Initialize API logger.
        
        Args:
            logger: Logger instance to use
        """
        self.logger = logger or get_logger('src.weather_map.services')
    
    def log_request(self, method: str, url: str, params: dict = None, headers: dict = None):
        """Log API request details."""
        self.logger.info(f"API Request: {method} {url}", extra={
            'method': method,
            'url': url,
            'params': params,
            'headers': {k: '***' if 'key' in k.lower() or 'token' in k.lower() else v 
                       for k, v in (headers or {}).items()}
        })
    
    def log_response(self, status_code: int, response_time: float, response_size: int = None):
        """Log API response details."""
        level = logging.INFO if 200 <= status_code < 400 else logging.WARNING
        self.logger.log(level, f"API Response: {status_code} in {response_time:.3f}s", extra={
            'status_code': status_code,
            'response_time': response_time,
            'response_size': response_size
        })
    
    def log_error(self, error: Exception, context: dict = None):
        """Log API error details."""
        self.logger.error(f"API Error: {error}", extra={
            'error_type': type(error).__name__,
            'error_message': str(error),
            'context': context or {}
        }, exc_info=True)
