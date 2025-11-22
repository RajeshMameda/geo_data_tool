import os
import sys
from loguru import logger

def configure_logging(level: str = "INFO"):
    """Configure application logging."""
    logger.remove()  # Remove default handler
    
    # Add console handler
    logger.add(
        sys.stderr,
        level=level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    )
    
    # Add file handler in production
    if os.getenv("ENVIRONMENT") == "production":
        logger.add(
            "logs/geodata_{time:YYYY-MM-DD}.log",
            rotation="10 MB",
            retention="30 days",
            level=level,
            enqueue=True
        )
    
    return logger