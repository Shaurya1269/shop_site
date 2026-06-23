import logging

logger = logging.getLogger("app.utils")

def log_exception(message, exc=None):
    """Utility to log exceptions consistently."""
    if exc:
        logger.error(f"{message}: {exc}", exc_info=True)
    else:
        logger.exception(message)
