"""
Custom AI Training API for Personal AI Assistant
Provides REST API endpoints for custom AI training and personalization
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import redis
import logging
from datetime import datetime
import json
from typing import Dict, List, Any, Optional

from custom_ai_training import (
    CustomAITrainingManager, 
    TrainingData, 
    UserProfile, 
    KnowledgeItem, 
    TrainingSession
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
CORS(app, origins="*")

# Initialize Redis and training manager
redis_client = redis.Redis(host='localhost', port=6379, db=7, decode_responses=True)
training_manager = CustomAITrainingManager(redis_client)

# Helper functions
def get_user_id_from_request():
    """Extract user ID from request headers or params"""
    user_id = request.headers.get('X-User-ID') or request.args.get('user_id')
    if not user_id:
        user_id = "default_user"  # For demo purposes
    return user_id

def validate_required_fields(data: dict, required_fields: list) -> tuple:
    """Validate required fields in request data"""
    missing_fields = [field for field in required_fields if field not in data]
    if missing_fields:
        return False, f"Missing required fields: {', '.join(missing_fields)}"
    return True, None

# Health check endpoint
@app.route('/api/training/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    try:
        # Test Redis connection
        redis_client.ping()
        
        return jsonify({
            'status': 'healthy',
            'service': 'Custom AI Training API',
            'timestamp': datetime.now().isoformat(),
            'redis_connected': True,
            'version': '1.0.0'
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

# User Profile Management
@app.route('/api/training/profile', methods=['POST'])
def create_user_profile():
    """Create a new user profile"""
    try:
        user_id = get_user_id_from_request()
        data = request.get_json() or {}
        
        initial_preferences = data.get('preferences', {})
        
        profile = training_manager.create_user_profile(user_id, initial_preferences)
        
        if profile:
            return jsonify({
                'success': True,
                'message': 'User profile created successfully',
                'profile': {
                    'user_id': profile.user_id,
                    'personalization_level': profile.personalization_level,
                    'communication_style': profile.communication_style,
                    'created_at': profile.created_at.isoformat()
                }
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to create user profile'
            }), 500
            
    except Exception as e:
        logger.error(f"Error creating user profile: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/training/profile', methods=['GET'])
def get_user_profile():
    """Get user profile"""
    try:
        user_id = get_user_id_from_request()
        
        profile = training_manager.get_user_profile(user_id)
        
        if profile:
            return jsonify({
                'success': True,
                'profile': {
                    'user_id': profile.user_id,
                    'preferences': profile.preferences,
                    'communication_style': profile.communication_style,
                    'expertise_areas': profile.expertise_areas,
                    'learning_goals': profile.learning_goals,
                    'personalization_level': profile.personalization_level,
                    'created_at': profile.created_at.isoformat(),
                    'updated_at': profile.updated_at.isoformat()
                }
            })
        else:
            return jsonify({
                'success': False,
                'error': 'User profile not found'
            }), 404
            
    except Exception as e:
        logger.error(f"Error getting user profile: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/training/profile', methods=['PUT'])
def update_user_profile():
    """Update user profile"""
    try:
        user_id = get_user_id_from_request()
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'No update data provided'
            }), 400
        
        success = training_manager.update_user_profile(user_id, data)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'User profile updated successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to update user profile'
            }), 500
            
    except Exception as e:
        logger.error(f"Error updating user profile: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Training Data Management
@app.route('/api/training/data', methods=['POST'])
def add_training_data():
    """Add training data"""
    try:
        user_id = get_user_id_from_request()
        data = request.get_json()
        
        # Validate required fields
        valid, error = validate_required_fields(data, ['data_type', 'content'])
        if not valid:
            return jsonify({
                'success': False,
                'error': error
            }), 400
        
        data_id = training_manager.add_training_data(
            user_id=user_id,
            data_type=data['data_type'],
            content=data['content'],
            metadata=data.get('metadata', {})
        )
        
        if data_id:
            return jsonify({
                'success': True,
                'message': 'Training data added successfully',
                'data_id': data_id
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to add training data'
            }), 500
            
    except Exception as e:
        logger.error(f"Error adding training data: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/training/data', methods=['GET'])
def get_training_data():
    """Get training data for user"""
    try:
        user_id = get_user_id_from_request()
        data_type = request.args.get('data_type')
        limit = int(request.args.get('limit', 100))
        
        training_data = training_manager.get_user_training_data(user_id, data_type, limit)
        
        data_list = []
        for data in training_data:
            data_list.append({
                'data_id': data.data_id,
                'data_type': data.data_type,
                'content': data.content[:200] + '...' if len(data.content) > 200 else data.content,
                'quality_score': data.quality_score,
                'created_at': data.created_at.isoformat()
            })
        
        return jsonify({
            'success': True,
            'training_data': data_list,
            'total_count': len(data_list)
        })
        
    except Exception as e:
        logger.error(f"Error getting training data: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Knowledge Base Management
@app.route('/api/training/knowledge', methods=['POST'])
def add_knowledge_item():
    """Add knowledge item"""
    try:
        user_id = get_user_id_from_request()
        data = request.get_json()
        
        # Validate required fields
        valid, error = validate_required_fields(data, ['title', 'content', 'category'])
        if not valid:
            return jsonify({
                'success': False,
                'error': error
            }), 400
        
        knowledge_id = training_manager.add_knowledge_item(
            user_id=user_id,
            title=data['title'],
            content=data['content'],
            category=data['category'],
            tags=data.get('tags', []),
            source=data.get('source', 'user_input')
        )
        
        if knowledge_id:
            return jsonify({
                'success': True,
                'message': 'Knowledge item added successfully',
                'knowledge_id': knowledge_id
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to add knowledge item'
            }), 500
            
    except Exception as e:
        logger.error(f"Error adding knowledge item: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/training/knowledge/search', methods=['GET'])
def search_knowledge():
    """Search knowledge base"""
    try:
        user_id = get_user_id_from_request()
        query = request.args.get('query', '')
        category = request.args.get('category')
        tags = request.args.getlist('tags')
        limit = int(request.args.get('limit', 10))
        
        if not query:
            return jsonify({
                'success': False,
                'error': 'Query parameter is required'
            }), 400
        
        knowledge_items = training_manager.search_knowledge(
            user_id=user_id,
            query=query,
            category=category,
            tags=tags,
            limit=limit
        )
        
        items_list = []
        for item in knowledge_items:
            items_list.append({
                'knowledge_id': item.knowledge_id,
                'title': item.title,
                'content': item.content[:300] + '...' if len(item.content) > 300 else item.content,
                'category': item.category,
                'tags': item.tags,
                'confidence': item.confidence,
                'usage_count': item.usage_count,
                'created_at': item.created_at.isoformat()
            })
        
        return jsonify({
            'success': True,
            'knowledge_items': items_list,
            'total_count': len(items_list)
        })
        
    except Exception as e:
        logger.error(f"Error searching knowledge: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/training/knowledge/<knowledge_id>/use', methods=['POST'])
def update_knowledge_usage():
    """Update knowledge item usage"""
    try:
        knowledge_id = request.view_args['knowledge_id']
        
        success = training_manager.update_knowledge_usage(knowledge_id)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Knowledge usage updated successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to update knowledge usage'
            }), 500
            
    except Exception as e:
        logger.error(f"Error updating knowledge usage: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Training Session Management
@app.route('/api/training/sessions', methods=['POST'])
def start_training_session():
    """Start a new training session"""
    try:
        user_id = get_user_id_from_request()
        data = request.get_json()
        
        # Validate required fields
        valid, error = validate_required_fields(data, ['session_type'])
        if not valid:
            return jsonify({
                'success': False,
                'error': error
            }), 400
        
        session_id = training_manager.start_training_session(
            user_id=user_id,
            session_type=data['session_type'],
            data_filter=data.get('data_filter', {})
        )
        
        if session_id:
            return jsonify({
                'success': True,
                'message': 'Training session started successfully',
                'session_id': session_id
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to start training session'
            }), 500
            
    except Exception as e:
        logger.error(f"Error starting training session: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/training/sessions/<session_id>', methods=['GET'])
def get_training_session():
    """Get training session details"""
    try:
        session_id = request.view_args['session_id']
        
        session = training_manager.get_training_session(session_id)
        
        if session:
            return jsonify({
                'success': True,
                'session': {
                    'session_id': session.session_id,
                    'user_id': session.user_id,
                    'session_type': session.session_type,
                    'status': session.status,
                    'progress': session.progress,
                    'data_points': session.data_points,
                    'improvements': session.improvements,
                    'started_at': session.started_at.isoformat(),
                    'completed_at': session.completed_at.isoformat() if session.completed_at else None
                }
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Training session not found'
            }), 404
            
    except Exception as e:
        logger.error(f"Error getting training session: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/training/sessions', methods=['GET'])
def get_user_training_sessions():
    """Get user's training sessions"""
    try:
        user_id = get_user_id_from_request()
        limit = int(request.args.get('limit', 20))
        
        sessions = training_manager.get_user_training_sessions(user_id, limit)
        
        sessions_list = []
        for session in sessions:
            sessions_list.append({
                'session_id': session.session_id,
                'session_type': session.session_type,
                'status': session.status,
                'progress': session.progress,
                'data_points': session.data_points,
                'started_at': session.started_at.isoformat(),
                'completed_at': session.completed_at.isoformat() if session.completed_at else None
            })
        
        return jsonify({
            'success': True,
            'sessions': sessions_list,
            'total_count': len(sessions_list)
        })
        
    except Exception as e:
        logger.error(f"Error getting user training sessions: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Personalization and Recommendations
@app.route('/api/training/personalization/style', methods=['GET'])
def get_personalized_response_style():
    """Get personalized response style for user"""
    try:
        user_id = get_user_id_from_request()
        
        style = training_manager.get_personalized_response_style(user_id)
        
        return jsonify({
            'success': True,
            'response_style': style
        })
        
    except Exception as e:
        logger.error(f"Error getting personalized response style: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/training/recommendations', methods=['GET'])
def get_training_recommendations():
    """Get training recommendations for user"""
    try:
        user_id = get_user_id_from_request()
        
        recommendations = training_manager.get_training_recommendations(user_id)
        
        return jsonify({
            'success': True,
            'recommendations': recommendations
        })
        
    except Exception as e:
        logger.error(f"Error getting training recommendations: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Analytics and Insights
@app.route('/api/training/analytics', methods=['GET'])
def get_training_analytics():
    """Get training analytics for user"""
    try:
        user_id = get_user_id_from_request()
        
        analytics = training_manager.get_training_analytics(user_id)
        
        return jsonify({
            'success': True,
            'analytics': analytics
        })
        
    except Exception as e:
        logger.error(f"Error getting training analytics: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Batch Operations
@app.route('/api/training/batch/feedback', methods=['POST'])
def batch_add_feedback():
    """Batch add feedback data"""
    try:
        user_id = get_user_id_from_request()
        data = request.get_json()
        
        feedback_items = data.get('feedback_items', [])
        if not feedback_items:
            return jsonify({
                'success': False,
                'error': 'No feedback items provided'
            }), 400
        
        added_count = 0
        for item in feedback_items:
            if 'content' in item and 'rating' in item:
                metadata = {
                    'user_rating': item['rating'],
                    'feedback_type': item.get('type', 'general'),
                    'context': item.get('context', '')
                }
                
                data_id = training_manager.add_training_data(
                    user_id=user_id,
                    data_type='feedback',
                    content=item['content'],
                    metadata=metadata
                )
                
                if data_id:
                    added_count += 1
        
        return jsonify({
            'success': True,
            'message': f'Added {added_count} feedback items',
            'added_count': added_count,
            'total_items': len(feedback_items)
        })
        
    except Exception as e:
        logger.error(f"Error batch adding feedback: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/training/batch/conversations', methods=['POST'])
def batch_add_conversations():
    """Batch add conversation data"""
    try:
        user_id = get_user_id_from_request()
        data = request.get_json()
        
        conversations = data.get('conversations', [])
        if not conversations:
            return jsonify({
                'success': False,
                'error': 'No conversations provided'
            }), 400
        
        added_count = 0
        for conversation in conversations:
            if 'user_message' in conversation and 'ai_response' in conversation:
                content = f"User: {conversation['user_message']}\nAI: {conversation['ai_response']}"
                metadata = {
                    'conversation_id': conversation.get('conversation_id', ''),
                    'timestamp': conversation.get('timestamp', datetime.now().isoformat()),
                    'response_length': len(conversation['ai_response']),
                    'topics': conversation.get('topics', [])
                }
                
                data_id = training_manager.add_training_data(
                    user_id=user_id,
                    data_type='conversation',
                    content=content,
                    metadata=metadata
                )
                
                if data_id:
                    added_count += 1
        
        return jsonify({
            'success': True,
            'message': f'Added {added_count} conversations',
            'added_count': added_count,
            'total_conversations': len(conversations)
        })
        
    except Exception as e:
        logger.error(f"Error batch adding conversations: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Training Categories and Configuration
@app.route('/api/training/categories', methods=['GET'])
def get_training_categories():
    """Get available training categories"""
    try:
        categories = list(redis_client.smembers("ai_training:categories"))
        
        return jsonify({
            'success': True,
            'categories': categories
        })
        
    except Exception as e:
        logger.error(f"Error getting training categories: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/training/algorithms', methods=['GET'])
def get_training_algorithms():
    """Get available training algorithms"""
    try:
        algorithms_data = redis_client.hgetall("ai_training:algorithms")
        algorithms = {}
        
        for algo_name, algo_config in algorithms_data.items():
            algorithms[algo_name] = json.loads(algo_config)
        
        return jsonify({
            'success': True,
            'algorithms': algorithms
        })
        
    except Exception as e:
        logger.error(f"Error getting training algorithms: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

if __name__ == '__main__':
    print("Starting Custom AI Training API...")
    print("API endpoints:")
    print("- POST /api/training/profile - Create user profile")
    print("- GET /api/training/profile - Get user profile")
    print("- PUT /api/training/profile - Update user profile")
    print("- POST /api/training/data - Add training data")
    print("- GET /api/training/data - Get training data")
    print("- POST /api/training/knowledge - Add knowledge item")
    print("- GET /api/training/knowledge/search - Search knowledge")
    print("- POST /api/training/sessions - Start training session")
    print("- GET /api/training/sessions/<id> - Get training session")
    print("- GET /api/training/sessions - Get user sessions")
    print("- GET /api/training/personalization/style - Get response style")
    print("- GET /api/training/recommendations - Get recommendations")
    print("- GET /api/training/analytics - Get analytics")
    print("- GET /api/training/health - Health check")
    
    app.run(host='0.0.0.0', port=5003, debug=True)

