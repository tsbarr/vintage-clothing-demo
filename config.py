# config.py - Shared configuration classes for all sync modules

import os
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

@dataclass
class DatabaseConfig:
    """Database connection configuration"""
    host: str = os.getenv('DB_HOST', 'localhost')
    port: str = os.getenv('DB_PORT', '5432')
    database: str = os.getenv('DB_NAME', 'db_name')
    user: str = os.getenv('DB_USER', 'postgres')
    password: str = os.getenv('DB_PASSWORD', 'password')
    
    def __post_init__(self):
        """Validate required configuration"""
        required_fields = ['host', 'database', 'user', 'password']
        missing = [field for field in required_fields if not getattr(self, field)]
        if missing:
            raise ValueError(f"Missing required database configuration: {', '.join(missing)}")
    
    @property
    def connection_string(self) -> str:
        """Generate PostgreSQL connection string"""
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"

@dataclass
class SquareConfig:
    """Square API configuration"""
    access_token: Optional[str] = os.getenv('SQUARE_ACCESS_TOKEN')
    environment: str = os.getenv('SQUARE_ENVIRONMENT', 'sandbox') # or 'production'
    application_id: Optional[str] = os.getenv('SQUARE_APPLICATION_ID')
    
    def __post_init__(self):
        """Validate required configuration"""
        if not self.access_token:
            raise ValueError("SQUARE_ACCESS_TOKEN environment variable is required")
        
        if self.environment not in ['sandbox', 'production']:
            raise ValueError("SQUARE_ENVIRONMENT must be 'sandbox' or 'production'")
    
    @property
    def is_production(self) -> bool:
        """Check if using production environment"""
        return self.environment.lower() == 'production'

@dataclass
class SocialMediaConfig:
    """Social Media APIs configuration"""
    # Instagram Graph API (Business/Creator accounts only)
    instagram_access_token: Optional[str] = os.getenv('INSTAGRAM_ACCESS_TOKEN')
    instagram_business_account_id: Optional[str] = os.getenv('INSTAGRAM_BUSINESS_ACCOUNT_ID')
    
    # Facebook Graph API
    facebook_access_token: Optional[str] = os.getenv('FACEBOOK_ACCESS_TOKEN')
    facebook_page_id: Optional[str] = os.getenv('FACEBOOK_PAGE_ID')
    
    # TikTok Business API (very restricted)
    tiktok_access_token: Optional[str] = os.getenv('TIKTOK_ACCESS_TOKEN')
    
    # Alternative: Third-party APIs for public data
    alternative_api_key: Optional[str] = os.getenv('ALTERNATIVE_SOCIAL_API_KEY')
    
    @property
    def has_instagram_config(self) -> bool:
        """Check if Instagram API is configured"""
        return bool(self.instagram_access_token and self.instagram_business_account_id)
    
    @property
    def has_facebook_config(self) -> bool:
        """Check if Facebook API is configured"""
        return bool(self.facebook_access_token and self.facebook_page_id)
    
    @property
    def has_tiktok_config(self) -> bool:
        """Check if TikTok API is configured"""
        return bool(self.tiktok_access_token)
    
    @property
    def configured_platforms(self) -> list[str]:
        """Get list of configured social media platforms"""
        platforms = []
        if self.has_instagram_config:
            platforms.append('instagram')
        if self.has_facebook_config:
            platforms.append('facebook')
        if self.has_tiktok_config:
            platforms.append('tiktok')
        return platforms

@dataclass
class LoggingConfig:
    """Logging configuration"""
    level: str = os.getenv('LOG_LEVEL', 'INFO')
    file_path: str = os.getenv('LOG_FILE_PATH', 'curated_closet_sync.log')
    max_file_size: int = int(os.getenv('LOG_MAX_FILE_SIZE', '10485760'))  # 10MB default
    backup_count: int = int(os.getenv('LOG_BACKUP_COUNT', '5'))
    
    def __post_init__(self):
        """Validate logging level"""
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if self.level.upper() not in valid_levels:
            raise ValueError(f"LOG_LEVEL must be one of: {', '.join(valid_levels)}")

