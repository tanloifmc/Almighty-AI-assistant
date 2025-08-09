"""
Background Worker System for AI Assistant
Handles background tasks, scheduled workflows, and event-driven automation
"""

from celery import Celery
from celery.schedules import crontab
import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List
import redis
from core_agent import PersonalAIAssistant
from tools import *

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Celery app
celery_app = Celery('ai_assistant_worker')

# Celery configuration
celery_app.conf.update(
    broker_url='redis://localhost:6379/0',
    result_backend='redis://localhost:6379/0',
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)

# Redis client for state management
redis_client = redis.Redis(host='localhost', port=6379, db=1, decode_responses=True)

class WorkflowEngine:
    """Engine for managing and executing automated workflows"""
    
    def __init__(self):
        self.ai_assistant = PersonalAIAssistant()
    
    def create_workflow(self, user_id: str, workflow_config: Dict[str, Any]) -> str:
        """Create a new automated workflow"""
        workflow_id = f"workflow_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        workflow_data = {
            'id': workflow_id,
            'user_id': user_id,
            'name': workflow_config.get('name', 'Unnamed Workflow'),
            'description': workflow_config.get('description', ''),
            'trigger': workflow_config.get('trigger', {}),
            'steps': workflow_config.get('steps', []),
            'status': 'active',
            'created_at': datetime.now().isoformat(),
            'last_run': None,
            'run_count': 0
        }
        
        # Store workflow in Redis
        redis_client.hset(f"workflow:{workflow_id}", mapping=workflow_data)
        
        # Add to user's workflow list
        redis_client.sadd(f"user_workflows:{user_id}", workflow_id)
        
        # Schedule if it's a time-based trigger
        if workflow_data['trigger'].get('type') == 'schedule':
            self._schedule_workflow(workflow_id, workflow_data['trigger'])
        
        logger.info(f"Created workflow {workflow_id} for user {user_id}")
        return workflow_id
    
    def _schedule_workflow(self, workflow_id: str, trigger: Dict[str, Any]):
        """Schedule a workflow based on trigger configuration"""
        if trigger.get('schedule_type') == 'cron':
            # Parse cron expression and schedule
            cron_expr = trigger.get('cron_expression')
            if cron_expr:
                execute_workflow.apply_async(
                    args=[workflow_id],
                    eta=self._parse_cron_next_run(cron_expr)
                )
        elif trigger.get('schedule_type') == 'interval':
            # Schedule recurring task
            interval_seconds = trigger.get('interval_seconds', 3600)
            execute_workflow.apply_async(
                args=[workflow_id],
                countdown=interval_seconds
            )
    
    def _parse_cron_next_run(self, cron_expr: str) -> datetime:
        """Parse cron expression and return next run time"""
        # Simple implementation - in production, use croniter library
        return datetime.now() + timedelta(hours=1)
    
    def execute_workflow_steps(self, workflow_id: str) -> Dict[str, Any]:
        """Execute all steps in a workflow"""
        workflow_data = redis_client.hgetall(f"workflow:{workflow_id}")
        if not workflow_data:
            raise ValueError(f"Workflow {workflow_id} not found")
        
        steps = json.loads(workflow_data.get('steps', '[]'))
        results = []
        
        for i, step in enumerate(steps):
            try:
                step_result = self._execute_step(step, workflow_data['user_id'])
                results.append({
                    'step_index': i,
                    'step_type': step.get('type'),
                    'status': 'success',
                    'result': step_result
                })
            except Exception as e:
                logger.error(f"Error executing step {i} in workflow {workflow_id}: {str(e)}")
                results.append({
                    'step_index': i,
                    'step_type': step.get('type'),
                    'status': 'error',
                    'error': str(e)
                })
                # Stop execution on error if configured
                if step.get('stop_on_error', True):
                    break
        
        # Update workflow statistics
        redis_client.hset(f"workflow:{workflow_id}", 
                         'last_run', datetime.now().isoformat())
        redis_client.hincrby(f"workflow:{workflow_id}", 'run_count', 1)
        
        return {
            'workflow_id': workflow_id,
            'execution_time': datetime.now().isoformat(),
            'steps_executed': len(results),
            'results': results
        }
    
    def _execute_step(self, step: Dict[str, Any], user_id: str) -> Any:
        """Execute a single workflow step"""
        step_type = step.get('type')
        
        if step_type == 'ai_task':
            # Execute AI task
            prompt = step.get('prompt', '')
            return self.ai_assistant.process_request(user_id, prompt)
        
        elif step_type == 'api_call':
            # Make API call
            url = step.get('url')
            method = step.get('method', 'GET')
            headers = step.get('headers', {})
            data = step.get('data', {})
            
            import requests
            response = requests.request(method, url, headers=headers, json=data)
            return response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text
        
        elif step_type == 'webhook':
            # Trigger webhook
            webhook_url = step.get('webhook_url')
            payload = step.get('payload', {})
            
            import requests
            response = requests.post(webhook_url, json=payload)
            return {'status_code': response.status_code, 'response': response.text}
        
        elif step_type == 'email':
            # Send email
            return send_email(
                step.get('to'),
                step.get('subject'),
                step.get('body')
            )
        
        elif step_type == 'social_media_post':
            # Post to social media
            return post_to_social_media(
                step.get('platform'),
                step.get('content'),
                step.get('media_urls', [])
            )
        
        else:
            raise ValueError(f"Unknown step type: {step_type}")

# Initialize workflow engine
workflow_engine = WorkflowEngine()

