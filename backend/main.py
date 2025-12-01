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
    # Validate configuration (only warn in development, don't exit)
    try:
        Config.validate()
    except ValueError as e:
        # In development mode, allow missing env vars for basic web serving
        is_dev = os.getenv('FLASK_ENV', 'default') in ['development', 'default'] or Config.DEBUG
        if is_dev:
            print(f"⚠️  Warning: {e}")
            print("⚠️  Some features may not work without these environment variables")
            print("⚠️  Continuing anyway in development mode...")
        else:
            print(f"Configuration error: {e}")
            sys.exit(1)
    
    # Run application
    print(f"🚀 Starting CASTOR ELECCIONES on http://{Config.HOST}:{Config.PORT}")
    print(f"📄 Web page: http://{Config.HOST}:{Config.PORT}/webpage")
    print(f"🔌 API: http://{Config.HOST}:{Config.PORT}/api")
    app.run(
        host=Config.HOST,
        port=Config.PORT,
        debug=Config.DEBUG
    )

