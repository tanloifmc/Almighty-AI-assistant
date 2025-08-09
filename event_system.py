"""
Event System for AI Assistant
Handles event-driven automation and workflow triggers
"""

import json
import redis
import logging
from datetime import datetime
from typing import Dict, Any, List, Callable
from dataclasses import dataclass
from enum import Enum
import threading
import time

logger = logging.getLogger(__name__)

class EventType(Enum):
    EMAIL_RECEIVED = "email_received"
    TASK_COMPLETED = "task_completed"
    TASK_CREATED = "task_created"
    CALENDAR_EVENT = "calendar_event"
    FILE_UPLOADED = "file_uploaded"
    USER_LOGIN = "user_login"
    WORKFLOW_COMPLETED = "workflow_completed"
    API_CALL_MADE = "api_call_made"
    SOCIAL_MEDIA_MENTION = "social_media_mention"
    CUSTOM_EVENT = "custom_event"

@dataclass
class Event:
    id: str
    type: EventType
    user_id: str
    data: Dict[str, Any]
    timestamp: datetime
    source: str = "system"
    processed: bool = False

class EventPublisher:
    """Publishes events to the event system"""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
    
    def publish_event(self, event: Event) -> bool:
        """Publish an event to the system"""
        try:
            event_data = {
                'id': event.id,
                'type': event.type.value,
                'user_id': event.user_id,
                'data': event.data,
                'timestamp': event.timestamp.isoformat(),
                'source': event.source,
                'processed': event.processed
            }
            
            # Publish to Redis pub/sub
            self.redis.publish('ai_assistant_events', json.dumps(event_data))
            
            # Store event for history
            self.redis.lpush(f"events:{event.user_id}", json.dumps(event_data))
            self.redis.ltrim(f"events:{event.user_id}", 0, 999)  # Keep last 1000 events
            
            logger.info(f"Published event {event.id} of type {event.type.value}")
            return True
            
        except Exception as e:
            logger.error(f"Error publishing event {event.id}: {str(e)}")
            return False

class EventListener:
    """Listens for events and triggers appropriate actions"""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.handlers: Dict[EventType, List[Callable]] = {}
        self.running = False
        self.listener_thread = None
    
    def register_handler(self, event_type: EventType, handler: Callable[[Event], None]):
        """Register an event handler"""
        if event_type not in self.handlers:
            self.handlers[event_type] = []
        self.handlers[event_type].append(handler)
        logger.info(f"Registered handler for event type {event_type.value}")
    
    def start_listening(self):
        """Start listening for events"""
        if self.running:
            return
        
        self.running = True
        self.listener_thread = threading.Thread(target=self._listen_loop, daemon=True)
        self.listener_thread.start()
        logger.info("Event listener started")
    
    def stop_listening(self):
        """Stop listening for events"""
        self.running = False
        if self.listener_thread:
            self.listener_thread.join()
        logger.info("Event listener stopped")
    
    def _listen_loop(self):
        """Main event listening loop"""
        pubsub = self.redis.pubsub()
        pubsub.subscribe('ai_assistant_events')
        
        try:
            for message in pubsub.listen():
                if not self.running:
                    break
                
                if message['type'] == 'message':
                    try:
                        event_data = json.loads(message['data'])
                        event = self._deserialize_event(event_data)
                        self._handle_event(event)
                    except Exception as e:
                        logger.error(f"Error processing event: {str(e)}")
        except Exception as e:
            logger.error(f"Error in event listener loop: {str(e)}")
        finally:
            pubsub.close()
    
    def _deserialize_event(self, event_data: Dict[str, Any]) -> Event:
        """Convert event data back to Event object"""
        return Event(
            id=event_data['id'],
            type=EventType(event_data['type']),
            user_id=event_data['user_id'],
            data=event_data['data'],
            timestamp=datetime.fromisoformat(event_data['timestamp']),
            source=event_data['source'],
            processed=event_data['processed']
        )
    
    def _handle_event(self, event: Event):
        """Handle an incoming event"""
        if event.type in self.handlers:
            for handler in self.handlers[event.type]:
                try:
                    handler(event)
                except Exception as e:
                    logger.error(f"Error in event handler for {event.type.value}: {str(e)}")

