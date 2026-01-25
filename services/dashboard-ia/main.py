"""
Main entry point for Dashboard IA Service.
"""
import os
import sys
from app import create_app
from config import Config

# Create Flask app
app = create_app(config_name=os.getenv('FLASK_ENV', 'default'))

if __name__ == '__main__':
    try:
        Config.validate()
    except ValueError as e:
        is_dev = os.getenv('FLASK_ENV', 'default') in ['development', 'default'] or Config.DEBUG
        if is_dev:
            print(f"Warning: {e}")
        else:
            print(f"Configuration error: {e}")
            sys.exit(1)

    print(f"Dashboard IA Service starting on http://{Config.HOST}:{Config.PORT}")
    print(f"API: http://{Config.HOST}:{Config.PORT}/api")
    app.run(
        host=Config.HOST,
        port=Config.PORT,
        debug=Config.DEBUG
    )
