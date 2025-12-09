"""
Sistema de logging para la Aplicación CLI.
"""
import logging
import json
import sys
from datetime import datetime, timezone


class JSONFormatter(logging.Formatter):
    """Formateador de logs en JSON."""
    
    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "component": "AppCLI",
            "message": record.getMessage(),
        }
        
        if hasattr(record, "request_id") and record.request_id:
            log_entry["request_id"] = record.request_id
        if hasattr(record, "extra_data") and record.extra_data:
            log_entry["details"] = record.extra_data
        
        return json.dumps(log_entry, ensure_ascii=False)


class TextFormatter(logging.Formatter):
    """Formateador de logs en texto."""
    
    def __init__(self):
        super().__init__(
            fmt="%(asctime)s | %(levelname)-8s | %(message)s",
            datefmt="%H:%M:%S"
        )


def setup_logger(level: str = "INFO", format_type: str = "text") -> logging.Logger:
    """Configura y retorna un logger."""
    logger = logging.getLogger("AppCLI")
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    
    if logger.hasHandlers():
        logger.handlers.clear()
    
    handler = logging.StreamHandler(sys.stdout)
    if format_type.lower() == "json":
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(TextFormatter())
    
    logger.addHandler(handler)
    logger.propagate = False
    
    return logger