# Celery Tasks
@celery_app.task(bind=True)
def execute_workflow(self, workflow_id: str):
    """Execute a workflow in the background"""
    try:
        logger.info(f"Executing workflow {workflow_id}")
        result = workflow_engine.execute_workflow_steps(workflow_id)
        
        # Store execution result
        redis_client.lpush(f"workflow_history:{workflow_id}", json.dumps(result))
        redis_client.ltrim(f"workflow_history:{workflow_id}", 0, 99)  # Keep last 100 executions
        
        return result
    except Exception as e:
        logger.error(f"Error executing workflow {workflow_id}: {str(e)}")
        self.retry(countdown=60, max_retries=3)

@celery_app.task
def process_ai_request(user_id: str, message: str, context: Dict[str, Any] = None):
    """Process AI request in background"""
    try:
        ai_assistant = PersonalAIAssistant()
        response = ai_assistant.process_request(user_id, message, context or {})
        
        # Store response in Redis for retrieval
        response_key = f"ai_response:{user_id}:{datetime.now().timestamp()}"
        redis_client.setex(response_key, 3600, json.dumps(response))  # Expire in 1 hour
        
        return response
    except Exception as e:
        logger.error(f"Error processing AI request for user {user_id}: {str(e)}")
        raise

@celery_app.task
def scheduled_task_reminder(user_id: str, task_data: Dict[str, Any]):
    """Send task reminder to user"""
    try:
        # Create reminder notification
        notification = {
            'type': 'task_reminder',
            'user_id': user_id,
            'task': task_data,
            'timestamp': datetime.now().isoformat()
        }
        
        # Store notification
        redis_client.lpush(f"notifications:{user_id}", json.dumps(notification))
        
        # Send email reminder if configured
        if task_data.get('email_reminder'):
            send_email(
                task_data.get('user_email'),
                f"Task Reminder: {task_data.get('title')}",
                f"This is a reminder for your task: {task_data.get('description')}\n\nDue: {task_data.get('due_date')}"
            )
        
        return notification
    except Exception as e:
        logger.error(f"Error sending task reminder for user {user_id}: {str(e)}")
        raise

@celery_app.task
def cleanup_old_data():
    """Clean up old data and logs"""
    try:
        # Clean up old AI responses
        pattern = "ai_response:*"
        keys = redis_client.keys(pattern)
        for key in keys:
            ttl = redis_client.ttl(key)
            if ttl == -1:  # No expiration set
                redis_client.expire(key, 3600)  # Set 1 hour expiration
        
        # Clean up old notifications (keep last 100)
        notification_patterns = redis_client.keys("notifications:*")
        for pattern in notification_patterns:
            redis_client.ltrim(pattern, 0, 99)
        
        logger.info("Completed data cleanup")
        return {"status": "completed", "cleaned_keys": len(keys)}
    except Exception as e:
        logger.error(f"Error during cleanup: {str(e)}")
        raise

# Periodic tasks
celery_app.conf.beat_schedule = {
    'cleanup-old-data': {
        'task': 'background_worker.cleanup_old_data',
        'schedule': crontab(hour=2, minute=0),  # Run daily at 2 AM
    },
}

class EventListener:
    """Listen for events and trigger workflows"""
    
    def __init__(self):
        self.redis_client = redis_client
    
    def listen_for_events(self):
        """Listen for events in Redis pub/sub"""
        pubsub = self.redis_client.pubsub()
        pubsub.subscribe('ai_assistant_events')
        
        for message in pubsub.listen():
            if message['type'] == 'message':
                try:
                    event_data = json.loads(message['data'])
                    self.handle_event(event_data)
                except Exception as e:
                    logger.error(f"Error handling event: {str(e)}")
    
    def handle_event(self, event_data: Dict[str, Any]):
        """Handle incoming events and trigger appropriate workflows"""
        event_type = event_data.get('type')
        user_id = event_data.get('user_id')
        
        if event_type == 'task_completed':
            # Trigger workflows that depend on task completion
            self.trigger_dependent_workflows(user_id, 'task_completed', event_data)
        
        elif event_type == 'email_received':
            # Process new email and potentially trigger workflows
            self.process_email_event(user_id, event_data)
        
        elif event_type == 'calendar_event':
            # Handle calendar events
            self.process_calendar_event(user_id, event_data)
    
    def trigger_dependent_workflows(self, user_id: str, trigger_type: str, event_data: Dict[str, Any]):
        """Trigger workflows that depend on specific events"""
        user_workflows = redis_client.smembers(f"user_workflows:{user_id}")
        
        for workflow_id in user_workflows:
            workflow_data = redis_client.hgetall(f"workflow:{workflow_id}")
            trigger = json.loads(workflow_data.get('trigger', '{}'))
            
            if trigger.get('type') == 'event' and trigger.get('event_type') == trigger_type:
                # Execute workflow asynchronously
                execute_workflow.delay(workflow_id)
    
    def process_email_event(self, user_id: str, event_data: Dict[str, Any]):
        """Process email events and potentially auto-respond or categorize"""
        # This could trigger AI analysis of the email and auto-categorization
        process_ai_request.delay(
            user_id,
            f"Analyze this email and suggest actions: {event_data.get('email_content', '')}",
            {'event_type': 'email_analysis', 'email_data': event_data}
        )
    
    def process_calendar_event(self, user_id: str, event_data: Dict[str, Any]):
        """Process calendar events"""
        event_time = event_data.get('event_time')
        if event_time:
            # Schedule reminder 15 minutes before
            reminder_time = datetime.fromisoformat(event_time) - timedelta(minutes=15)
            scheduled_task_reminder.apply_async(
                args=[user_id, event_data],
                eta=reminder_time
            )

def start_event_listener():
    """Start the event listener in a separate process"""
    listener = EventListener()
    listener.listen_for_events()

if __name__ == '__main__':
    # Start Celery worker
    celery_app.start()

