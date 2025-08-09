"""
Advanced Security Manager for AI Assistant
Handles authentication, authorization, encryption, and security monitoring
"""

import os
import jwt
import bcrypt
import secrets
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import redis
import json
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization
import base64
import ipaddress
import re
from passlib.context import CryptContext
from argon2 import PasswordHasher
import time

logger = logging.getLogger(__name__)

class UserRole(Enum):
    ADMIN = "admin"
    USER = "user"
    GUEST = "guest"
    SERVICE = "service"

class SecurityLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class SecurityEvent:
    id: str
    user_id: str
    event_type: str
    severity: SecurityLevel
    description: str
    ip_address: str
    user_agent: str
    timestamp: datetime
    metadata: Dict[str, Any]

@dataclass
class User:
    id: str
    username: str
    email: str
    password_hash: str
    role: UserRole
    is_active: bool
    is_verified: bool
    created_at: datetime
    last_login: Optional[datetime]
    failed_login_attempts: int
    locked_until: Optional[datetime]
    two_factor_enabled: bool
    two_factor_secret: Optional[str]

class EncryptionManager:
    """Handles data encryption and decryption"""
    
    def __init__(self, master_key: Optional[str] = None):
        if master_key:
            self.master_key = master_key.encode()
        else:
            self.master_key = os.environ.get('MASTER_KEY', self._generate_master_key()).encode()
        
        # Initialize Fernet for symmetric encryption
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'ai_assistant_salt',
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(self.master_key))
        self.fernet = Fernet(key)
        
        # Generate RSA key pair for asymmetric encryption
        self.private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )
        self.public_key = self.private_key.public_key()
    
    def _generate_master_key(self) -> str:
        """Generate a new master key"""
        return secrets.token_urlsafe(32)
    
    def encrypt_data(self, data: str) -> str:
        """Encrypt data using symmetric encryption"""
        return self.fernet.encrypt(data.encode()).decode()
    
    def decrypt_data(self, encrypted_data: str) -> str:
        """Decrypt data using symmetric encryption"""
        return self.fernet.decrypt(encrypted_data.encode()).decode()
    
    def encrypt_sensitive_data(self, data: str) -> str:
        """Encrypt sensitive data using asymmetric encryption"""
        encrypted = self.public_key.encrypt(
            data.encode(),
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        return base64.b64encode(encrypted).decode()
    
    def decrypt_sensitive_data(self, encrypted_data: str) -> str:
        """Decrypt sensitive data using asymmetric encryption"""
        encrypted_bytes = base64.b64decode(encrypted_data.encode())
        decrypted = self.private_key.decrypt(
            encrypted_bytes,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        return decrypted.decode()
    
    def hash_password(self, password: str) -> str:
        """Hash password using Argon2"""
        ph = PasswordHasher()
        return ph.hash(password)
    
    def verify_password(self, password: str, hashed: str) -> bool:
        """Verify password against hash"""
        ph = PasswordHasher()
        try:
            ph.verify(hashed, password)
            return True
        except:
            return False

class AuthenticationManager:
    """Handles user authentication and session management"""
    
    def __init__(self, redis_client: redis.Redis, encryption_manager: EncryptionManager):
        self.redis = redis_client
        self.encryption = encryption_manager
        self.jwt_secret = os.environ.get('JWT_SECRET', secrets.token_urlsafe(32))
        self.jwt_algorithm = 'HS256'
        self.access_token_expire = timedelta(hours=1)
        self.refresh_token_expire = timedelta(days=7)
        
        # Rate limiting settings
        self.max_login_attempts = 5
        self.lockout_duration = timedelta(minutes=30)
        
        # Password policy
        self.min_password_length = 12
        self.require_uppercase = True
        self.require_lowercase = True
        self.require_numbers = True
        self.require_special_chars = True
    
    def register_user(self, username: str, email: str, password: str, role: UserRole = UserRole.USER) -> Tuple[bool, str]:
        """Register a new user"""
        # Validate input
        if not self._validate_username(username):
            return False, "Invalid username format"
        
        if not self._validate_email(email):
            return False, "Invalid email format"
        
        if not self._validate_password(password):
            return False, "Password does not meet security requirements"
        
        # Check if user already exists
        if self._user_exists(username, email):
            return False, "User already exists"
        
        # Create user
        user_id = secrets.token_urlsafe(16)
        password_hash = self.encryption.hash_password(password)
        
        user = User(
            id=user_id,
            username=username,
            email=email,
            password_hash=password_hash,
            role=role,
            is_active=True,
            is_verified=False,
            created_at=datetime.now(),
            last_login=None,
            failed_login_attempts=0,
            locked_until=None,
            two_factor_enabled=False,
            two_factor_secret=None
        )
        
        # Store user
        self._store_user(user)
        
        logger.info(f"User {username} registered successfully")
        return True, user_id
    
    def authenticate_user(self, username: str, password: str, ip_address: str, user_agent: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """Authenticate user and return access token"""
        user = self._get_user_by_username(username)
        
        if not user:
            self._log_security_event(
                "", "failed_login", SecurityLevel.MEDIUM,
                f"Login attempt with non-existent username: {username}",
                ip_address, user_agent
            )
            return False, None, "Invalid credentials"
        
        # Check if account is locked
        if user.locked_until and datetime.now() < user.locked_until:
            self._log_security_event(
                user.id, "locked_account_access", SecurityLevel.HIGH,
                f"Access attempt on locked account: {username}",
                ip_address, user_agent
            )
            return False, None, "Account is temporarily locked"
        
        # Verify password
        if not self.encryption.verify_password(password, user.password_hash):
            user.failed_login_attempts += 1
            
            # Lock account if too many failed attempts
            if user.failed_login_attempts >= self.max_login_attempts:
                user.locked_until = datetime.now() + self.lockout_duration
                self._log_security_event(
                    user.id, "account_locked", SecurityLevel.HIGH,
                    f"Account locked due to {self.max_login_attempts} failed login attempts",
                    ip_address, user_agent
                )
            
            self._store_user(user)
            
            self._log_security_event(
                user.id, "failed_login", SecurityLevel.MEDIUM,
                f"Failed login attempt for user: {username}",
                ip_address, user_agent
            )
            return False, None, "Invalid credentials"
        
        # Check if account is active
        if not user.is_active:
            self._log_security_event(
                user.id, "inactive_account_access", SecurityLevel.MEDIUM,
                f"Login attempt on inactive account: {username}",
                ip_address, user_agent
            )
            return False, None, "Account is inactive"
        
        # Reset failed attempts on successful login
        user.failed_login_attempts = 0
        user.locked_until = None
        user.last_login = datetime.now()
        self._store_user(user)
        
        # Generate tokens
        access_token = self._generate_access_token(user)
        refresh_token = self._generate_refresh_token(user)
        
        # Store session
        self._store_session(user.id, access_token, refresh_token, ip_address, user_agent)
        
        self._log_security_event(
            user.id, "successful_login", SecurityLevel.LOW,
            f"Successful login for user: {username}",
            ip_address, user_agent
        )
        
        return True, access_token, refresh_token
    
    def validate_token(self, token: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Validate JWT token"""
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=[self.jwt_algorithm])
            
            # Check if token is blacklisted
            if self.redis.sismember("blacklisted_tokens", token):
                return False, None
            
            # Check if session exists
            session_key = f"session:{payload['user_id']}:{payload['jti']}"
            if not self.redis.exists(session_key):
                return False, None
            
            return True, payload
        except jwt.ExpiredSignatureError:
            return False, None
        except jwt.InvalidTokenError:
            return False, None
    
    def refresh_access_token(self, refresh_token: str) -> Tuple[bool, Optional[str]]:
        """Refresh access token using refresh token"""
        try:
            payload = jwt.decode(refresh_token, self.jwt_secret, algorithms=[self.jwt_algorithm])
            
            if payload.get('type') != 'refresh':
                return False, None
            
            user = self._get_user_by_id(payload['user_id'])
            if not user or not user.is_active:
                return False, None
            
            # Generate new access token
            new_access_token = self._generate_access_token(user)
            
            return True, new_access_token
        except jwt.InvalidTokenError:
            return False, None
    
    def logout_user(self, token: str) -> bool:
        """Logout user and invalidate token"""
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=[self.jwt_algorithm])
            
            # Add token to blacklist
            self.redis.sadd("blacklisted_tokens", token)
            self.redis.expire("blacklisted_tokens", int(self.access_token_expire.total_seconds()))
            
            # Remove session
            session_key = f"session:{payload['user_id']}:{payload['jti']}"
            self.redis.delete(session_key)
            
            return True
        except jwt.InvalidTokenError:
            return False
    
    def _validate_username(self, username: str) -> bool:
        """Validate username format"""
        if len(username) < 3 or len(username) > 50:
            return False
        return re.match(r'^[a-zA-Z0-9_.-]+$', username) is not None
    
    def _validate_email(self, email: str) -> bool:
        """Validate email format"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    def _validate_password(self, password: str) -> bool:
        """Validate password against security policy"""
        if len(password) < self.min_password_length:
            return False
        
        if self.require_uppercase and not re.search(r'[A-Z]', password):
            return False
        
        if self.require_lowercase and not re.search(r'[a-z]', password):
            return False
        
        if self.require_numbers and not re.search(r'\d', password):
            return False
        
        if self.require_special_chars and not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            return False
        
        return True
    
    def _user_exists(self, username: str, email: str) -> bool:
        """Check if user already exists"""
        return (self.redis.exists(f"user:username:{username}") or 
                self.redis.exists(f"user:email:{email}"))
    
    def _store_user(self, user: User):
        """Store user in Redis"""
        user_data = {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'password_hash': user.password_hash,
            'role': user.role.value,
            'is_active': str(user.is_active),
            'is_verified': str(user.is_verified),
            'created_at': user.created_at.isoformat(),
            'last_login': user.last_login.isoformat() if user.last_login else '',
            'failed_login_attempts': str(user.failed_login_attempts),
            'locked_until': user.locked_until.isoformat() if user.locked_until else '',
            'two_factor_enabled': str(user.two_factor_enabled),
            'two_factor_secret': user.two_factor_secret or ''
        }
        
        # Store user data
        self.redis.hset(f"user:{user.id}", mapping=user_data)
        
        # Create indexes
        self.redis.set(f"user:username:{user.username}", user.id)
        self.redis.set(f"user:email:{user.email}", user.id)
    
    def _get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username"""
        user_id = self.redis.get(f"user:username:{username}")
        if not user_id:
            return None
        return self._get_user_by_id(user_id)
    
    def _get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID"""
        user_data = self.redis.hgetall(f"user:{user_id}")
        if not user_data:
            return None
        
        return User(
            id=user_data['id'],
            username=user_data['username'],
            email=user_data['email'],
            password_hash=user_data['password_hash'],
            role=UserRole(user_data['role']),
            is_active=user_data['is_active'].lower() == 'true',
            is_verified=user_data['is_verified'].lower() == 'true',
            created_at=datetime.fromisoformat(user_data['created_at']),
            last_login=datetime.fromisoformat(user_data['last_login']) if user_data['last_login'] else None,
            failed_login_attempts=int(user_data['failed_login_attempts']),
            locked_until=datetime.fromisoformat(user_data['locked_until']) if user_data['locked_until'] else None,
            two_factor_enabled=user_data['two_factor_enabled'].lower() == 'true',
            two_factor_secret=user_data['two_factor_secret'] if user_data['two_factor_secret'] else None
        )
    
    def _generate_access_token(self, user: User) -> str:
        """Generate JWT access token"""
        payload = {
            'user_id': user.id,
            'username': user.username,
            'role': user.role.value,
            'type': 'access',
            'exp': datetime.utcnow() + self.access_token_expire,
            'iat': datetime.utcnow(),
            'jti': secrets.token_urlsafe(16)
        }
        return jwt.encode(payload, self.jwt_secret, algorithm=self.jwt_algorithm)
    
    def _generate_refresh_token(self, user: User) -> str:
        """Generate JWT refresh token"""
        payload = {
            'user_id': user.id,
            'type': 'refresh',
            'exp': datetime.utcnow() + self.refresh_token_expire,
            'iat': datetime.utcnow(),
            'jti': secrets.token_urlsafe(16)
        }
        return jwt.encode(payload, self.jwt_secret, algorithm=self.jwt_algorithm)
    
    def _store_session(self, user_id: str, access_token: str, refresh_token: str, ip_address: str, user_agent: str):
        """Store user session"""
        access_payload = jwt.decode(access_token, self.jwt_secret, algorithms=[self.jwt_algorithm])
        
        session_data = {
            'user_id': user_id,
            'access_token': access_token,
            'refresh_token': refresh_token,
            'ip_address': ip_address,
            'user_agent': user_agent,
            'created_at': datetime.now().isoformat()
        }
        
        session_key = f"session:{user_id}:{access_payload['jti']}"
        self.redis.hset(session_key, mapping=session_data)
        self.redis.expire(session_key, int(self.refresh_token_expire.total_seconds()))
    
    def _log_security_event(self, user_id: str, event_type: str, severity: SecurityLevel, 
                           description: str, ip_address: str, user_agent: str, metadata: Dict[str, Any] = None):
        """Log security event"""
        event = SecurityEvent(
            id=secrets.token_urlsafe(16),
            user_id=user_id,
            event_type=event_type,
            severity=severity,
            description=description,
            ip_address=ip_address,
            user_agent=user_agent,
            timestamp=datetime.now(),
            metadata=metadata or {}
        )
        
        event_data = {
            'id': event.id,
            'user_id': event.user_id,
            'event_type': event.event_type,
            'severity': event.severity.value,
            'description': event.description,
            'ip_address': event.ip_address,
            'user_agent': event.user_agent,
            'timestamp': event.timestamp.isoformat(),
            'metadata': json.dumps(event.metadata)
        }
        
        # Store security event
        self.redis.lpush("security_events", json.dumps(event_data))
        self.redis.ltrim("security_events", 0, 9999)  # Keep last 10000 events
        
        # Alert on high severity events
        if severity in [SecurityLevel.HIGH, SecurityLevel.CRITICAL]:
            self._send_security_alert(event)
    
    def _send_security_alert(self, event: SecurityEvent):
        """Send security alert for high severity events"""
        # This would integrate with alerting systems (email, Slack, etc.)
        logger.warning(f"SECURITY ALERT: {event.description} - User: {event.user_id}, IP: {event.ip_address}")

class AuthorizationManager:
    """Handles role-based access control and permissions"""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self._setup_default_permissions()
    
    def _setup_default_permissions(self):
        """Setup default role permissions"""
        permissions = {
            UserRole.ADMIN: [
                'user:create', 'user:read', 'user:update', 'user:delete',
                'workflow:create', 'workflow:read', 'workflow:update', 'workflow:delete',
                'task:create', 'task:read', 'task:update', 'task:delete',
                'system:configure', 'system:monitor', 'security:manage'
            ],
            UserRole.USER: [
                'user:read_own', 'user:update_own',
                'workflow:create', 'workflow:read_own', 'workflow:update_own', 'workflow:delete_own',
                'task:create', 'task:read_own', 'task:update_own', 'task:delete_own'
            ],
            UserRole.GUEST: [
                'user:read_own',
                'workflow:read_own',
                'task:read_own'
            ],
            UserRole.SERVICE: [
                'workflow:execute', 'task:execute', 'system:monitor'
            ]
        }
        
        for role, perms in permissions.items():
            self.redis.delete(f"role_permissions:{role.value}")
            for perm in perms:
                self.redis.sadd(f"role_permissions:{role.value}", perm)
    
    def check_permission(self, user_role: UserRole, permission: str) -> bool:
        """Check if user role has specific permission"""
        return self.redis.sismember(f"role_permissions:{user_role.value}", permission)
    
    def add_permission(self, role: UserRole, permission: str) -> bool:
        """Add permission to role"""
        return self.redis.sadd(f"role_permissions:{role.value}", permission) > 0
    
    def remove_permission(self, role: UserRole, permission: str) -> bool:
        """Remove permission from role"""
        return self.redis.srem(f"role_permissions:{role.value}", permission) > 0

class SecurityMonitor:
    """Monitors system for security threats and anomalies"""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.threat_patterns = self._load_threat_patterns()
    
    def _load_threat_patterns(self) -> Dict[str, Any]:
        """Load threat detection patterns"""
        return {
            'brute_force': {
                'max_attempts': 10,
                'time_window': 300,  # 5 minutes
                'severity': SecurityLevel.HIGH
            },
            'suspicious_ip': {
                'known_bad_ips': set(),
                'severity': SecurityLevel.MEDIUM
            },
            'unusual_access_pattern': {
                'max_requests_per_minute': 100,
                'severity': SecurityLevel.MEDIUM
            }
        }
    
    def analyze_request(self, ip_address: str, user_agent: str, endpoint: str, user_id: str = None) -> List[SecurityEvent]:
        """Analyze incoming request for security threats"""
        threats = []
        
        # Check for brute force attacks
        if self._detect_brute_force(ip_address):
            threats.append(self._create_threat_event(
                'brute_force_detected', SecurityLevel.HIGH,
                f"Brute force attack detected from IP: {ip_address}",
                ip_address, user_agent, user_id
            ))
        
        # Check for suspicious IP addresses
        if self._is_suspicious_ip(ip_address):
            threats.append(self._create_threat_event(
                'suspicious_ip', SecurityLevel.MEDIUM,
                f"Request from suspicious IP: {ip_address}",
                ip_address, user_agent, user_id
            ))
        
        # Check for unusual access patterns
        if self._detect_unusual_access(ip_address):
            threats.append(self._create_threat_event(
                'unusual_access_pattern', SecurityLevel.MEDIUM,
                f"Unusual access pattern detected from IP: {ip_address}",
                ip_address, user_agent, user_id
            ))
        
        return threats
    
    def _detect_brute_force(self, ip_address: str) -> bool:
        """Detect brute force attacks"""
        key = f"requests:{ip_address}"
        current_time = int(time.time())
        window_start = current_time - self.threat_patterns['brute_force']['time_window']
        
        # Remove old entries
        self.redis.zremrangebyscore(key, 0, window_start)
        
        # Add current request
        self.redis.zadd(key, {str(current_time): current_time})
        self.redis.expire(key, self.threat_patterns['brute_force']['time_window'])
        
        # Check if threshold exceeded
        request_count = self.redis.zcard(key)
        return request_count > self.threat_patterns['brute_force']['max_attempts']
    
    def _is_suspicious_ip(self, ip_address: str) -> bool:
        """Check if IP address is suspicious"""
        # Check against known bad IPs
        if ip_address in self.threat_patterns['suspicious_ip']['known_bad_ips']:
            return True
        
        # Check if IP is in private ranges (could be suspicious for external access)
        try:
            ip = ipaddress.ip_address(ip_address)
            if ip.is_private and not ip.is_loopback:
                return False  # Private IPs are generally OK
        except ValueError:
            return True  # Invalid IP format is suspicious
        
        return False
    
    def _detect_unusual_access(self, ip_address: str) -> bool:
        """Detect unusual access patterns"""
        key = f"access_rate:{ip_address}"
        current_minute = int(time.time() / 60)
        
        # Increment counter for current minute
        self.redis.hincrby(key, str(current_minute), 1)
        self.redis.expire(key, 300)  # Keep for 5 minutes
        
        # Check current minute's request count
        current_count = int(self.redis.hget(key, str(current_minute)) or 0)
        return current_count > self.threat_patterns['unusual_access_pattern']['max_requests_per_minute']
    
    def _create_threat_event(self, event_type: str, severity: SecurityLevel, description: str,
                           ip_address: str, user_agent: str, user_id: str = None) -> SecurityEvent:
        """Create security threat event"""
        return SecurityEvent(
            id=secrets.token_urlsafe(16),
            user_id=user_id or "",
            event_type=event_type,
            severity=severity,
            description=description,
            ip_address=ip_address,
            user_agent=user_agent,
            timestamp=datetime.now(),
            metadata={}
        )

# Global security manager instances
redis_client = redis.Redis(host='localhost', port=6379, db=4, decode_responses=True)
encryption_manager = EncryptionManager()
auth_manager = AuthenticationManager(redis_client, encryption_manager)
authz_manager = AuthorizationManager(redis_client)
security_monitor = SecurityMonitor(redis_client)

# Create a unified security manager
class SecurityManager:
    def __init__(self):
        self.encryption = encryption_manager
        self.auth = auth_manager
        self.authz = authz_manager
        self.monitor = security_monitor
    
    def get_user_permissions(self, user_id: str):
        """Get user permissions"""
        return self.authz.get_user_permissions(user_id)

security_manager = SecurityManager()

# Decorators for Flask routes
from functools import wraps
from flask import request, jsonify

def require_auth(f):
    """Decorator to require authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Authentication required'}), 401
        
        token = auth_header.split(' ')[1]
        user_data = auth_manager.verify_token(token)
        
        if not user_data:
            return jsonify({'error': 'Invalid token'}), 401
        
        request.user_id = user_data['user_id']
        request.user_data = user_data
        
        return f(*args, **kwargs)
    return decorated_function

def require_permission(permission: str):
    """Decorator to require specific permission"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not hasattr(request, 'user_id'):
                return jsonify({'error': 'Authentication required'}), 401
            
            user_permissions = authz_manager.get_user_permissions(request.user_id)
            if permission not in user_permissions:
                return jsonify({'error': 'Insufficient permissions'}), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def initialize_security():
    """Initialize security system"""
    logger.info("Security system initialized")

if __name__ == '__main__':
    initialize_security()

