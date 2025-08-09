"""
Custom AI Training System for Personal AI Assistant
Provides personalized AI training, fine-tuning, and knowledge base management
"""

import os
import json
import logging
import redis
import uuid
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict, Counter
import pickle
import base64

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class TrainingData:
    data_id: str
    user_id: str
    data_type: str  # conversation, document, feedback, correction
    content: str
    metadata: Dict[str, Any]
    quality_score: float
    created_at: datetime
    updated_at: datetime

@dataclass
class UserProfile:
    user_id: str
    preferences: Dict[str, Any]
    communication_style: str
    expertise_areas: List[str]
    learning_goals: List[str]
    interaction_patterns: Dict[str, Any]
    personalization_level: str  # basic, intermediate, advanced
    created_at: datetime
    updated_at: datetime

@dataclass
class KnowledgeItem:
    knowledge_id: str
    user_id: str
    title: str
    content: str
    category: str
    tags: List[str]
    source: str
    confidence: float
    usage_count: int
    last_used: datetime
    created_at: datetime

@dataclass
class TrainingSession:
    session_id: str
    user_id: str
    session_type: str  # fine_tuning, knowledge_update, preference_learning
    status: str  # pending, running, completed, failed
    progress: float
    data_points: int
    improvements: Dict[str, Any]
    started_at: datetime
    completed_at: Optional[datetime]

