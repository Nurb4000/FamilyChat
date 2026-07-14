# config.py
import os
import secrets
class Config:
    # Require a strong secret key — never use the default in production
    _provided_secret = os.environ.get('SECRET_KEY')
    if not _provided_secret:
        # Generate a fresh one each run (dev convenience only)
        SECRET_KEY = secrets.token_hex(32)
    else:
        SECRET_KEY = _provided_secret
    DATABASE_URL = 'sqlite:///family_chat.db'
    MAX_IMAGE_SIZE = (800, 600)  # Maximum dimensions for resized images  
    UPLOAD_FOLDER = 'static/uploads'  
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}  
    # Pagination settings
    POSTS_PER_PAGE = 10
    REPLIES_PER_PAGE = 15
    # Self-signup settings
    SELF_SIGNUP_ENABLED = True  # Default to disabled
    # Create upload directory if it doesn't exist  
    if not os.path.exists(UPLOAD_FOLDER):  
        os.makedirs(UPLOAD_FOLDER)