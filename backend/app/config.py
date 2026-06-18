import os
from dotenv import load_dotenv

# Load .env file from the backend folder
base_dir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
load_dotenv(os.path.join(base_dir, '.env'))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'tg-secret-key-1337')
    
    # Database configuration (fallback to local MySQL dev defaults if not specified)
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL', 
        'mysql+pymysql://root:password@localhost:3306/transaction_guard'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # File uploads
    _raw_upload = os.environ.get('UPLOAD_FOLDER', 'uploads')
    UPLOAD_FOLDER = _raw_upload if os.path.isabs(_raw_upload) else os.path.abspath(os.path.join(base_dir, _raw_upload))
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH', 16 * 1024 * 1024)) # Default 16MB
    
    # Validation engine limits
    ROW_SPLIT_THRESHOLD = int(os.environ.get('ROW_SPLIT_THRESHOLD', 50000))
    
    # Email required configuration (can be configured per dataset type/run)
    EMAIL_REQUIRED = True
    
    # Ensure directories exist
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
