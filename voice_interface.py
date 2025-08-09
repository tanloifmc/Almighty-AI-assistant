"""
Voice Interface for AI Assistant
Handles Speech-to-Text and Text-to-Speech functionality
"""

import os
import io
import logging
import tempfile
import base64
from typing import Dict, Any, Optional, Tuple, List
from dataclasses import dataclass
from enum import Enum
import json
import redis
import speech_recognition as sr
from pydub import AudioSegment
from pydub.playback import play
import threading
import queue
import time
from datetime import datetime

logger = logging.getLogger(__name__)

class VoiceLanguage(Enum):
    ENGLISH = "en-US"
    VIETNAMESE = "vi-VN"
    CHINESE = "zh-CN"
    JAPANESE = "ja-JP"
    KOREAN = "ko-KR"
    SPANISH = "es-ES"
    FRENCH = "fr-FR"
    GERMAN = "de-DE"
    ITALIAN = "it-IT"
    PORTUGUESE = "pt-PT"
    RUSSIAN = "ru-RU"
    ARABIC = "ar-SA"
    HINDI = "hi-IN"
    THAI = "th-TH"

class VoiceGender(Enum):
    MALE = "male"
    FEMALE = "female"
    NEUTRAL = "neutral"

@dataclass
class VoiceSettings:
    language: VoiceLanguage
    gender: VoiceGender
    speed: float = 1.0  # 0.5 to 2.0
    pitch: float = 1.0  # 0.5 to 2.0
    volume: float = 1.0  # 0.0 to 1.0

@dataclass
class AudioData:
    data: bytes
    format: str
    sample_rate: int
    channels: int
    duration: float

class SpeechToTextEngine:
    """Handles speech recognition using multiple engines"""
    
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.microphone = None
        self.redis_client = redis.Redis(host='localhost', port=6379, db=6, decode_responses=True)
        
        # Configure recognizer settings
        self.recognizer.energy_threshold = 300
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.pause_threshold = 0.8
        self.recognizer.operation_timeout = None
        self.recognizer.phrase_threshold = 0.3
        self.recognizer.non_speaking_duration = 0.8
        
        # Initialize microphone if available
        try:
            self.microphone = sr.Microphone()
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source)
            logger.info("Microphone initialized successfully")
        except Exception as e:
            logger.warning(f"Microphone not available: {str(e)}")
    
    def transcribe_audio_file(self, audio_file_path: str, language: str = "en-US") -> Tuple[bool, str]:
        """Transcribe audio file to text"""
        try:
            with sr.AudioFile(audio_file_path) as source:
                audio = self.recognizer.record(source)
            
            # Try Google Speech Recognition first
            try:
                text = self.recognizer.recognize_google(audio, language=language)
                return True, text
            except sr.UnknownValueError:
                return False, "Could not understand audio"
            except sr.RequestError as e:
                logger.error(f"Google Speech Recognition error: {e}")
                
                # Fallback to offline recognition
                try:
                    text = self.recognizer.recognize_sphinx(audio)
                    return True, text
                except:
                    return False, "Speech recognition failed"
                    
        except Exception as e:
            logger.error(f"Error transcribing audio file: {str(e)}")
            return False, f"Error: {str(e)}"
    
    def transcribe_audio_data(self, audio_data: bytes, language: str = "en-US") -> Tuple[bool, str]:
        """Transcribe audio data to text"""
        try:
            # Save audio data to temporary file
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                temp_file.write(audio_data)
                temp_file_path = temp_file.name
            
            try:
                result = self.transcribe_audio_file(temp_file_path, language)
                return result
            finally:
                os.unlink(temp_file_path)
                
        except Exception as e:
            logger.error(f"Error transcribing audio data: {str(e)}")
            return False, f"Error: {str(e)}"
    
    def listen_continuously(self, callback, language: str = "en-US", timeout: int = None):
        """Listen continuously for speech and call callback with transcribed text"""
        if not self.microphone:
            logger.error("Microphone not available for continuous listening")
            return
        
        def listen_worker():
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source)
            
            stop_listening = self.recognizer.listen_in_background(
                self.microphone, 
                lambda recognizer, audio: self._process_audio_background(recognizer, audio, callback, language),
                phrase_time_limit=5
            )
            
            if timeout:
                time.sleep(timeout)
                stop_listening(wait_for_stop=False)
            
            return stop_listening
        
        return listen_worker()
    
    def _process_audio_background(self, recognizer, audio, callback, language):
        """Process audio in background thread"""
        try:
            text = recognizer.recognize_google(audio, language=language)
            callback(True, text)
        except sr.UnknownValueError:
            callback(False, "Could not understand audio")
        except sr.RequestError as e:
            callback(False, f"Recognition error: {e}")