class WorkflowEventHandler:
    """Handles events that trigger workflows"""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
    
    def handle_event(self, event: Event):
        """Handle event and trigger appropriate workflows"""
        # Find workflows that are triggered by this event type
        workflow_ids = self.redis.smembers(f"event_workflows:{event.type.value}")
        
        for workflow_id in workflow_ids:
            try:
                # Check if workflow conditions are met
                if self._check_workflow_conditions(workflow_id, event):
                    self._trigger_workflow(workflow_id, event)
            except Exception as e:
                logger.error(f"Error triggering workflow {workflow_id} for event {event.id}: {str(e)}")
    
    def _check_workflow_conditions(self, workflow_id: str, event: Event) -> bool:
        """Check if workflow conditions are met for the event"""
        workflow_data = self.redis.hgetall(f"workflow:{workflow_id}")
        if not workflow_data:
            return False
        
        trigger_data = json.loads(workflow_data.get('trigger', '{}'))
        conditions = trigger_data.get('config', {}).get('conditions', [])
        
        # If no conditions, always trigger
        if not conditions:
            return True
        
        # Check each condition
        for condition in conditions:
            if not self._evaluate_condition(condition, event):
                return False
        
        return True
    
    def _evaluate_condition(self, condition: Dict[str, Any], event: Event) -> bool:
        """Evaluate a single condition against the event"""
        field = condition.get('field')
        operator = condition.get('operator')
        value = condition.get('value')
        
        if not all([field, operator, value]):
            return True  # Invalid condition, allow trigger
        
        # Get field value from event
        if field.startswith('data.'):
            field_value = event.data.get(field[5:])
        elif field == 'user_id':
            field_value = event.user_id
        elif field == 'source':
            field_value = event.source
        else:
            return True  # Unknown field, allow trigger
        
        # Evaluate condition
        if operator == 'equals':
            return field_value == value
        elif operator == 'contains':
            return value in str(field_value)
        elif operator == 'greater_than':
            return float(field_value) > float(value)
        elif operator == 'less_than':
            return float(field_value) < float(value)
        else:
            return True  # Unknown operator, allow trigger
    
    def _trigger_workflow(self, workflow_id: str, event: Event):
        """Trigger a workflow execution"""
        from background_worker import execute_workflow
        
        # Add event context to workflow execution
        context = {
            'trigger_event': {
                'id': event.id,
                'type': event.type.value,
                'data': event.data,
                'timestamp': event.timestamp.isoformat()
            }
        }
        
        # Queue workflow for execution
        execute_workflow.delay(workflow_id)
        logger.info(f"Triggered workflow {workflow_id} from event {event.id}")

class EventGenerator:
    """Generates events from various sources"""
    
    def __init__(self, event_publisher: EventPublisher):
        self.publisher = event_publisher
    
    def generate_email_event(self, user_id: str, email_data: Dict[str, Any]):
        """Generate email received event"""
        event = Event(
            id=f"email_{datetime.now().timestamp()}",
            type=EventType.EMAIL_RECEIVED,
            user_id=user_id,
            data=email_data,
            timestamp=datetime.now(),
            source="email_monitor"
        )
        self.publisher.publish_event(event)
    
    def generate_task_event(self, user_id: str, task_data: Dict[str, Any], event_type: EventType):
        """Generate task-related event"""
        event = Event(
            id=f"task_{datetime.now().timestamp()}",
            type=event_type,
            user_id=user_id,
            data=task_data,
            timestamp=datetime.now(),
            source="task_manager"
        )
        self.publisher.publish_event(event)
    
    def generate_calendar_event(self, user_id: str, calendar_data: Dict[str, Any]):
        """Generate calendar event"""
        event = Event(
            id=f"calendar_{datetime.now().timestamp()}",
            type=EventType.CALENDAR_EVENT,
            user_id=user_id,
            data=calendar_data,
            timestamp=datetime.now(),
            source="calendar_sync"
        )
        self.publisher.publish_event(event)
    
    def generate_custom_event(self, user_id: str, event_name: str, data: Dict[str, Any]):
        """Generate custom user-defined event"""
        event = Event(
            id=f"custom_{event_name}_{datetime.now().timestamp()}",
            type=EventType.CUSTOM_EVENT,
            user_id=user_id,
            data={**data, 'custom_event_name': event_name},
            timestamp=datetime.now(),
            source="user_defined"
        )
        self.publisher.publish_event(event)

