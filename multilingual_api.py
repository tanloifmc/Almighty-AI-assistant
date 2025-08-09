"""
Multilingual API with i18n Support
Enhanced version of secure_api.py with comprehensive multilingual support
"""

from flask import Flask, request, jsonify, g
from flask_cors import CORS
import logging
import json
from datetime import datetime
from functools import wraps
from typing import Dict, Any, Optional, Tuple
import os
from security_manager import (
    auth_manager, authz_manager, security_monitor, encryption_manager,
    UserRole, SecurityLevel
)
from i18n_manager import i18n_manager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app, origins="*")

# Multilingual middleware
def multilingual_middleware():
    """Middleware to handle language detection and setup"""
    # Get language from header, query param, or user preference
    user_language = None
    
    # 1. Check Accept-Language header
    accept_language = request.headers.get('Accept-Language')
    if accept_language:
        # Parse Accept-Language header (e.g., "en-US,en;q=0.9,vi;q=0.8")
        languages = []
        for lang_item in accept_language.split(','):
            lang = lang_item.split(';')[0].strip()
            if '-' in lang:
                lang = lang.split('-')[0]  # Convert en-US to en
            languages.append(lang)
        
        # Use the first supported language
        supported_langs = [lang.value for lang in i18n_manager.localization_manager.SupportedLanguage]
        for lang in languages:
            if lang in supported_langs:
                user_language = lang
                break
    
    # 2. Check query parameter
    if not user_language:
        user_language = request.args.get('lang')
    
    # 3. Check user preference if authenticated
    if not user_language and hasattr(g, 'user_id'):
        user_language = i18n_manager.get_user_language(g.user_id)
    
    # 4. Default to English
    if not user_language:
        user_language = 'en'
    
    # Store in request context
    g.user_language = user_language
    
    return None

@app.before_request
def before_request():
    """Execute before each request"""
    # Apply security middleware first
    from secure_api import security_middleware
    security_response = security_middleware()
    if security_response:
        return security_response
    
    # Apply multilingual middleware
    multilingual_response = multilingual_middleware()
    if multilingual_response:
        return multilingual_response

def require_auth(f):
    """Decorator to require authentication with i18n support"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        
        if not auth_header or not auth_header.startswith('Bearer '):
            error_msg = i18n_manager.localize_for_user('', 'unauthorized', user_id='')
            return jsonify({'error': error_msg}), 401
        
        token = auth_header.split(' ')[1]
        is_valid, payload = auth_manager.validate_token(token)
        
        if not is_valid:
            error_msg = i18n_manager.localize_for_user('', 'invalid_token', user_id='')
            return jsonify({'error': error_msg}), 401
        
        # Store user info in request context
        g.user_id = payload['user_id']
        g.username = payload['username']
        g.user_role = UserRole(payload['role'])
        
        # Update user language preference
        if hasattr(g, 'user_language'):
            i18n_manager.set_user_language(g.user_id, g.user_language)
        
        return f(*args, **kwargs)
    
    return decorated_function

def localized_response(data: Dict[str, Any], status_code: int = 200) -> Tuple[Any, int]:
    """Create localized response"""
    user_id = getattr(g, 'user_id', '')
    
    # Localize error messages
    if 'error' in data and isinstance(data['error'], str):
        # Try to localize the error message
        localized_error = i18n_manager.localize_for_user(user_id, data['error'])
        if localized_error != data['error']:  # If localization found
            data['error'] = localized_error
    
    # Localize success messages
    if 'message' in data and isinstance(data['message'], str):
        localized_message = i18n_manager.localize_for_user(user_id, data['message'])
        if localized_message != data['message']:
            data['message'] = localized_message
    
    # Add language info to response
    data['language'] = getattr(g, 'user_language', 'en')
    
    return jsonify(data), status_code

# Language management endpoints
@app.route('/api/languages', methods=['GET'])
def get_supported_languages():
    """Get list of supported languages"""
    try:
        languages = i18n_manager.get_supported_languages()
        return localized_response({'languages': languages})
        
    except Exception as e:
        logger.error(f"Error in get_supported_languages: {str(e)}")
        return localized_response({'error': 'server_error'}, 500)

@app.route('/api/user/language', methods=['POST'])
@require_auth
def set_user_language():
    """Set user's preferred language"""
    try:
        data = request.get_json()
        
        if not data or 'language' not in data:
            return localized_response({'error': 'missing_language'}, 400)
        
        language = data['language']
        i18n_manager.set_user_language(g.user_id, language)
        
        return localized_response({'message': 'language_updated_successfully'})
        
    except Exception as e:
        logger.error(f"Error in set_user_language: {str(e)}")
        return localized_response({'error': 'server_error'}, 500)

