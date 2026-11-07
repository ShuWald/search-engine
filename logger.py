import os
import sys
import logging

LOGPATH = "logs"
os.makedirs(LOGPATH, exist_ok=True)

# Configure base root logging for the application
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)

# Regular logger
def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)

# Logs to files
def get_file_logger(name: str, propagate: bool = False, filename: str | None = None) -> logging.Logger:
    """
    `name` is logger name
    `propagate` toggles sending logs to the console
    `filename` is the file to write logs to (defaults to `name`)
    """
    logger = logging.getLogger(name)
    if filename is None:
        filename = f"{name}.log"  # Added a default extension just in case

    # Prevent duplicate handlers
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        logger.propagate = propagate  # Control whether logs are sent to the console
        
        # File path joining
        file_path = os.path.join(LOGPATH, filename)
        file_handler = logging.FileHandler(file_path)
        file_handler.setLevel(logging.INFO)
        
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        
        logger.addHandler(file_handler)
        
    return logger