"""
Advanced Scheduler for AI Assistant
Handles scheduling of tasks, workflows, and automated actions
"""

import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import redis
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.jobstores.redis import RedisJobStore
from apscheduler.executors.pool import ThreadPoolExecutor

logger = logging.getLogger(__name__)

class ScheduleType(Enum):
    ONE_TIME = "one_time"
    RECURRING = "recurring"
    CRON = "cron"
    INTERVAL = "interval"

class TaskStatus(Enum):
    SCHEDULED = "scheduled"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class ScheduledTask:
    id: str
    user_id: str
    name: str
    description: str
    task_type: str
    task_config: Dict[str, Any]
    schedule_type: ScheduleType
    schedule_config: Dict[str, Any]
    status: TaskStatus
    created_at: datetime
    next_run: Optional[datetime] = None
    last_run: Optional[datetime] = None
    run_count: int = 0
    max_runs: Optional[int] = None
    enabled: bool = True

class AIAssistantScheduler:
    """Advanced scheduler for AI Assistant tasks and workflows"""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        
        # Configure APScheduler
        jobstores = {
            'default': RedisJobStore(host='localhost', port=6379, db=3)
        }
        executors = {
            'default': ThreadPoolExecutor(20)
        }
        job_defaults = {
            'coalesce': False,
            'max_instances': 3
        }
        
        self.scheduler = BackgroundScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults
        )
        
        # Task handlers
        self.task_handlers: Dict[str, Callable] = {}
        self._register_default_handlers()
    
    def start(self):
        """Start the scheduler"""
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("AI Assistant Scheduler started")
    
    def stop(self):
        """Stop the scheduler"""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("AI Assistant Scheduler stopped")
    
    def schedule_task(self, user_id: str, task_config: Dict[str, Any]) -> str:
        """Schedule a new task"""
        task_id = str(uuid.uuid4())
        
        # Create scheduled task object
        scheduled_task = ScheduledTask(
            id=task_id,
            user_id=user_id,
            name=task_config['name'],
            description=task_config.get('description', ''),
            task_type=task_config['type'],
            task_config=task_config.get('config', {}),
            schedule_type=ScheduleType(task_config['schedule']['type']),
            schedule_config=task_config['schedule']['config'],
            status=TaskStatus.SCHEDULED,
            created_at=datetime.now(),
            max_runs=task_config.get('max_runs'),
            enabled=task_config.get('enabled', True)
        )
        
        # Store task
        self._store_task(scheduled_task)
        
        # Add to scheduler
        if scheduled_task.enabled:
            self._add_to_scheduler(scheduled_task)
        
        logger.info(f"Scheduled task {task_id} for user {user_id}")
        return task_id
    
    def cancel_task(self, task_id: str) -> bool:
        """Cancel a scheduled task"""
        task = self.get_task(task_id)
        if not task:
            return False
        
        # Remove from scheduler
        try:
            self.scheduler.remove_job(task_id)
        except:
            pass  # Job might not exist in scheduler
        
        # Update status
        task.status = TaskStatus.CANCELLED
        self._store_task(task)
        
        logger.info(f"Cancelled task {task_id}")
        return True
    
    def pause_task(self, task_id: str) -> bool:
        """Pause a scheduled task"""
        task = self.get_task(task_id)
        if not task:
            return False
        
        try:
            self.scheduler.pause_job(task_id)
            task.enabled = False
            self._store_task(task)
            logger.info(f"Paused task {task_id}")
            return True
        except Exception as e:
            logger.error(f"Error pausing task {task_id}: {str(e)}")
            return False
    
    def resume_task(self, task_id: str) -> bool:
        """Resume a paused task"""
        task = self.get_task(task_id)
        if not task:
            return False
        
        try:
            self.scheduler.resume_job(task_id)
            task.enabled = True
            self._store_task(task)
            logger.info(f"Resumed task {task_id}")
            return True
        except Exception as e:
            logger.error(f"Error resuming task {task_id}: {str(e)}")
            return False
    
    def get_task(self, task_id: str) -> Optional[ScheduledTask]:
        """Get task by ID"""
        task_data = self.redis.hgetall(f"scheduled_task:{task_id}")
        if not task_data:
            return None
        
        return self._deserialize_task(task_data)
    
    def list_user_tasks(self, user_id: str) -> List[ScheduledTask]:
        """List all tasks for a user"""
        task_ids = self.redis.smembers(f"user_tasks:{user_id}")
        tasks = []
        
        for task_id in task_ids:
            task = self.get_task(task_id)
            if task:
                tasks.append(task)
        
        return tasks
    
    def get_upcoming_tasks(self, user_id: str, hours: int = 24) -> List[ScheduledTask]:
        """Get tasks scheduled to run in the next N hours"""
        user_tasks = self.list_user_tasks(user_id)
        upcoming = []
        
        cutoff_time = datetime.now() + timedelta(hours=hours)
        
        for task in user_tasks:
            if (task.next_run and 
                task.next_run <= cutoff_time and 
                task.status == TaskStatus.SCHEDULED):
                upcoming.append(task)
        
        return sorted(upcoming, key=lambda t: t.next_run or datetime.max)
    
    def execute_task_now(self, task_id: str) -> bool:
        """Execute a task immediately"""
        task = self.get_task(task_id)
        if not task:
            return False
        
        try:
            self._execute_task(task_id)
            return True
        except Exception as e:
            logger.error(f"Error executing task {task_id}: {str(e)}")
            return False
    
    def register_task_handler(self, task_type: str, handler: Callable):
        """Register a handler for a specific task type"""
        self.task_handlers[task_type] = handler
        logger.info(f"Registered handler for task type: {task_type}")
    
    def _store_task(self, task: ScheduledTask):
        """Store task in Redis"""
        task_data = self._serialize_task(task)
        
        # Store task
        self.redis.hset(f"scheduled_task:{task.id}", mapping=task_data)
        
        # Add to user's task list
        self.redis.sadd(f"user_tasks:{task.user_id}", task.id)
    
    def _serialize_task(self, task: ScheduledTask) -> Dict[str, str]:
        """Serialize task to Redis-compatible format"""
        return {
            'id': task.id,
            'user_id': task.user_id,
            'name': task.name,
            'description': task.description,
            'task_type': task.task_type,
            'task_config': json.dumps(task.task_config),
            'schedule_type': task.schedule_type.value,
            'schedule_config': json.dumps(task.schedule_config),
            'status': task.status.value,
            'created_at': task.created_at.isoformat(),
            'next_run': task.next_run.isoformat() if task.next_run else '',
            'last_run': task.last_run.isoformat() if task.last_run else '',
            'run_count': str(task.run_count),
            'max_runs': str(task.max_runs) if task.max_runs else '',
            'enabled': str(task.enabled)
        }
    
    def _deserialize_task(self, task_data: Dict[str, str]) -> ScheduledTask:
        """Deserialize task from Redis format"""
        return ScheduledTask(
            id=task_data['id'],
            user_id=task_data['user_id'],
            name=task_data['name'],
            description=task_data['description'],
            task_type=task_data['task_type'],
            task_config=json.loads(task_data['task_config']),
            schedule_type=ScheduleType(task_data['schedule_type']),
            schedule_config=json.loads(task_data['schedule_config']),
            status=TaskStatus(task_data['status']),
            created_at=datetime.fromisoformat(task_data['created_at']),
            next_run=datetime.fromisoformat(task_data['next_run']) if task_data['next_run'] else None,
            last_run=datetime.fromisoformat(task_data['last_run']) if task_data['last_run'] else None,
            run_count=int(task_data['run_count']),
            max_runs=int(task_data['max_runs']) if task_data['max_runs'] else None,
            enabled=task_data['enabled'].lower() == 'true'
        )
    
    def _add_to_scheduler(self, task: ScheduledTask):
        """Add task to APScheduler"""
        trigger = self._create_trigger(task)
        
        self.scheduler.add_job(
            func=self._execute_task,
            trigger=trigger,
            id=task.id,
            args=[task.id],
            name=task.name,
            max_instances=1,
            replace_existing=True
        )
        
        # Update next run time
        job = self.scheduler.get_job(task.id)
        if job and job.next_run_time:
            task.next_run = job.next_run_time
            self._store_task(task)
    
    def _create_trigger(self, task: ScheduledTask):
        """Create APScheduler trigger from task configuration"""
        if task.schedule_type == ScheduleType.ONE_TIME:
            run_date = datetime.fromisoformat(task.schedule_config['run_date'])
            return DateTrigger(run_date=run_date)
        
        elif task.schedule_type == ScheduleType.CRON:
            cron_config = task.schedule_config
            return CronTrigger(
                second=cron_config.get('second', 0),
                minute=cron_config.get('minute', 0),
                hour=cron_config.get('hour', 0),
                day=cron_config.get('day', '*'),
                month=cron_config.get('month', '*'),
                day_of_week=cron_config.get('day_of_week', '*'),
                timezone=cron_config.get('timezone', 'UTC')
            )
        
        elif task.schedule_type == ScheduleType.INTERVAL:
            interval_config = task.schedule_config
            return IntervalTrigger(
                seconds=interval_config.get('seconds', 0),
                minutes=interval_config.get('minutes', 0),
                hours=interval_config.get('hours', 0),
                days=interval_config.get('days', 0),
                start_date=datetime.fromisoformat(interval_config['start_date']) if 'start_date' in interval_config else None,
                end_date=datetime.fromisoformat(interval_config['end_date']) if 'end_date' in interval_config else None
            )
        
        else:
            raise ValueError(f"Unsupported schedule type: {task.schedule_type}")
    
    def _execute_task(self, task_id: str):
        """Execute a scheduled task"""
        task = self.get_task(task_id)
        if not task:
            logger.error(f"Task {task_id} not found")
            return
        
        # Update status
        task.status = TaskStatus.RUNNING
        task.last_run = datetime.now()
        self._store_task(task)
        
        try:
            # Get task handler
            handler = self.task_handlers.get(task.task_type)
            if not handler:
                raise ValueError(f"No handler registered for task type: {task.task_type}")
            
            # Execute task
            result = handler(task)
            
            # Update task
            task.status = TaskStatus.COMPLETED
            task.run_count += 1
            
            # Check if max runs reached
            if task.max_runs and task.run_count >= task.max_runs:
                self.cancel_task(task_id)
            else:
                # Update next run time
                job = self.scheduler.get_job(task_id)
                if job and job.next_run_time:
                    task.next_run = job.next_run_time
                else:
                    task.status = TaskStatus.COMPLETED
            
            self._store_task(task)
            
            # Store execution result
            self._store_execution_result(task_id, result)
            
            logger.info(f"Successfully executed task {task_id}")
            
        except Exception as e:
            task.status = TaskStatus.FAILED
            self._store_task(task)
            
            # Store error
            self._store_execution_result(task_id, {'error': str(e)})
            
            logger.error(f"Error executing task {task_id}: {str(e)}")
    
    def _store_execution_result(self, task_id: str, result: Any):
        """Store task execution result"""
        execution_data = {
            'task_id': task_id,
            'timestamp': datetime.now().isoformat(),
            'result': json.dumps(result) if isinstance(result, (dict, list)) else str(result)
        }
        
        self.redis.lpush(f"task_executions:{task_id}", json.dumps(execution_data))
        self.redis.ltrim(f"task_executions:{task_id}", 0, 99)  # Keep last 100 executions
    
    def _register_default_handlers(self):
        """Register default task handlers"""
        
        def ai_task_handler(task: ScheduledTask):
            """Handle AI-powered tasks"""
            from core_agent import PersonalAIAssistant
            
            ai_assistant = PersonalAIAssistant()
            prompt = task.task_config.get('prompt', '')
            context = task.task_config.get('context', {})
            
            return ai_assistant.process_request(task.user_id, prompt, context)
        
        def email_task_handler(task: ScheduledTask):
            """Handle email tasks"""
            from tools import send_email
            
            config = task.task_config
            return send_email(
                config.get('to'),
                config.get('subject'),
                config.get('body')
            )
        
        def workflow_task_handler(task: ScheduledTask):
            """Handle workflow execution tasks"""
            from background_worker import execute_workflow
            
            workflow_id = task.task_config.get('workflow_id')
            if workflow_id:
                execute_workflow.delay(workflow_id)
                return {'status': 'workflow_queued', 'workflow_id': workflow_id}
            else:
                raise ValueError("No workflow_id specified in task config")
        
        def reminder_task_handler(task: ScheduledTask):
            """Handle reminder tasks"""
            from event_system import event_generator, EventType
            
            reminder_data = task.task_config
            event_generator.generate_custom_event(
                task.user_id,
                'reminder',
                {
                    'title': reminder_data.get('title'),
                    'message': reminder_data.get('message'),
                    'type': 'reminder'
                }
            )
            
            return {'status': 'reminder_sent', 'title': reminder_data.get('title')}
        
        def api_call_handler(task: ScheduledTask):
            """Handle API call tasks"""
            import requests
            
            config = task.task_config
            method = config.get('method', 'GET')
            url = config.get('url')
            headers = config.get('headers', {})
            data = config.get('data', {})
            
            response = requests.request(method, url, headers=headers, json=data)
            
            return {
                'status_code': response.status_code,
                'response': response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text
            }
        
        # Register handlers
        self.register_task_handler('ai_task', ai_task_handler)
        self.register_task_handler('email', email_task_handler)
        self.register_task_handler('workflow', workflow_task_handler)
        self.register_task_handler('reminder', reminder_task_handler)
        self.register_task_handler('api_call', api_call_handler)

# Global scheduler instance
redis_client = redis.Redis(host='localhost', port=6379, db=3, decode_responses=True)
ai_scheduler = AIAssistantScheduler(redis_client)

def start_scheduler():
    """Start the AI Assistant scheduler"""
    ai_scheduler.start()

def stop_scheduler():
    """Stop the AI Assistant scheduler"""
    ai_scheduler.stop()

if __name__ == '__main__':
    start_scheduler()
    try:
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        stop_scheduler()

