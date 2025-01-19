from typing import Dict, Any, Optional
from pathlib import Path
import os
import logging
from dataclasses import dataclass
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class APIConfig:
    """API configuration settings."""
    anthropic_api_key: str
    pinecone_api_key: str

@dataclass
class GoogleSheetsConfig:
    """Google Sheets configuration settings."""
    spreadsheet_name: str
    service_account_file: str
    scopes: list[str] = None

    def __post_init__(self):
        if self.scopes is None:
            self.scopes = [
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive"
            ]

@dataclass
class PineconeConfig:
    """Pinecone vector database configuration settings."""
    environment: str
    index_name: str
    namespace_categories: list[str] = None

    def __post_init__(self):
        if self.namespace_categories is None:
            self.namespace_categories = [
                "Housing", "Grocery", "Fun", "Investment", "Miscellaneous"
            ]

@dataclass
class LLMConfig:
    """Language model configuration settings."""
    model: str
    temperature: float
    max_tokens: int
    timeout: Optional[int]
    max_retries: int

class ConfigurationError(Exception):
    """Raised when there's an error in configuration."""
    pass

class Config:
    """Main configuration class for ExpensAI."""
    
    def __init__(self, env_file: str = ".env"):
        """Initialize configuration from environment variables."""
        self._load_environment(env_file)
        self._init_config()
        self.validate()
        logger.info("Configuration loaded successfully")

    def _load_environment(self, env_file: str) -> None:
        """Load environment variables from .env file."""
        env_path = Path(env_file)
        if env_path.exists():
            load_dotenv(env_path)
            logger.info(f"Loaded environment from {env_file}")
        else:
            logger.warning(f"Environment file {env_file} not found, using system environment variables")

    def _init_config(self) -> None:
        """Initialize configuration objects from environment variables."""
        try:
            # Initialize API configuration
            self.api = APIConfig(
                anthropic_api_key=self._get_env("ANTHROPIC_API_KEY"),
                pinecone_api_key=self._get_env("PINECONE_API_KEY")
            )

            # Initialize Google Sheets configuration
            self.sheets = GoogleSheetsConfig(
                spreadsheet_name=self._get_env("EXPENSE_SHEET_NAME", "ExpensAI"),
                service_account_file=self._get_env("GOOGLE_SERVICE_ACCOUNT_FILE")
            )

            # Initialize Pinecone configuration
            self.pinecone = PineconeConfig(
                environment=self._get_env("PINECONE_ENV", "production"),
                index_name=self._get_env("PINECONE_INDEX_NAME", "expense-vectors")
            )

            # Initialize LLM configuration
            self.llm = LLMConfig(
                model=self._get_env("LLM_MODEL", "claude-3-5-sonnet-20240620"),
                temperature=float(self._get_env("LLM_TEMPERATURE", "0")),
                max_tokens=int(self._get_env("LLM_MAX_TOKENS", "1024")),
                timeout=None,
                max_retries=int(self._get_env("LLM_MAX_RETRIES", "2"))
            )

        except Exception as e:
            raise ConfigurationError(f"Error initializing configuration: {str(e)}")

    def _get_env(self, key: str, default: Any = None) -> Any:
        """
        Get environment variable with optional default value.
        Raises ConfigurationError if required variable is missing.
        """
        value = os.getenv(key, default)
        if value is None:
            raise ConfigurationError(f"Missing required environment variable: {key}")
        return value

    def validate(self) -> bool:
        """Validate the configuration."""
        try:
            # Validate API keys
            if not self.api.anthropic_api_key or not self.api.pinecone_api_key:
                raise ConfigurationError("Missing required API keys")

            # Validate Google Sheets configuration
            if not Path(self.sheets.service_account_file).exists():
                raise ConfigurationError(f"Service account file not found: {self.sheets.service_account_file}")

            # Validate Pinecone configuration
            if not self.pinecone.index_name:
                raise ConfigurationError("Missing Pinecone index name")

            return True

        except Exception as e:
            raise ConfigurationError(f"Configuration validation failed: {str(e)}")

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary format."""
        return {
            "api": {
                "anthropic_api_key": "***masked***",
                "pinecone_api_key": "***masked***"
            },
            "sheets": {
                "spreadsheet_name": self.sheets.spreadsheet_name,
                "service_account_file": self.sheets.service_account_file,
                "scopes": self.sheets.scopes
            },
            "pinecone": {
                "environment": self.pinecone.environment,
                "index_name": self.pinecone.index_name,
                "namespace_categories": self.pinecone.namespace_categories
            },
            "llm": {
                "model": self.llm.model,
                "temperature": self.llm.temperature,
                "max_tokens": self.llm.max_tokens,
                "timeout": self.llm.timeout,
                "max_retries": self.llm.max_retries
            }
        }

# Create a global configuration instance
try:
    config = Config()
except ConfigurationError as e:
    logger.error(f"Failed to load configuration: {str(e)}")
    raise