"""
Internationalization (i18n) Manager for AI Assistant
Handles multi-language support for the entire system
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import redis
from googletrans import Translator
from langdetect import detect, DetectorFactory
from babel import Locale
from babel.dates import format_datetime
from babel.numbers import format_currency
import re

# Set seed for consistent language detection
DetectorFactory.seed = 0

logger = logging.getLogger(__name__)

class SupportedLanguage(Enum):
    ENGLISH = "en"
    VIETNAMESE = "vi"
    CHINESE_SIMPLIFIED = "zh-cn"
    CHINESE_TRADITIONAL = "zh-tw"
    JAPANESE = "ja"
    KOREAN = "ko"
    SPANISH = "es"
    FRENCH = "fr"
    GERMAN = "de"
    ITALIAN = "it"
    PORTUGUESE = "pt"
    RUSSIAN = "ru"
    ARABIC = "ar"
    HINDI = "hi"
    THAI = "th"
    INDONESIAN = "id"
    MALAY = "ms"

@dataclass
class TranslationEntry:
    key: str
    language: str
    text: str
    context: str = ""
    created_at: str = ""
    updated_at: str = ""

class LanguageDetector:
    """Detects language of input text"""
    
    def __init__(self):
        self.confidence_threshold = 0.8
    
    def detect_language(self, text: str) -> Tuple[str, float]:
        """Detect language of text with confidence score"""
        try:
            # Clean text for better detection
            cleaned_text = self._clean_text(text)
            
            if len(cleaned_text) < 3:
                return "en", 0.5  # Default to English for very short text
            
            detected_lang = detect(cleaned_text)
            
            # Map some common language codes
            lang_mapping = {
                'zh-cn': 'zh',
                'zh-tw': 'zh',
            }
            
            detected_lang = lang_mapping.get(detected_lang, detected_lang)
            
            # Calculate confidence based on text length and content
            confidence = self._calculate_confidence(cleaned_text, detected_lang)
            
            return detected_lang, confidence
            
        except Exception as e:
            logger.warning(f"Language detection failed: {str(e)}")
            return "en", 0.5  # Default to English
    
    def _clean_text(self, text: str) -> str:
        """Clean text for better language detection"""
        # Remove URLs, emails, numbers, and special characters
        text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)
        text = re.sub(r'\S+@\S+', '', text)
        text = re.sub(r'\d+', '', text)
        text = re.sub(r'[^\w\s]', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def _calculate_confidence(self, text: str, detected_lang: str) -> float:
        """Calculate confidence score for language detection"""
        base_confidence = 0.7
        
        # Increase confidence for longer text
        if len(text) > 50:
            base_confidence += 0.1
        if len(text) > 100:
            base_confidence += 0.1
        
        # Language-specific confidence adjustments
        if detected_lang in ['vi', 'zh', 'ja', 'ko', 'ar', 'hi', 'th']:
            # These languages have distinctive characters
            base_confidence += 0.1
        
        return min(base_confidence, 1.0)

class TranslationService:
    """Handles text translation using Google Translate"""
    
    def __init__(self):
        self.translator = Translator()
        self.cache_enabled = True
        self.redis_client = redis.Redis(host='localhost', port=6379, db=5, decode_responses=True)
    
    def translate_text(self, text: str, target_lang: str, source_lang: str = None) -> str:
        """Translate text to target language"""
        try:
            # Check cache first
            if self.cache_enabled:
                cached_translation = self._get_cached_translation(text, target_lang, source_lang)
                if cached_translation:
                    return cached_translation
            
            # Perform translation
            if source_lang:
                result = self.translator.translate(text, src=source_lang, dest=target_lang)
            else:
                result = self.translator.translate(text, dest=target_lang)
            
            translated_text = result.text
            
            # Cache the translation
            if self.cache_enabled:
                self._cache_translation(text, target_lang, source_lang, translated_text)
            
            return translated_text
            
        except Exception as e:
            logger.error(f"Translation failed: {str(e)}")
            return text  # Return original text if translation fails
    
    def translate_batch(self, texts: List[str], target_lang: str, source_lang: str = None) -> List[str]:
        """Translate multiple texts efficiently"""
        translations = []
        
        for text in texts:
            translation = self.translate_text(text, target_lang, source_lang)
            translations.append(translation)
        
        return translations
    
    def _get_cached_translation(self, text: str, target_lang: str, source_lang: str = None) -> Optional[str]:
        """Get cached translation"""
        cache_key = self._generate_cache_key(text, target_lang, source_lang)
        return self.redis_client.get(cache_key)
    
    def _cache_translation(self, text: str, target_lang: str, source_lang: str, translation: str):
        """Cache translation result"""
        cache_key = self._generate_cache_key(text, target_lang, source_lang)
        # Cache for 7 days
        self.redis_client.setex(cache_key, 604800, translation)
    
    def _generate_cache_key(self, text: str, target_lang: str, source_lang: str = None) -> str:
        """Generate cache key for translation"""
        import hashlib
        
        text_hash = hashlib.md5(text.encode()).hexdigest()
        source_part = f"_{source_lang}" if source_lang else ""
        return f"translation:{text_hash}{source_part}_{target_lang}"

class LocalizationManager:
    """Manages localized strings and formatting"""
    
    def __init__(self):
        self.translations: Dict[str, Dict[str, str]] = {}
        self.default_language = SupportedLanguage.ENGLISH.value
        self.fallback_language = SupportedLanguage.ENGLISH.value
        self.redis_client = redis.Redis(host='localhost', port=6379, db=5, decode_responses=True)
        
        # Load default translations
        self._load_default_translations()
    
    def get_text(self, key: str, language: str, **kwargs) -> str:
        """Get localized text for a key"""
        # Try to get from cache first
        cached_text = self._get_cached_localization(key, language)
        if cached_text:
            return self._format_text(cached_text, **kwargs)
        
        # Try to get from loaded translations
        if language in self.translations and key in self.translations[language]:
            text = self.translations[language][key]
        elif self.fallback_language in self.translations and key in self.translations[self.fallback_language]:
            text = self.translations[self.fallback_language][key]
        else:
            # Return the key itself if no translation found
            text = key
        
        # Cache the result
        self._cache_localization(key, language, text)
        
        return self._format_text(text, **kwargs)
    
    def add_translation(self, key: str, language: str, text: str, context: str = ""):
        """Add or update a translation"""
        if language not in self.translations:
            self.translations[language] = {}
        
        self.translations[language][key] = text
        
        # Store in Redis for persistence
        translation_entry = TranslationEntry(
            key=key,
            language=language,
            text=text,
            context=context,
            created_at=str(int(time.time())),
            updated_at=str(int(time.time()))
        )
        
        self._store_translation(translation_entry)
    
    def get_supported_languages(self) -> List[Dict[str, str]]:
        """Get list of supported languages"""
        languages = []
        for lang in SupportedLanguage:
            locale = Locale.parse(lang.value)
            languages.append({
                'code': lang.value,
                'name': locale.display_name,
                'native_name': locale.get_display_name(lang.value)
            })
        return languages
    
    def format_datetime(self, dt, language: str, format: str = 'medium') -> str:
        """Format datetime according to locale"""
        try:
            locale = Locale.parse(language)
            return format_datetime(dt, format=format, locale=locale)
        except:
            return str(dt)
    
    def format_currency(self, amount: float, currency: str, language: str) -> str:
        """Format currency according to locale"""
        try:
            locale = Locale.parse(language)
            return format_currency(amount, currency, locale=locale)
        except:
            return f"{amount} {currency}"
    
    def _format_text(self, text: str, **kwargs) -> str:
        """Format text with variables"""
        try:
            return text.format(**kwargs)
        except:
            return text
    
    def _get_cached_localization(self, key: str, language: str) -> Optional[str]:
        """Get cached localization"""
        cache_key = f"localization:{language}:{key}"
        return self.redis_client.get(cache_key)
    
    def _cache_localization(self, key: str, language: str, text: str):
        """Cache localization result"""
        cache_key = f"localization:{language}:{key}"
        # Cache for 1 day
        self.redis_client.setex(cache_key, 86400, text)
    
    def _store_translation(self, entry: TranslationEntry):
        """Store translation in Redis"""
        key = f"translation:{entry.language}:{entry.key}"
        data = {
            'text': entry.text,
            'context': entry.context,
            'created_at': entry.created_at,
            'updated_at': entry.updated_at
        }
        self.redis_client.hset(key, mapping=data)
    
    def _load_default_translations(self):
        """Load default translations for common UI elements"""
        import time
        
        default_translations = {
            'en': {
                'welcome': 'Welcome to AI Assistant',
                'login': 'Login',
                'logout': 'Logout',
                'register': 'Register',
                'username': 'Username',
                'password': 'Password',
                'email': 'Email',
                'submit': 'Submit',
                'cancel': 'Cancel',
                'save': 'Save',
                'delete': 'Delete',
                'edit': 'Edit',
                'create': 'Create',
                'search': 'Search',
                'loading': 'Loading...',
                'error': 'Error',
                'success': 'Success',
                'warning': 'Warning',
                'info': 'Information',
                'yes': 'Yes',
                'no': 'No',
                'ok': 'OK',
                'close': 'Close',
                'back': 'Back',
                'next': 'Next',
                'previous': 'Previous',
                'home': 'Home',
                'dashboard': 'Dashboard',
                'settings': 'Settings',
                'profile': 'Profile',
                'help': 'Help',
                'about': 'About',
                'contact': 'Contact',
                'privacy': 'Privacy',
                'terms': 'Terms of Service',
                'workflow': 'Workflow',
                'task': 'Task',
                'schedule': 'Schedule',
                'automation': 'Automation',
                'ai_assistant': 'AI Assistant',
                'chat': 'Chat',
                'message': 'Message',
                'send': 'Send',
                'type_message': 'Type your message...',
                'invalid_credentials': 'Invalid credentials',
                'account_locked': 'Account is locked',
                'login_successful': 'Login successful',
                'logout_successful': 'Logout successful',
                'registration_successful': 'Registration successful',
                'password_too_weak': 'Password is too weak',
                'email_invalid': 'Invalid email address',
                'username_taken': 'Username is already taken',
                'server_error': 'Server error occurred',
                'network_error': 'Network error occurred',
                'permission_denied': 'Permission denied',
                'not_found': 'Not found',
                'unauthorized': 'Unauthorized access'
            },
            'vi': {
                'welcome': 'Chào mừng đến với Trợ lý AI',
                'login': 'Đăng nhập',
                'logout': 'Đăng xuất',
                'register': 'Đăng ký',
                'username': 'Tên đăng nhập',
                'password': 'Mật khẩu',
                'email': 'Email',
                'submit': 'Gửi',
                'cancel': 'Hủy',
                'save': 'Lưu',
                'delete': 'Xóa',
                'edit': 'Chỉnh sửa',
                'create': 'Tạo mới',
                'search': 'Tìm kiếm',
                'loading': 'Đang tải...',
                'error': 'Lỗi',
                'success': 'Thành công',
                'warning': 'Cảnh báo',
                'info': 'Thông tin',
                'yes': 'Có',
                'no': 'Không',
                'ok': 'OK',
                'close': 'Đóng',
                'back': 'Quay lại',
                'next': 'Tiếp theo',
                'previous': 'Trước đó',
                'home': 'Trang chủ',
                'dashboard': 'Bảng điều khiển',
                'settings': 'Cài đặt',
                'profile': 'Hồ sơ',
                'help': 'Trợ giúp',
                'about': 'Giới thiệu',
                'contact': 'Liên hệ',
                'privacy': 'Quyền riêng tư',
                'terms': 'Điều khoản dịch vụ',
                'workflow': 'Quy trình làm việc',
                'task': 'Nhiệm vụ',
                'schedule': 'Lịch trình',
                'automation': 'Tự động hóa',
                'ai_assistant': 'Trợ lý AI',
                'chat': 'Trò chuyện',
                'message': 'Tin nhắn',
                'send': 'Gửi',
                'type_message': 'Nhập tin nhắn của bạn...',
                'invalid_credentials': 'Thông tin đăng nhập không hợp lệ',
                'account_locked': 'Tài khoản đã bị khóa',
                'login_successful': 'Đăng nhập thành công',
                'logout_successful': 'Đăng xuất thành công',
                'registration_successful': 'Đăng ký thành công',
                'password_too_weak': 'Mật khẩu quá yếu',
                'email_invalid': 'Địa chỉ email không hợp lệ',
                'username_taken': 'Tên đăng nhập đã được sử dụng',
                'server_error': 'Lỗi máy chủ',
                'network_error': 'Lỗi mạng',
                'permission_denied': 'Không có quyền truy cập',
                'not_found': 'Không tìm thấy',
                'unauthorized': 'Truy cập không được phép'
            }
        }
        
        # Load translations into memory and Redis
        for language, translations in default_translations.items():
            self.translations[language] = translations
            
            for key, text in translations.items():
                entry = TranslationEntry(
                    key=key,
                    language=language,
                    text=text,
                    context="default",
                    created_at=str(int(time.time())),
                    updated_at=str(int(time.time()))
                )
                self._store_translation(entry)

class I18nManager:
    """Main internationalization manager"""
    
    def __init__(self):
        self.language_detector = LanguageDetector()
        self.translation_service = TranslationService()
        self.localization_manager = LocalizationManager()
        self.user_languages: Dict[str, str] = {}  # user_id -> language_code
        
    def detect_user_language(self, text: str) -> str:
        """Detect user's preferred language from text"""
        detected_lang, confidence = self.language_detector.detect_language(text)
        
        # Only use detected language if confidence is high enough
        if confidence >= 0.8:
            return detected_lang
        else:
            return self.localization_manager.default_language
    
    def set_user_language(self, user_id: str, language: str):
        """Set user's preferred language"""
        if language in [lang.value for lang in SupportedLanguage]:
            self.user_languages[user_id] = language
            
            # Store in Redis for persistence
            self.localization_manager.redis_client.set(f"user_language:{user_id}", language)
        else:
            logger.warning(f"Unsupported language: {language}")
    
    def get_user_language(self, user_id: str) -> str:
        """Get user's preferred language"""
        # Check memory first
        if user_id in self.user_languages:
            return self.user_languages[user_id]
        
        # Check Redis
        stored_lang = self.localization_manager.redis_client.get(f"user_language:{user_id}")
        if stored_lang:
            self.user_languages[user_id] = stored_lang
            return stored_lang
        
        return self.localization_manager.default_language
    
    def translate_for_user(self, user_id: str, text: str, source_lang: str = None) -> str:
        """Translate text for specific user"""
        target_lang = self.get_user_language(user_id)
        
        # Don't translate if target language is the same as source
        if source_lang and source_lang == target_lang:
            return text
        
        return self.translation_service.translate_text(text, target_lang, source_lang)
    
    def localize_for_user(self, user_id: str, key: str, **kwargs) -> str:
        """Get localized text for specific user"""
        user_lang = self.get_user_language(user_id)
        return self.localization_manager.get_text(key, user_lang, **kwargs)
    
    def process_ai_response(self, user_id: str, ai_response: str) -> str:
        """Process AI response for user's language"""
        user_lang = self.get_user_language(user_id)
        
        # If user's language is not English, translate the AI response
        if user_lang != 'en':
            return self.translation_service.translate_text(ai_response, user_lang, 'en')
        
        return ai_response
    
    def process_user_input(self, user_id: str, user_input: str) -> Tuple[str, str]:
        """Process user input and detect/translate if needed"""
        # Detect input language
        detected_lang, confidence = self.language_detector.detect_language(user_input)
        
        # If input is not in English and we need to process it with English AI
        if detected_lang != 'en' and confidence >= 0.7:
            # Translate to English for AI processing
            english_input = self.translation_service.translate_text(user_input, 'en', detected_lang)
            return english_input, detected_lang
        
        return user_input, detected_lang
    
    def get_supported_languages(self) -> List[Dict[str, str]]:
        """Get list of supported languages"""
        return self.localization_manager.get_supported_languages()

# Global i18n manager instance
i18n_manager = I18nManager()

def initialize_i18n():
    """Initialize internationalization system"""
    logger.info("Internationalization system initialized")

if __name__ == '__main__':
    initialize_i18n()