@dataclass
class AppConfig:
    """Main application configuration container"""
    database: DatabaseConfig
    square: SquareConfig
    social_media: SocialMediaConfig
    logging: LoggingConfig
    
    # Application-specific settings
    sync_days_back: int = int(os.getenv('SYNC_DAYS_BACK', '30'))
    quick_sync_days: int = int(os.getenv('QUICK_SYNC_DAYS', '7'))
    health_check_timeout: int = int(os.getenv('HEALTH_CHECK_TIMEOUT', '10'))
    
    @classmethod
    def load(cls) -> 'AppConfig':
        """Load configuration from environment variables"""
        return cls(
            database=DatabaseConfig(),
            square=SquareConfig(),
            social_media=SocialMediaConfig(),
            logging=LoggingConfig()
        )
    
    def validate(self) -> tuple[bool, list[str]]:
        """Validate all configuration and return (is_valid, error_messages)"""
        errors = []
        
        try:
            # Database validation happens in __post_init__
            DatabaseConfig()
        except ValueError as e:
            errors.append(f"Database: {e}")
        
        try:
            # Square validation happens in __post_init__
            SquareConfig()
        except ValueError as e:
            errors.append(f"Square: {e}")
        
        # Social media is optional, so just check if at least one platform is configured
        if not self.social_media.configured_platforms:
            errors.append("Social Media: No social media platforms configured (optional but recommended)")
        
        try:
            # Logging validation happens in __post_init__
            LoggingConfig()
        except ValueError as e:
            errors.append(f"Logging: {e}")
        
        return len(errors) == 0, errors

def create_env_template(file_path: str = '.env') -> bool:
    """Create a template .env file with all required configuration"""
    env_template = """# Curated Closet Vintage Clothing - Data Sync Configuration
# Copy this file to .env and fill in your actual values

# =============================================================================
# DATABASE CONFIGURATION
# =============================================================================
DB_HOST=localhost
DB_PORT=5432
DB_NAME=curated_closet_db
DB_USER=postgres
DB_PASSWORD=your_password_here

# =============================================================================
# SQUARE API CONFIGURATION (Required)
# =============================================================================
# Get these from Square Developer Dashboard: https://developer.squareup.com/
SQUARE_ACCESS_TOKEN=your_square_access_token_here
SQUARE_ENVIRONMENT=sandbox  # Change to 'production' for live data
SQUARE_APPLICATION_ID=your_square_application_id_here

# =============================================================================
# SOCIAL MEDIA API CONFIGURATION (Optional but recommended)
# =============================================================================

# Instagram Graph API
# Note: Personal Instagram accounts no longer supported as of Dec 2024
# Setup: Convert to Business account, create Facebook app, get access token
INSTAGRAM_ACCESS_TOKEN=your_instagram_access_token_here
INSTAGRAM_BUSINESS_ACCOUNT_ID=your_instagram_business_account_id_here

# Facebook Graph API
# Setup: Create Facebook app, get page access token
FACEBOOK_ACCESS_TOKEN=your_facebook_access_token_here
FACEBOOK_PAGE_ID=your_facebook_page_id_here

# TikTok Business API
TIKTOK_ACCESS_TOKEN=your_tiktok_access_token_here

# Alternative Social Media APIs (Optional)
ALTERNATIVE_SOCIAL_API_KEY=your_alternative_api_key_here

# =============================================================================
# APPLICATION SETTINGS
# =============================================================================

# Logging Configuration
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_FILE_PATH=curated_closet_sync.log
LOG_MAX_FILE_SIZE=10485760  # 10MB
LOG_BACKUP_COUNT=5

# Sync Settings
SYNC_DAYS_BACK=30  # How many days back to sync in full sync
QUICK_SYNC_DAYS=7  # How many days back to sync in quick sync
HEALTH_CHECK_TIMEOUT=10  # Timeout for API health checks in seconds

# =============================================================================
# SETUP INSTRUCTIONS
# =============================================================================
# 1. Fill in your database connection details above
# 2. Get Square API credentials from Square Developer Dashboard
# 3. Set up social media API access:
#    - Instagram: Convert to Business account, get Graph API token
#    - Facebook: Create app, get page access token
# 4. Test configuration: python main_sync.py health
# 5. Run initial sync: python main_sync.py full
"""
    
    if os.path.exists(file_path):
        return False
    
    try:
        with open(file_path, 'w') as f:
            f.write(env_template)
        return True
    except Exception as e:
        raise RuntimeError(f"Failed to create {file_path}: {e}")

