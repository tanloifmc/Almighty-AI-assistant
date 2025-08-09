"""
Advanced Analytics API for AI Assistant
Provides REST endpoints for analytics and insights functionality
"""

import os
import json
import logging
import math
from datetime import datetime, timedelta
from typing import Dict, Any, List
from flask import Flask, request, jsonify
from flask_cors import CORS

# Import security components
from security_manager import security_manager, require_auth, require_permission

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
CORS(app, origins="*")

# Simple analytics storage (using Redis)
import redis
redis_client = redis.Redis(host='localhost', port=6379, db=6, decode_responses=True)

class SimpleAnalyticsManager:
    """Simplified analytics manager without heavy dependencies"""
    
    def __init__(self, redis_client):
        self.redis = redis_client
        self.metrics_key = "analytics:metrics"
        self.behavior_key = "analytics:behavior"
        self.performance_key = "analytics:performance"
        
    def track_user_behavior(self, user_id: str, action: str, duration: float = 0.0, 
                           context: Dict[str, Any] = None) -> bool:
        """Track user behavior"""
        try:
            behavior_data = {
                'user_id': user_id,
                'action': action,
                'duration': duration,
                'timestamp': datetime.now().isoformat(),
                'context': context or {}
            }
            
            behavior_id = f"{user_id}_{datetime.now().timestamp()}"
            self.redis.hset(self.behavior_key, behavior_id, json.dumps(behavior_data))
            
            # Add to user timeline
            user_key = f"analytics:user:{user_id}"
            self.redis.lpush(user_key, behavior_id)
            self.redis.ltrim(user_key, 0, 999)  # Keep last 1000
            
            return True
        except Exception as e:
            logger.error(f"Error tracking behavior: {str(e)}")
            return False
    
    def record_performance_metric(self, metric_name: str, value: float, 
                                 component: str, details: Dict[str, Any] = None) -> bool:
        """Record performance metric"""
        try:
            metric_data = {
                'metric_name': metric_name,
                'value': value,
                'component': component,
                'timestamp': datetime.now().isoformat(),
                'details': details or {}
            }
            
            metric_id = f"{component}_{metric_name}_{datetime.now().timestamp()}"
            self.redis.hset(self.performance_key, metric_id, json.dumps(metric_data))
            
            # Add to component timeline
            component_key = f"analytics:component:{component}"
            self.redis.lpush(component_key, metric_id)
            self.redis.ltrim(component_key, 0, 999)
            
            return True
        except Exception as e:
            logger.error(f"Error recording metric: {str(e)}")
            return False
    
    def get_user_analytics(self, user_id: str, days: int = 30) -> Dict[str, Any]:
        """Get user analytics"""
        try:
            user_key = f"analytics:user:{user_id}"
            behavior_ids = self.redis.lrange(user_key, 0, -1)
            
            behaviors = []
            for behavior_id in behavior_ids:
                behavior_data = self.redis.hget(self.behavior_key, behavior_id)
                if behavior_data:
                    behavior = json.loads(behavior_data)
                    behavior_time = datetime.fromisoformat(behavior['timestamp'])
                    if (datetime.now() - behavior_time).days <= days:
                        behaviors.append(behavior)
            
            # Calculate analytics
            total_actions = len(behaviors)
            total_duration = sum(b.get('duration', 0) for b in behaviors)
            unique_days = len(set(datetime.fromisoformat(b['timestamp']).date() for b in behaviors))
            
            action_counts = {}
            for behavior in behaviors:
                action = behavior['action']
                action_counts[action] = action_counts.get(action, 0) + 1
            
            return {
                'user_id': user_id,
                'period_days': days,
                'total_actions': total_actions,
                'total_duration': total_duration,
                'unique_active_days': unique_days,
                'average_daily_actions': total_actions / max(unique_days, 1),
                'average_daily_time': total_duration / max(unique_days, 1),
                'most_common_actions': dict(sorted(action_counts.items(), key=lambda x: x[1], reverse=True)[:10]),
                'engagement_score': min(100, (total_actions / max(days, 1)) * 2 + (total_duration / 3600) * 10)
            }
            
        except Exception as e:
            logger.error(f"Error getting user analytics: {str(e)}")
            return {}
    
    def get_system_performance(self, hours: int = 24) -> Dict[str, Any]:
        """Get system performance analytics"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            
            # Get all performance metrics
            all_metrics = self.redis.hgetall(self.performance_key)
            recent_metrics = []
            
            for metric_id, metric_data in all_metrics.items():
                metric = json.loads(metric_data)
                metric_time = datetime.fromisoformat(metric['timestamp'])
                if metric_time >= cutoff_time:
                    recent_metrics.append(metric)
            
            # Group by component and metric
            component_metrics = {}
            for metric in recent_metrics:
                component = metric['component']
                metric_name = metric['metric_name']
                
                if component not in component_metrics:
                    component_metrics[component] = {}
                if metric_name not in component_metrics[component]:
                    component_metrics[component][metric_name] = []
                
                component_metrics[component][metric_name].append(metric['value'])
            
            # Calculate statistics
            performance_summary = {}
            for component, metrics in component_metrics.items():
                component_summary = {}
                for metric_name, values in metrics.items():
                    if values:
                        component_summary[metric_name] = {
                            'current': values[-1],
                            'average': sum(values) / len(values),
                            'min': min(values),
                            'max': max(values),
                            'count': len(values)
                        }
                performance_summary[component] = component_summary
            
            # Calculate overall health score
            health_score = self._calculate_health_score(performance_summary)
            
            return {
                'period_hours': hours,
                'components': performance_summary,
                'health_score': health_score,
                'total_metrics': len(recent_metrics),
                'last_updated': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting system performance: {str(e)}")
            return {}
    
    def _calculate_health_score(self, performance_summary: Dict[str, Any]) -> float:
        """Calculate overall system health score"""
        try:
            if not performance_summary:
                return 0.0
            
            component_scores = []
            
            for component, metrics in performance_summary.items():
                component_score = 100.0
                
                for metric_name, stats in metrics.items():
                    current_value = stats['current']
                    
                    # Apply penalties based on metric type and value
                    if 'error' in metric_name.lower():
                        if current_value > 10:
                            component_score -= 30
                        elif current_value > 5:
                            component_score -= 15
                        elif current_value > 1:
                            component_score -= 5
                    
                    elif 'response_time' in metric_name.lower():
                        if current_value > 1000:  # ms
                            component_score -= 25
                        elif current_value > 500:
                            component_score -= 10
                        elif current_value > 200:
                            component_score -= 5
                    
                    elif 'cpu' in metric_name.lower() or 'memory' in metric_name.lower():
                        if current_value > 90:  # %
                            component_score -= 20
                        elif current_value > 80:
                            component_score -= 10
                        elif current_value > 70:
                            component_score -= 5
                
                component_scores.append(max(0, component_score))
            
            return sum(component_scores) / len(component_scores) if component_scores else 0.0
            
        except Exception as e:
            logger.error(f"Error calculating health score: {str(e)}")
            return 0.0
    
    def get_ai_effectiveness(self, days: int = 7) -> Dict[str, Any]:
        """Get AI effectiveness metrics"""
        try:
            cutoff_time = datetime.now() - timedelta(days=days)
            
            # Get AI-related behaviors
            ai_behaviors = []
            all_behavior_ids = self.redis.keys("analytics:user:*")
            
            for user_key in all_behavior_ids:
                behavior_ids = self.redis.lrange(user_key, 0, -1)
                for behavior_id in behavior_ids:
                    behavior_data = self.redis.hget(self.behavior_key, behavior_id)
                    if behavior_data:
                        behavior = json.loads(behavior_data)
                        behavior_time = datetime.fromisoformat(behavior['timestamp'])
                        if (behavior_time >= cutoff_time and 
                            any(keyword in behavior['action'].lower() 
                                for keyword in ['ai', 'chat', 'assistant', 'generate', 'analyze'])):
                            ai_behaviors.append(behavior)
            
            if not ai_behaviors:
                return {'period_days': days, 'total_interactions': 0}
            
            # Calculate effectiveness metrics
            total_interactions = len(ai_behaviors)
            successful_interactions = len([b for b in ai_behaviors 
                                         if b.get('context', {}).get('success', True)])
            
            avg_response_time = sum(b.get('duration', 0) for b in ai_behaviors) / total_interactions
            
            # Categorize interactions
            interaction_types = {}
            for behavior in ai_behaviors:
                action = behavior['action']
                interaction_types[action] = interaction_types.get(action, 0) + 1
            
            return {
                'period_days': days,
                'total_interactions': total_interactions,
                'successful_interactions': successful_interactions,
                'success_rate': successful_interactions / total_interactions,
                'average_response_time': avg_response_time,
                'interaction_types': dict(sorted(interaction_types.items(), key=lambda x: x[1], reverse=True)),
                'effectiveness_score': min(100, (successful_interactions / total_interactions) * 100)
            }
            
        except Exception as e:
            logger.error(f"Error getting AI effectiveness: {str(e)}")
            return {}
    
    def generate_insights(self, analytics_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate simple insights from analytics data"""
        insights = []
        
        try:
            # User engagement insights
            if 'engagement_score' in analytics_data:
                score = analytics_data['engagement_score']
                if score >= 80:
                    insights.append({
                        'type': 'positive',
                        'title': 'High User Engagement',
                        'description': f'User engagement is excellent at {score:.1f}%',
                        'recommendations': ['Continue current engagement strategies', 'Monitor for sustainability']
                    })
                elif score < 40:
                    insights.append({
                        'type': 'warning',
                        'title': 'Low User Engagement',
                        'description': f'User engagement is low at {score:.1f}%',
                        'recommendations': ['Improve user experience', 'Add more interactive features', 'Conduct user feedback survey']
                    })
            
            # Performance insights
            if 'health_score' in analytics_data:
                health = analytics_data['health_score']
                if health < 70:
                    insights.append({
                        'type': 'critical',
                        'title': 'System Health Issues',
                        'description': f'System health is below optimal at {health:.1f}%',
                        'recommendations': ['Investigate performance bottlenecks', 'Scale infrastructure', 'Optimize database queries']
                    })
                elif health >= 90:
                    insights.append({
                        'type': 'positive',
                        'title': 'Excellent System Health',
                        'description': f'System is performing optimally at {health:.1f}%',
                        'recommendations': ['Maintain current practices', 'Plan for future scaling']
                    })
            
            # AI effectiveness insights
            if 'success_rate' in analytics_data:
                success_rate = analytics_data['success_rate']
                if success_rate < 0.8:
                    insights.append({
                        'type': 'warning',
                        'title': 'AI Effectiveness Needs Improvement',
                        'description': f'AI success rate is {success_rate*100:.1f}%',
                        'recommendations': ['Improve AI training data', 'Optimize prompts', 'Add error handling']
                    })
                elif success_rate >= 0.95:
                    insights.append({
                        'type': 'positive',
                        'title': 'Excellent AI Performance',
                        'description': f'AI success rate is {success_rate*100:.1f}%',
                        'recommendations': ['Document successful practices', 'Share learnings with team']
                    })
            
        except Exception as e:
            logger.error(f"Error generating insights: {str(e)}")
        
        return insights

