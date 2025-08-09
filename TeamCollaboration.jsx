import React, { useState, useEffect } from 'react';
import { 
  Users, 
  Plus, 
  Settings, 
  CheckSquare, 
  BookOpen, 
  Bell,
  Calendar,
  MessageSquare,
  Star,
  Filter,
  Search,
  UserPlus,
  MoreHorizontal,
  Clock,
  AlertCircle,
  CheckCircle,
  XCircle
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';

const TeamCollaboration = ({ userId, isAuthenticated }) => {
  const [teams, setTeams] = useState([]);
  const [selectedTeam, setSelectedTeam] = useState(null);
  const [tasks, setTasks] = useState([]);
  const [knowledge, setKnowledge] = useState([]);
  const [notifications, setNotifications] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  
  // Modal states
  const [showCreateTeam, setShowCreateTeam] = useState(false);
  const [showCreateTask, setShowCreateTask] = useState(false);
  const [showShareKnowledge, setShowShareKnowledge] = useState(false);
  const [showInviteMember, setShowInviteMember] = useState(false);
  
  // Form states
  const [teamForm, setTeamForm] = useState({ name: '', description: '' });
  const [taskForm, setTaskForm] = useState({
    title: '',
    description: '',
    priority: 'medium',
    assigned_to: [],
    due_date: '',
    tags: ''
  });
  const [knowledgeForm, setKnowledgeForm] = useState({
    title: '',
    content: '',
    type: 'document',
    category: 'general',
    tags: '',
    is_public: false
  });
  const [inviteForm, setInviteForm] = useState({ email: '', role: 'member' });

  useEffect(() => {
    if (isAuthenticated) {
      loadUserTeams();
      loadNotifications();
    }
  }, [isAuthenticated]);

  useEffect(() => {
    if (selectedTeam) {
      loadTeamData(selectedTeam.team_id);
    }
  }, [selectedTeam]);

  const getAuthHeaders = () => ({
    'Authorization': `Bearer ${localStorage.getItem('auth_token')}`,
    'Content-Type': 'application/json'
  });

  const loadUserTeams = async () => {
    try {
      setLoading(true);
      const response = await fetch('/api/collaboration/user/teams', {
        headers: getAuthHeaders()
      });
      const data = await response.json();
      
      if (data.success) {
        setTeams(data.teams);
        if (data.teams.length > 0 && !selectedTeam) {
          setSelectedTeam(data.teams[0]);
        }
      } else {
        setError(data.error);
      }
    } catch (error) {
      setError('Failed to load teams');
    } finally {
      setLoading(false);
    }
  };

  const loadTeamData = async (teamId) => {
    try {
      // Load tasks
      const tasksResponse = await fetch(`/api/collaboration/teams/${teamId}/tasks`, {
        headers: getAuthHeaders()
      });
      const tasksData = await tasksResponse.json();
      if (tasksData.success) {
        setTasks(tasksData.tasks);
      }

      // Load knowledge
      const knowledgeResponse = await fetch(`/api/collaboration/teams/${teamId}/knowledge`, {
        headers: getAuthHeaders()
      });
      const knowledgeData = await knowledgeResponse.json();
      if (knowledgeData.success) {
        setKnowledge(knowledgeData.knowledge);
      }
    } catch (error) {
      console.error('Error loading team data:', error);
    }
  };

  const loadNotifications = async () => {
    try {
      const response = await fetch('/api/collaboration/notifications', {
        headers: getAuthHeaders()
      });
      const data = await response.json();
      
      if (data.success) {
        setNotifications(data.notifications);
      }
    } catch (error) {
      console.error('Error loading notifications:', error);
    }
  };

  const createTeam = async () => {
    try {
      const response = await fetch('/api/collaboration/teams', {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify(teamForm)
      });
      const data = await response.json();
      
      if (data.success) {
        setShowCreateTeam(false);
        setTeamForm({ name: '', description: '' });
        loadUserTeams();
      } else {
        setError(data.error);
      }
    } catch (error) {
      setError('Failed to create team');
    }
  };

  const createTask = async () => {
    try {
      const taskData = {
        ...taskForm,
        assigned_to: taskForm.assigned_to.split(',').map(id => id.trim()).filter(id => id),
        tags: taskForm.tags.split(',').map(tag => tag.trim()).filter(tag => tag),
        due_date: taskForm.due_date || null
      };

      const response = await fetch(`/api/collaboration/teams/${selectedTeam.team_id}/tasks`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify(taskData)
      });
      const data = await response.json();
      
      if (data.success) {
        setShowCreateTask(false);
        setTaskForm({
          title: '',
          description: '',
          priority: 'medium',
          assigned_to: [],
          due_date: '',
          tags: ''
        });
        loadTeamData(selectedTeam.team_id);
      } else {
        setError(data.error);
      }
    } catch (error) {
      setError('Failed to create task');
    }
  };

  const shareKnowledge = async () => {
    try {
      const knowledgeData = {
        ...knowledgeForm,
        tags: knowledgeForm.tags.split(',').map(tag => tag.trim()).filter(tag => tag)
      };

      const response = await fetch(`/api/collaboration/teams/${selectedTeam.team_id}/knowledge`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify(knowledgeData)
      });
      const data = await response.json();
      
      if (data.success) {
        setShowShareKnowledge(false);
        setKnowledgeForm({
          title: '',
          content: '',
          type: 'document',
          category: 'general',
          tags: '',
          is_public: false
        });
        loadTeamData(selectedTeam.team_id);
      } else {
        setError(data.error);
      }
    } catch (error) {
      setError('Failed to share knowledge');
    }
  };

  const inviteMember = async () => {
    try {
      const response = await fetch(`/api/collaboration/teams/${selectedTeam.team_id}/invite`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify(inviteForm)
      });
      const data = await response.json();
      
      if (data.success) {
        setShowInviteMember(false);
        setInviteForm({ email: '', role: 'member' });
        // Show success message
        alert('Invitation sent successfully!');
      } else {
        setError(data.error);
      }
    } catch (error) {
      setError('Failed to send invitation');
    }
  };

  const updateTaskStatus = async (taskId, status) => {
    try {
      const response = await fetch(`/api/collaboration/tasks/${taskId}/status`, {
        method: 'PUT',
        headers: getAuthHeaders(),
        body: JSON.stringify({ status })
      });
      const data = await response.json();
      
      if (data.success) {
        loadTeamData(selectedTeam.team_id);
      } else {
        setError(data.error);
      }
    } catch (error) {
      setError('Failed to update task status');
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="w-4 h-4 text-green-500" />;
      case 'in_progress':
        return <Clock className="w-4 h-4 text-blue-500" />;
      case 'cancelled':
        return <XCircle className="w-4 h-4 text-red-500" />;
      default:
        return <AlertCircle className="w-4 h-4 text-yellow-500" />;
    }
  };

  const getPriorityColor = (priority) => {
    switch (priority) {
      case 'urgent':
        return 'bg-red-500';
      case 'high':
        return 'bg-orange-500';
      case 'medium':
        return 'bg-blue-500';
      case 'low':
        return 'bg-gray-500';
      default:
        return 'bg-gray-500';
    }
  };

  if (!isAuthenticated) {
    return (
      <div className="team-collaboration-disabled p-6 text-center">
        <Users className="w-12 h-12 mx-auto mb-4 text-gray-400" />
        <h3 className="text-lg font-semibold mb-2">Team Collaboration</h3>
        <p className="text-gray-600">Please log in to access team collaboration features</p>
      </div>
    );
  }

  return (
    <div className="team-collaboration p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-bold flex items-center">
            <Users className="w-6 h-6 mr-2" />
            Team Collaboration
          </h2>
          <p className="text-gray-600">Collaborate with your team on tasks and knowledge sharing</p>
        </div>
        
        <div className="flex space-x-2">
          <Dialog open={showCreateTeam} onOpenChange={setShowCreateTeam}>
            <DialogTrigger asChild>
              <Button>
                <Plus className="w-4 h-4 mr-2" />
                Create Team
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Create New Team</DialogTitle>
              </DialogHeader>
              <div className="space-y-4">
                <Input
                  placeholder="Team name"
                  value={teamForm.name}
                  onChange={(e) => setTeamForm({...teamForm, name: e.target.value})}
                />
                <Textarea
                  placeholder="Team description"
                  value={teamForm.description}
                  onChange={(e) => setTeamForm({...teamForm, description: e.target.value})}
                />
                <div className="flex justify-end space-x-2">
                  <Button variant="outline" onClick={() => setShowCreateTeam(false)}>
                    Cancel
                  </Button>
                  <Button onClick={createTeam}>Create Team</Button>
                </div>
              </div>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      {/* Error Display */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
          <div className="flex items-center">
            <AlertCircle className="w-4 h-4 text-red-500 mr-2" />
            <span className="text-red-700">{error}</span>
            <Button 
              variant="ghost" 
              size="sm" 
              className="ml-auto"
              onClick={() => setError('')}
            >
              ×
            </Button>
          </div>
        </div>
      )}

      {/* Team Selector */}
      {teams.length > 0 && (
        <div className="mb-6">
          <Select
            value={selectedTeam?.team_id || ''}
            onValueChange={(teamId) => {
              const team = teams.find(t => t.team_id === teamId);
              setSelectedTeam(team);
            }}
          >
            <SelectTrigger className="w-64">
              <SelectValue placeholder="Select a team" />
            </SelectTrigger>
            <SelectContent>
              {teams.map((team) => (
                <SelectItem key={team.team_id} value={team.team_id}>
                  <div className="flex items-center">
                    <Users className="w-4 h-4 mr-2" />
                    <span>{team.name}</span>
                    <Badge variant="outline" className="ml-2">
                      {team.members_count} members
                    </Badge>
                  </div>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      )}

      {selectedTeam ? (
        <Tabs defaultValue="tasks" className="w-full">
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="tasks">
              <CheckSquare className="w-4 h-4 mr-2" />
              Tasks
            </TabsTrigger>
            <TabsTrigger value="knowledge">
              <BookOpen className="w-4 h-4 mr-2" />
              Knowledge
            </TabsTrigger>
            <TabsTrigger value="members">
              <Users className="w-4 h-4 mr-2" />
              Members
            </TabsTrigger>
            <TabsTrigger value="notifications">
              <Bell className="w-4 h-4 mr-2" />
              Notifications
            </TabsTrigger>
          </TabsList>

          {/* Tasks Tab */}
          <TabsContent value="tasks" className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold">Team Tasks</h3>
              <Dialog open={showCreateTask} onOpenChange={setShowCreateTask}>
                <DialogTrigger asChild>
                  <Button>
                    <Plus className="w-4 h-4 mr-2" />
                    Create Task
                  </Button>
                </DialogTrigger>
                <DialogContent className="max-w-md">
                  <DialogHeader>
                    <DialogTitle>Create New Task</DialogTitle>
                  </DialogHeader>
                  <div className="space-y-4">
                    <Input
                      placeholder="Task title"
                      value={taskForm.title}
                      onChange={(e) => setTaskForm({...taskForm, title: e.target.value})}
                    />
                    <Textarea
                      placeholder="Task description"
                      value={taskForm.description}
                      onChange={(e) => setTaskForm({...taskForm, description: e.target.value})}
                    />
                    <Select
                      value={taskForm.priority}
                      onValueChange={(value) => setTaskForm({...taskForm, priority: value})}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="low">Low Priority</SelectItem>
                        <SelectItem value="medium">Medium Priority</SelectItem>
                        <SelectItem value="high">High Priority</SelectItem>
                        <SelectItem value="urgent">Urgent</SelectItem>
                      </SelectContent>
                    </Select>
                    <Input
                      type="datetime-local"
                      value={taskForm.due_date}
                      onChange={(e) => setTaskForm({...taskForm, due_date: e.target.value})}
                    />
                    <Input
                      placeholder="Assigned to (user IDs, comma-separated)"
                      value={taskForm.assigned_to}
                      onChange={(e) => setTaskForm({...taskForm, assigned_to: e.target.value})}
                    />
                    <Input
                      placeholder="Tags (comma-separated)"
                      value={taskForm.tags}
                      onChange={(e) => setTaskForm({...taskForm, tags: e.target.value})}
                    />
                    <div className="flex justify-end space-x-2">
                      <Button variant="outline" onClick={() => setShowCreateTask(false)}>
                        Cancel
                      </Button>
                      <Button onClick={createTask}>Create Task</Button>
                    </div>
                  </div>
                </DialogContent>
              </Dialog>
            </div>

            <div className="grid gap-4">
              {tasks.map((task) => (
                <Card key={task.task_id}>
                  <CardContent className="p-4">
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center space-x-2 mb-2">
                          {getStatusIcon(task.status)}
                          <h4 className="font-semibold">{task.title}</h4>
                          <Badge className={`${getPriorityColor(task.priority)} text-white`}>
                            {task.priority}
                          </Badge>
                        </div>
                        <p className="text-gray-600 text-sm mb-2">{task.description}</p>
                        <div className="flex items-center space-x-4 text-xs text-gray-500">
                          <span>Created: {new Date(task.created_at).toLocaleDateString()}</span>
                          {task.due_date && (
                            <span>Due: {new Date(task.due_date).toLocaleDateString()}</span>
                          )}
                          <span>Assigned: {task.assigned_to.length} people</span>
                        </div>
                        {task.tags.length > 0 && (
                          <div className="flex flex-wrap gap-1 mt-2">
                            {task.tags.map((tag, index) => (
                              <Badge key={index} variant="outline" className="text-xs">
                                {tag}
                              </Badge>
                            ))}
                          </div>
                        )}
                      </div>
                      <div className="flex space-x-1">
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => updateTaskStatus(task.task_id, 'in_progress')}
                          disabled={task.status === 'in_progress'}
                        >
                          Start
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => updateTaskStatus(task.task_id, 'completed')}
                          disabled={task.status === 'completed'}
                        >
                          Complete
                        </Button>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </TabsContent>

          {/* Knowledge Tab */}
          <TabsContent value="knowledge" className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold">Team Knowledge</h3>
              <Dialog open={showShareKnowledge} onOpenChange={setShowShareKnowledge}>
                <DialogTrigger asChild>
                  <Button>
                    <Plus className="w-4 h-4 mr-2" />
                    Share Knowledge
                  </Button>
                </DialogTrigger>
                <DialogContent className="max-w-md">
                  <DialogHeader>
                    <DialogTitle>Share Knowledge</DialogTitle>
                  </DialogHeader>
                  <div className="space-y-4">
                    <Input
                      placeholder="Title"
                      value={knowledgeForm.title}
                      onChange={(e) => setKnowledgeForm({...knowledgeForm, title: e.target.value})}
                    />
                    <Textarea
                      placeholder="Content"
                      value={knowledgeForm.content}
                      onChange={(e) => setKnowledgeForm({...knowledgeForm, content: e.target.value})}
                      rows={4}
                    />
                    <Select
                      value={knowledgeForm.type}
                      onValueChange={(value) => setKnowledgeForm({...knowledgeForm, type: value})}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="document">Document</SelectItem>
                        <SelectItem value="workflow">Workflow</SelectItem>
                        <SelectItem value="template">Template</SelectItem>
                        <SelectItem value="faq">FAQ</SelectItem>
                      </SelectContent>
                    </Select>
                    <Input
                      placeholder="Category"
                      value={knowledgeForm.category}
                      onChange={(e) => setKnowledgeForm({...knowledgeForm, category: e.target.value})}
                    />
                    <Input
                      placeholder="Tags (comma-separated)"
                      value={knowledgeForm.tags}
                      onChange={(e) => setKnowledgeForm({...knowledgeForm, tags: e.target.value})}
                    />
                    <div className="flex justify-end space-x-2">
                      <Button variant="outline" onClick={() => setShowShareKnowledge(false)}>
                        Cancel
                      </Button>
                      <Button onClick={shareKnowledge}>Share</Button>
                    </div>
                  </div>
                </DialogContent>
              </Dialog>
            </div>

            <div className="grid gap-4">
              {knowledge.map((item) => (
                <Card key={item.knowledge_id}>
                  <CardContent className="p-4">
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center space-x-2 mb-2">
                          <BookOpen className="w-4 h-4" />
                          <h4 className="font-semibold">{item.title}</h4>
                          <Badge variant="outline">{item.type}</Badge>
                          <Badge variant="outline">{item.category}</Badge>
                        </div>
                        <div className="flex items-center space-x-4 text-xs text-gray-500 mb-2">
                          <span>Created: {new Date(item.created_at).toLocaleDateString()}</span>
                          <span>Views: {item.access_count}</span>
                          <div className="flex items-center">
                            <Star className="w-3 h-3 mr-1" />
                            <span>{item.rating.toFixed(1)}</span>
                          </div>
                        </div>
                        {item.tags.length > 0 && (
                          <div className="flex flex-wrap gap-1">
                            {item.tags.map((tag, index) => (
                              <Badge key={index} variant="outline" className="text-xs">
                                {tag}
                              </Badge>
                            ))}
                          </div>
                        )}
                      </div>
                      <Button size="sm" variant="outline">
                        View
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </TabsContent>

          {/* Members Tab */}
          <TabsContent value="members" className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold">Team Members</h3>
              <Dialog open={showInviteMember} onOpenChange={setShowInviteMember}>
                <DialogTrigger asChild>
                  <Button>
                    <UserPlus className="w-4 h-4 mr-2" />
                    Invite Member
                  </Button>
                </DialogTrigger>
                <DialogContent>
                  <DialogHeader>
                    <DialogTitle>Invite Team Member</DialogTitle>
                  </DialogHeader>
                  <div className="space-y-4">
                    <Input
                      type="email"
                      placeholder="Email address"
                      value={inviteForm.email}
                      onChange={(e) => setInviteForm({...inviteForm, email: e.target.value})}
                    />
                    <Select
                      value={inviteForm.role}
                      onValueChange={(value) => setInviteForm({...inviteForm, role: value})}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="viewer">Viewer</SelectItem>
                        <SelectItem value="member">Member</SelectItem>
                        <SelectItem value="admin">Admin</SelectItem>
                      </SelectContent>
                    </Select>
                    <div className="flex justify-end space-x-2">
                      <Button variant="outline" onClick={() => setShowInviteMember(false)}>
                        Cancel
                      </Button>
                      <Button onClick={inviteMember}>Send Invitation</Button>
                    </div>
                  </div>
                </DialogContent>
              </Dialog>
            </div>

            <div className="text-center py-8 text-gray-500">
              <Users className="w-12 h-12 mx-auto mb-4 opacity-50" />
              <p>Team member management will be available after team selection</p>
            </div>
          </TabsContent>

          {/* Notifications Tab */}
          <TabsContent value="notifications" className="space-y-4">
            <h3 className="text-lg font-semibold">Notifications</h3>
            
            <div className="space-y-2">
              {notifications.length > 0 ? (
                notifications.map((notification) => (
                  <Card key={notification.notification_id} className={notification.is_read ? 'opacity-60' : ''}>
                    <CardContent className="p-4">
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <h4 className="font-semibold text-sm">{notification.title}</h4>
                          <p className="text-gray-600 text-sm">{notification.message}</p>
                          <span className="text-xs text-gray-500">
                            {new Date(notification.created_at).toLocaleString()}
                          </span>
                        </div>
                        {!notification.is_read && (
                          <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
                        )}
                      </div>
                    </CardContent>
                  </Card>
                ))
              ) : (
                <div className="text-center py-8 text-gray-500">
                  <Bell className="w-12 h-12 mx-auto mb-4 opacity-50" />
                  <p>No notifications yet</p>
                </div>
              )}
            </div>
          </TabsContent>
        </Tabs>
      ) : (
        <div className="text-center py-12">
          <Users className="w-16 h-16 mx-auto mb-4 text-gray-400" />
          <h3 className="text-xl font-semibold mb-2">No Teams Yet</h3>
          <p className="text-gray-600 mb-4">Create your first team to start collaborating</p>
          <Button onClick={() => setShowCreateTeam(true)}>
            <Plus className="w-4 h-4 mr-2" />
            Create Your First Team
          </Button>
        </div>
      )}
    </div>
  );
};

export default TeamCollaboration;

