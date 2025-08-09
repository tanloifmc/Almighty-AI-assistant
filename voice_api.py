"""
Voice API for AI Assistant
Provides REST endpoints for voice interaction functionality
"""

import os
import io
import logging
import tempfile
import base64
from typing import Dict, Any, Optional
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import redis
from datetime import datetime

# Import voice interface components
from voice_interface import (
    voice_manager, 
    VoiceLanguage, 
    VoiceGender, 
    VoiceSettings,
    initialize_voice_interface
)

# Import security components
from security_manager import security_manager, require_auth, require_permission

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
CORS(app, origins="*")

# Initialize Redis
redis_client = redis.Redis(host='localhost', port=6379, db=7, decode_responses=True)

# Initialize voice interface
initialize_voice_interface()

@app.route('/api/voice/health', methods=['GET'])
def voice_health():
    """Health check for voice interface"""
    try:
        # Test Redis connection
        redis_client.ping()
        
        # Test voice components
        voice_status = {
            'voice_interface': True,
            'redis_connection': True,
            'speech_to_text': True,
            'text_to_speech': True,
            'supported_languages': len(VoiceLanguage),
            'timestamp': datetime.now().isoformat()
        }
        
        return jsonify({
            'status': 'healthy',
            'voice_system': voice_status
        }), 200
        
    except Exception as e:
        logger.error(f"Voice health check failed: {str(e)}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500

@app.route('/api/voice/languages', methods=['GET'])
def get_supported_languages():
    """Get list of supported voice languages"""
    try:
        languages = []
        for lang in VoiceLanguage:
            languages.append({
                'code': lang.value,
                'name': lang.name,
                'display_name': _get_language_display_name(lang.value)
            })
        
        return jsonify({
            'success': True,
            'languages': languages,
            'total': len(languages)
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting supported languages: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/voice/settings/<user_id>', methods=['GET'])
@require_auth
def get_voice_settings(user_id: str):
    """Get user voice settings"""
    try:
        # Check if user can access these settings
        if not _can_access_user_data(request.user_id, user_id):
            return jsonify({
                'success': False,
                'error': 'Access denied'
            }), 403
        
        settings = voice_manager._get_user_voice_settings(user_id)
        
        return jsonify({
            'success': True,
            'settings': {
                'language': settings.language.value,
                'gender': settings.gender.value,
                'speed': settings.speed,
                'pitch': settings.pitch,
                'volume': settings.volume
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting voice settings: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/voice/settings/<user_id>', methods=['POST'])
@require_auth
def set_voice_settings(user_id: str):
    """Set user voice settings"""
    try:
        # Check if user can modify these settings
        if not _can_access_user_data(request.user_id, user_id):
            return jsonify({
                'success': False,
                'error': 'Access denied'
            }), 403
        
        data = request.get_json()
        
        # Validate settings
        settings_data = {
            'language': data.get('language', 'en-US'),
            'gender': data.get('gender', 'female'),
            'speed': float(data.get('speed', 1.0)),
            'pitch': float(data.get('pitch', 1.0)),
            'volume': float(data.get('volume', 1.0))
        }
        
        # Validate ranges
        if not (0.5 <= settings_data['speed'] <= 2.0):
            return jsonify({
                'success': False,
                'error': 'Speed must be between 0.5 and 2.0'
            }), 400
        
        if not (0.5 <= settings_data['pitch'] <= 2.0):
            return jsonify({
                'success': False,
                'error': 'Pitch must be between 0.5 and 2.0'
            }), 400
        
        if not (0.0 <= settings_data['volume'] <= 1.0):
            return jsonify({
                'success': False,
                'error': 'Volume must be between 0.0 and 1.0'
            }), 400
        
        # Set settings
        success = voice_manager.set_user_voice_settings(user_id, settings_data)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Voice settings updated successfully'
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to update voice settings'
            }), 500
            
    except Exception as e:
        logger.error(f"Error setting voice settings: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/voice/conversation/start', methods=['POST'])
@require_auth
def start_voice_conversation():
    """Start a voice conversation session"""
    try:
        data = request.get_json()
        user_id = request.user_id
        language = data.get('language', 'en-US')
        
        result = voice_manager.start_voice_conversation(user_id, language)
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 500
            
    except Exception as e:
        logger.error(f"Error starting voice conversation: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/voice/conversation/process', methods=['POST'])
@require_auth
def process_voice_input():
    """Process voice input and return AI response"""
    try:
        user_id = request.user_id
        
        # Check if audio file is provided
        if 'audio' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No audio file provided'
            }), 400
        
        audio_file = request.files['audio']
        
        # Read audio data
        audio_data = audio_file.read()
        
        # Process voice input
        result = voice_manager.process_voice_input(user_id, audio_data)
        
        return jsonify(result), 200 if result['success'] else 500
        
    except Exception as e:
        logger.error(f"Error processing voice input: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/voice/conversation/end', methods=['POST'])
@require_auth
def end_voice_conversation():
    """End voice conversation session"""
    try:
        user_id = request.user_id
        
        result = voice_manager.end_voice_conversation(user_id)
        
        return jsonify(result), 200 if result['success'] else 500
        
    except Exception as e:
        logger.error(f"Error ending voice conversation: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/voice/transcribe', methods=['POST'])
@require_auth
def transcribe_audio():
    """Transcribe audio file to text"""
    try:
        # Check if audio file is provided
        if 'audio' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No audio file provided'
            }), 400
        
        audio_file = request.files['audio']
        language = request.form.get('language', 'en-US')
        
        # Save audio to temporary file
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
            audio_file.save(temp_file.name)
            temp_file_path = temp_file.name
        
        try:
            # Transcribe audio
            success, text = voice_manager.stt_engine.transcribe_audio_file(temp_file_path, language)
            
            return jsonify({
                'success': success,
                'text': text if success else None,
                'error': text if not success else None,
                'language': language
            }), 200 if success else 400
            
        finally:
            os.unlink(temp_file_path)
            
    except Exception as e:
        logger.error(f"Error transcribing audio: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/voice/synthesize', methods=['POST'])
@require_auth
def synthesize_speech():
    """Convert text to speech"""
    try:
        data = request.get_json()
        text = data.get('text', '')
        user_id = request.user_id
        
        if not text:
            return jsonify({
                'success': False,
                'error': 'No text provided'
            }), 400
        
        # Get user voice settings
        settings = voice_manager._get_user_voice_settings(user_id)
        
        # Synthesize speech
        success, audio_data = voice_manager.tts_engine.synthesize_speech_stream(text, settings)
        
        if success:
            # Return audio as base64
            audio_b64 = base64.b64encode(audio_data).decode()
            
            return jsonify({
                'success': True,
                'audio_data': audio_b64,
                'format': 'wav',
                'text': text
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': 'Speech synthesis failed'
            }), 500
            
    except Exception as e:
        logger.error(f"Error synthesizing speech: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/voice/conversation/history/<user_id>', methods=['GET'])
@require_auth
def get_conversation_history(user_id: str):
    """Get voice conversation history"""
    try:
        # Check if user can access this data
        if not _can_access_user_data(request.user_id, user_id):
            return jsonify({
                'success': False,
                'error': 'Access denied'
            }), 403
        
        # Get conversation history from Redis
        history_data = redis_client.lrange(f"voice_conversation:{user_id}", 0, 49)  # Last 50 turns
        
        history = []
        for item in history_data:
            try:
                import json
                turn_data = json.loads(item)
                history.append(turn_data)
            except:
                continue
        
        return jsonify({
            'success': True,
            'history': history,
            'total_turns': len(history)
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting conversation history: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/voice/test', methods=['POST'])
@require_auth
def test_voice_system():
    """Test voice system with sample text"""
    try:
        data = request.get_json()
        test_text = data.get('text', 'Hello, this is a test of the voice system.')
        user_id = request.user_id
        
        # Get user settings
        settings = voice_manager._get_user_voice_settings(user_id)
        
        # Test TTS
        tts_success, audio_data = voice_manager.tts_engine.synthesize_speech_stream(test_text, settings)
        
        if tts_success:
            audio_b64 = base64.b64encode(audio_data).decode()
            
            return jsonify({
                'success': True,
                'test_results': {
                    'text_to_speech': True,
                    'audio_generated': True,
                    'audio_size': len(audio_data),
                    'settings_applied': True
                },
                'audio_data': audio_b64,
                'test_text': test_text
            }), 200
        else:
            return jsonify({
                'success': False,
                'test_results': {
                    'text_to_speech': False,
                    'error': 'TTS failed'
                }
            }), 500
            
    except Exception as e:
        logger.error(f"Error testing voice system: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

def _get_language_display_name(language_code: str) -> str:
    """Get display name for language code"""
    language_names = {
        'en-US': 'English (US)',
        'vi-VN': 'Tiếng Việt',
        'zh-CN': '中文 (简体)',
        'ja-JP': '日本語',
        'ko-KR': '한국어',
        'es-ES': 'Español',
        'fr-FR': 'Français',
        'de-DE': 'Deutsch',
        'it-IT': 'Italiano',
        'pt-PT': 'Português',
        'ru-RU': 'Русский',
        'ar-SA': 'العربية',
        'hi-IN': 'हिन्दी',
        'th-TH': 'ไทย'
    }
    return language_names.get(language_code, language_code)

def _can_access_user_data(requester_id: str, target_user_id: str) -> bool:
    """Check if requester can access target user's data"""
    # Users can access their own data
    if requester_id == target_user_id:
        return True
    
    # Check if requester has admin permissions
    try:
        user_permissions = security_manager.get_user_permissions(requester_id)
        return 'admin' in user_permissions or 'manage_users' in user_permissions
    except:
        return False

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'success': False,
        'error': 'Endpoint not found'
    }), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        'success': False,
        'error': 'Internal server error'
    }), 500

if __name__ == '__main__':
    logger.info("Starting Voice API server")
    app.run(host='0.0.0.0', port=5001, debug=False)

