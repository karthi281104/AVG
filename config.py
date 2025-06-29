import os
import secrets
from datetime import timedelta


class Config:
    # Flask application settings
    SECRET_KEY = os.environ.get('SECRET_KEY') or secrets.token_hex(32)
    DEBUG = False
    TESTING = False

    # Session settings
    PERMANENT_SESSION_LIFETIME = timedelta(hours=12)

    # File upload settings
    UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max upload size
    ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'doc', 'docx', 'xls', 'xlsx'}

    # Database settings (basic SQLite for development)
    SQLALCHEMY_DATABASE_URI = 'sqlite:///avg_loan.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Security settings
    SESSION_COOKIE_SECURE = False  # Set to True in production with HTTPS
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'

    # Gold rates API (replace with an actual API key in production)
    GOLD_API_KEY = os.environ.get('GOLD_API_KEY')

    @staticmethod
    def init_app(app):
        # Create upload folder if it doesn't exist
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)


class DevelopmentConfig(Config):
    DEBUG = True


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///test.db'
    WTF_CSRF_ENABLED = False


class ProductionConfig(Config):
    # Production specific settings
    SESSION_COOKIE_SECURE = True

    # Use PostgreSQL in production
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'postgresql://user:pass@localhost/avg_loan'

    # Use environment variables for sensitive data
    SECRET_KEY = os.environ.get('SECRET_KEY')

    # Error logging and monitoring
    LOG_LEVEL = 'INFO'


# Dictionary to select environment config
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}