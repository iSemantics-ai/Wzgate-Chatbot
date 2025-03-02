from datetime import datetime
import logging
from logging.handlers import RotatingFileHandler

import boto3

from botocore.exceptions import NoCredentialsError, PartialCredentialsError
from .config import settings
import os
from pathlib import Path


class S3LogHandler(logging.Handler):
    def __init__(self, bucket_name: str, log_key_prefix: str):
        super().__init__()
        self.bucket_name = bucket_name
        self.log_key_prefix = log_key_prefix
        self.s3_client = boto3.client('s3')
    
    def emit(self, record: logging.LogRecord):
        try:
            log_message = self.format(record)
            # Generate a unique key for each log file
            log_key = f"{self.log_key_prefix}{datetime.utcnow().strftime('%Y-%m-%d')}.log"
            
            # Upload the log to s3
            self.s3_client.put_object(
                Bucket = self.bucket_name,
                Key=log_key,
                Body=log_message + '\n',
                ContentType='text/plain'           
            )
        except (NoCredentialsError, PartialCredentialsError) as e:
            print(f"Failed to upload log to S3: {e}")
        except Exception as e:
            print(f"Unexpected error: {e}")
def setup_logging(bucket_name: str = "wzgate-search-bar-bucket", log_key_prefix='logs/', log_level: int = logging.INFO) -> None:
       
    # Create a logger
    logger = logging.getLogger()
    logger.setLevel(log_level)  # Set the global logging level

    # Define log format
    log_format = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Console handler (outputs logs to the terminal)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)  # Set the console logging level
    console_handler.setFormatter(log_format)  # Apply the format
    logger.addHandler(console_handler)

    # S3 handler for storing logs in S3
    s3_handler = S3LogHandler(bucket_name=bucket_name, log_key_prefix=log_key_prefix)
    s3_handler.setLevel(log_level)
    s3_handler.setFormatter(log_format)
    logger.addHandler(s3_handler)

    # Suppress third-party library logs (optional)
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)

    # Test log message (optional)
    logger.info("Logging has been configured with s3 support.")
