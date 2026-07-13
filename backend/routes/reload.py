from flask import request, jsonify
import os
from .model_loader import model_loader

def register_reload_endpoint(app):
    """Register the /reload-model endpoint."""
    
    @app.route('/reload-model', methods=['POST'])
    def reload_model():
        """Internal endpoint to reload models without server restart."""
        
        # Validate internal secret
        auth_header = request.headers.get('X-Internal-Secret')
        internal_secret = os.getenv('INTERNAL_SECRET')
        
        if not internal_secret or auth_header != internal_secret:
            return jsonify({
                'error': 'Unauthorized',
                'message': 'Invalid or missing internal secret'
            }), 401
        
        # Reload models
        success = model_loader.reload_models()
        
        if success:
            return jsonify({
                'status': 'success',
                'message': 'Models reloaded successfully',
                'status': model_loader.get_status()
            }), 200
        else:
            return jsonify({
                'status': 'error',
                'message': 'Failed to reload models'
            }), 500
    
    @app.route('/model-status', methods=['GET'])
    def model_status():
        """Check model status."""
        return jsonify(model_loader.get_status()), 200