class TextToSpeechEngine:
    """Handles text-to-speech conversion"""
    
    def __init__(self):
        self.redis_client = redis.Redis(host='localhost', port=6379, db=6, decode_responses=True)
        self.cache_enabled = True
        
        # Default voice settings
        self.default_settings = VoiceSettings(
            language=VoiceLanguage.ENGLISH,
            gender=VoiceGender.FEMALE,
            speed=1.0,
            pitch=1.0,
            volume=1.0
        )
    
    def synthesize_speech(self, text: str, settings: VoiceSettings = None, output_file: str = None) -> Tuple[bool, str]:
        """Convert text to speech"""
        if not settings:
            settings = self.default_settings
        
        try:
            # Check cache first
            if self.cache_enabled:
                cached_audio = self._get_cached_audio(text, settings)
                if cached_audio and output_file:
                    with open(output_file, 'wb') as f:
                        f.write(base64.b64decode(cached_audio))
                    return True, output_file
            
            # Use the media_generate_speech tool for actual TTS
            if not output_file:
                output_file = tempfile.mktemp(suffix=".wav")
            
            # Import the media generation function
            from media_generate_speech import media_generate_speech
            
            # Determine voice type based on gender
            voice_type = "female_voice" if settings.gender == VoiceGender.FEMALE else "male_voice"
            
            # Generate speech
            result = media_generate_speech(
                brief="Generate speech for voice interface",
                path=output_file,
                text=text,
                voice=voice_type
            )
            
            if result and os.path.exists(output_file):
                # Cache the result
                if self.cache_enabled:
                    with open(output_file, 'rb') as f:
                        audio_data = f.read()
                    self._cache_audio(text, settings, audio_data)
                
                return True, output_file
            else:
                return False, "Speech synthesis failed"
                
        except Exception as e:
            logger.error(f"Error synthesizing speech: {str(e)}")
            return False, f"Error: {str(e)}"
    
    def synthesize_speech_stream(self, text: str, settings: VoiceSettings = None) -> Tuple[bool, bytes]:
        """Convert text to speech and return audio data"""
        success, output_file = self.synthesize_speech(text, settings)
        
        if success:
            try:
                with open(output_file, 'rb') as f:
                    audio_data = f.read()
                os.unlink(output_file)
                return True, audio_data
            except Exception as e:
                logger.error(f"Error reading audio file: {str(e)}")
                return False, b""
        
        return False, b""
    
    def _get_cached_audio(self, text: str, settings: VoiceSettings) -> Optional[str]:
        """Get cached audio data"""
        cache_key = self._generate_cache_key(text, settings)
        return self.redis_client.get(cache_key)
    
    def _cache_audio(self, text: str, settings: VoiceSettings, audio_data: bytes):
        """Cache audio data"""
        cache_key = self._generate_cache_key(text, settings)
        audio_b64 = base64.b64encode(audio_data).decode()
        # Cache for 24 hours
        self.redis_client.setex(cache_key, 86400, audio_b64)
    
    def _generate_cache_key(self, text: str, settings: VoiceSettings) -> str:
        """Generate cache key for audio"""
        import hashlib
        
        text_hash = hashlib.md5(text.encode()).hexdigest()
        settings_str = f"{settings.language.value}_{settings.gender.value}_{settings.speed}_{settings.pitch}"
        return f"tts:{text_hash}_{settings_str}"

