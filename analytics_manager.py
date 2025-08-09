"""
Advanced Analytics Manager for AI Assistant
Provides comprehensive analytics, insights, and data visualization capabilities
"""

import os
import json
import logging
import redis
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict, Counter
import uuid

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set matplotlib backend for headless environment
plt.switch_backend('Agg')

# Configure fonts for better text rendering
plt.rcParams['font.family'] = ['DejaVu Sans', 'Liberation Sans', 'Arial', 'sans-serif']
plt.rcParams['font.size'] = 10
plt.rcParams['axes.unicode_minus'] = False

@dataclass
class AnalyticsMetric:
    metric_id: str
    name: str
    value: float
    unit: str
    category: str
    timestamp: datetime
    metadata: Dict[str, Any]

@dataclass
class UserBehaviorData:
    user_id: str
    session_id: str
    action: str
    timestamp: datetime
    duration: float
    context: Dict[str, Any]

@dataclass
class PerformanceMetric:
    metric_name: str
    value: float
    timestamp: datetime
    component: str
    details: Dict[str, Any]

@dataclass
class AIInsight:
    insight_id: str
    title: str
    description: str
    category: str
    confidence: float
    data_points: List[Dict[str, Any]]
    recommendations: List[str]
    created_at: datetime

class AdvancedAnalyticsManager:
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.metrics_key = "analytics:metrics"
        self.behavior_key = "analytics:behavior"
        self.performance_key = "analytics:performance"
        self.insights_key = "analytics:insights"
        self.reports_key = "analytics:reports"
        
        # Initialize analytics storage
        self._initialize_analytics()
        
    def _initialize_analytics(self):
        """Initialize analytics storage and default metrics"""
        try:
            # Create default metric categories
            default_categories = [
                "user_engagement",
                "system_performance",
                "ai_effectiveness",
                "collaboration_metrics",
                "workflow_efficiency",
                "knowledge_usage",
                "error_tracking",
                "resource_utilization"
            ]
            
            for category in default_categories:
                self.redis.sadd("analytics:categories", category)
                
            logger.info("Analytics system initialized")
            
        except Exception as e:
            logger.error(f"Error initializing analytics: {str(e)}")

    # Data Collection Methods
    def track_user_behavior(self, user_id: str, action: str, duration: float = 0.0, 
                           context: Dict[str, Any] = None) -> bool:
        """Track user behavior and interactions"""
        try:
            session_id = context.get('session_id', str(uuid.uuid4())) if context else str(uuid.uuid4())
            
            behavior_data = UserBehaviorData(
                user_id=user_id,
                session_id=session_id,
                action=action,
                timestamp=datetime.now(),
                duration=duration,
                context=context or {}
            )
            
            # Store behavior data
            behavior_id = str(uuid.uuid4())
            self.redis.hset(
                self.behavior_key, 
                behavior_id, 
                json.dumps(asdict(behavior_data), default=str)
            )
            
            # Add to user's behavior timeline
            user_behavior_key = f"analytics:user_behavior:{user_id}"
            self.redis.lpush(user_behavior_key, behavior_id)
            self.redis.ltrim(user_behavior_key, 0, 999)  # Keep last 1000 actions
            
            # Update real-time metrics
            self._update_realtime_metrics(user_id, action, duration)
            
            return True
            
        except Exception as e:
            logger.error(f"Error tracking user behavior: {str(e)}")
            return False

    def record_performance_metric(self, metric_name: str, value: float, 
                                 component: str, details: Dict[str, Any] = None) -> bool:
        """Record system performance metrics"""
        try:
            performance_data = PerformanceMetric(
                metric_name=metric_name,
                value=value,
                timestamp=datetime.now(),
                component=component,
                details=details or {}
            )
            
            # Store performance data
            metric_id = str(uuid.uuid4())
            self.redis.hset(
                self.performance_key,
                metric_id,
                json.dumps(asdict(performance_data), default=str)
            )
            
            # Add to component's metrics timeline
            component_metrics_key = f"analytics:component_metrics:{component}"
            self.redis.lpush(component_metrics_key, metric_id)
            self.redis.ltrim(component_metrics_key, 0, 999)  # Keep last 1000 metrics
            
            # Update performance alerts if needed
            self._check_performance_alerts(metric_name, value, component)
            
            return True
            
        except Exception as e:
            logger.error(f"Error recording performance metric: {str(e)}")
            return False

    def store_analytics_metric(self, name: str, value: float, unit: str, 
                              category: str, metadata: Dict[str, Any] = None) -> bool:
        """Store custom analytics metric"""
        try:
            metric = AnalyticsMetric(
                metric_id=str(uuid.uuid4()),
                name=name,
                value=value,
                unit=unit,
                category=category,
                timestamp=datetime.now(),
                metadata=metadata or {}
            )
            
            # Store metric
            self.redis.hset(
                self.metrics_key,
                metric.metric_id,
                json.dumps(asdict(metric), default=str)
            )
            
            # Add to category timeline
            category_key = f"analytics:category_metrics:{category}"
            self.redis.lpush(category_key, metric.metric_id)
            self.redis.ltrim(category_key, 0, 999)
            
            return True
            
        except Exception as e:
            logger.error(f"Error storing analytics metric: {str(e)}")
            return False

    # Analytics Query Methods
    def get_user_analytics(self, user_id: str, days: int = 30) -> Dict[str, Any]:
        """Get comprehensive user analytics"""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            # Get user behavior data
            user_behavior_key = f"analytics:user_behavior:{user_id}"
            behavior_ids = self.redis.lrange(user_behavior_key, 0, -1)
            
            behaviors = []
            for behavior_id in behavior_ids:
                behavior_data = self.redis.hget(self.behavior_key, behavior_id)
                if behavior_data:
                    behavior = json.loads(behavior_data)
                    behavior_time = datetime.fromisoformat(behavior['timestamp'])
                    if start_date <= behavior_time <= end_date:
                        behaviors.append(behavior)
            
            # Analyze user patterns
            analytics = self._analyze_user_patterns(behaviors)
            
            # Add user engagement metrics
            analytics.update(self._calculate_user_engagement(behaviors))
            
            # Add productivity insights
            analytics.update(self._calculate_productivity_metrics(behaviors))
            
            return analytics
            
        except Exception as e:
            logger.error(f"Error getting user analytics: {str(e)}")
            return {}

    def get_system_performance_analytics(self, hours: int = 24) -> Dict[str, Any]:
        """Get system performance analytics"""
        try:
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=hours)
            
            # Get all performance metrics
            performance_data = []
            all_metrics = self.redis.hgetall(self.performance_key)
            
            for metric_id, metric_data in all_metrics.items():
                metric = json.loads(metric_data)
                metric_time = datetime.fromisoformat(metric['timestamp'])
                if start_time <= metric_time <= end_time:
                    performance_data.append(metric)
            
            # Analyze performance trends
            analytics = self._analyze_performance_trends(performance_data)
            
            # Add system health metrics
            analytics.update(self._calculate_system_health(performance_data))
            
            # Add resource utilization
            analytics.update(self._calculate_resource_utilization(performance_data))
            
            return analytics
            
        except Exception as e:
            logger.error(f"Error getting system performance analytics: {str(e)}")
            return {}

    def get_ai_effectiveness_analytics(self, days: int = 7) -> Dict[str, Any]:
        """Get AI effectiveness and accuracy analytics"""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            # Get AI-related behavior data
            ai_behaviors = []
            all_behavior_ids = self.redis.keys("analytics:user_behavior:*")
            
            for user_behavior_key in all_behavior_ids:
                behavior_ids = self.redis.lrange(user_behavior_key, 0, -1)
                for behavior_id in behavior_ids:
                    behavior_data = self.redis.hget(self.behavior_key, behavior_id)
                    if behavior_data:
                        behavior = json.loads(behavior_data)
                        behavior_time = datetime.fromisoformat(behavior['timestamp'])
                        if (start_date <= behavior_time <= end_date and 
                            'ai' in behavior['action'].lower()):
                            ai_behaviors.append(behavior)
            
            # Analyze AI effectiveness
            analytics = self._analyze_ai_effectiveness(ai_behaviors)
            
            # Add conversation quality metrics
            analytics.update(self._calculate_conversation_quality(ai_behaviors))
            
            # Add task completion rates
            analytics.update(self._calculate_task_completion_rates(ai_behaviors))
            
            return analytics
            
        except Exception as e:
            logger.error(f"Error getting AI effectiveness analytics: {str(e)}")
            return {}

    def get_collaboration_analytics(self, team_id: str = None, days: int = 30) -> Dict[str, Any]:
        """Get team collaboration analytics"""
        try:
            # Import collaboration manager to get team data
            from collaboration_manager import collaboration_manager
            
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            if team_id:
                teams = [collaboration_manager.get_team(team_id)]
            else:
                # Get all teams (simplified for demo)
                teams = []
            
            analytics = {
                'team_performance': {},
                'collaboration_patterns': {},
                'knowledge_sharing': {},
                'task_efficiency': {}
            }
            
            for team in teams:
                if not team:
                    continue
                    
                team_analytics = collaboration_manager.get_team_analytics(team.team_id)
                analytics['team_performance'][team.team_id] = team_analytics
                
                # Add collaboration patterns analysis
                analytics['collaboration_patterns'][team.team_id] = self._analyze_collaboration_patterns(team)
            
            return analytics
            
        except Exception as e:
            logger.error(f"Error getting collaboration analytics: {str(e)}")
            return {}

    # Data Analysis Methods
    def _analyze_user_patterns(self, behaviors: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze user behavior patterns"""
        if not behaviors:
            return {'user_patterns': {}}
        
        # Convert to DataFrame for analysis
        df = pd.DataFrame(behaviors)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['hour'] = df['timestamp'].dt.hour
        df['day_of_week'] = df['timestamp'].dt.day_name()
        
        patterns = {
            'most_active_hours': df['hour'].value_counts().head(5).to_dict(),
            'most_active_days': df['day_of_week'].value_counts().to_dict(),
            'common_actions': df['action'].value_counts().head(10).to_dict(),
            'average_session_duration': df['duration'].mean(),
            'total_actions': len(behaviors),
            'unique_sessions': df['session_id'].nunique()
        }
        
        return {'user_patterns': patterns}

    def _calculate_user_engagement(self, behaviors: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate user engagement metrics"""
        if not behaviors:
            return {'engagement': {}}
        
        df = pd.DataFrame(behaviors)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # Calculate engagement metrics
        total_time = df['duration'].sum()
        unique_days = df['timestamp'].dt.date.nunique()
        avg_daily_time = total_time / max(unique_days, 1)
        
        engagement = {
            'total_time_spent': total_time,
            'average_daily_time': avg_daily_time,
            'session_frequency': len(df) / max(unique_days, 1),
            'engagement_score': min(100, (avg_daily_time / 3600) * 20 + (len(df) / max(unique_days, 1)) * 5)
        }
        
        return {'engagement': engagement}

    def _calculate_productivity_metrics(self, behaviors: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate productivity metrics"""
        if not behaviors:
            return {'productivity': {}}
        
        df = pd.DataFrame(behaviors)
        
        # Categorize actions by productivity
        productive_actions = ['create_task', 'complete_task', 'share_knowledge', 'create_workflow']
        communication_actions = ['send_message', 'voice_chat', 'team_discussion']
        
        productive_count = df[df['action'].isin(productive_actions)].shape[0]
        communication_count = df[df['action'].isin(communication_actions)].shape[0]
        total_count = len(df)
        
        productivity = {
            'productive_actions': productive_count,
            'communication_actions': communication_count,
            'productivity_ratio': productive_count / max(total_count, 1),
            'communication_ratio': communication_count / max(total_count, 1),
            'productivity_score': min(100, (productive_count / max(total_count, 1)) * 100)
        }
        
        return {'productivity': productivity}

    def _analyze_performance_trends(self, performance_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze system performance trends"""
        if not performance_data:
            return {'performance_trends': {}}
        
        df = pd.DataFrame(performance_data)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # Group by metric name and calculate trends
        trends = {}
        for metric_name in df['metric_name'].unique():
            metric_df = df[df['metric_name'] == metric_name].sort_values('timestamp')
            
            if len(metric_df) > 1:
                # Calculate trend (simple linear regression slope)
                x = np.arange(len(metric_df))
                y = metric_df['value'].values
                slope = np.polyfit(x, y, 1)[0]
                
                trends[metric_name] = {
                    'current_value': float(metric_df['value'].iloc[-1]),
                    'average_value': float(metric_df['value'].mean()),
                    'trend_slope': float(slope),
                    'trend_direction': 'increasing' if slope > 0 else 'decreasing' if slope < 0 else 'stable',
                    'data_points': len(metric_df)
                }
        
        return {'performance_trends': trends}

    def _calculate_system_health(self, performance_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate overall system health score"""
        if not performance_data:
            return {'system_health': {'score': 0, 'status': 'unknown'}}
        
        df = pd.DataFrame(performance_data)
        
        # Define health thresholds
        health_thresholds = {
            'response_time': {'good': 200, 'warning': 500, 'critical': 1000},
            'cpu_usage': {'good': 70, 'warning': 85, 'critical': 95},
            'memory_usage': {'good': 70, 'warning': 85, 'critical': 95},
            'error_rate': {'good': 1, 'warning': 5, 'critical': 10}
        }
        
        health_scores = []
        component_health = {}
        
        for component in df['component'].unique():
            component_df = df[df['component'] == component]
            component_score = 100
            
            for metric_name in component_df['metric_name'].unique():
                metric_values = component_df[component_df['metric_name'] == metric_name]['value']
                avg_value = metric_values.mean()
                
                if metric_name in health_thresholds:
                    thresholds = health_thresholds[metric_name]
                    if avg_value > thresholds['critical']:
                        component_score -= 30
                    elif avg_value > thresholds['warning']:
                        component_score -= 15
                    elif avg_value > thresholds['good']:
                        component_score -= 5
            
            component_health[component] = max(0, component_score)
            health_scores.append(component_score)
        
        overall_health = np.mean(health_scores) if health_scores else 0
        
        # Determine status
        if overall_health >= 90:
            status = 'excellent'
        elif overall_health >= 75:
            status = 'good'
        elif overall_health >= 60:
            status = 'warning'
        else:
            status = 'critical'
        
        return {
            'system_health': {
                'score': float(overall_health),
                'status': status,
                'component_health': component_health,
                'last_updated': datetime.now().isoformat()
            }
        }

    def _calculate_resource_utilization(self, performance_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate resource utilization metrics"""
        if not performance_data:
            return {'resource_utilization': {}}
        
        df = pd.DataFrame(performance_data)
        
        # Calculate resource utilization by component
        utilization = {}
        
        for component in df['component'].unique():
            component_df = df[df['component'] == component]
            
            component_utilization = {}
            for metric_name in component_df['metric_name'].unique():
                metric_values = component_df[component_df['metric_name'] == metric_name]['value']
                component_utilization[metric_name] = {
                    'current': float(metric_values.iloc[-1]) if len(metric_values) > 0 else 0,
                    'average': float(metric_values.mean()),
                    'peak': float(metric_values.max()),
                    'minimum': float(metric_values.min())
                }
            
            utilization[component] = component_utilization
        
        return {'resource_utilization': utilization}

    def _analyze_ai_effectiveness(self, ai_behaviors: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze AI effectiveness metrics"""
        if not ai_behaviors:
            return {'ai_effectiveness': {}}
        
        df = pd.DataFrame(ai_behaviors)
        
        # Calculate AI effectiveness metrics
        total_interactions = len(df)
        successful_interactions = len(df[df['context'].apply(
            lambda x: x.get('success', True) if isinstance(x, dict) else True
        )])
        
        avg_response_time = df['duration'].mean()
        
        effectiveness = {
            'total_interactions': total_interactions,
            'successful_interactions': successful_interactions,
            'success_rate': successful_interactions / max(total_interactions, 1),
            'average_response_time': float(avg_response_time),
            'effectiveness_score': min(100, (successful_interactions / max(total_interactions, 1)) * 100)
        }
        
        return {'ai_effectiveness': effectiveness}

    def _calculate_conversation_quality(self, ai_behaviors: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate conversation quality metrics"""
        if not ai_behaviors:
            return {'conversation_quality': {}}
        
        # Simplified conversation quality analysis
        conversation_actions = [b for b in ai_behaviors if 'chat' in b['action'].lower()]
        
        if not conversation_actions:
            return {'conversation_quality': {}}
        
        total_conversations = len(conversation_actions)
        avg_conversation_length = np.mean([
            b['context'].get('message_length', 0) if isinstance(b['context'], dict) else 0
            for b in conversation_actions
        ])
        
        quality = {
            'total_conversations': total_conversations,
            'average_conversation_length': float(avg_conversation_length),
            'quality_score': min(100, avg_conversation_length / 10)  # Simplified scoring
        }
        
        return {'conversation_quality': quality}

    def _calculate_task_completion_rates(self, ai_behaviors: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate task completion rates"""
        if not ai_behaviors:
            return {'task_completion': {}}
        
        task_actions = [b for b in ai_behaviors if 'task' in b['action'].lower()]
        
        if not task_actions:
            return {'task_completion': {}}
        
        completed_tasks = len([b for b in task_actions if 'complete' in b['action'].lower()])
        total_tasks = len(task_actions)
        
        completion = {
            'total_tasks': total_tasks,
            'completed_tasks': completed_tasks,
            'completion_rate': completed_tasks / max(total_tasks, 1),
            'completion_score': min(100, (completed_tasks / max(total_tasks, 1)) * 100)
        }
        
        return {'task_completion': completion}

    def _analyze_collaboration_patterns(self, team) -> Dict[str, Any]:
        """Analyze team collaboration patterns"""
        # Simplified collaboration analysis
        patterns = {
            'team_size': len(team.members),
            'active_members': len([m for m in team.members if 
                                 (datetime.now() - m.last_active).days < 7]),
            'collaboration_score': min(100, len(team.members) * 10)
        }
        
        return patterns

    # Real-time Analytics Methods
    def _update_realtime_metrics(self, user_id: str, action: str, duration: float):
        """Update real-time metrics"""
        try:
            # Update action counters
            action_key = f"analytics:realtime:actions:{action}"
            self.redis.incr(action_key)
            self.redis.expire(action_key, 3600)  # Expire after 1 hour
            
            # Update user activity
            user_activity_key = f"analytics:realtime:users:{user_id}"
            self.redis.hset(user_activity_key, "last_action", action)
            self.redis.hset(user_activity_key, "last_seen", datetime.now().isoformat())
            self.redis.expire(user_activity_key, 86400)  # Expire after 24 hours
            
            # Update duration metrics
            if duration > 0:
                duration_key = f"analytics:realtime:durations:{action}"
                current_avg = float(self.redis.hget(duration_key, "average") or 0)
                current_count = int(self.redis.hget(duration_key, "count") or 0)
                
                new_avg = ((current_avg * current_count) + duration) / (current_count + 1)
                
                self.redis.hset(duration_key, "average", new_avg)
                self.redis.hset(duration_key, "count", current_count + 1)
                self.redis.expire(duration_key, 3600)
                
        except Exception as e:
            logger.error(f"Error updating realtime metrics: {str(e)}")

    def _check_performance_alerts(self, metric_name: str, value: float, component: str):
        """Check for performance alerts"""
        try:
            # Define alert thresholds
            alert_thresholds = {
                'response_time': 1000,  # ms
                'cpu_usage': 90,        # %
                'memory_usage': 90,     # %
                'error_rate': 10        # %
            }
            
            if metric_name in alert_thresholds and value > alert_thresholds[metric_name]:
                alert = {
                    'alert_id': str(uuid.uuid4()),
                    'metric_name': metric_name,
                    'value': value,
                    'threshold': alert_thresholds[metric_name],
                    'component': component,
                    'severity': 'high' if value > alert_thresholds[metric_name] * 1.2 else 'medium',
                    'timestamp': datetime.now().isoformat()
                }
                
                # Store alert
                alerts_key = "analytics:alerts"
                self.redis.lpush(alerts_key, json.dumps(alert))
                self.redis.ltrim(alerts_key, 0, 99)  # Keep last 100 alerts
                
                logger.warning(f"Performance alert: {metric_name} = {value} for {component}")
                
        except Exception as e:
            logger.error(f"Error checking performance alerts: {str(e)}")

    # Visualization Methods
    def generate_analytics_charts(self, analytics_data: Dict[str, Any], 
                                 output_dir: str = "/tmp") -> List[str]:
        """Generate analytics visualization charts"""
        try:
            chart_files = []
            
            # User engagement chart
            if 'engagement' in analytics_data:
                engagement_chart = self._create_engagement_chart(
                    analytics_data['engagement'], 
                    os.path.join(output_dir, "engagement_chart.png")
                )
                if engagement_chart:
                    chart_files.append(engagement_chart)
            
            # Performance trends chart
            if 'performance_trends' in analytics_data:
                performance_chart = self._create_performance_chart(
                    analytics_data['performance_trends'],
                    os.path.join(output_dir, "performance_chart.png")
                )
                if performance_chart:
                    chart_files.append(performance_chart)
            
            # System health chart
            if 'system_health' in analytics_data:
                health_chart = self._create_health_chart(
                    analytics_data['system_health'],
                    os.path.join(output_dir, "health_chart.png")
                )
                if health_chart:
                    chart_files.append(health_chart)
            
            return chart_files
            
        except Exception as e:
            logger.error(f"Error generating analytics charts: {str(e)}")
            return []

    def _create_engagement_chart(self, engagement_data: Dict[str, Any], output_path: str) -> str:
        """Create user engagement visualization"""
        try:
            fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(12, 8))
            fig.suptitle('User Engagement Analytics', fontsize=16, fontweight='bold')
            
            # Engagement score gauge
            score = engagement_data.get('engagement_score', 0)
            ax1.pie([score, 100-score], labels=['Engaged', 'Remaining'], 
                   colors=['#4CAF50', '#E0E0E0'], startangle=90)
            ax1.set_title(f'Engagement Score: {score:.1f}%')
            
            # Daily time spent
            daily_time = engagement_data.get('average_daily_time', 0) / 3600  # Convert to hours
            ax2.bar(['Daily Time'], [daily_time], color='#2196F3')
            ax2.set_ylabel('Hours')
            ax2.set_title('Average Daily Time Spent')
            
            # Session frequency
            frequency = engagement_data.get('session_frequency', 0)
            ax3.bar(['Session Frequency'], [frequency], color='#FF9800')
            ax3.set_ylabel('Sessions per Day')
            ax3.set_title('Session Frequency')
            
            # Total time
            total_time = engagement_data.get('total_time_spent', 0) / 3600  # Convert to hours
            ax4.bar(['Total Time'], [total_time], color='#9C27B0')
            ax4.set_ylabel('Hours')
            ax4.set_title('Total Time Spent')
            
            plt.tight_layout()
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
            plt.close()
            
            return output_path
            
        except Exception as e:
            logger.error(f"Error creating engagement chart: {str(e)}")
            return None

    def _create_performance_chart(self, performance_data: Dict[str, Any], output_path: str) -> str:
        """Create performance trends visualization"""
        try:
            metrics = list(performance_data.keys())
            if not metrics:
                return None
            
            fig, axes = plt.subplots(2, 2, figsize=(12, 8))
            fig.suptitle('System Performance Trends', fontsize=16, fontweight='bold')
            axes = axes.flatten()
            
            for i, metric_name in enumerate(metrics[:4]):  # Show up to 4 metrics
                if i >= len(axes):
                    break
                    
                metric_data = performance_data[metric_name]
                current_value = metric_data.get('current_value', 0)
                average_value = metric_data.get('average_value', 0)
                trend_direction = metric_data.get('trend_direction', 'stable')
                
                # Create bar chart for current vs average
                axes[i].bar(['Current', 'Average'], [current_value, average_value], 
                           color=['#4CAF50' if trend_direction == 'decreasing' else '#F44336', '#2196F3'])
                axes[i].set_title(f'{metric_name.replace("_", " ").title()}')
                axes[i].set_ylabel('Value')
                
                # Add trend indicator
                trend_color = {'increasing': 'red', 'decreasing': 'green', 'stable': 'gray'}
                axes[i].text(0.5, max(current_value, average_value) * 0.8, 
                           f'Trend: {trend_direction}', 
                           ha='center', color=trend_color.get(trend_direction, 'gray'))
            
            # Hide unused subplots
            for i in range(len(metrics), len(axes)):
                axes[i].set_visible(False)
            
            plt.tight_layout()
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
            plt.close()
            
            return output_path
            
        except Exception as e:
            logger.error(f"Error creating performance chart: {str(e)}")
            return None

    def _create_health_chart(self, health_data: Dict[str, Any], output_path: str) -> str:
        """Create system health visualization"""
        try:
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
            fig.suptitle('System Health Overview', fontsize=16, fontweight='bold')
            
            # Overall health score gauge
            score = health_data.get('score', 0)
            status = health_data.get('status', 'unknown')
            
            # Create gauge chart
            colors = ['#F44336', '#FF9800', '#4CAF50']  # Red, Orange, Green
            sizes = [33.33, 33.33, 33.34]
            
            wedges, texts = ax1.pie(sizes, colors=colors, startangle=180, 
                                   counterclock=False, wedgeprops=dict(width=0.3))
            
            # Add score indicator
            angle = 180 - (score / 100) * 180
            ax1.annotate('', xy=(0.7 * np.cos(np.radians(angle)), 0.7 * np.sin(np.radians(angle))), 
                        xytext=(0, 0), arrowprops=dict(arrowstyle='->', lw=3, color='black'))
            
            ax1.set_title(f'Health Score: {score:.1f}%\nStatus: {status.title()}')
            
            # Component health breakdown
            component_health = health_data.get('component_health', {})
            if component_health:
                components = list(component_health.keys())
                scores = list(component_health.values())
                
                bars = ax2.barh(components, scores, color=['#4CAF50' if s >= 80 else '#FF9800' if s >= 60 else '#F44336' for s in scores])
                ax2.set_xlabel('Health Score')
                ax2.set_title('Component Health')
                ax2.set_xlim(0, 100)
                
                # Add score labels
                for i, (bar, score) in enumerate(zip(bars, scores)):
                    ax2.text(score + 2, i, f'{score:.1f}%', va='center')
            
            plt.tight_layout()
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
            plt.close()
            
            return output_path
            
        except Exception as e:
            logger.error(f"Error creating health chart: {str(e)}")
            return None

    # AI Insights Generation
    def generate_ai_insights(self, analytics_data: Dict[str, Any]) -> List[AIInsight]:
        """Generate AI-powered insights from analytics data"""
        try:
            insights = []
            
            # User engagement insights
            if 'engagement' in analytics_data:
                engagement_insight = self._generate_engagement_insights(analytics_data['engagement'])
                if engagement_insight:
                    insights.append(engagement_insight)
            
            # Performance insights
            if 'performance_trends' in analytics_data:
                performance_insight = self._generate_performance_insights(analytics_data['performance_trends'])
                if performance_insight:
                    insights.append(performance_insight)
            
            # System health insights
            if 'system_health' in analytics_data:
                health_insight = self._generate_health_insights(analytics_data['system_health'])
                if health_insight:
                    insights.append(health_insight)
            
            return insights
            
        except Exception as e:
            logger.error(f"Error generating AI insights: {str(e)}")
            return []

    def _generate_engagement_insights(self, engagement_data: Dict[str, Any]) -> Optional[AIInsight]:
        """Generate insights about user engagement"""
        try:
            score = engagement_data.get('engagement_score', 0)
            daily_time = engagement_data.get('average_daily_time', 0) / 3600
            frequency = engagement_data.get('session_frequency', 0)
            
            if score >= 80:
                title = "Excellent User Engagement"
                description = f"Users are highly engaged with an engagement score of {score:.1f}%"
                recommendations = [
                    "Continue current engagement strategies",
                    "Consider expanding features that drive high engagement",
                    "Monitor for engagement sustainability"
                ]
                confidence = 0.9
            elif score >= 60:
                title = "Good User Engagement"
                description = f"Users show good engagement with room for improvement (score: {score:.1f}%)"
                recommendations = [
                    "Identify features that could increase daily usage time",
                    "Implement gamification elements",
                    "Improve user onboarding experience"
                ]
                confidence = 0.8
            else:
                title = "Low User Engagement"
                description = f"User engagement is below optimal levels (score: {score:.1f}%)"
                recommendations = [
                    "Conduct user feedback surveys",
                    "Redesign user interface for better usability",
                    "Implement retention strategies",
                    "Add more interactive features"
                ]
                confidence = 0.85
            
            return AIInsight(
                insight_id=str(uuid.uuid4()),
                title=title,
                description=description,
                category="user_engagement",
                confidence=confidence,
                data_points=[
                    {"metric": "engagement_score", "value": score},
                    {"metric": "daily_time_hours", "value": daily_time},
                    {"metric": "session_frequency", "value": frequency}
                ],
                recommendations=recommendations,
                created_at=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Error generating engagement insights: {str(e)}")
            return None

    def _generate_performance_insights(self, performance_data: Dict[str, Any]) -> Optional[AIInsight]:
        """Generate insights about system performance"""
        try:
            declining_metrics = []
            improving_metrics = []
            
            for metric_name, metric_data in performance_data.items():
                trend = metric_data.get('trend_direction', 'stable')
                if trend == 'increasing' and 'error' in metric_name.lower():
                    declining_metrics.append(metric_name)
                elif trend == 'decreasing' and 'time' in metric_name.lower():
                    improving_metrics.append(metric_name)
            
            if declining_metrics:
                title = "Performance Issues Detected"
                description = f"Several performance metrics are showing concerning trends: {', '.join(declining_metrics)}"
                recommendations = [
                    "Investigate root causes of performance degradation",
                    "Optimize database queries and API calls",
                    "Consider scaling infrastructure resources",
                    "Implement performance monitoring alerts"
                ]
                confidence = 0.85
            elif improving_metrics:
                title = "Performance Improvements Observed"
                description = f"System performance is improving in key areas: {', '.join(improving_metrics)}"
                recommendations = [
                    "Continue current optimization efforts",
                    "Document successful performance improvements",
                    "Apply similar optimizations to other components"
                ]
                confidence = 0.8
            else:
                title = "Stable System Performance"
                description = "System performance metrics are stable with no significant trends"
                recommendations = [
                    "Maintain current performance monitoring",
                    "Plan for future capacity needs",
                    "Regular performance reviews"
                ]
                confidence = 0.7
            
            return AIInsight(
                insight_id=str(uuid.uuid4()),
                title=title,
                description=description,
                category="system_performance",
                confidence=confidence,
                data_points=[
                    {"metric": metric_name, "trend": metric_data.get('trend_direction')}
                    for metric_name, metric_data in performance_data.items()
                ],
                recommendations=recommendations,
                created_at=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Error generating performance insights: {str(e)}")
            return None

    def _generate_health_insights(self, health_data: Dict[str, Any]) -> Optional[AIInsight]:
        """Generate insights about system health"""
        try:
            score = health_data.get('score', 0)
            status = health_data.get('status', 'unknown')
            component_health = health_data.get('component_health', {})
            
            unhealthy_components = [comp for comp, health in component_health.items() if health < 70]
            
            if score >= 90:
                title = "Excellent System Health"
                description = f"System is operating at optimal health levels ({score:.1f}%)"
                recommendations = [
                    "Maintain current operational practices",
                    "Continue regular health monitoring",
                    "Plan for preventive maintenance"
                ]
                confidence = 0.9
            elif unhealthy_components:
                title = "System Health Issues"
                description = f"Some components need attention: {', '.join(unhealthy_components)}"
                recommendations = [
                    f"Investigate issues in {', '.join(unhealthy_components)}",
                    "Implement component-specific monitoring",
                    "Consider component upgrades or replacements",
                    "Increase monitoring frequency for affected components"
                ]
                confidence = 0.85
            else:
                title = "Good System Health"
                description = f"System health is good but has room for improvement ({score:.1f}%)"
                recommendations = [
                    "Optimize underperforming components",
                    "Implement proactive monitoring",
                    "Regular system maintenance"
                ]
                confidence = 0.8
            
            return AIInsight(
                insight_id=str(uuid.uuid4()),
                title=title,
                description=description,
                category="system_health",
                confidence=confidence,
                data_points=[
                    {"metric": "overall_health", "value": score},
                    {"metric": "status", "value": status}
                ] + [
                    {"metric": f"{comp}_health", "value": health}
                    for comp, health in component_health.items()
                ],
                recommendations=recommendations,
                created_at=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Error generating health insights: {str(e)}")
            return None

    # Report Generation
    def generate_analytics_report(self, report_type: str = "comprehensive", 
                                 days: int = 30) -> Dict[str, Any]:
        """Generate comprehensive analytics report"""
        try:
            report = {
                'report_id': str(uuid.uuid4()),
                'report_type': report_type,
                'generated_at': datetime.now().isoformat(),
                'period_days': days,
                'sections': {}
            }
            
            if report_type in ['comprehensive', 'performance']:
                report['sections']['system_performance'] = self.get_system_performance_analytics(days * 24)
            
            if report_type in ['comprehensive', 'ai']:
                report['sections']['ai_effectiveness'] = self.get_ai_effectiveness_analytics(days)
            
            if report_type in ['comprehensive', 'collaboration']:
                report['sections']['collaboration'] = self.get_collaboration_analytics(days=days)
            
            # Generate insights
            all_analytics = {}
            for section_data in report['sections'].values():
                all_analytics.update(section_data)
            
            report['insights'] = [asdict(insight) for insight in self.generate_ai_insights(all_analytics)]
            
            # Store report
            report_id = report['report_id']
            self.redis.hset(self.reports_key, report_id, json.dumps(report, default=str))
            
            return report
            
        except Exception as e:
            logger.error(f"Error generating analytics report: {str(e)}")
            return {}

# Initialize analytics manager
redis_client = redis.Redis(host='localhost', port=6379, db=6, decode_responses=True)
analytics_manager = AdvancedAnalyticsManager(redis_client)

def initialize_analytics():
    """Initialize analytics system"""
    logger.info("Advanced analytics system initialized")

if __name__ == '__main__':
    initialize_analytics()

