"""
Collaboration API for AI Assistant
Provides REST endpoints for team collaboration functionality
"""

import os
import logging
from datetime import datetime
from typing import Dict, Any, List
from flask import Flask, request, jsonify
from flask_cors import CORS

# Import collaboration components
from collaboration_manager import (
    collaboration_manager,
    TeamRole,
    TaskStatus,
    TaskPriority,
    NotificationType
)

# Import security components
from security_manager import security_manager, require_auth, require_permission

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
CORS(app, origins="*")

@app.route('/api/collaboration/health', methods=['GET'])
def collaboration_health():
    """Health check for collaboration system"""
    try:
        # Test Redis connection
        collaboration_manager.redis.ping()
        
        return jsonify({
            'status': 'healthy',
            'collaboration_system': {
                'redis_connection': True,
                'team_management': True,
                'task_management': True,
                'knowledge_sharing': True,
                'notifications': True,
                'timestamp': datetime.now().isoformat()
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Collaboration health check failed: {str(e)}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500

# Team Management Endpoints
@app.route('/api/collaboration/teams', methods=['POST'])
@require_auth
def create_team():
    """Create a new team"""
    try:
        data = request.get_json()
        user_id = request.user_id
        user_data = request.user_data
        
        # Validate required fields
        if not data.get('name'):
            return jsonify({
                'success': False,
                'error': 'Team name is required'
            }), 400
        
        team = collaboration_manager.create_team(
            name=data['name'],
            description=data.get('description', ''),
            owner_id=user_id,
            owner_username=user_data.get('username', 'Unknown'),
            owner_email=user_data.get('email', '')
        )
        
        return jsonify({
            'success': True,
            'team': {
                'team_id': team.team_id,
                'name': team.name,
                'description': team.description,
                'owner_id': team.owner_id,
                'created_at': team.created_at.isoformat(),
                'members_count': len(team.members)
            }
        }), 201
        
    except Exception as e:
        logger.error(f"Error creating team: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/collaboration/teams/<team_id>', methods=['GET'])
@require_auth
def get_team(team_id: str):
    """Get team details"""
    try:
        user_id = request.user_id
        
        team = collaboration_manager.get_team(team_id)
        if not team:
            return jsonify({
                'success': False,
                'error': 'Team not found'
            }), 404
        
        # Check if user is member
        user_member = next((m for m in team.members if m.user_id == user_id), None)
        if not user_member:
            return jsonify({
                'success': False,
                'error': 'Access denied'
            }), 403
        
        return jsonify({
            'success': True,
            'team': {
                'team_id': team.team_id,
                'name': team.name,
                'description': team.description,
                'owner_id': team.owner_id,
                'created_at': team.created_at.isoformat(),
                'updated_at': team.updated_at.isoformat(),
                'members': [
                    {
                        'user_id': m.user_id,
                        'username': m.username,
                        'email': m.email,
                        'role': m.role.value,
                        'joined_at': m.joined_at.isoformat(),
                        'last_active': m.last_active.isoformat(),
                        'permissions': m.permissions
                    } for m in team.members
                ],
                'settings': team.settings,
                'user_role': user_member.role.value
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting team: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/collaboration/teams/<team_id>/invite', methods=['POST'])
@require_auth
def invite_member(team_id: str):
    """Invite member to team"""
    try:
        data = request.get_json()
        user_id = request.user_id
        
        if not data.get('email'):
            return jsonify({
                'success': False,
                'error': 'Email is required'
            }), 400
        
        role = TeamRole(data.get('role', 'member'))
        
        success = collaboration_manager.invite_member(
            team_id=team_id,
            inviter_id=user_id,
            email=data['email'],
            role=role
        )
        
        if success:
            return jsonify({
                'success': True,
                'message': f'Invitation sent to {data["email"]}'
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to send invitation'
            }), 400
            
    except Exception as e:
        logger.error(f"Error inviting member: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/collaboration/teams/<team_id>/join', methods=['POST'])
@require_auth
def join_team(team_id: str):
    """Join team with invitation token"""
    try:
        data = request.get_json()
        user_id = request.user_id
        user_data = request.user_data
        
        if not data.get('invite_token'):
            return jsonify({
                'success': False,
                'error': 'Invitation token is required'
            }), 400
        
        success = collaboration_manager.join_team(
            team_id=team_id,
            user_id=user_id,
            username=user_data.get('username', 'Unknown'),
            email=user_data.get('email', ''),
            invite_token=data['invite_token']
        )
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Successfully joined team'
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': 'Invalid invitation token'
            }), 400
            
    except Exception as e:
        logger.error(f"Error joining team: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/collaboration/user/teams', methods=['GET'])
@require_auth
def get_user_teams():
    """Get user's teams"""
    try:
        user_id = request.user_id
        team_ids = collaboration_manager.get_user_teams(user_id)
        
        teams = []
        for team_id in team_ids:
            team = collaboration_manager.get_team(team_id)
            if team:
                user_member = next((m for m in team.members if m.user_id == user_id), None)
                teams.append({
                    'team_id': team.team_id,
                    'name': team.name,
                    'description': team.description,
                    'members_count': len(team.members),
                    'user_role': user_member.role.value if user_member else 'unknown',
                    'last_active': team.updated_at.isoformat()
                })
        
        return jsonify({
            'success': True,
            'teams': teams
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting user teams: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Task Management Endpoints
@app.route('/api/collaboration/teams/<team_id>/tasks', methods=['POST'])
@require_auth
def create_task(team_id: str):
    """Create a shared task"""
    try:
        data = request.get_json()
        user_id = request.user_id
        
        if not data.get('title'):
            return jsonify({
                'success': False,
                'error': 'Task title is required'
            }), 400
        
        # Parse due date if provided
        due_date = None
        if data.get('due_date'):
            due_date = datetime.fromisoformat(data['due_date'])
        
        task = collaboration_manager.create_shared_task(
            title=data['title'],
            description=data.get('description', ''),
            team_id=team_id,
            created_by=user_id,
            assigned_to=data.get('assigned_to', []),
            priority=TaskPriority(data.get('priority', 'medium')),
            due_date=due_date,
            tags=data.get('tags', [])
        )
        
        return jsonify({
            'success': True,
            'task': {
                'task_id': task.task_id,
                'title': task.title,
                'description': task.description,
                'status': task.status.value,
                'priority': task.priority.value,
                'created_by': task.created_by,
                'assigned_to': task.assigned_to,
                'created_at': task.created_at.isoformat(),
                'due_date': task.due_date.isoformat() if task.due_date else None,
                'tags': task.tags
            }
        }), 201
        
    except Exception as e:
        logger.error(f"Error creating task: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/collaboration/tasks/<task_id>', methods=['GET'])
@require_auth
def get_task(task_id: str):
    """Get task details"""
    try:
        user_id = request.user_id
        
        task = collaboration_manager.get_shared_task(task_id)
        if not task:
            return jsonify({
                'success': False,
                'error': 'Task not found'
            }), 404
        
        # Check if user has access to this task
        team = collaboration_manager.get_team(task.team_id)
        if not team:
            return jsonify({
                'success': False,
                'error': 'Team not found'
            }), 404
        
        user_member = next((m for m in team.members if m.user_id == user_id), None)
        if not user_member:
            return jsonify({
                'success': False,
                'error': 'Access denied'
            }), 403
        
        return jsonify({
            'success': True,
            'task': {
                'task_id': task.task_id,
                'title': task.title,
                'description': task.description,
                'team_id': task.team_id,
                'status': task.status.value,
                'priority': task.priority.value,
                'created_by': task.created_by,
                'assigned_to': task.assigned_to,
                'created_at': task.created_at.isoformat(),
                'updated_at': task.updated_at.isoformat(),
                'due_date': task.due_date.isoformat() if task.due_date else None,
                'tags': task.tags,
                'comments': task.comments,
                'attachments': task.attachments
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting task: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/collaboration/tasks/<task_id>/status', methods=['PUT'])
@require_auth
def update_task_status(task_id: str):
    """Update task status"""
    try:
        data = request.get_json()
        user_id = request.user_id
        
        if not data.get('status'):
            return jsonify({
                'success': False,
                'error': 'Status is required'
            }), 400
        
        status = TaskStatus(data['status'])
        comment = data.get('comment', '')
        
        success = collaboration_manager.update_task_status(
            task_id=task_id,
            user_id=user_id,
            status=status,
            comment=comment
        )
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Task status updated successfully'
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to update task status'
            }), 400
            
    except Exception as e:
        logger.error(f"Error updating task status: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/collaboration/teams/<team_id>/tasks', methods=['GET'])
@require_auth
def get_team_tasks(team_id: str):
    """Get team tasks"""
    try:
        user_id = request.user_id
        
        # Check if user is team member
        team = collaboration_manager.get_team(team_id)
        if not team:
            return jsonify({
                'success': False,
                'error': 'Team not found'
            }), 404
        
        user_member = next((m for m in team.members if m.user_id == user_id), None)
        if not user_member:
            return jsonify({
                'success': False,
                'error': 'Access denied'
            }), 403
        
        task_ids = collaboration_manager.get_team_tasks(team_id)
        tasks = []
        
        for task_id in task_ids:
            task = collaboration_manager.get_shared_task(task_id)
            if task:
                tasks.append({
                    'task_id': task.task_id,
                    'title': task.title,
                    'description': task.description,
                    'status': task.status.value,
                    'priority': task.priority.value,
                    'created_by': task.created_by,
                    'assigned_to': task.assigned_to,
                    'created_at': task.created_at.isoformat(),
                    'updated_at': task.updated_at.isoformat(),
                    'due_date': task.due_date.isoformat() if task.due_date else None,
                    'tags': task.tags
                })
        
        return jsonify({
            'success': True,
            'tasks': tasks
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting team tasks: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Knowledge Sharing Endpoints
@app.route('/api/collaboration/teams/<team_id>/knowledge', methods=['POST'])
@require_auth
def share_knowledge(team_id: str):
    """Share knowledge with team"""
    try:
        data = request.get_json()
        user_id = request.user_id
        
        if not data.get('title') or not data.get('content'):
            return jsonify({
                'success': False,
                'error': 'Title and content are required'
            }), 400
        
        knowledge = collaboration_manager.share_knowledge(
            title=data['title'],
            content=data['content'],
            knowledge_type=data.get('type', 'document'),
            team_id=team_id,
            created_by=user_id,
            category=data.get('category', 'general'),
            tags=data.get('tags', []),
            is_public=data.get('is_public', False)
        )
        
        return jsonify({
            'success': True,
            'knowledge': {
                'knowledge_id': knowledge.knowledge_id,
                'title': knowledge.title,
                'type': knowledge.type,
                'category': knowledge.category,
                'created_by': knowledge.created_by,
                'created_at': knowledge.created_at.isoformat(),
                'tags': knowledge.tags,
                'is_public': knowledge.is_public
            }
        }), 201
        
    except Exception as e:
        logger.error(f"Error sharing knowledge: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/collaboration/teams/<team_id>/knowledge', methods=['GET'])
@require_auth
def get_team_knowledge(team_id: str):
    """Get team knowledge"""
    try:
        user_id = request.user_id
        
        # Check if user is team member
        team = collaboration_manager.get_team(team_id)
        if not team:
            return jsonify({
                'success': False,
                'error': 'Team not found'
            }), 404
        
        user_member = next((m for m in team.members if m.user_id == user_id), None)
        if not user_member:
            return jsonify({
                'success': False,
                'error': 'Access denied'
            }), 403
        
        knowledge_ids = collaboration_manager.get_team_knowledge(team_id)
        knowledge_items = []
        
        for knowledge_id in knowledge_ids:
            knowledge = collaboration_manager.get_knowledge_item(knowledge_id)
            if knowledge:
                knowledge_items.append({
                    'knowledge_id': knowledge.knowledge_id,
                    'title': knowledge.title,
                    'type': knowledge.type,
                    'category': knowledge.category,
                    'created_by': knowledge.created_by,
                    'created_at': knowledge.created_at.isoformat(),
                    'updated_at': knowledge.updated_at.isoformat(),
                    'tags': knowledge.tags,
                    'access_count': knowledge.access_count,
                    'rating': knowledge.rating,
                    'is_public': knowledge.is_public
                })
        
        return jsonify({
            'success': True,
            'knowledge': knowledge_items
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting team knowledge: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/collaboration/knowledge/<knowledge_id>', methods=['GET'])
@require_auth
def get_knowledge(knowledge_id: str):
    """Get knowledge item"""
    try:
        user_id = request.user_id
        
        knowledge = collaboration_manager.get_knowledge_item(knowledge_id)
        if not knowledge:
            return jsonify({
                'success': False,
                'error': 'Knowledge not found'
            }), 404
        
        # Check if user has access
        team = collaboration_manager.get_team(knowledge.team_id)
        if not team:
            return jsonify({
                'success': False,
                'error': 'Team not found'
            }), 404
        
        user_member = next((m for m in team.members if m.user_id == user_id), None)
        if not user_member and not knowledge.is_public:
            return jsonify({
                'success': False,
                'error': 'Access denied'
            }), 403
        
        # Increment access count
        knowledge.access_count += 1
        collaboration_manager.redis.hset(
            collaboration_manager.knowledge_key, 
            knowledge_id, 
            json.dumps(asdict(knowledge), default=str)
        )
        
        return jsonify({
            'success': True,
            'knowledge': {
                'knowledge_id': knowledge.knowledge_id,
                'title': knowledge.title,
                'content': knowledge.content,
                'type': knowledge.type,
                'category': knowledge.category,
                'created_by': knowledge.created_by,
                'created_at': knowledge.created_at.isoformat(),
                'updated_at': knowledge.updated_at.isoformat(),
                'tags': knowledge.tags,
                'access_count': knowledge.access_count,
                'rating': knowledge.rating,
                'is_public': knowledge.is_public
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting knowledge: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/collaboration/teams/<team_id>/knowledge/search', methods=['GET'])
@require_auth
def search_knowledge(team_id: str):
    """Search team knowledge"""
    try:
        user_id = request.user_id
        query = request.args.get('q', '')
        category = request.args.get('category')
        knowledge_type = request.args.get('type')
        
        # Check if user is team member
        team = collaboration_manager.get_team(team_id)
        if not team:
            return jsonify({
                'success': False,
                'error': 'Team not found'
            }), 404
        
        user_member = next((m for m in team.members if m.user_id == user_id), None)
        if not user_member:
            return jsonify({
                'success': False,
                'error': 'Access denied'
            }), 403
        
        results = collaboration_manager.search_knowledge(
            team_id=team_id,
            query=query,
            category=category,
            knowledge_type=knowledge_type
        )
        
        knowledge_items = []
        for knowledge in results:
            knowledge_items.append({
                'knowledge_id': knowledge.knowledge_id,
                'title': knowledge.title,
                'type': knowledge.type,
                'category': knowledge.category,
                'created_by': knowledge.created_by,
                'created_at': knowledge.created_at.isoformat(),
                'tags': knowledge.tags,
                'access_count': knowledge.access_count,
                'rating': knowledge.rating
            })
        
        return jsonify({
            'success': True,
            'results': knowledge_items,
            'query': query,
            'total': len(knowledge_items)
        }), 200
        
    except Exception as e:
        logger.error(f"Error searching knowledge: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Notification Endpoints
@app.route('/api/collaboration/notifications', methods=['GET'])
@require_auth
def get_notifications():
    """Get user notifications"""
    try:
        user_id = request.user_id
        unread_only = request.args.get('unread_only', 'false').lower() == 'true'
        
        notification_ids = collaboration_manager.get_user_notifications(user_id, unread_only)
        notifications = []
        
        for notification_id in notification_ids:
            notification_data = collaboration_manager.redis.hget(
                collaboration_manager.notifications_key, 
                notification_id
            )
            if notification_data:
                notification = json.loads(notification_data)
                notifications.append({
                    'notification_id': notification['notification_id'],
                    'type': notification['type'],
                    'title': notification['title'],
                    'message': notification['message'],
                    'data': notification['data'],
                    'created_at': notification['created_at'],
                    'is_read': notification.get('is_read', False),
                    'read_at': notification.get('read_at')
                })
        
        return jsonify({
            'success': True,
            'notifications': notifications
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting notifications: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/collaboration/notifications/<notification_id>/read', methods=['PUT'])
@require_auth
def mark_notification_read(notification_id: str):
    """Mark notification as read"""
    try:
        user_id = request.user_id
        
        success = collaboration_manager.mark_notification_read(notification_id, user_id)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Notification marked as read'
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to mark notification as read'
            }), 400
            
    except Exception as e:
        logger.error(f"Error marking notification read: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Analytics Endpoints
@app.route('/api/collaboration/teams/<team_id>/analytics', methods=['GET'])
@require_auth
def get_team_analytics(team_id: str):
    """Get team analytics"""
    try:
        user_id = request.user_id
        
        # Check if user is team member with analytics permission
        team = collaboration_manager.get_team(team_id)
        if not team:
            return jsonify({
                'success': False,
                'error': 'Team not found'
            }), 404
        
        user_member = next((m for m in team.members if m.user_id == user_id), None)
        if not user_member:
            return jsonify({
                'success': False,
                'error': 'Access denied'
            }), 403
        
        # Check if user has analytics permission
        if user_member.role not in [TeamRole.OWNER, TeamRole.ADMIN]:
            return jsonify({
                'success': False,
                'error': 'Insufficient permissions'
            }), 403
        
        analytics = collaboration_manager.get_team_analytics(team_id)
        
        return jsonify({
            'success': True,
            'analytics': analytics
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting team analytics: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

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
    logger.info("Starting Collaboration API server")
    app.run(host='0.0.0.0', port=5002, debug=False)

