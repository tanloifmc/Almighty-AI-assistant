"""
Secure API with Authentication and Authorization Middleware
Enhanced version of backend_api.py with comprehensive security features
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

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app, origins="*")

# Security middleware
def security_middleware():
    """Security middleware to analyze all requests"""
    ip_address = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
    user_agent = request.headers.get('User-Agent', '')
    endpoint = request.endpoint or request.path
    
    # Get user ID if authenticated
    user_id = getattr(g, 'user_id', None)
    
    # Analyze request for threats
    threats = security_monitor.analyze_request(ip_address, user_agent, endpoint, user_id)
    
    # Log threats
    for threat in threats:
        logger.warning(f"Security threat detected: {threat.description}")
        
        # Block request if critical threat
        if threat.severity == SecurityLevel.CRITICAL:
            return jsonify({'error': 'Request blocked due to security threat'}), 403
    
    return None

@app.before_request
def before_request():
    """Execute before each request"""
    # Apply security middleware
    security_response = security_middleware()
    if security_response:
        return security_response

def require_auth(f):
    """Decorator to require authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Missing or invalid authorization header'}), 401
        
        token = auth_header.split(' ')[1]
        is_valid, payload = auth_manager.validate_token(token)
        
        if not is_valid:
            return jsonify({'error': 'Invalid or expired token'}), 401
        
        # Store user info in request context
        g.user_id = payload['user_id']
        g.username = payload['username']
        g.user_role = UserRole(payload['role'])
        
        return f(*args, **kwargs)
    
    return decorated_function

def require_permission(permission: str):
    """Decorator to require specific permission"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not hasattr(g, 'user_role'):
                return jsonify({'error': 'Authentication required'}), 401
            
            if not authz_manager.check_permission(g.user_role, permission):
                return jsonify({'error': 'Insufficient permissions'}), 403
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator

def require_role(required_role: UserRole):
    """Decorator to require specific role"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not hasattr(g, 'user_role'):
                return jsonify({'error': 'Authentication required'}), 401
            
            if g.user_role != required_role and g.user_role != UserRole.ADMIN:
                return jsonify({'error': 'Insufficient role'}), 403
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator

