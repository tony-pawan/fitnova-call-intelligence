import logging
import sys

def setup_logging(log_level: str = "INFO") -> None:
    """
    Configures centralized console logging with a custom format.
    Clears standard handlers to prevent duplicate logs.
    """
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Root logger config
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    
    # Remove existing handlers
    if root_logger.handlers:
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
            
    # Console handler using standard output
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    
    # Custom format to support prefixes naturally from the logger name
    formatter = logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

def get_logger(module_name: str) -> logging.Logger:
    """
    Returns a configured logger with the module name formatted as a bracketed prefix.
    Example: get_logger("UPLOAD") -> logger named "[UPLOAD]"
    """
    prefix = module_name.strip("[]").upper()
    return logging.getLogger(f"[{prefix}]")
