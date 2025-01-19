import logging
import logging.config
from typing import Optional
from pathlib import Path
import json
from config.base import Config, ConfigurationError

def setup_logging(log_file: Optional[str] = None, log_level: str = "INFO") -> None:
    """
    Set up logging configuration for the application.
    
    Args:
        log_file: Optional path to log file
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    log_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {
                "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "standard",
                "stream": "ext://sys.stdout"
            },
        },
        "loggers": {
            "": {  # root logger
                "handlers": ["console"],
                "level": log_level,
            }
        }
    }

    if log_file:
        log_config["handlers"]["file"] = {
            "class": "logging.FileHandler",
            "filename": log_file,
            "formatter": "standard"
        }
        log_config["loggers"][""]["handlers"].append("file")

    logging.config.dictConfig(log_config)

def load_config(env_file: str = ".env") -> Config:
    """
    Load and validate configuration.
    
    Args:
        env_file: Path to .env file
        
    Returns:
        Config: Validated configuration object
        
    Raises:
        ConfigurationError: If configuration is invalid or missing required values
    """
    try:
        config = Config(env_file=env_file)
        logging.info("Configuration loaded successfully")
        return config
    except ConfigurationError as e:
        logging.error(f"Failed to load configuration: {str(e)}")
        raise

def save_config_template() -> None:
    """
    Save a template .env file if it doesn't exist.
    """
    template_path = Path(".env.example")
    env_path = Path(".env")
    
    if not env_path.exists() and template_path.exists():
        template_path.copy(env_path)
        logging.info("Created .env file from template")

def print_config(config: Config) -> None:
    """
    Print current configuration (with sensitive values masked).
    
    Args:
        config: Configuration object to print
    """
    config_dict = config.to_dict()
    print(json.dumps(config_dict, indent=2))