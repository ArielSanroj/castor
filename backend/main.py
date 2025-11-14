"""
Main entry point for CASTOR ELECCIONES Flask application.
"""
import os
import sys
from app import create_app
from config import Config

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Create Flask app
app = create_app(config_name=os.getenv('FLASK_ENV', 'default'))

if __name__ == '__main__':
    # Validate configuration
    try:
        Config.validate()
    except ValueError as e:
        print(f"Configuration error: {e}")
        sys.exit(1)
    
    # Run application
    app.run(
        host=Config.HOST,
        port=Config.PORT,
        debug=Config.DEBUG
    )