class CustomAITrainingManager:
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.training_data_key = "ai_training:data"
        self.user_profiles_key = "ai_training:profiles"
        self.knowledge_base_key = "ai_training:knowledge"
        self.training_sessions_key = "ai_training:sessions"
        self.models_key = "ai_training:models"
        
        # Initialize training system
        self._initialize_training_system()
    
    def _initialize_training_system(self):
        """Initialize the custom AI training system"""
        try:
            # Create default categories
            default_categories = [
                "personal_preferences",
                "work_patterns",
                "communication_style",
                "domain_knowledge",
                "task_preferences",
                "learning_style",
                "feedback_patterns",
                "error_corrections"
            ]
            
            for category in default_categories:
                self.redis.sadd("ai_training:categories", category)
            
            # Initialize training algorithms
            self._initialize_training_algorithms()
            
            logger.info("Custom AI training system initialized")
            
        except Exception as e:
            logger.error(f"Error initializing training system: {str(e)}")
    
    def _initialize_training_algorithms(self):
        """Initialize training algorithms and models"""
        try:
            # Define training algorithms
            algorithms = {
                "preference_learning": {
                    "description": "Learn user preferences from interactions",
                    "data_types": ["conversation", "feedback", "choices"],
                    "update_frequency": "real_time",
                    "confidence_threshold": 0.7
                },
                "style_adaptation": {
                    "description": "Adapt communication style to user preferences",
                    "data_types": ["conversation", "feedback"],
                    "update_frequency": "daily",
                    "confidence_threshold": 0.8
                },
                "knowledge_integration": {
                    "description": "Integrate user-specific knowledge",
                    "data_types": ["document", "manual_input", "corrections"],
                    "update_frequency": "immediate",
                    "confidence_threshold": 0.9
                },
                "error_correction": {
                    "description": "Learn from user corrections",
                    "data_types": ["correction", "feedback"],
                    "update_frequency": "immediate",
                    "confidence_threshold": 0.95
                }
            }
            
            for algo_name, algo_config in algorithms.items():
                self.redis.hset("ai_training:algorithms", algo_name, json.dumps(algo_config))
            
        except Exception as e:
            logger.error(f"Error initializing training algorithms: {str(e)}")
    
    # User Profile Management
    def create_user_profile(self, user_id: str, initial_preferences: Dict[str, Any] = None) -> UserProfile:
        """Create a new user profile for personalized AI training"""
        try:
            profile = UserProfile(
                user_id=user_id,
                preferences=initial_preferences or {},
                communication_style="adaptive",
                expertise_areas=[],
                learning_goals=[],
                interaction_patterns={},
                personalization_level="basic",
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            # Store profile
            self.redis.hset(
                self.user_profiles_key,
                user_id,
                json.dumps(asdict(profile), default=str)
            )
            
            # Initialize user-specific training data storage
            user_training_key = f"ai_training:user_data:{user_id}"
            self.redis.hset(user_training_key, "created", datetime.now().isoformat())
            
            logger.info(f"Created user profile for {user_id}")
            return profile
            
        except Exception as e:
            logger.error(f"Error creating user profile: {str(e)}")
            return None
    
    def get_user_profile(self, user_id: str) -> Optional[UserProfile]:
        """Get user profile"""
        try:
            profile_data = self.redis.hget(self.user_profiles_key, user_id)
            if profile_data:
                profile_dict = json.loads(profile_data)
                profile_dict['created_at'] = datetime.fromisoformat(profile_dict['created_at'])
                profile_dict['updated_at'] = datetime.fromisoformat(profile_dict['updated_at'])
                return UserProfile(**profile_dict)
            return None
            
        except Exception as e:
            logger.error(f"Error getting user profile: {str(e)}")
            return None
    
    def update_user_profile(self, user_id: str, updates: Dict[str, Any]) -> bool:
        """Update user profile"""
        try:
            profile = self.get_user_profile(user_id)
            if not profile:
                return False
            
            # Update profile fields
            for key, value in updates.items():
                if hasattr(profile, key):
                    setattr(profile, key, value)
            
            profile.updated_at = datetime.now()
            
            # Store updated profile
            self.redis.hset(
                self.user_profiles_key,
                user_id,
                json.dumps(asdict(profile), default=str)
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating user profile: {str(e)}")
            return False
    
    # Training Data Management
    def add_training_data(self, user_id: str, data_type: str, content: str, 
                         metadata: Dict[str, Any] = None) -> str:
        """Add training data for user"""
        try:
            data_id = str(uuid.uuid4())
            
            # Calculate quality score based on content and metadata
            quality_score = self._calculate_quality_score(content, metadata or {})
            
            training_data = TrainingData(
                data_id=data_id,
                user_id=user_id,
                data_type=data_type,
                content=content,
                metadata=metadata or {},
                quality_score=quality_score,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            # Store training data
            self.redis.hset(
                self.training_data_key,
                data_id,
                json.dumps(asdict(training_data), default=str)
            )
            
            # Add to user's training data index
            user_data_key = f"ai_training:user_data:{user_id}"
            self.redis.lpush(user_data_key, data_id)
            self.redis.ltrim(user_data_key, 0, 9999)  # Keep last 10000 items
            
            # Trigger real-time learning if applicable
            self._trigger_realtime_learning(user_id, training_data)
            
            return data_id
            
        except Exception as e:
            logger.error(f"Error adding training data: {str(e)}")
            return None
    
    def _calculate_quality_score(self, content: str, metadata: Dict[str, Any]) -> float:
        """Calculate quality score for training data"""
        try:
            score = 0.5  # Base score
            
            # Content length factor
            content_length = len(content)
            if content_length > 100:
                score += 0.2
            if content_length > 500:
                score += 0.1
            
            # Metadata richness
            if metadata:
                score += min(0.2, len(metadata) * 0.05)
            
            # User feedback factor
            if metadata.get('user_rating'):
                rating = float(metadata['user_rating'])
                score += (rating - 3) * 0.1  # Assuming 1-5 scale, 3 is neutral
            
            # Correction factor
            if metadata.get('is_correction'):
                score += 0.3  # Corrections are high-value training data
            
            # Expertise factor
            if metadata.get('expertise_level'):
                expertise_levels = {'beginner': 0.1, 'intermediate': 0.2, 'expert': 0.3}
                score += expertise_levels.get(metadata['expertise_level'], 0)
            
            return min(1.0, max(0.0, score))
            
        except Exception as e:
            logger.error(f"Error calculating quality score: {str(e)}")
            return 0.5
    
    def get_user_training_data(self, user_id: str, data_type: str = None, 
                              limit: int = 100) -> List[TrainingData]:
        """Get training data for user"""
        try:
            user_data_key = f"ai_training:user_data:{user_id}"
            data_ids = self.redis.lrange(user_data_key, 0, limit - 1)
            
            training_data = []
            for data_id in data_ids:
                data_json = self.redis.hget(self.training_data_key, data_id)
                if data_json:
                    data_dict = json.loads(data_json)
                    data_dict['created_at'] = datetime.fromisoformat(data_dict['created_at'])
                    data_dict['updated_at'] = datetime.fromisoformat(data_dict['updated_at'])
                    
                    data_obj = TrainingData(**data_dict)
                    
                    # Filter by data type if specified
                    if data_type is None or data_obj.data_type == data_type:
                        training_data.append(data_obj)
            
            return training_data
            
        except Exception as e:
            logger.error(f"Error getting user training data: {str(e)}")
            return []
    
    # Knowledge Base Management
    def add_knowledge_item(self, user_id: str, title: str, content: str, 
                          category: str, tags: List[str] = None, 
                          source: str = "user_input") -> str:
        """Add knowledge item to user's personal knowledge base"""
        try:
            knowledge_id = str(uuid.uuid4())
            
            knowledge_item = KnowledgeItem(
                knowledge_id=knowledge_id,
                user_id=user_id,
                title=title,
                content=content,
                category=category,
                tags=tags or [],
                source=source,
                confidence=0.8,  # Default confidence
                usage_count=0,
                last_used=datetime.now(),
                created_at=datetime.now()
            )
            
            # Store knowledge item
            self.redis.hset(
                self.knowledge_base_key,
                knowledge_id,
                json.dumps(asdict(knowledge_item), default=str)
            )
            
            # Add to user's knowledge index
            user_knowledge_key = f"ai_training:user_knowledge:{user_id}"
            self.redis.lpush(user_knowledge_key, knowledge_id)
            
            # Add to category index
            category_key = f"ai_training:knowledge_category:{category}"
            self.redis.sadd(category_key, knowledge_id)
            
            # Add to tag indices
            for tag in tags or []:
                tag_key = f"ai_training:knowledge_tag:{tag}"
                self.redis.sadd(tag_key, knowledge_id)
            
            return knowledge_id
            
        except Exception as e:
            logger.error(f"Error adding knowledge item: {str(e)}")
            return None
    
    def search_knowledge(self, user_id: str, query: str, category: str = None, 
                        tags: List[str] = None, limit: int = 10) -> List[KnowledgeItem]:
        """Search user's knowledge base"""
        try:
            user_knowledge_key = f"ai_training:user_knowledge:{user_id}"
            knowledge_ids = self.redis.lrange(user_knowledge_key, 0, -1)
            
            matching_items = []
            query_lower = query.lower()
            
            for knowledge_id in knowledge_ids:
                knowledge_data = self.redis.hget(self.knowledge_base_key, knowledge_id)
                if knowledge_data:
                    knowledge_dict = json.loads(knowledge_data)
                    knowledge_dict['created_at'] = datetime.fromisoformat(knowledge_dict['created_at'])
                    knowledge_dict['last_used'] = datetime.fromisoformat(knowledge_dict['last_used'])
                    
                    knowledge_item = KnowledgeItem(**knowledge_dict)
                    
                    # Check if item matches search criteria
                    matches = False
                    
                    # Text search
                    if (query_lower in knowledge_item.title.lower() or 
                        query_lower in knowledge_item.content.lower()):
                        matches = True
                    
                    # Category filter
                    if category and knowledge_item.category != category:
                        matches = False
                    
                    # Tags filter
                    if tags and not any(tag in knowledge_item.tags for tag in tags):
                        matches = False
                    
                    if matches:
                        matching_items.append(knowledge_item)
            
            # Sort by relevance (simplified scoring)
            matching_items.sort(key=lambda x: (
                x.usage_count * 0.3 + 
                x.confidence * 0.7 + 
                (1 if query_lower in x.title.lower() else 0) * 0.5
            ), reverse=True)
            
            return matching_items[:limit]
            
        except Exception as e:
            logger.error(f"Error searching knowledge: {str(e)}")
            return []
    
    def update_knowledge_usage(self, knowledge_id: str) -> bool:
        """Update knowledge item usage statistics"""
        try:
            knowledge_data = self.redis.hget(self.knowledge_base_key, knowledge_id)
            if knowledge_data:
                knowledge_dict = json.loads(knowledge_data)
                knowledge_dict['usage_count'] += 1
                knowledge_dict['last_used'] = datetime.now().isoformat()
                
                self.redis.hset(
                    self.knowledge_base_key,
                    knowledge_id,
                    json.dumps(knowledge_dict)
                )
                return True
            return False
            
        except Exception as e:
            logger.error(f"Error updating knowledge usage: {str(e)}")
            return False
    
    # AI Training and Personalization
    def start_training_session(self, user_id: str, session_type: str, 
                              data_filter: Dict[str, Any] = None) -> str:
        """Start a new training session"""
        try:
            session_id = str(uuid.uuid4())
            
            # Get training data for session
            training_data = self.get_user_training_data(user_id)
            
            # Filter data based on session type and filters
            filtered_data = self._filter_training_data(training_data, session_type, data_filter or {})
            
            session = TrainingSession(
                session_id=session_id,
                user_id=user_id,
                session_type=session_type,
                status="pending",
                progress=0.0,
                data_points=len(filtered_data),
                improvements={},
                started_at=datetime.now(),
                completed_at=None
            )
            
            # Store session
            self.redis.hset(
                self.training_sessions_key,
                session_id,
                json.dumps(asdict(session), default=str)
            )
            
            # Start training process (async simulation)
            self._process_training_session(session_id, filtered_data)
            
            return session_id
            
        except Exception as e:
            logger.error(f"Error starting training session: {str(e)}")
            return None
    
    def _filter_training_data(self, training_data: List[TrainingData], 
                             session_type: str, data_filter: Dict[str, Any]) -> List[TrainingData]:
        """Filter training data for specific session type"""
        try:
            filtered_data = []
            
            for data in training_data:
                include = True
                
                # Filter by session type
                if session_type == "preference_learning":
                    include = data.data_type in ["conversation", "feedback", "choices"]
                elif session_type == "style_adaptation":
                    include = data.data_type in ["conversation", "feedback"]
                elif session_type == "knowledge_integration":
                    include = data.data_type in ["document", "manual_input", "corrections"]
                elif session_type == "error_correction":
                    include = data.data_type in ["correction", "feedback"]
                
                # Apply additional filters
                if include and data_filter:
                    if "min_quality" in data_filter:
                        include = data.quality_score >= data_filter["min_quality"]
                    
                    if "date_range" in data_filter:
                        start_date, end_date = data_filter["date_range"]
                        include = start_date <= data.created_at <= end_date
                    
                    if "data_types" in data_filter:
                        include = data.data_type in data_filter["data_types"]
                
                if include:
                    filtered_data.append(data)
            
            return filtered_data
            
        except Exception as e:
            logger.error(f"Error filtering training data: {str(e)}")
            return []
    
    def _process_training_session(self, session_id: str, training_data: List[TrainingData]):
        """Process training session (simplified simulation)"""
        try:
            # Update session status
            session_data = self.redis.hget(self.training_sessions_key, session_id)
            if not session_data:
                return
            
            session_dict = json.loads(session_data)
            session_dict['status'] = 'running'
            session_dict['progress'] = 0.1
            
            self.redis.hset(self.training_sessions_key, session_id, json.dumps(session_dict))
            
            # Simulate training process
            improvements = {}
            
            if session_dict['session_type'] == "preference_learning":
                improvements = self._learn_preferences(training_data)
            elif session_dict['session_type'] == "style_adaptation":
                improvements = self._adapt_communication_style(training_data)
            elif session_dict['session_type'] == "knowledge_integration":
                improvements = self._integrate_knowledge(training_data)
            elif session_dict['session_type'] == "error_correction":
                improvements = self._learn_from_corrections(training_data)
            
            # Update session completion
            session_dict['status'] = 'completed'
            session_dict['progress'] = 1.0
            session_dict['improvements'] = improvements
            session_dict['completed_at'] = datetime.now().isoformat()
            
            self.redis.hset(self.training_sessions_key, session_id, json.dumps(session_dict))
            
            # Apply improvements to user profile
            self._apply_training_improvements(session_dict['user_id'], improvements)
            
            logger.info(f"Training session {session_id} completed")
            
        except Exception as e:
            logger.error(f"Error processing training session: {str(e)}")
    
    def _learn_preferences(self, training_data: List[TrainingData]) -> Dict[str, Any]:
        """Learn user preferences from training data"""
        try:
            preferences = {}
            
            # Analyze conversation patterns
            conversation_data = [d for d in training_data if d.data_type == "conversation"]
            
            if conversation_data:
                # Analyze response length preferences
                response_lengths = []
                for data in conversation_data:
                    if 'response_length' in data.metadata:
                        response_lengths.append(data.metadata['response_length'])
                
                if response_lengths:
                    avg_length = sum(response_lengths) / len(response_lengths)
                    if avg_length < 50:
                        preferences['response_style'] = 'concise'
                    elif avg_length > 200:
                        preferences['response_style'] = 'detailed'
                    else:
                        preferences['response_style'] = 'balanced'
                
                # Analyze topic preferences
                topics = []
                for data in conversation_data:
                    if 'topics' in data.metadata:
                        topics.extend(data.metadata['topics'])
                
                if topics:
                    topic_counts = Counter(topics)
                    preferences['favorite_topics'] = dict(topic_counts.most_common(5))
            
            # Analyze feedback patterns
            feedback_data = [d for d in training_data if d.data_type == "feedback"]
            
            if feedback_data:
                positive_feedback = [d for d in feedback_data if d.metadata.get('sentiment') == 'positive']
                preferences['positive_feedback_ratio'] = len(positive_feedback) / len(feedback_data)
            
            return {
                'type': 'preference_learning',
                'preferences_learned': preferences,
                'data_points_analyzed': len(training_data),
                'confidence': min(1.0, len(training_data) / 100)  # More data = higher confidence
            }
            
        except Exception as e:
            logger.error(f"Error learning preferences: {str(e)}")
            return {}
    
    def _adapt_communication_style(self, training_data: List[TrainingData]) -> Dict[str, Any]:
        """Adapt communication style based on user interactions"""
        try:
            style_adaptations = {}
            
            # Analyze communication patterns
            conversation_data = [d for d in training_data if d.data_type == "conversation"]
            
            if conversation_data:
                # Analyze formality level
                formal_indicators = 0
                informal_indicators = 0
                
                for data in conversation_data:
                    content_lower = data.content.lower()
                    if any(word in content_lower for word in ['please', 'thank you', 'would you', 'could you']):
                        formal_indicators += 1
                    if any(word in content_lower for word in ['hey', 'yeah', 'ok', 'cool']):
                        informal_indicators += 1
                
                if formal_indicators > informal_indicators:
                    style_adaptations['formality'] = 'formal'
                elif informal_indicators > formal_indicators:
                    style_adaptations['formality'] = 'informal'
                else:
                    style_adaptations['formality'] = 'balanced'
                
                # Analyze technical level
                technical_terms = 0
                for data in conversation_data:
                    if 'technical_level' in data.metadata:
                        technical_terms += data.metadata['technical_level']
                
                if technical_terms > 0:
                    avg_technical = technical_terms / len(conversation_data)
                    if avg_technical > 0.7:
                        style_adaptations['technical_level'] = 'high'
                    elif avg_technical > 0.3:
                        style_adaptations['technical_level'] = 'medium'
                    else:
                        style_adaptations['technical_level'] = 'low'
            
            return {
                'type': 'style_adaptation',
                'style_adaptations': style_adaptations,
                'data_points_analyzed': len(training_data),
                'confidence': min(1.0, len(conversation_data) / 50)
            }
            
        except Exception as e:
            logger.error(f"Error adapting communication style: {str(e)}")
            return {}
    
    def _integrate_knowledge(self, training_data: List[TrainingData]) -> Dict[str, Any]:
        """Integrate new knowledge from training data"""
        try:
            knowledge_integrated = {}
            
            # Process document data
            document_data = [d for d in training_data if d.data_type == "document"]
            
            for data in document_data:
                # Extract key concepts (simplified)
                content_words = data.content.split()
                if len(content_words) > 10:  # Only process substantial content
                    # Simulate knowledge extraction
                    concepts = self._extract_concepts(data.content)
                    
                    for concept in concepts:
                        if concept not in knowledge_integrated:
                            knowledge_integrated[concept] = {
                                'frequency': 0,
                                'sources': [],
                                'confidence': 0.0
                            }
                        
                        knowledge_integrated[concept]['frequency'] += 1
                        knowledge_integrated[concept]['sources'].append(data.data_id)
                        knowledge_integrated[concept]['confidence'] = min(1.0, 
                            knowledge_integrated[concept]['frequency'] * 0.2)
            
            return {
                'type': 'knowledge_integration',
                'concepts_learned': len(knowledge_integrated),
                'knowledge_items': knowledge_integrated,
                'data_points_analyzed': len(training_data),
                'confidence': min(1.0, len(document_data) / 20)
            }
            
        except Exception as e:
            logger.error(f"Error integrating knowledge: {str(e)}")
            return {}
    
    def _extract_concepts(self, content: str) -> List[str]:
        """Extract key concepts from content (simplified)"""
        try:
            # Simple concept extraction based on word frequency and length
            words = content.lower().split()
            
            # Filter out common words and short words
            stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'can', 'this', 'that', 'these', 'those'}
            
            filtered_words = [word for word in words if len(word) > 3 and word not in stop_words]
            
            # Count word frequency
            word_counts = Counter(filtered_words)
            
            # Return top concepts
            return [word for word, count in word_counts.most_common(10) if count > 1]
            
        except Exception as e:
            logger.error(f"Error extracting concepts: {str(e)}")
            return []
    
    def _learn_from_corrections(self, training_data: List[TrainingData]) -> Dict[str, Any]:
        """Learn from user corrections"""
        try:
            corrections_learned = {}
            
            correction_data = [d for d in training_data if d.data_type == "correction"]
            
            for data in correction_data:
                if 'original_response' in data.metadata and 'corrected_response' in data.metadata:
                    original = data.metadata['original_response']
                    corrected = data.metadata['corrected_response']
                    
                    # Analyze the correction pattern
                    correction_type = self._analyze_correction_type(original, corrected)
                    
                    if correction_type not in corrections_learned:
                        corrections_learned[correction_type] = {
                            'count': 0,
                            'examples': [],
                            'confidence': 0.0
                        }
                    
                    corrections_learned[correction_type]['count'] += 1
                    corrections_learned[correction_type]['examples'].append({
                        'original': original[:100],  # Truncate for storage
                        'corrected': corrected[:100]
                    })
                    corrections_learned[correction_type]['confidence'] = min(1.0,
                        corrections_learned[correction_type]['count'] * 0.3)
            
            return {
                'type': 'error_correction',
                'correction_patterns': corrections_learned,
                'data_points_analyzed': len(training_data),
                'confidence': min(1.0, len(correction_data) / 10)
            }
            
        except Exception as e:
            logger.error(f"Error learning from corrections: {str(e)}")
            return {}
    
    def _analyze_correction_type(self, original: str, corrected: str) -> str:
        """Analyze the type of correction made"""
        try:
            original_len = len(original)
            corrected_len = len(corrected)
            
            # Length-based analysis
            if corrected_len > original_len * 1.5:
                return "expansion"
            elif corrected_len < original_len * 0.7:
                return "simplification"
            elif abs(corrected_len - original_len) < original_len * 0.2:
                return "refinement"
            else:
                return "restructuring"
                
        except Exception as e:
            logger.error(f"Error analyzing correction type: {str(e)}")
            return "unknown"
    
    def _apply_training_improvements(self, user_id: str, improvements: Dict[str, Any]):
        """Apply training improvements to user profile"""
        try:
            profile = self.get_user_profile(user_id)
            if not profile:
                return
            
            # Apply improvements based on type
            improvement_type = improvements.get('type')
            
            if improvement_type == "preference_learning":
                preferences = improvements.get('preferences_learned', {})
                profile.preferences.update(preferences)
            
            elif improvement_type == "style_adaptation":
                adaptations = improvements.get('style_adaptations', {})
                if 'formality' in adaptations:
                    profile.communication_style = adaptations['formality']
                profile.preferences.update(adaptations)
            
            elif improvement_type == "knowledge_integration":
                # Update expertise areas based on learned concepts
                concepts = improvements.get('knowledge_items', {})
                new_expertise = [concept for concept, data in concepts.items() 
                               if data['confidence'] > 0.7]
                profile.expertise_areas.extend(new_expertise)
                profile.expertise_areas = list(set(profile.expertise_areas))  # Remove duplicates
            
            elif improvement_type == "error_correction":
                # Update learning goals based on correction patterns
                patterns = improvements.get('correction_patterns', {})
                for pattern_type in patterns:
                    if pattern_type not in profile.learning_goals:
                        profile.learning_goals.append(f"improve_{pattern_type}")
            
            # Update personalization level based on training data volume
            confidence = improvements.get('confidence', 0)
            if confidence > 0.8:
                profile.personalization_level = "advanced"
            elif confidence > 0.5:
                profile.personalization_level = "intermediate"
            
            # Save updated profile
            self.update_user_profile(user_id, asdict(profile))
            
        except Exception as e:
            logger.error(f"Error applying training improvements: {str(e)}")
    
    def _trigger_realtime_learning(self, user_id: str, training_data: TrainingData):
        """Trigger real-time learning for high-quality data"""
        try:
            # Only trigger for high-quality data
            if training_data.quality_score < 0.8:
                return
            
            # Check if this is a correction or high-value feedback
            if training_data.data_type in ["correction", "feedback"]:
                # Start immediate learning session
                session_id = self.start_training_session(
                    user_id, 
                    "error_correction" if training_data.data_type == "correction" else "preference_learning",
                    {"data_types": [training_data.data_type], "min_quality": 0.8}
                )
                
                if session_id:
                    logger.info(f"Started real-time learning session {session_id} for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error triggering real-time learning: {str(e)}")
    
    # Training Session Management
    def get_training_session(self, session_id: str) -> Optional[TrainingSession]:
        """Get training session details"""
        try:
            session_data = self.redis.hget(self.training_sessions_key, session_id)
            if session_data:
                session_dict = json.loads(session_data)
                session_dict['started_at'] = datetime.fromisoformat(session_dict['started_at'])
                if session_dict['completed_at']:
                    session_dict['completed_at'] = datetime.fromisoformat(session_dict['completed_at'])
                return TrainingSession(**session_dict)
            return None
            
        except Exception as e:
            logger.error(f"Error getting training session: {str(e)}")
            return None
    
    def get_user_training_sessions(self, user_id: str, limit: int = 20) -> List[TrainingSession]:
        """Get user's training sessions"""
        try:
            all_sessions = self.redis.hgetall(self.training_sessions_key)
            user_sessions = []
            
            for session_id, session_data in all_sessions.items():
                session_dict = json.loads(session_data)
                if session_dict['user_id'] == user_id:
                    session_dict['started_at'] = datetime.fromisoformat(session_dict['started_at'])
                    if session_dict['completed_at']:
                        session_dict['completed_at'] = datetime.fromisoformat(session_dict['completed_at'])
                    user_sessions.append(TrainingSession(**session_dict))
            
            # Sort by start time (most recent first)
            user_sessions.sort(key=lambda x: x.started_at, reverse=True)
            
            return user_sessions[:limit]
            
        except Exception as e:
            logger.error(f"Error getting user training sessions: {str(e)}")
            return []
    
    # Personalization and Recommendations
    def get_personalized_response_style(self, user_id: str) -> Dict[str, Any]:
        """Get personalized response style for user"""
        try:
            profile = self.get_user_profile(user_id)
            if not profile:
                return self._get_default_response_style()
            
            style = {
                'formality': profile.preferences.get('formality', 'balanced'),
                'technical_level': profile.preferences.get('technical_level', 'medium'),
                'response_style': profile.preferences.get('response_style', 'balanced'),
                'communication_style': profile.communication_style,
                'expertise_areas': profile.expertise_areas,
                'personalization_level': profile.personalization_level
            }
            
            return style
            
        except Exception as e:
            logger.error(f"Error getting personalized response style: {str(e)}")
            return self._get_default_response_style()
    
    def _get_default_response_style(self) -> Dict[str, Any]:
        """Get default response style"""
        return {
            'formality': 'balanced',
            'technical_level': 'medium',
            'response_style': 'balanced',
            'communication_style': 'adaptive',
            'expertise_areas': [],
            'personalization_level': 'basic'
        }
    
    def get_training_recommendations(self, user_id: str) -> List[Dict[str, Any]]:
        """Get training recommendations for user"""
        try:
            profile = self.get_user_profile(user_id)
            if not profile:
                return []
            
            recommendations = []
            
            # Check training data volume
            training_data = self.get_user_training_data(user_id, limit=1000)
            
            if len(training_data) < 50:
                recommendations.append({
                    'type': 'data_collection',
                    'priority': 'high',
                    'title': 'Increase Training Data',
                    'description': 'Provide more interactions to improve personalization',
                    'action': 'Continue using the assistant and provide feedback'
                })
            
            # Check for recent corrections
            recent_corrections = [d for d in training_data 
                                if d.data_type == "correction" and 
                                (datetime.now() - d.created_at).days < 7]
            
            if recent_corrections:
                recommendations.append({
                    'type': 'error_correction',
                    'priority': 'medium',
                    'title': 'Process Recent Corrections',
                    'description': f'Learn from {len(recent_corrections)} recent corrections',
                    'action': 'Start error correction training session'
                })
            
            # Check personalization level
            if profile.personalization_level == 'basic' and len(training_data) > 100:
                recommendations.append({
                    'type': 'personalization_upgrade',
                    'priority': 'medium',
                    'title': 'Upgrade Personalization',
                    'description': 'Sufficient data available for advanced personalization',
                    'action': 'Start comprehensive training session'
                })
            
            # Check knowledge base
            user_knowledge_key = f"ai_training:user_knowledge:{user_id}"
            knowledge_count = self.redis.llen(user_knowledge_key)
            
            if knowledge_count < 10:
                recommendations.append({
                    'type': 'knowledge_building',
                    'priority': 'low',
                    'title': 'Build Knowledge Base',
                    'description': 'Add personal knowledge items for better assistance',
                    'action': 'Add documents, notes, or manual knowledge entries'
                })
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error getting training recommendations: {str(e)}")
            return []
    
    # Analytics and Insights
    def get_training_analytics(self, user_id: str) -> Dict[str, Any]:
        """Get training analytics for user"""
        try:
            profile = self.get_user_profile(user_id)
            training_data = self.get_user_training_data(user_id, limit=1000)
            training_sessions = self.get_user_training_sessions(user_id)
            
            # Calculate analytics
            analytics = {
                'profile_info': {
                    'personalization_level': profile.personalization_level if profile else 'basic',
                    'expertise_areas_count': len(profile.expertise_areas) if profile else 0,
                    'learning_goals_count': len(profile.learning_goals) if profile else 0,
                    'communication_style': profile.communication_style if profile else 'adaptive'
                },
                'training_data': {
                    'total_data_points': len(training_data),
                    'data_by_type': {},
                    'average_quality_score': 0.0,
                    'recent_data_points': 0
                },
                'training_sessions': {
                    'total_sessions': len(training_sessions),
                    'completed_sessions': len([s for s in training_sessions if s.status == 'completed']),
                    'recent_sessions': len([s for s in training_sessions 
                                          if (datetime.now() - s.started_at).days < 30])
                },
                'knowledge_base': {
                    'total_items': self.redis.llen(f"ai_training:user_knowledge:{user_id}"),
                    'categories': len(self.redis.smembers("ai_training:categories"))
                }
            }
            
            # Calculate data by type
            data_by_type = {}
            quality_scores = []
            recent_count = 0
            
            for data in training_data:
                data_by_type[data.data_type] = data_by_type.get(data.data_type, 0) + 1
                quality_scores.append(data.quality_score)
                
                if (datetime.now() - data.created_at).days < 30:
                    recent_count += 1
            
            analytics['training_data']['data_by_type'] = data_by_type
            analytics['training_data']['average_quality_score'] = (
                sum(quality_scores) / len(quality_scores) if quality_scores else 0.0
            )
            analytics['training_data']['recent_data_points'] = recent_count
            
            return analytics
            
        except Exception as e:
            logger.error(f"Error getting training analytics: {str(e)}")
            return {}

# Initialize custom AI training manager
redis_client = redis.Redis(host='localhost', port=6379, db=7, decode_responses=True)
custom_ai_training_manager = CustomAITrainingManager(redis_client)

def initialize_custom_ai_training():
    """Initialize custom AI training system"""
    logger.info("Custom AI training system initialized")

if __name__ == '__main__':
    initialize_custom_ai_training()