@app.route('/api/user/language', methods=['GET'])
@require_auth
def get_user_language():
    """Get user's current language preference"""
    try:
        user_language = i18n_manager.get_user_language(g.user_id)
        return localized_response({'language': user_language})
        
    except Exception as e:
        logger.error(f"Error in get_user_language: {str(e)}")
        return localized_response({'error': 'server_error'}, 500)

# Enhanced authentication endpoints with i18n
@app.route('/api/auth/register', methods=['POST'])
def register():
    """Register new user with i18n support"""
    try:
        data = request.get_json()
        
        if not data or not all(k in data for k in ['username', 'email', 'password']):
            return localized_response({'error': 'missing_required_fields'}, 400)
        
        username = data['username']
        email = data['email']
        password = data['password']
        role = UserRole(data.get('role', 'user'))
        
        success, result = auth_manager.register_user(username, email, password, role)
        
        if success:
            # Set user's language preference if provided
            if 'language' in data:
                i18n_manager.set_user_language(result, data['language'])
            
            return localized_response({
                'message': 'registration_successful',
                'user_id': result
            }, 201)
        else:
            return localized_response({'error': result}, 400)
            
    except Exception as e:
        logger.error(f"Error in register: {str(e)}")
        return localized_response({'error': 'server_error'}, 500)

@app.route('/api/auth/login', methods=['POST'])
def login():
    """Authenticate user with i18n support"""
    try:
        data = request.get_json()
        
        if not data or not all(k in data for k in ['username', 'password']):
            return localized_response({'error': 'missing_credentials'}, 400)
        
        username = data['username']
        password = data['password']
        ip_address = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
        user_agent = request.headers.get('User-Agent', '')
        
        success, access_token, refresh_token = auth_manager.authenticate_user(
            username, password, ip_address, user_agent
        )
        
        if success:
            # Decode token to get user_id for language setting
            import jwt
            payload = jwt.decode(access_token, auth_manager.jwt_secret, algorithms=[auth_manager.jwt_algorithm])
            user_id = payload['user_id']
            
            # Set user's language preference if provided
            if 'language' in data:
                i18n_manager.set_user_language(user_id, data['language'])
            
            return localized_response({
                'message': 'login_successful',
                'access_token': access_token,
                'refresh_token': refresh_token,
                'token_type': 'Bearer'
            })
        else:
            return localized_response({'error': 'invalid_credentials'}, 401)
            
    except Exception as e:
        logger.error(f"Error in login: {str(e)}")
        return localized_response({'error': 'server_error'}, 500)

