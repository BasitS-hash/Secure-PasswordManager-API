"""
Secure Password Manager API - Flask Application
Zero-knowledge password storage with client-side encryption
"""

import os
from flask import Flask, send_from_directory, jsonify
from dotenv import load_dotenv
from datetime import datetime
from flask_swagger_ui import get_swaggerui_blueprint

from src.logger import logger
from src.routes.auth import auth_bp
from src.routes.entries import entries_bp
from src.middleware.rate_limit import limiter

# Load environment variables
load_dotenv()

# Create Flask app
app = Flask(__name__, static_folder='public', static_url_path='')

# Initialize rate limiter
limiter.init_app(app)

# Security headers
@app.after_request
def set_security_headers(response):
    """Add security headers to all responses."""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:"
    return response


# Register blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(entries_bp)

# Swagger UI
swaggerui_bp = get_swaggerui_blueprint(
    '/docs',
    '/static/swagger.json',
    config={'app_name': 'Secure Password Manager API'}
)
app.register_blueprint(swaggerui_bp)


# Serve static files
@app.route('/')
def serve_index():
    """Serve the main index page."""
    return send_from_directory('public', 'index.html')


@app.route('/<path:filename>')
def serve_static(filename):
    """Serve static files from public directory."""
    return send_from_directory('public', filename)


@app.route('/static/swagger.json')
def swagger_spec():
    """Serve the OpenAPI spec."""
    return send_from_directory('static', 'swagger.json')


# Health check endpoint
@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.utcnow().isoformat()
    }), 200


# Error handlers
@app.errorhandler(404)
def not_found(error):
    """Handle 404 Not Found errors."""
    return jsonify({'error': 'Not found'}), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 Internal Server Error."""
    logger.error(f'Internal server error: {error}')
    return jsonify({'error': 'Internal server error'}), 500


@app.errorhandler(429)
def rate_limit_handler(error):
    """Handle rate limit exceeded."""
    return jsonify({'error': 'Too many requests, slow down.'}), 429


if __name__ == '__main__':
    PORT = int(os.getenv('PORT', 4000))
    DEBUG = os.getenv('DEBUG', 'false').lower() == 'true'
    
    logger.info(f'Starting Secure Password Manager API on port {PORT}')
    app.run(host='0.0.0.0', port=PORT, debug=DEBUG)
