import logging
import logging.config
from pathlib import Path
from config.base import Config, ConfigurationError

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