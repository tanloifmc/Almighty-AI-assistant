"""
Collaboration Manager for AI Assistant
Handles team collaboration, shared tasks, knowledge sharing, and multi-user interactions
"""

import os
import json
import logging
import redis
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import uuid

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TeamRole(Enum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"

class TaskStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class TaskPriority(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"

class NotificationType(Enum):
    TASK_ASSIGNED = "task_assigned"
    TASK_COMPLETED = "task_completed"
    TEAM_INVITE = "team_invite"
    KNOWLEDGE_SHARED = "knowledge_shared"
    WORKFLOW_SHARED = "workflow_shared"

@dataclass
class TeamMember:
    user_id: str
    username: str
    email: str
    role: TeamRole
    joined_at: datetime
    last_active: datetime
    permissions: List[str]
    avatar_url: Optional[str] = None

@dataclass
class Team:
    team_id: str
    name: str
    description: str
    owner_id: str
    created_at: datetime
    updated_at: datetime
    members: List[TeamMember]
    settings: Dict[str, Any]
    is_active: bool = True

@dataclass
class SharedTask:
    task_id: str
    title: str
    description: str
    team_id: str
    created_by: str
    assigned_to: List[str]
    status: TaskStatus
    priority: TaskPriority
    due_date: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    tags: List[str]
    attachments: List[str]
    comments: List[Dict[str, Any]]
    workflow_id: Optional[str] = None

@dataclass
class KnowledgeItem:
    knowledge_id: str
    title: str
    content: str
    type: str  # document, workflow, template, faq
    team_id: str
    created_by: str
    created_at: datetime
    updated_at: datetime
    tags: List[str]
    category: str
    is_public: bool
    access_count: int
    rating: float

@dataclass
class Notification:
    notification_id: str
    user_id: str
    team_id: str
    type: NotificationType
    title: str
    message: str
    data: Dict[str, Any]
    created_at: datetime
    read_at: Optional[datetime]
    is_read: bool = False

class CollaborationManager:
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.teams_key = "collaboration:teams"
        self.tasks_key = "collaboration:tasks"
        self.knowledge_key = "collaboration:knowledge"
        self.notifications_key = "collaboration:notifications"
        self.user_teams_key = "collaboration:user_teams"
        
    # Team Management
    def create_team(self, name: str, description: str, owner_id: str, owner_username: str, owner_email: str) -> Team:
        """Create a new team"""
        try:
            team_id = str(uuid.uuid4())
            now = datetime.now()
            
            # Create owner as first member
            owner = TeamMember(
                user_id=owner_id,
                username=owner_username,
                email=owner_email,
                role=TeamRole.OWNER,
                joined_at=now,
                last_active=now,
                permissions=["all"]
            )
            
            team = Team(
                team_id=team_id,
                name=name,
                description=description,
                owner_id=owner_id,
                created_at=now,
                updated_at=now,
                members=[owner],
                settings={
                    "allow_member_invite": False,
                    "auto_assign_tasks": False,
                    "knowledge_sharing": True,
                    "notification_settings": {
                        "email": True,
                        "push": True,
                        "in_app": True
                    }
                }
            )
            
            # Store team
            self.redis.hset(self.teams_key, team_id, json.dumps(asdict(team), default=str))
            
            # Add to user's teams
            user_teams = self.get_user_teams(owner_id)
            user_teams.append(team_id)
            self.redis.hset(self.user_teams_key, owner_id, json.dumps(user_teams))
            
            logger.info(f"Created team {team_id} for user {owner_id}")
            return team
            
        except Exception as e:
            logger.error(f"Error creating team: {str(e)}")
            raise

    def get_team(self, team_id: str) -> Optional[Team]:
        """Get team by ID"""
        try:
            team_data = self.redis.hget(self.teams_key, team_id)
            if not team_data:
                return None
            
            team_dict = json.loads(team_data)
            
            # Convert members
            members = []
            for member_data in team_dict['members']:
                member_data['role'] = TeamRole(member_data['role'])
                member_data['joined_at'] = datetime.fromisoformat(member_data['joined_at'])
                member_data['last_active'] = datetime.fromisoformat(member_data['last_active'])
                members.append(TeamMember(**member_data))
            
            team_dict['members'] = members
            team_dict['created_at'] = datetime.fromisoformat(team_dict['created_at'])
            team_dict['updated_at'] = datetime.fromisoformat(team_dict['updated_at'])
            
            return Team(**team_dict)
            
        except Exception as e:
            logger.error(f"Error getting team {team_id}: {str(e)}")
            return None

    def invite_member(self, team_id: str, inviter_id: str, email: str, role: TeamRole = TeamRole.MEMBER) -> bool:
        """Invite a member to team"""
        try:
            team = self.get_team(team_id)
            if not team:
                return False
            
            # Check if inviter has permission
            inviter_member = next((m for m in team.members if m.user_id == inviter_id), None)
            if not inviter_member or inviter_member.role not in [TeamRole.OWNER, TeamRole.ADMIN]:
                return False
            
            # Check if already member
            if any(m.email == email for m in team.members):
                return False
            
            # Create invitation notification (would be sent via email in real implementation)
            invite_data = {
                "team_id": team_id,
                "team_name": team.name,
                "inviter": inviter_member.username,
                "role": role.value,
                "invite_token": str(uuid.uuid4())
            }
            
            # Store invitation
            self.redis.hset(f"collaboration:invitations", email, json.dumps(invite_data, default=str))
            self.redis.expire(f"collaboration:invitations:{email}", 7 * 24 * 3600)  # 7 days
            
            logger.info(f"Invited {email} to team {team_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error inviting member: {str(e)}")
            return False

    def join_team(self, team_id: str, user_id: str, username: str, email: str, invite_token: str) -> bool:
        """Join team with invitation token"""
        try:
            # Verify invitation
            invite_data = self.redis.hget("collaboration:invitations", email)
            if not invite_data:
                return False
            
            invite_info = json.loads(invite_data)
            if invite_info["team_id"] != team_id or invite_info["invite_token"] != invite_token:
                return False
            
            team = self.get_team(team_id)
            if not team:
                return False
            
            # Add member
            now = datetime.now()
            new_member = TeamMember(
                user_id=user_id,
                username=username,
                email=email,
                role=TeamRole(invite_info["role"]),
                joined_at=now,
                last_active=now,
                permissions=self._get_default_permissions(TeamRole(invite_info["role"]))
            )
            
            team.members.append(new_member)
            team.updated_at = now
            
            # Update team
            self.redis.hset(self.teams_key, team_id, json.dumps(asdict(team), default=str))
            
            # Add to user's teams
            user_teams = self.get_user_teams(user_id)
            user_teams.append(team_id)
            self.redis.hset(self.user_teams_key, user_id, json.dumps(user_teams))
            
            # Remove invitation
            self.redis.hdel("collaboration:invitations", email)
            
            # Send notification to team
            self._send_team_notification(
                team_id, 
                NotificationType.TEAM_INVITE,
                f"{username} joined the team",
                f"{username} has joined {team.name}",
                {"new_member_id": user_id}
            )
            
            logger.info(f"User {user_id} joined team {team_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error joining team: {str(e)}")
            return False

    def get_user_teams(self, user_id: str) -> List[str]:
        """Get list of team IDs for user"""
        try:
            teams_data = self.redis.hget(self.user_teams_key, user_id)
            if not teams_data:
                return []
            return json.loads(teams_data)
        except:
            return []

    # Task Management
    def create_shared_task(self, title: str, description: str, team_id: str, created_by: str, 
                          assigned_to: List[str], priority: TaskPriority = TaskPriority.MEDIUM,
                          due_date: Optional[datetime] = None, tags: List[str] = None) -> SharedTask:
        """Create a shared task"""
        try:
            task_id = str(uuid.uuid4())
            now = datetime.now()
            
            task = SharedTask(
                task_id=task_id,
                title=title,
                description=description,
                team_id=team_id,
                created_by=created_by,
                assigned_to=assigned_to or [],
                status=TaskStatus.PENDING,
                priority=priority,
                due_date=due_date,
                created_at=now,
                updated_at=now,
                tags=tags or [],
                attachments=[],
                comments=[]
            )
            
            # Store task
            self.redis.hset(self.tasks_key, task_id, json.dumps(asdict(task), default=str))
            
            # Add to team's tasks
            team_tasks = self.get_team_tasks(team_id)
            team_tasks.append(task_id)
            self.redis.hset(f"collaboration:team_tasks", team_id, json.dumps(team_tasks))
            
            # Send notifications to assigned members
            for user_id in assigned_to:
                self._send_notification(
                    user_id,
                    team_id,
                    NotificationType.TASK_ASSIGNED,
                    "New task assigned",
                    f"You have been assigned to task: {title}",
                    {"task_id": task_id}
                )
            
            logger.info(f"Created shared task {task_id} in team {team_id}")
            return task
            
        except Exception as e:
            logger.error(f"Error creating shared task: {str(e)}")
            raise

    def update_task_status(self, task_id: str, user_id: str, status: TaskStatus, comment: str = "") -> bool:
        """Update task status"""
        try:
            task = self.get_shared_task(task_id)
            if not task:
                return False
            
            # Check if user can update task
            if user_id not in task.assigned_to and user_id != task.created_by:
                team = self.get_team(task.team_id)
                if team:
                    user_member = next((m for m in team.members if m.user_id == user_id), None)
                    if not user_member or user_member.role not in [TeamRole.OWNER, TeamRole.ADMIN]:
                        return False
            
            old_status = task.status
            task.status = status
            task.updated_at = datetime.now()
            
            # Add comment if provided
            if comment:
                task.comments.append({
                    "user_id": user_id,
                    "comment": comment,
                    "timestamp": datetime.now().isoformat(),
                    "type": "status_update"
                })
            
            # Update task
            self.redis.hset(self.tasks_key, task_id, json.dumps(asdict(task), default=str))
            
            # Send notification if completed
            if status == TaskStatus.COMPLETED:
                self._send_team_notification(
                    task.team_id,
                    NotificationType.TASK_COMPLETED,
                    "Task completed",
                    f"Task '{task.title}' has been completed",
                    {"task_id": task_id, "completed_by": user_id}
                )
            
            logger.info(f"Updated task {task_id} status from {old_status.value} to {status.value}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating task status: {str(e)}")
            return False

    def get_shared_task(self, task_id: str) -> Optional[SharedTask]:
        """Get shared task by ID"""
        try:
            task_data = self.redis.hget(self.tasks_key, task_id)
            if not task_data:
                return None
            
            task_dict = json.loads(task_data)
            task_dict['status'] = TaskStatus(task_dict['status'])
            task_dict['priority'] = TaskPriority(task_dict['priority'])
            task_dict['created_at'] = datetime.fromisoformat(task_dict['created_at'])
            task_dict['updated_at'] = datetime.fromisoformat(task_dict['updated_at'])
            
            if task_dict['due_date']:
                task_dict['due_date'] = datetime.fromisoformat(task_dict['due_date'])
            
            return SharedTask(**task_dict)
            
        except Exception as e:
            logger.error(f"Error getting shared task {task_id}: {str(e)}")
            return None

    def get_team_tasks(self, team_id: str) -> List[str]:
        """Get list of task IDs for team"""
        try:
            tasks_data = self.redis.hget(f"collaboration:team_tasks", team_id)
            if not tasks_data:
                return []
            return json.loads(tasks_data)
        except:
            return []

    # Knowledge Sharing
    def share_knowledge(self, title: str, content: str, knowledge_type: str, team_id: str, 
                       created_by: str, category: str, tags: List[str] = None, is_public: bool = False) -> KnowledgeItem:
        """Share knowledge with team"""
        try:
            knowledge_id = str(uuid.uuid4())
            now = datetime.now()
            
            knowledge = KnowledgeItem(
                knowledge_id=knowledge_id,
                title=title,
                content=content,
                type=knowledge_type,
                team_id=team_id,
                created_by=created_by,
                created_at=now,
                updated_at=now,
                tags=tags or [],
                category=category,
                is_public=is_public,
                access_count=0,
                rating=0.0
            )
            
            # Store knowledge
            self.redis.hset(self.knowledge_key, knowledge_id, json.dumps(asdict(knowledge), default=str))
            
            # Add to team's knowledge
            team_knowledge = self.get_team_knowledge(team_id)
            team_knowledge.append(knowledge_id)
            self.redis.hset(f"collaboration:team_knowledge", team_id, json.dumps(team_knowledge))
            
            # Send notification
            self._send_team_notification(
                team_id,
                NotificationType.KNOWLEDGE_SHARED,
                "New knowledge shared",
                f"New {knowledge_type}: {title}",
                {"knowledge_id": knowledge_id}
            )
            
            logger.info(f"Shared knowledge {knowledge_id} in team {team_id}")
            return knowledge
            
        except Exception as e:
            logger.error(f"Error sharing knowledge: {str(e)}")
            raise

    def get_knowledge_item(self, knowledge_id: str) -> Optional[KnowledgeItem]:
        """Get knowledge item by ID"""
        try:
            knowledge_data = self.redis.hget(self.knowledge_key, knowledge_id)
            if not knowledge_data:
                return None
            
            knowledge_dict = json.loads(knowledge_data)
            knowledge_dict['created_at'] = datetime.fromisoformat(knowledge_dict['created_at'])
            knowledge_dict['updated_at'] = datetime.fromisoformat(knowledge_dict['updated_at'])
            
            return KnowledgeItem(**knowledge_dict)
            
        except Exception as e:
            logger.error(f"Error getting knowledge item {knowledge_id}: {str(e)}")
            return None

    def get_team_knowledge(self, team_id: str) -> List[str]:
        """Get list of knowledge IDs for team"""
        try:
            knowledge_data = self.redis.hget(f"collaboration:team_knowledge", team_id)
            if not knowledge_data:
                return []
            return json.loads(knowledge_data)
        except:
            return []

    def search_knowledge(self, team_id: str, query: str, category: str = None, knowledge_type: str = None) -> List[KnowledgeItem]:
        """Search knowledge in team"""
        try:
            knowledge_ids = self.get_team_knowledge(team_id)
            results = []
            
            for knowledge_id in knowledge_ids:
                knowledge = self.get_knowledge_item(knowledge_id)
                if not knowledge:
                    continue
                
                # Filter by category and type
                if category and knowledge.category != category:
                    continue
                if knowledge_type and knowledge.type != knowledge_type:
                    continue
                
                # Search in title, content, and tags
                search_text = f"{knowledge.title} {knowledge.content} {' '.join(knowledge.tags)}".lower()
                if query.lower() in search_text:
                    results.append(knowledge)
            
            # Sort by relevance (simple scoring)
            results.sort(key=lambda x: x.access_count + x.rating, reverse=True)
            return results
            
        except Exception as e:
            logger.error(f"Error searching knowledge: {str(e)}")
            return []

    # Notification System
    def _send_notification(self, user_id: str, team_id: str, notification_type: NotificationType,
                          title: str, message: str, data: Dict[str, Any] = None):
        """Send notification to user"""
        try:
            notification_id = str(uuid.uuid4())
            notification = Notification(
                notification_id=notification_id,
                user_id=user_id,
                team_id=team_id,
                type=notification_type,
                title=title,
                message=message,
                data=data or {},
                created_at=datetime.now()
            )
            
            # Store notification
            self.redis.hset(self.notifications_key, notification_id, json.dumps(asdict(notification), default=str))
            
            # Add to user's notifications
            user_notifications = self.get_user_notifications(user_id)
            user_notifications.append(notification_id)
            self.redis.hset(f"collaboration:user_notifications", user_id, json.dumps(user_notifications))
            
        except Exception as e:
            logger.error(f"Error sending notification: {str(e)}")

    def _send_team_notification(self, team_id: str, notification_type: NotificationType,
                               title: str, message: str, data: Dict[str, Any] = None):
        """Send notification to all team members"""
        try:
            team = self.get_team(team_id)
            if not team:
                return
            
            for member in team.members:
                self._send_notification(member.user_id, team_id, notification_type, title, message, data)
                
        except Exception as e:
            logger.error(f"Error sending team notification: {str(e)}")

    def get_user_notifications(self, user_id: str, unread_only: bool = False) -> List[str]:
        """Get user notifications"""
        try:
            notifications_data = self.redis.hget(f"collaboration:user_notifications", user_id)
            if not notifications_data:
                return []
            
            notification_ids = json.loads(notifications_data)
            
            if unread_only:
                unread_ids = []
                for notification_id in notification_ids:
                    notification_data = self.redis.hget(self.notifications_key, notification_id)
                    if notification_data:
                        notification = json.loads(notification_data)
                        if not notification.get('is_read', False):
                            unread_ids.append(notification_id)
                return unread_ids
            
            return notification_ids
            
        except:
            return []

    def mark_notification_read(self, notification_id: str, user_id: str) -> bool:
        """Mark notification as read"""
        try:
            notification_data = self.redis.hget(self.notifications_key, notification_id)
            if not notification_data:
                return False
            
            notification = json.loads(notification_data)
            if notification['user_id'] != user_id:
                return False
            
            notification['is_read'] = True
            notification['read_at'] = datetime.now().isoformat()
            
            self.redis.hset(self.notifications_key, notification_id, json.dumps(notification))
            return True
            
        except Exception as e:
            logger.error(f"Error marking notification read: {str(e)}")
            return False

    # Utility Methods
    def _get_default_permissions(self, role: TeamRole) -> List[str]:
        """Get default permissions for role"""
        if role == TeamRole.OWNER:
            return ["all"]
        elif role == TeamRole.ADMIN:
            return ["manage_tasks", "manage_knowledge", "invite_members", "view_analytics"]
        elif role == TeamRole.MEMBER:
            return ["create_tasks", "share_knowledge", "view_team"]
        else:  # VIEWER
            return ["view_team", "view_knowledge"]

    def get_team_analytics(self, team_id: str) -> Dict[str, Any]:
        """Get team analytics"""
        try:
            team = self.get_team(team_id)
            if not team:
                return {}
            
            task_ids = self.get_team_tasks(team_id)
            knowledge_ids = self.get_team_knowledge(team_id)
            
            # Task statistics
            task_stats = {
                "total": len(task_ids),
                "completed": 0,
                "in_progress": 0,
                "pending": 0
            }
            
            for task_id in task_ids:
                task = self.get_shared_task(task_id)
                if task:
                    if task.status == TaskStatus.COMPLETED:
                        task_stats["completed"] += 1
                    elif task.status == TaskStatus.IN_PROGRESS:
                        task_stats["in_progress"] += 1
                    elif task.status == TaskStatus.PENDING:
                        task_stats["pending"] += 1
            
            # Knowledge statistics
            knowledge_stats = {
                "total": len(knowledge_ids),
                "documents": 0,
                "workflows": 0,
                "templates": 0
            }
            
            for knowledge_id in knowledge_ids:
                knowledge = self.get_knowledge_item(knowledge_id)
                if knowledge:
                    knowledge_stats[knowledge.type + "s"] = knowledge_stats.get(knowledge.type + "s", 0) + 1
            
            return {
                "team_info": {
                    "name": team.name,
                    "members_count": len(team.members),
                    "created_at": team.created_at.isoformat()
                },
                "tasks": task_stats,
                "knowledge": knowledge_stats,
                "activity": {
                    "last_updated": team.updated_at.isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting team analytics: {str(e)}")
            return {}

# Initialize collaboration manager
redis_client = redis.Redis(host='localhost', port=6379, db=5, decode_responses=True)
collaboration_manager = CollaborationManager(redis_client)

def initialize_collaboration():
    """Initialize collaboration system"""
    logger.info("Collaboration system initialized")

if __name__ == '__main__':
    initialize_collaboration()

