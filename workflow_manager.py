"""
Workflow Manager for AI Assistant
Manages creation, execution, and monitoring of automated workflows
"""

import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import redis
from dataclasses import dataclass, asdict
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class TriggerType(Enum):
    SCHEDULE = "schedule"
    EVENT = "event"
    MANUAL = "manual"
    CONDITION = "condition"

class WorkflowStatus(Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    DISABLED = "disabled"
    ERROR = "error"

@dataclass
class WorkflowStep:
    id: str
    type: str
    name: str
    config: Dict[str, Any]
    dependencies: List[str] = None
    retry_count: int = 3
    timeout: int = 300  # 5 minutes
    stop_on_error: bool = True

@dataclass
class WorkflowTrigger:
    type: TriggerType
    config: Dict[str, Any]
    enabled: bool = True

@dataclass
class Workflow:
    id: str
    user_id: str
    name: str
    description: str
    trigger: WorkflowTrigger
    steps: List[WorkflowStep]
    status: WorkflowStatus
    created_at: datetime
    updated_at: datetime
    last_run: Optional[datetime] = None
    run_count: int = 0
    success_count: int = 0
    error_count: int = 0
    tags: List[str] = None

class WorkflowManager:
    """Manages automated workflows for the AI Assistant"""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.workflow_templates = self._load_workflow_templates()
    
    def create_workflow(self, user_id: str, workflow_config: Dict[str, Any]) -> str:
        """Create a new workflow"""
        workflow_id = str(uuid.uuid4())
        
        # Parse trigger configuration
        trigger_config = workflow_config.get('trigger', {})
        trigger = WorkflowTrigger(
            type=TriggerType(trigger_config.get('type', 'manual')),
            config=trigger_config.get('config', {}),
            enabled=trigger_config.get('enabled', True)
        )
        
        # Parse steps
        steps = []
        for step_config in workflow_config.get('steps', []):
            step = WorkflowStep(
                id=step_config.get('id', str(uuid.uuid4())),
                type=step_config['type'],
                name=step_config['name'],
                config=step_config['config'],
                dependencies=step_config.get('dependencies', []),
                retry_count=step_config.get('retry_count', 3),
                timeout=step_config.get('timeout', 300),
                stop_on_error=step_config.get('stop_on_error', True)
            )
            steps.append(step)
        
        # Create workflow object
        workflow = Workflow(
            id=workflow_id,
            user_id=user_id,
            name=workflow_config['name'],
            description=workflow_config.get('description', ''),
            trigger=trigger,
            steps=steps,
            status=WorkflowStatus.ACTIVE,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            tags=workflow_config.get('tags', [])
        )
        
        # Store workflow
        self._store_workflow(workflow)
        
        # Set up trigger if needed
        if trigger.type == TriggerType.SCHEDULE:
            self._setup_schedule_trigger(workflow)
        elif trigger.type == TriggerType.EVENT:
            self._setup_event_trigger(workflow)
        
        logger.info(f"Created workflow {workflow_id} for user {user_id}")
        return workflow_id
    
    def get_workflow(self, workflow_id: str) -> Optional[Workflow]:
        """Get workflow by ID"""
        workflow_data = self.redis.hgetall(f"workflow:{workflow_id}")
        if not workflow_data:
            return None
        
        return self._deserialize_workflow(workflow_data)
    
    def list_user_workflows(self, user_id: str) -> List[Workflow]:
        """List all workflows for a user"""
        workflow_ids = self.redis.smembers(f"user_workflows:{user_id}")
        workflows = []
        
        for workflow_id in workflow_ids:
            workflow = self.get_workflow(workflow_id)
            if workflow:
                workflows.append(workflow)
        
        return workflows
    
    def update_workflow(self, workflow_id: str, updates: Dict[str, Any]) -> bool:
        """Update workflow configuration"""
        workflow = self.get_workflow(workflow_id)
        if not workflow:
            return False
        
        # Update fields
        if 'name' in updates:
            workflow.name = updates['name']
        if 'description' in updates:
            workflow.description = updates['description']
        if 'status' in updates:
            workflow.status = WorkflowStatus(updates['status'])
        if 'steps' in updates:
            workflow.steps = [WorkflowStep(**step) for step in updates['steps']]
        if 'trigger' in updates:
            workflow.trigger = WorkflowTrigger(**updates['trigger'])
        
        workflow.updated_at = datetime.now()
        
        # Store updated workflow
        self._store_workflow(workflow)
        
        return True
    
    def delete_workflow(self, workflow_id: str) -> bool:
        """Delete a workflow"""
        workflow = self.get_workflow(workflow_id)
        if not workflow:
            return False
        
        # Remove from user's workflow list
        self.redis.srem(f"user_workflows:{workflow.user_id}", workflow_id)
        
        # Delete workflow data
        self.redis.delete(f"workflow:{workflow_id}")
        self.redis.delete(f"workflow_history:{workflow_id}")
        
        # Cancel scheduled tasks if any
        self._cancel_scheduled_tasks(workflow_id)
        
        logger.info(f"Deleted workflow {workflow_id}")
        return True
    
    def execute_workflow(self, workflow_id: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute a workflow manually"""
        from background_worker import execute_workflow
        
        # Queue workflow for execution
        task = execute_workflow.delay(workflow_id)
        
        return {
            'task_id': task.id,
            'status': 'queued',
            'workflow_id': workflow_id
        }
    
    def get_workflow_history(self, workflow_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get execution history for a workflow"""
        history_data = self.redis.lrange(f"workflow_history:{workflow_id}", 0, limit - 1)
        return [json.loads(data) for data in history_data]
    
    def create_from_template(self, user_id: str, template_name: str, config: Dict[str, Any]) -> str:
        """Create workflow from a predefined template"""
        if template_name not in self.workflow_templates:
            raise ValueError(f"Template {template_name} not found")
        
        template = self.workflow_templates[template_name].copy()
        
        # Merge user config with template
        template.update(config)
        template['name'] = config.get('name', template['name'])
        
        return self.create_workflow(user_id, template)
    
    def get_available_templates(self) -> Dict[str, Dict[str, Any]]:
        """Get all available workflow templates"""
        return self.workflow_templates
    
    def _store_workflow(self, workflow: Workflow):
        """Store workflow in Redis"""
        workflow_data = self._serialize_workflow(workflow)
        
        # Store workflow
        self.redis.hset(f"workflow:{workflow.id}", mapping=workflow_data)
        
        # Add to user's workflow list
        self.redis.sadd(f"user_workflows:{workflow.user_id}", workflow.id)
    
    def _serialize_workflow(self, workflow: Workflow) -> Dict[str, str]:
        """Serialize workflow to Redis-compatible format"""
        return {
            'id': workflow.id,
            'user_id': workflow.user_id,
            'name': workflow.name,
            'description': workflow.description,
            'trigger': json.dumps(asdict(workflow.trigger)),
            'steps': json.dumps([asdict(step) for step in workflow.steps]),
            'status': workflow.status.value,
            'created_at': workflow.created_at.isoformat(),
            'updated_at': workflow.updated_at.isoformat(),
            'last_run': workflow.last_run.isoformat() if workflow.last_run else '',
            'run_count': str(workflow.run_count),
            'success_count': str(workflow.success_count),
            'error_count': str(workflow.error_count),
            'tags': json.dumps(workflow.tags or [])
        }
    
    def _deserialize_workflow(self, workflow_data: Dict[str, str]) -> Workflow:
        """Deserialize workflow from Redis format"""
        trigger_data = json.loads(workflow_data['trigger'])
        trigger = WorkflowTrigger(
            type=TriggerType(trigger_data['type']),
            config=trigger_data['config'],
            enabled=trigger_data['enabled']
        )
        
        steps_data = json.loads(workflow_data['steps'])
        steps = [WorkflowStep(**step_data) for step_data in steps_data]
        
        return Workflow(
            id=workflow_data['id'],
            user_id=workflow_data['user_id'],
            name=workflow_data['name'],
            description=workflow_data['description'],
            trigger=trigger,
            steps=steps,
            status=WorkflowStatus(workflow_data['status']),
            created_at=datetime.fromisoformat(workflow_data['created_at']),
            updated_at=datetime.fromisoformat(workflow_data['updated_at']),
            last_run=datetime.fromisoformat(workflow_data['last_run']) if workflow_data['last_run'] else None,
            run_count=int(workflow_data['run_count']),
            success_count=int(workflow_data['success_count']),
            error_count=int(workflow_data['error_count']),
            tags=json.loads(workflow_data['tags'])
        )
    
    def _setup_schedule_trigger(self, workflow: Workflow):
        """Set up scheduled trigger for workflow"""
        from background_worker import execute_workflow
        
        trigger_config = workflow.trigger.config
        
        if trigger_config.get('type') == 'cron':
            # Use Celery beat for cron scheduling
            from celery.schedules import crontab
            
            # This would typically be configured in celery beat schedule
            # For now, we'll use a simple approach
            pass
        
        elif trigger_config.get('type') == 'interval':
            # Schedule recurring execution
            interval_seconds = trigger_config.get('interval_seconds', 3600)
            execute_workflow.apply_async(
                args=[workflow.id],
                countdown=interval_seconds
            )
    
    def _setup_event_trigger(self, workflow: Workflow):
        """Set up event-based trigger for workflow"""
        # Register workflow for event listening
        event_type = workflow.trigger.config.get('event_type')
        if event_type:
            self.redis.sadd(f"event_workflows:{event_type}", workflow.id)
    
    def _cancel_scheduled_tasks(self, workflow_id: str):
        """Cancel any scheduled tasks for a workflow"""
        # This would cancel Celery tasks if we had task IDs stored
        # For now, we'll just log
        logger.info(f"Cancelled scheduled tasks for workflow {workflow_id}")
    
    def _load_workflow_templates(self) -> Dict[str, Dict[str, Any]]:
        """Load predefined workflow templates"""
        return {
            'daily_summary': {
                'name': 'Daily Summary Report',
                'description': 'Generate and send daily summary of activities',
                'trigger': {
                    'type': 'schedule',
                    'config': {
                        'type': 'cron',
                        'cron_expression': '0 18 * * *'  # 6 PM daily
                    }
                },
                'steps': [
                    {
                        'type': 'ai_task',
                        'name': 'Generate Summary',
                        'config': {
                            'prompt': 'Generate a summary of today\'s activities and tasks'
                        }
                    },
                    {
                        'type': 'email',
                        'name': 'Send Summary',
                        'config': {
                            'subject': 'Daily Summary - {{date}}',
                            'template': 'daily_summary'
                        }
                    }
                ]
            },
            'email_auto_reply': {
                'name': 'Email Auto-Reply',
                'description': 'Automatically reply to emails based on content analysis',
                'trigger': {
                    'type': 'event',
                    'config': {
                        'event_type': 'email_received'
                    }
                },
                'steps': [
                    {
                        'type': 'ai_task',
                        'name': 'Analyze Email',
                        'config': {
                            'prompt': 'Analyze this email and determine if it needs an auto-reply: {{email_content}}'
                        }
                    },
                    {
                        'type': 'conditional',
                        'name': 'Check Reply Needed',
                        'config': {
                            'condition': 'ai_response.needs_reply == true'
                        }
                    },
                    {
                        'type': 'ai_task',
                        'name': 'Generate Reply',
                        'config': {
                            'prompt': 'Generate an appropriate reply to this email: {{email_content}}'
                        }
                    },
                    {
                        'type': 'email',
                        'name': 'Send Reply',
                        'config': {
                            'to': '{{email_sender}}',
                            'subject': 'Re: {{email_subject}}',
                            'body': '{{ai_generated_reply}}'
                        }
                    }
                ]
            },
            'social_media_scheduler': {
                'name': 'Social Media Scheduler',
                'description': 'Schedule and post content to social media platforms',
                'trigger': {
                    'type': 'schedule',
                    'config': {
                        'type': 'cron',
                        'cron_expression': '0 9,15 * * *'  # 9 AM and 3 PM daily
                    }
                },
                'steps': [
                    {
                        'type': 'ai_task',
                        'name': 'Generate Content',
                        'config': {
                            'prompt': 'Generate engaging social media content for today'
                        }
                    },
                    {
                        'type': 'social_media_post',
                        'name': 'Post to Facebook',
                        'config': {
                            'platform': 'facebook',
                            'content': '{{ai_generated_content}}'
                        }
                    },
                    {
                        'type': 'social_media_post',
                        'name': 'Post to Twitter',
                        'config': {
                            'platform': 'twitter',
                            'content': '{{ai_generated_content}}'
                        }
                    }
                ]
            },
            'task_reminder': {
                'name': 'Task Reminder System',
                'description': 'Send reminders for upcoming tasks and deadlines',
                'trigger': {
                    'type': 'schedule',
                    'config': {
                        'type': 'interval',
                        'interval_seconds': 3600  # Every hour
                    }
                },
                'steps': [
                    {
                        'type': 'ai_task',
                        'name': 'Check Upcoming Tasks',
                        'config': {
                            'prompt': 'Check for tasks due in the next 24 hours'
                        }
                    },
                    {
                        'type': 'conditional',
                        'name': 'Has Upcoming Tasks',
                        'config': {
                            'condition': 'ai_response.has_upcoming_tasks == true'
                        }
                    },
                    {
                        'type': 'email',
                        'name': 'Send Reminder',
                        'config': {
                            'subject': 'Task Reminder - Upcoming Deadlines',
                            'template': 'task_reminder'
                        }
                    }
                ]
            }
        }