# Enhanced chat endpoint with multilingual support
@app.route('/api/chat', methods=['POST'])
@require_auth
def chat():
    """Process chat message with multilingual AI assistant"""
    try:
        data = request.get_json()
        
        if not data or 'message' not in data:
            return localized_response({'error': 'missing_message'}, 400)
        
        user_message = data['message']
        context = data.get('context', {})
        
        # Process user input for language detection and translation
        processed_input, detected_lang = i18n_manager.process_user_input(g.user_id, user_message)
        
        # Add multilingual context
        context.update({
            'user_id': g.user_id,
            'username': g.username,
            'user_language': i18n_manager.get_user_language(g.user_id),
            'detected_language': detected_lang,
            'original_message': user_message,
            'processed_message': processed_input
        })
        
        # Process with AI assistant
        from core_agent import PersonalAIAssistant
        ai_assistant = PersonalAIAssistant()
        
        # Use processed (potentially translated) input for AI
        ai_response = ai_assistant.process_request(g.user_id, processed_input, context)
        
        # Translate AI response back to user's language if needed
        localized_response_text = i18n_manager.process_ai_response(g.user_id, ai_response)
        
        return localized_response({
            'response': localized_response_text,
            'original_response': ai_response if ai_response != localized_response_text else None,
            'detected_language': detected_lang,
            'user_language': i18n_manager.get_user_language(g.user_id),
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error in chat: {str(e)}")
        return localized_response({'error': 'server_error'}, 500)

# Translation endpoint
@app.route('/api/translate', methods=['POST'])
@require_auth
def translate_text():
    """Translate text to user's preferred language"""
    try:
        data = request.get_json()
        
        if not data or 'text' not in data:
            return localized_response({'error': 'missing_text'}, 400)
        
        text = data['text']
        target_lang = data.get('target_language', i18n_manager.get_user_language(g.user_id))
        source_lang = data.get('source_language')
        
        translated_text = i18n_manager.translation_service.translate_text(
            text, target_lang, source_lang
        )
        
        return localized_response({
            'original_text': text,
            'translated_text': translated_text,
            'source_language': source_lang,
            'target_language': target_lang
        })
        
    except Exception as e:
        logger.error(f"Error in translate_text: {str(e)}")
        return localized_response({'error': 'server_error'}, 500)

# Enhanced workflow endpoints with i18n
@app.route('/api/workflows', methods=['GET'])
@require_auth
def get_workflows():
    """Get user's workflows with localized names and descriptions"""
    try:
        from workflow_manager import WorkflowManager
        import redis
        
        redis_client = redis.Redis(host='localhost', port=6379, db=1, decode_responses=True)
        workflow_manager = WorkflowManager(redis_client)
        
        workflows = workflow_manager.list_user_workflows(g.user_id)
        
        # Localize workflow data
        workflows_data = []
        for workflow in workflows:
            # Try to translate workflow name and description
            localized_name = i18n_manager.translate_for_user(g.user_id, workflow.name)
            localized_description = i18n_manager.translate_for_user(g.user_id, workflow.description)
            
            workflows_data.append({
                'id': workflow.id,
                'name': localized_name,
                'description': localized_description,
                'original_name': workflow.name if localized_name != workflow.name else None,
                'status': workflow.status.value,
                'created_at': workflow.created_at.isoformat(),
                'last_run': workflow.last_run.isoformat() if workflow.last_run else None,
                'run_count': workflow.run_count
            })
        
        return localized_response({'workflows': workflows_data})
        
    except Exception as e:
        logger.error(f"Error in get_workflows: {str(e)}")
        return localized_response({'error': 'server_error'}, 500)

# Localization management endpoints (Admin only)
@app.route('/api/admin/translations', methods=['POST'])
@require_auth
def add_translation():
    """Add new translation (Admin only)"""
    try:
        if g.user_role != UserRole.ADMIN:
            return localized_response({'error': 'permission_denied'}, 403)
        
        data = request.get_json()
        
        if not data or not all(k in data for k in ['key', 'language', 'text']):
            return localized_response({'error': 'missing_required_fields'}, 400)
        
        key = data['key']
        language = data['language']
        text = data['text']
        context = data.get('context', '')
        
        i18n_manager.localization_manager.add_translation(key, language, text, context)
        
        return localized_response({'message': 'translation_added_successfully'}, 201)
        
    except Exception as e:
        logger.error(f"Error in add_translation: {str(e)}")
        return localized_response({'error': 'server_error'}, 500)

@app.route('/api/admin/translations/<language>', methods=['GET'])
@require_auth
def get_translations(language):
    """Get all translations for a language (Admin only)"""
    try:
        if g.user_role != UserRole.ADMIN:
            return localized_response({'error': 'permission_denied'}, 403)
        
        translations = i18n_manager.localization_manager.translations.get(language, {})
        
        return localized_response({
            'language': language,
            'translations': translations,
            'count': len(translations)
        })
        
    except Exception as e:
        logger.error(f"Error in get_translations: {str(e)}")
        return localized_response({'error': 'server_error'}, 500)

# Health check with i18n
@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint with language info"""
    user_language = getattr(g, 'user_language', 'en')
    
    return localized_response({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '2.1.0',
        'i18n_enabled': True,
        'supported_languages': len(i18n_manager.get_supported_languages())
    })

# User profile with language preference
@app.route('/api/user/profile', methods=['GET'])
@require_auth
def get_user_profile():
    """Get user profile with language preference"""
    try:
        user_language = i18n_manager.get_user_language(g.user_id)
        
        return localized_response({
            'user_id': g.user_id,
            'username': g.username,
            'role': g.user_role.value,
            'language': user_language,
            'supported_languages': i18n_manager.get_supported_languages()
        })
        
    except Exception as e:
        logger.error(f"Error in get_user_profile: {str(e)}")
        return localized_response({'error': 'server_error'}, 500)

# Error handlers with i18n
@app.errorhandler(404)
def not_found(error):
    return localized_response({'error': 'not_found'}, 404)

@app.errorhandler(405)
def method_not_allowed(error):
    return localized_response({'error': 'method_not_allowed'}, 405)

@app.errorhandler(500)
def internal_error(error):
    return localized_response({'error': 'server_error'}, 500)

if __name__ == '__main__':
    # Initialize systems
    from security_manager import initialize_security
    from i18n_manager import initialize_i18n
    
    initialize_security()
    initialize_i18n()
    
    logger.info("Starting Multilingual AI Assistant API")
    
    # Run the multilingual API
    app.run(host='0.0.0.0', port=5000, debug=False)