class EventMonitor:
    """Monitors external sources for events"""
    
    def __init__(self, event_generator: EventGenerator):
        self.generator = event_generator
        self.monitoring = False
        self.monitor_threads = []
    
    def start_monitoring(self):
        """Start monitoring external sources"""
        if self.monitoring:
            return
        
        self.monitoring = True
        
        # Start email monitoring
        email_thread = threading.Thread(target=self._monitor_email, daemon=True)
        email_thread.start()
        self.monitor_threads.append(email_thread)
        
        # Start calendar monitoring
        calendar_thread = threading.Thread(target=self._monitor_calendar, daemon=True)
        calendar_thread.start()
        self.monitor_threads.append(calendar_thread)
        
        logger.info("Event monitoring started")
    
    def stop_monitoring(self):
        """Stop monitoring external sources"""
        self.monitoring = False
        for thread in self.monitor_threads:
            thread.join()
        self.monitor_threads.clear()
        logger.info("Event monitoring stopped")
    
    def _monitor_email(self):
        """Monitor email for new messages"""
        # This would integrate with email APIs (Gmail, Outlook, etc.)
        # For now, we'll simulate with a simple loop
        while self.monitoring:
            try:
                # Simulate checking for new emails
                # In real implementation, this would call email APIs
                time.sleep(60)  # Check every minute
                
                # Example: Generate fake email event for testing
                # self.generator.generate_email_event(
                #     "user123",
                #     {
                #         "subject": "Test Email",
                #         "sender": "test@example.com",
                #         "content": "This is a test email",
                #         "received_at": datetime.now().isoformat()
                #     }
                # )
                
            except Exception as e:
                logger.error(f"Error monitoring email: {str(e)}")
                time.sleep(60)
    
    def _monitor_calendar(self):
        """Monitor calendar for upcoming events"""
        # This would integrate with calendar APIs (Google Calendar, Outlook, etc.)
        while self.monitoring:
            try:
                # Simulate checking for calendar events
                time.sleep(300)  # Check every 5 minutes
                
                # Example: Generate calendar event for testing
                # self.generator.generate_calendar_event(
                #     "user123",
                #     {
                #         "event_title": "Meeting with Team",
                #         "start_time": (datetime.now() + timedelta(minutes=15)).isoformat(),
                #         "end_time": (datetime.now() + timedelta(hours=1)).isoformat(),
                #         "attendees": ["team@example.com"]
                #     }
                # )
                
            except Exception as e:
                logger.error(f"Error monitoring calendar: {str(e)}")
                time.sleep(300)

# Global event system instance
redis_client = redis.Redis(host='localhost', port=6379, db=2, decode_responses=True)
event_publisher = EventPublisher(redis_client)
event_listener = EventListener(redis_client)
event_generator = EventGenerator(event_publisher)
event_monitor = EventMonitor(event_generator)

# Register workflow event handler
workflow_handler = WorkflowEventHandler(redis_client)
for event_type in EventType:
    event_listener.register_handler(event_type, workflow_handler.handle_event)

def start_event_system():
    """Start the complete event system"""
    event_listener.start_listening()
    event_monitor.start_monitoring()
    logger.info("Event system started")

def stop_event_system():
    """Stop the complete event system"""
    event_listener.stop_listening()
    event_monitor.stop_monitoring()
    logger.info("Event system stopped")

if __name__ == '__main__':
    start_event_system()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        stop_event_system()