# Authentication endpoints
@app.route('/api/auth/register', methods=['POST'])
def register():
    """Register new user"""
    try:
        data = request.get_json()
        
        if not data or not all(k in data for k in ['username', 'email', 'password']):
            return jsonify({'error': 'Missing required fields'}), 400
        
        username = data['username']
        email = data['email']
        password = data['password']
        role = UserRole(data.get('role', 'user'))
        
        success, result = auth_manager.register_user(username, email, password, role)
        
        if success:
            return jsonify({
                'message': 'User registered successfully',
                'user_id': result
            }), 201
        else:
            return jsonify({'error': result}), 400
            
    except Exception as e:
        logger.error(f"Error in register: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/auth/login', methods=['POST'])
def login():
    """Authenticate user"""
    try:
        data = request.get_json()
        
        if not data or not all(k in data for k in ['username', 'password']):
            return jsonify({'error': 'Missing username or password'}), 400
        
        username = data['username']
        password = data['password']
        ip_address = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
        user_agent = request.headers.get('User-Agent', '')
        
        success, access_token, refresh_token = auth_manager.authenticate_user(
            username, password, ip_address, user_agent
        )
        
        if success:
            return jsonify({
                'access_token': access_token,
                'refresh_token': refresh_token,
                'token_type': 'Bearer'
            }), 200
        else:
            return jsonify({'error': refresh_token}), 401
            
    except Exception as e:
        logger.error(f"Error in login: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/auth/refresh', methods=['POST'])
def refresh_token():
    """Refresh access token"""
    try:
        data = request.get_json()
        
        if not data or 'refresh_token' not in data:
            return jsonify({'error': 'Missing refresh token'}), 400
        
        refresh_token = data['refresh_token']
        success, new_access_token = auth_manager.refresh_access_token(refresh_token)
        
        if success:
            return jsonify({
                'access_token': new_access_token,
                'token_type': 'Bearer'
            }), 200
        else:
            return jsonify({'error': 'Invalid refresh token'}), 401
            
    except Exception as e:
        logger.error(f"Error in refresh_token: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/auth/logout', methods=['POST'])
@require_auth
def logout():
    """Logout user"""
    try:
        auth_header = request.headers.get('Authorization')
        token = auth_header.split(' ')[1]
        
        success = auth_manager.logout_user(token)
        
        if success:
            return jsonify({'message': 'Logged out successfully'}), 200
        else:
            return jsonify({'error': 'Failed to logout'}), 400
            
    except Exception as e:
        logger.error(f"Error in logout: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

# Protected endpoints
@app.route('/api/chat', methods=['POST'])
@require_auth
@require_permission('task:create')
def chat():
    """Process chat message with AI assistant"""
    try:
        data = request.get_json()
        
        if not data or 'message' not in data:
            return jsonify({'error': 'Missing message'}), 400
        
        message = data['message']
        context = data.get('context', {})
        
        # Add user context
        context['user_id'] = g.user_id
        context['username'] = g.username
        
        # Process with AI assistant (import here to avoid circular imports)
        from core_agent import PersonalAIAssistant
        ai_assistant = PersonalAIAssistant()
        
        response = ai_assistant.process_request(g.user_id, message, context)
        
        return jsonify({
            'response': response,
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Error in chat: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/workflows', methods=['GET'])
@require_auth
@require_permission('workflow:read_own')
def get_workflows():
    """Get user's workflows"""
    try:
        from workflow_manager import WorkflowManager
        import redis
        
        redis_client = redis.Redis(host='localhost', port=6379, db=1, decode_responses=True)
        workflow_manager = WorkflowManager(redis_client)
        
        workflows = workflow_manager.list_user_workflows(g.user_id)
        
        # Convert to JSON-serializable format
        workflows_data = []
        for workflow in workflows:
            workflows_data.append({
                'id': workflow.id,
                'name': workflow.name,
                'description': workflow.description,
                'status': workflow.status.value,
                'created_at': workflow.created_at.isoformat(),
                'last_run': workflow.last_run.isoformat() if workflow.last_run else None,
                'run_count': workflow.run_count
            })
        
        return jsonify({'workflows': workflows_data}), 200
        
    except Exception as e:
        logger.error(f"Error in get_workflows: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/workflows', methods=['POST'])
@require_auth
@require_permission('workflow:create')
def create_workflow():
    """Create new workflow"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Missing workflow data'}), 400
        
        from workflow_manager import WorkflowManager
        import redis
        
        redis_client = redis.Redis(host='localhost', port=6379, db=1, decode_responses=True)
        workflow_manager = WorkflowManager(redis_client)
        
        workflow_id = workflow_manager.create_workflow(g.user_id, data)
        
        return jsonify({
            'message': 'Workflow created successfully',
            'workflow_id': workflow_id
        }), 201
        
    except Exception as e:
        logger.error(f"Error in create_workflow: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/workflows/<workflow_id>', methods=['DELETE'])
@require_auth
@require_permission('workflow:delete_own')
def delete_workflow(workflow_id):
    """Delete workflow"""
    try:
        from workflow_manager import WorkflowManager
        import redis
        
        redis_client = redis.Redis(host='localhost', port=6379, db=1, decode_responses=True)
        workflow_manager = WorkflowManager(redis_client)
        
        # Check if workflow belongs to user
        workflow = workflow_manager.get_workflow(workflow_id)
        if not workflow or workflow.user_id != g.user_id:
            return jsonify({'error': 'Workflow not found'}), 404
        
        success = workflow_manager.delete_workflow(workflow_id)
        
        if success:
            return jsonify({'message': 'Workflow deleted successfully'}), 200
        else:
            return jsonify({'error': 'Failed to delete workflow'}), 400
            
    except Exception as e:
        logger.error(f"Error in delete_workflow: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/tasks', methods=['GET'])
@require_auth
@require_permission('task:read_own')
def get_tasks():
    """Get user's scheduled tasks"""
    try:
        from scheduler import ai_scheduler
        
        tasks = ai_scheduler.list_user_tasks(g.user_id)
        
        # Convert to JSON-serializable format
        tasks_data = []
        for task in tasks:
            tasks_data.append({
                'id': task.id,
                'name': task.name,
                'description': task.description,
                'task_type': task.task_type,
                'status': task.status.value,
                'next_run': task.next_run.isoformat() if task.next_run else None,
                'last_run': task.last_run.isoformat() if task.last_run else None,
                'run_count': task.run_count
            })
        
        return jsonify({'tasks': tasks_data}), 200
        
    except Exception as e:
        logger.error(f"Error in get_tasks: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/tasks', methods=['POST'])
@require_auth
@require_permission('task:create')
def create_task():
    """Create new scheduled task"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Missing task data'}), 400
        
        from scheduler import ai_scheduler
        
        task_id = ai_scheduler.schedule_task(g.user_id, data)
        
        return jsonify({
            'message': 'Task scheduled successfully',
            'task_id': task_id
        }), 201
        
    except Exception as e:
        logger.error(f"Error in create_task: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/security/events', methods=['GET'])
@require_auth
@require_role(UserRole.ADMIN)
def get_security_events():
    """Get security events (admin only)"""
    try:
        import redis
        
        redis_client = redis.Redis(host='localhost', port=6379, db=4, decode_responses=True)
        
        limit = request.args.get('limit', 100, type=int)
        events_data = redis_client.lrange("security_events", 0, limit - 1)
        
        events = [json.loads(event) for event in events_data]
        
        return jsonify({'events': events}), 200
        
    except Exception as e:
        logger.error(f"Error in get_security_events: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '2.0.0'
    }), 200

@app.route('/api/user/profile', methods=['GET'])
@require_auth
def get_user_profile():
    """Get user profile"""
    try:
        return jsonify({
            'user_id': g.user_id,
            'username': g.username,
            'role': g.user_role.value
        }), 200
        
    except Exception as e:
        logger.error(f"Error in get_user_profile: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(405)
def method_not_allowed(error):
    return jsonify({'error': 'Method not allowed'}), 405

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    # Initialize security system
    from security_manager import initialize_security
    initialize_security()
    
    # Run the secure API
    app.run(host='0.0.0.0', port=5000, debug=False)