def get_required_env_vars() -> list[str]:
    """Get list of required environment variables"""
    return [
        'DB_HOST',
        'DB_NAME', 
        'DB_USER',
        'DB_PASSWORD',
        'SQUARE_ACCESS_TOKEN'
    ]

def get_optional_env_vars() -> dict[str, list[str]]:
    """Get dictionary of optional environment variables by category"""
    return {
        'square': ['SQUARE_ENVIRONMENT', 'SQUARE_APPLICATION_ID'],
        'instagram': ['INSTAGRAM_ACCESS_TOKEN', 'INSTAGRAM_BUSINESS_ACCOUNT_ID'],
        'facebook': ['FACEBOOK_ACCESS_TOKEN', 'FACEBOOK_PAGE_ID'],
        'tiktok': ['TIKTOK_ACCESS_TOKEN'],
        'logging': ['LOG_LEVEL', 'LOG_FILE_PATH', 'LOG_MAX_FILE_SIZE', 'LOG_BACKUP_COUNT'],
        'sync': ['SYNC_DAYS_BACK', 'QUICK_SYNC_DAYS', 'HEALTH_CHECK_TIMEOUT']
    }

def validate_environment() -> tuple[bool, list[str], list[str]]:
    """
    Validate environment configuration
    Returns: (is_valid, missing_required, missing_optional)
    """
    required_vars = get_required_env_vars()
    optional_vars = get_optional_env_vars()
    
    missing_required = [var for var in required_vars if not os.getenv(var)]
    missing_optional = []
    
    for category, vars_list in optional_vars.items():
        category_missing = [var for var in vars_list if not os.getenv(var)]
        if category_missing:
            missing_optional.extend(f"{category}: {var}" for var in category_missing)
    
    return len(missing_required) == 0, missing_required, missing_optional

# Convenience function to get a fully loaded configuration
def load_config() -> AppConfig:
    """Load and validate complete application configuration"""
    try:
        config = AppConfig.load()
        is_valid, errors = config.validate()
        
        if not is_valid:
            error_msg = "Configuration validation failed:\n" + "\n".join(f"  - {error}" for error in errors)
            raise ValueError(error_msg)
        
        return config
    except Exception as e:
        raise RuntimeError(f"Failed to load configuration: {e}")

if __name__ == "__main__":
    # Quick test of configuration loading
    try:
        config = load_config()
        print("✓ Configuration loaded successfully")
        print(f"✓ Database: {config.database.host}:{config.database.port}/{config.database.database}")
        print(f"✓ Square Environment: {config.square.environment}")
        print(f"✓ Configured Social Platforms: {', '.join(config.social_media.configured_platforms) or 'None'}")
    except Exception as e:
        print(f"✗ Configuration error: {e}")
        print("\nRun the following to create a template .env file:")
        print("python config.py --create-template")
        
        if "--create-template" in __import__('sys').argv:
            if create_env_template():
                print("✓ Created .env template file. Now add your values to it.")
            else:
                print("✗ .env file already exists")