# Initialize analytics manager
analytics_manager = SimpleAnalyticsManager(redis_client)

@app.route('/api/analytics/health', methods=['GET'])
def analytics_health():
    """Health check for analytics system"""
    try:
        # Test Redis connection
        redis_client.ping()
        
        return jsonify({
            'status': 'healthy',
            'analytics_system': {
                'redis_connection': True,
                'user_tracking': True,
                'performance_monitoring': True,
                'ai_effectiveness': True,
                'insights_generation': True,
                'timestamp': datetime.now().isoformat()
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Analytics health check failed: {str(e)}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500

@app.route('/api/analytics/track', methods=['POST'])
@require_auth
def track_behavior():
    """Track user behavior"""
    try:
        data = request.get_json()
        user_id = request.user_id
        
        action = data.get('action')
        duration = data.get('duration', 0.0)
        context = data.get('context', {})
        
        if not action:
            return jsonify({
                'success': False,
                'error': 'Action is required'
            }), 400
        
        success = analytics_manager.track_user_behavior(user_id, action, duration, context)
        
        return jsonify({
            'success': success,
            'message': 'Behavior tracked successfully' if success else 'Failed to track behavior'
        }), 200 if success else 500
        
    except Exception as e:
        logger.error(f"Error tracking behavior: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/analytics/performance', methods=['POST'])
@require_auth
def record_performance():
    """Record performance metric"""
    try:
        data = request.get_json()
        
        metric_name = data.get('metric_name')
        value = data.get('value')
        component = data.get('component')
        details = data.get('details', {})
        
        if not all([metric_name, value is not None, component]):
            return jsonify({
                'success': False,
                'error': 'metric_name, value, and component are required'
            }), 400
        
        success = analytics_manager.record_performance_metric(metric_name, value, component, details)
        
        return jsonify({
            'success': success,
            'message': 'Performance metric recorded successfully' if success else 'Failed to record metric'
        }), 200 if success else 500
        
    except Exception as e:
        logger.error(f"Error recording performance: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/analytics/user/<user_id>', methods=['GET'])
@require_auth
def get_user_analytics(user_id: str):
    """Get user analytics"""
    try:
        current_user_id = request.user_id
        
        # Users can only access their own analytics unless they're admin
        if current_user_id != user_id:
            user_data = request.user_data
            if user_data.get('role') != 'admin':
                return jsonify({
                    'success': False,
                    'error': 'Access denied'
                }), 403
        
        days = int(request.args.get('days', 30))
        analytics = analytics_manager.get_user_analytics(user_id, days)
        
        # Generate insights
        insights = analytics_manager.generate_insights(analytics)
        analytics['insights'] = insights
        
        return jsonify({
            'success': True,
            'analytics': analytics
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting user analytics: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/analytics/system/performance', methods=['GET'])
@require_auth
def get_system_performance():
    """Get system performance analytics"""
    try:
        # Check if user has admin permissions
        user_data = request.user_data
        if user_data.get('role') not in ['admin', 'moderator']:
            return jsonify({
                'success': False,
                'error': 'Admin access required'
            }), 403
        
        hours = int(request.args.get('hours', 24))
        performance = analytics_manager.get_system_performance(hours)
        
        # Generate insights
        insights = analytics_manager.generate_insights(performance)
        performance['insights'] = insights
        
        return jsonify({
            'success': True,
            'performance': performance
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting system performance: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/analytics/ai/effectiveness', methods=['GET'])
@require_auth
def get_ai_effectiveness():
    """Get AI effectiveness analytics"""
    try:
        # Check if user has admin permissions
        user_data = request.user_data
        if user_data.get('role') not in ['admin', 'moderator']:
            return jsonify({
                'success': False,
                'error': 'Admin access required'
            }), 403
        
        days = int(request.args.get('days', 7))
        effectiveness = analytics_manager.get_ai_effectiveness(days)
        
        # Generate insights
        insights = analytics_manager.generate_insights(effectiveness)
        effectiveness['insights'] = insights
        
        return jsonify({
            'success': True,
            'effectiveness': effectiveness
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting AI effectiveness: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/analytics/dashboard', methods=['GET'])
@require_auth
def get_analytics_dashboard():
    """Get comprehensive analytics dashboard"""
    try:
        user_id = request.user_id
        user_data = request.user_data
        
        dashboard = {
            'user_analytics': analytics_manager.get_user_analytics(user_id, 30),
            'timestamp': datetime.now().isoformat()
        }
        
        # Add system-wide analytics for admins
        if user_data.get('role') in ['admin', 'moderator']:
            dashboard['system_performance'] = analytics_manager.get_system_performance(24)
            dashboard['ai_effectiveness'] = analytics_manager.get_ai_effectiveness(7)
        
        # Generate combined insights
        all_data = {}
        for key, value in dashboard.items():
            if isinstance(value, dict):
                all_data.update(value)
        
        dashboard['insights'] = analytics_manager.generate_insights(all_data)
        
        return jsonify({
            'success': True,
            'dashboard': dashboard
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting analytics dashboard: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/analytics/insights', methods=['GET'])
@require_auth
def get_insights():
    """Get AI-generated insights"""
    try:
        user_id = request.user_id
        user_data = request.user_data
        
        # Get user analytics
        user_analytics = analytics_manager.get_user_analytics(user_id, 30)
        insights_data = user_analytics.copy()
        
        # Add system analytics for admins
        if user_data.get('role') in ['admin', 'moderator']:
            system_performance = analytics_manager.get_system_performance(24)
            ai_effectiveness = analytics_manager.get_ai_effectiveness(7)
            insights_data.update(system_performance)
            insights_data.update(ai_effectiveness)
        
        # Generate insights
        insights = analytics_manager.generate_insights(insights_data)
        
        return jsonify({
            'success': True,
            'insights': insights,
            'generated_at': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting insights: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/analytics/export', methods=['GET'])
@require_auth
def export_analytics():
    """Export analytics data"""
    try:
        user_id = request.user_id
        user_data = request.user_data
        
        export_type = request.args.get('type', 'user')  # user, system, all
        format_type = request.args.get('format', 'json')  # json, csv
        days = int(request.args.get('days', 30))
        
        export_data = {}
        
        if export_type in ['user', 'all']:
            export_data['user_analytics'] = analytics_manager.get_user_analytics(user_id, days)
        
        if export_type in ['system', 'all'] and user_data.get('role') in ['admin', 'moderator']:
            export_data['system_performance'] = analytics_manager.get_system_performance(days * 24)
            export_data['ai_effectiveness'] = analytics_manager.get_ai_effectiveness(days)
        
        export_data['export_info'] = {
            'exported_by': user_id,
            'export_type': export_type,
            'period_days': days,
            'exported_at': datetime.now().isoformat()
        }
        
        if format_type == 'json':
            return jsonify({
                'success': True,
                'data': export_data
            }), 200
        else:
            # For CSV format, we'd need to flatten the data structure
            return jsonify({
                'success': False,
                'error': 'CSV export not implemented yet'
            }), 501
        
    except Exception as e:
        logger.error(f"Error exporting analytics: {str(e)}")
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
    logger.info("Starting Advanced Analytics API server")
    app.run(host='0.0.0.0', port=5003, debug=False)