class VoiceConversationManager:
    """Manages voice conversations with the AI assistant"""
    
    def __init__(self):
        self.stt_engine = SpeechToTextEngine()
        self.tts_engine = TextToSpeechEngine()
        self.redis_client = redis.Redis(host='localhost', port=6379, db=6, decode_responses=True)
        
        self.conversation_active = False
        self.user_settings = {}
        self.conversation_history = []
    
    def start_voice_conversation(self, user_id: str, language: str = "en-US") -> Dict[str, Any]:
        """Start a voice conversation session"""
        try:
            # Get user voice settings
            settings = self._get_user_voice_settings(user_id)
            
            # Initialize conversation
            self.conversation_active = True
            self.conversation_history = []
            
            # Store session info
            session_data = {
                'user_id': user_id,
                'language': language,
                'started_at': datetime.now().isoformat(),
                'status': 'active'
            }
            
            self.redis_client.hset(f"voice_session:{user_id}", mapping=session_data)
            
            # Generate welcome message
            welcome_text = self._get_welcome_message(language)
            success, audio_file = self.tts_engine.synthesize_speech(welcome_text, settings)
            
            return {
                'success': True,
                'session_id': user_id,
                'welcome_audio': audio_file if success else None,
                'welcome_text': welcome_text,
                'language': language,
                'settings': settings.__dict__
            }
            
        except Exception as e:
            logger.error(f"Error starting voice conversation: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def process_voice_input(self, user_id: str, audio_data: bytes) -> Dict[str, Any]:
        """Process voice input and return AI response"""
        try:
            # Get session info
            session_data = self.redis_client.hgetall(f"voice_session:{user_id}")
            if not session_data:
                return {'success': False, 'error': 'No active voice session'}
            
            language = session_data.get('language', 'en-US')
            settings = self._get_user_voice_settings(user_id)
            
            # Transcribe speech to text
            success, transcribed_text = self.stt_engine.transcribe_audio_data(audio_data, language)
            
            if not success:
                return {
                    'success': False,
                    'error': transcribed_text,
                    'transcribed_text': None
                }
            
            # Process with AI assistant
            from core_agent import PersonalAIAssistant
            ai_assistant = PersonalAIAssistant()
            
            context = {
                'user_id': user_id,
                'voice_mode': True,
                'language': language,
                'conversation_history': self.conversation_history[-5:]  # Last 5 exchanges
            }
            
            ai_response = ai_assistant.process_request(user_id, transcribed_text, context)
            
            # Convert AI response to speech
            tts_success, response_audio = self.tts_engine.synthesize_speech(ai_response, settings)
            
            # Update conversation history
            self.conversation_history.append({
                'timestamp': datetime.now().isoformat(),
                'user_input': transcribed_text,
                'ai_response': ai_response
            })
            
            # Store conversation in Redis
            self._store_conversation_turn(user_id, transcribed_text, ai_response)
            
            return {
                'success': True,
                'transcribed_text': transcribed_text,
                'ai_response': ai_response,
                'response_audio': response_audio if tts_success else None,
                'conversation_id': len(self.conversation_history)
            }
            
        except Exception as e:
            logger.error(f"Error processing voice input: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def end_voice_conversation(self, user_id: str) -> Dict[str, Any]:
        """End voice conversation session"""
        try:
            # Get session data
            session_data = self.redis_client.hgetall(f"voice_session:{user_id}")
            
            if session_data:
                # Update session status
                session_data['status'] = 'ended'
                session_data['ended_at'] = datetime.now().isoformat()
                self.redis_client.hset(f"voice_session:{user_id}", mapping=session_data)
                
                # Generate goodbye message
                language = session_data.get('language', 'en-US')
                goodbye_text = self._get_goodbye_message(language)
                settings = self._get_user_voice_settings(user_id)
                
                success, audio_file = self.tts_engine.synthesize_speech(goodbye_text, settings)
                
                # Store conversation summary
                self._store_conversation_summary(user_id)
                
                self.conversation_active = False
                
                return {
                    'success': True,
                    'goodbye_audio': audio_file if success else None,
                    'goodbye_text': goodbye_text,
                    'conversation_turns': len(self.conversation_history),
                    'duration': self._calculate_session_duration(session_data)
                }
            
            return {'success': True, 'message': 'No active session to end'}
            
        except Exception as e:
            logger.error(f"Error ending voice conversation: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def set_user_voice_settings(self, user_id: str, settings: Dict[str, Any]) -> bool:
        """Set user voice preferences"""
        try:
            # Validate settings
            voice_settings = VoiceSettings(
                language=VoiceLanguage(settings.get('language', 'en-US')),
                gender=VoiceGender(settings.get('gender', 'female')),
                speed=float(settings.get('speed', 1.0)),
                pitch=float(settings.get('pitch', 1.0)),
                volume=float(settings.get('volume', 1.0))
            )
            
            # Store in Redis
            settings_data = {
                'language': voice_settings.language.value,
                'gender': voice_settings.gender.value,
                'speed': str(voice_settings.speed),
                'pitch': str(voice_settings.pitch),
                'volume': str(voice_settings.volume),
                'updated_at': datetime.now().isoformat()
            }
            
            self.redis_client.hset(f"voice_settings:{user_id}", mapping=settings_data)
            self.user_settings[user_id] = voice_settings
            
            return True
            
        except Exception as e:
            logger.error(f"Error setting user voice settings: {str(e)}")
            return False
    
    def _get_user_voice_settings(self, user_id: str) -> VoiceSettings:
        """Get user voice settings"""
        if user_id in self.user_settings:
            return self.user_settings[user_id]
        
        # Load from Redis
        settings_data = self.redis_client.hgetall(f"voice_settings:{user_id}")
        
        if settings_data:
            try:
                voice_settings = VoiceSettings(
                    language=VoiceLanguage(settings_data['language']),
                    gender=VoiceGender(settings_data['gender']),
                    speed=float(settings_data['speed']),
                    pitch=float(settings_data['pitch']),
                    volume=float(settings_data['volume'])
                )
                self.user_settings[user_id] = voice_settings
                return voice_settings
            except:
                pass
        
        # Return default settings
        return self.tts_engine.default_settings
    
    def _get_welcome_message(self, language: str) -> str:
        """Get welcome message in specified language"""
        messages = {
            'en-US': "Hello! I'm your AI assistant. How can I help you today?",
            'vi-VN': "Xin chào! Tôi là trợ lý AI của bạn. Tôi có thể giúp gì cho bạn hôm nay?",
            'zh-CN': "您好！我是您的AI助手。今天我能为您做些什么？",
            'ja-JP': "こんにちは！私はあなたのAIアシスタントです。今日はどのようにお手伝いできますか？",
            'ko-KR': "안녕하세요! 저는 당신의 AI 어시스턴트입니다. 오늘 어떻게 도와드릴까요?",
            'es-ES': "¡Hola! Soy tu asistente de IA. ¿Cómo puedo ayudarte hoy?",
            'fr-FR': "Bonjour! Je suis votre assistant IA. Comment puis-je vous aider aujourd'hui?",
            'de-DE': "Hallo! Ich bin Ihr KI-Assistent. Wie kann ich Ihnen heute helfen?",
        }
        return messages.get(language, messages['en-US'])
    
    def _get_goodbye_message(self, language: str) -> str:
        """Get goodbye message in specified language"""
        messages = {
            'en-US': "Thank you for using the voice assistant. Have a great day!",
            'vi-VN': "Cảm ơn bạn đã sử dụng trợ lý giọng nói. Chúc bạn một ngày tốt lành!",
            'zh-CN': "感谢您使用语音助手。祝您有美好的一天！",
            'ja-JP': "音声アシスタントをご利用いただき、ありがとうございました。良い一日をお過ごしください！",
            'ko-KR': "음성 어시스턴트를 사용해 주셔서 감사합니다. 좋은 하루 되세요!",
            'es-ES': "Gracias por usar el asistente de voz. ¡Que tengas un gran día!",
            'fr-FR': "Merci d'avoir utilisé l'assistant vocal. Passez une excellente journée!",
            'de-DE': "Vielen Dank für die Nutzung des Sprachassistenten. Haben Sie einen schönen Tag!",
        }
        return messages.get(language, messages['en-US'])
    
    def _store_conversation_turn(self, user_id: str, user_input: str, ai_response: str):
        """Store conversation turn in Redis"""
        turn_data = {
            'user_input': user_input,
            'ai_response': ai_response,
            'timestamp': datetime.now().isoformat()
        }
        
        self.redis_client.lpush(f"voice_conversation:{user_id}", json.dumps(turn_data))
        self.redis_client.ltrim(f"voice_conversation:{user_id}", 0, 99)  # Keep last 100 turns
    
    def _store_conversation_summary(self, user_id: str):
        """Store conversation summary"""
        summary_data = {
            'user_id': user_id,
            'total_turns': len(self.conversation_history),
            'started_at': self.redis_client.hget(f"voice_session:{user_id}", 'started_at'),
            'ended_at': datetime.now().isoformat(),
            'conversation_history': json.dumps(self.conversation_history)
        }
        
        self.redis_client.hset(f"voice_summary:{user_id}:{int(time.time())}", mapping=summary_data)
    
    def _calculate_session_duration(self, session_data: Dict[str, str]) -> str:
        """Calculate session duration"""
        try:
            start_time = datetime.fromisoformat(session_data['started_at'])
            end_time = datetime.now()
            duration = end_time - start_time
            
            minutes = int(duration.total_seconds() // 60)
            seconds = int(duration.total_seconds() % 60)
            
            return f"{minutes}m {seconds}s"
        except:
            return "Unknown"

# Global voice interface instance
voice_manager = VoiceConversationManager()

def initialize_voice_interface():
    """Initialize voice interface system"""
    logger.info("Voice interface system initialized")

if __name__ == '__main__':
    initialize_voice_interface()

