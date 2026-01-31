"""Logging configuration for FlagGuard.

Provides consistent logging setup across all FlagGuard modules
with environment-based configuration.
"""

import logging
import os
import sys
from typing import Optional


def setup_logging(
    level: Optional[str] = None,
    format_string: Optional[str] = None,
) -> logging.Logger:
    """Configure and return the FlagGuard root logger.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
               Defaults to LOG_LEVEL env var or INFO.
        format_string: Custom format string for log messages.
    
    Returns:
        The configured root logger for FlagGuard.
    """
    log_level = level or os.getenv("LOG_LEVEL", "INFO")
    
    logger = logging.getLogger("flagguard")
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    
    # Only add handler if none exist (avoid duplicate handlers)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setLevel(getattr(logging, log_level.upper(), logging.INFO))
        
        formatter = logging.Formatter(
            format_string or "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """Get a child logger for a specific module.
    
    Args:
        name: The module name (will be prefixed with 'flagguard.')
    
    Returns:
        A logger instance for the specified module.
    
    Example:
        >>> logger = get_logger("parsers")
        >>> logger.info("Parsing config file")
    """
    return logging.getLogger(f"flagguard.{name}")


# Create a simple logger for immediate use
_default_logger: Optional[logging.Logger] = None


def log() -> logging.Logger:
    """Get the default FlagGuard logger.
    
    Lazily initializes the logger on first use.
    
    Returns:
        The default FlagGuard logger.
    """
    global _default_logger
    if _default_logger is None:
        _default_logger = setup_logging()
    return _default_logger
