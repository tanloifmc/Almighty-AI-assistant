#!/usr/bin/env python3
"""
Comprehensive Test Suite for Personal AI Assistant
Tests all components and APIs of the system
"""

import requests
import json
import time
import sys
import subprocess
import threading
from datetime import datetime
import redis

class PersonalAIAssistantTester:
    def __init__(self):
        self.base_urls = {
            'backend': 'http://localhost:5000',
            'multilingual': 'http://localhost:5001',
            'voice': 'http://localhost:5002',
            'collaboration': 'http://localhost:5003',
            'analytics': 'http://localhost:5004',
            'training': 'http://localhost:5005'
        }
        self.test_results = {}
        self.redis_client = None
        
    def setup_redis(self):
        """Setup Redis connection"""
        try:
            self.redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)
            self.redis_client.ping()
            print("✅ Redis connection established")
            return True
        except Exception as e:
            print(f"❌ Redis connection failed: {e}")
            return False
    
    def test_health_endpoints(self):
        """Test health endpoints for all services"""
        print("\n🔍 Testing Health Endpoints...")
        
        health_endpoints = {
            'backend': '/api/health',
            'multilingual': '/api/multilingual/health',
            'voice': '/api/voice/health',
            'collaboration': '/api/collaboration/health',
            'analytics': '/api/analytics/health',
            'training': '/api/training/health'
        }
        
        results = {}
        for service, endpoint in health_endpoints.items():
            try:
                url = f"{self.base_urls[service]}{endpoint}"
                response = requests.get(url, timeout=5)
                
                if response.status_code == 200:
                    print(f"✅ {service.capitalize()} API: Healthy")
                    results[service] = True
                else:
                    print(f"❌ {service.capitalize()} API: Unhealthy (Status: {response.status_code})")
                    results[service] = False
                    
            except requests.exceptions.RequestException as e:
                print(f"❌ {service.capitalize()} API: Connection failed - {e}")
                results[service] = False
        
        self.test_results['health_checks'] = results
        return results
    
    def test_backend_api(self):
        """Test backend API functionality"""
        print("\n🔍 Testing Backend API...")
        
        try:
            # Test chat session creation
            response = requests.post(f"{self.base_urls['backend']}/api/chat/start")
            if response.status_code == 200:
                session_data = response.json()
                session_id = session_data.get('session_id')
                print(f"✅ Chat session created: {session_id}")
                
                # Test sending message
                message_data = {
                    'message': 'Hello, this is a test message',
                    'user_id': 'test_user'
                }
                response = requests.post(
                    f"{self.base_urls['backend']}/api/chat/{session_id}/send",
                    json=message_data
                )
                
                if response.status_code == 200:
                    print("✅ Message sent successfully")
                    return True
                else:
                    print(f"❌ Message sending failed: {response.status_code}")
                    return False
            else:
                print(f"❌ Chat session creation failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Backend API test failed: {e}")
            return False
    
    def test_multilingual_api(self):
        """Test multilingual API functionality"""
        print("\n🔍 Testing Multilingual API...")
        
        try:
            # Test language detection
            test_data = {
                'text': 'Xin chào, tôi là trợ lý AI của bạn'
            }
            response = requests.post(
                f"{self.base_urls['multilingual']}/api/multilingual/detect",
                json=test_data
            )
            
            if response.status_code == 200:
                result = response.json()
                detected_lang = result.get('language')
                print(f"✅ Language detected: {detected_lang}")
                
                # Test translation
                translate_data = {
                    'text': 'Hello, how are you?',
                    'target_language': 'vi'
                }
                response = requests.post(
                    f"{self.base_urls['multilingual']}/api/multilingual/translate",
                    json=translate_data
                )
                
                if response.status_code == 200:
                    print("✅ Translation successful")
                    return True
                else:
                    print(f"❌ Translation failed: {response.status_code}")
                    return False
            else:
                print(f"❌ Language detection failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Multilingual API test failed: {e}")
            return False
    
    def test_voice_api(self):
        """Test voice API functionality"""
        print("\n🔍 Testing Voice API...")
        
        try:
            # Test voice settings
            response = requests.get(f"{self.base_urls['voice']}/api/voice/settings/test_user")
            
            if response.status_code == 200:
                print("✅ Voice settings retrieved")
                
                # Test TTS
                tts_data = {
                    'text': 'This is a test message for text-to-speech',
                    'voice': 'male_voice'
                }
                response = requests.post(
                    f"{self.base_urls['voice']}/api/voice/tts",
                    json=tts_data
                )
                
                if response.status_code == 200:
                    print("✅ Text-to-speech successful")
                    return True
                else:
                    print(f"❌ Text-to-speech failed: {response.status_code}")
                    return False
            else:
                print(f"❌ Voice settings retrieval failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Voice API test failed: {e}")
            return False
    
    def test_collaboration_api(self):
        """Test collaboration API functionality"""
        print("\n🔍 Testing Collaboration API...")
        
        try:
            # Test team creation
            team_data = {
                'name': 'Test Team',
                'description': 'A test team for API testing'
            }
            response = requests.post(
                f"{self.base_urls['collaboration']}/api/collaboration/teams",
                json=team_data,
                headers={'X-User-ID': 'test_user'}
            )
            
            if response.status_code == 200:
                team_result = response.json()
                team_id = team_result.get('team_id')
                print(f"✅ Team created: {team_id}")
                
                # Test task creation
                task_data = {
                    'title': 'Test Task',
                    'description': 'A test task for API testing',
                    'priority': 'medium'
                }
                response = requests.post(
                    f"{self.base_urls['collaboration']}/api/collaboration/teams/{team_id}/tasks",
                    json=task_data,
                    headers={'X-User-ID': 'test_user'}
                )
                
                if response.status_code == 200:
                    print("✅ Task created successfully")
                    return True
                else:
                    print(f"❌ Task creation failed: {response.status_code}")
                    return False
            else:
                print(f"❌ Team creation failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Collaboration API test failed: {e}")
            return False
    
    def test_analytics_api(self):
        """Test analytics API functionality"""
        print("\n🔍 Testing Analytics API...")
        
        try:
            # Test analytics dashboard
            response = requests.get(
                f"{self.base_urls['analytics']}/api/analytics/dashboard",
                headers={'X-User-ID': 'test_user'}
            )
            
            if response.status_code == 200:
                print("✅ Analytics dashboard retrieved")
                
                # Test metrics
                response = requests.get(
                    f"{self.base_urls['analytics']}/api/analytics/metrics",
                    headers={'X-User-ID': 'test_user'}
                )
                
                if response.status_code == 200:
                    print("✅ Analytics metrics retrieved")
                    return True
                else:
                    print(f"❌ Analytics metrics failed: {response.status_code}")
                    return False
            else:
                print(f"❌ Analytics dashboard failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Analytics API test failed: {e}")
            return False
    
    def test_training_api(self):
        """Test custom AI training API functionality"""
        print("\n🔍 Testing Custom AI Training API...")
        
        try:
            # Test profile creation
            profile_data = {
                'preferences': {
                    'communication_style': 'formal',
                    'response_length': 'detailed'
                }
            }
            response = requests.post(
                f"{self.base_urls['training']}/api/training/profile",
                json=profile_data,
                headers={'X-User-ID': 'test_user'}
            )
            
            if response.status_code == 200:
                print("✅ Training profile created")
                
                # Test adding training data
                training_data = {
                    'data_type': 'conversation',
                    'content': 'User: Hello\nAI: Hello! How can I help you today?',
                    'metadata': {
                        'quality': 'high',
                        'context': 'greeting'
                    }
                }
                response = requests.post(
                    f"{self.base_urls['training']}/api/training/data",
                    json=training_data,
                    headers={'X-User-ID': 'test_user'}
                )
                
                if response.status_code == 200:
                    print("✅ Training data added")
                    return True
                else:
                    print(f"❌ Training data addition failed: {response.status_code}")
                    return False
            else:
                print(f"❌ Training profile creation failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Training API test failed: {e}")
            return False
    
    def test_redis_functionality(self):
        """Test Redis functionality"""
        print("\n🔍 Testing Redis Functionality...")
        
        try:
            # Test basic Redis operations
            self.redis_client.set('test_key', 'test_value')
            value = self.redis_client.get('test_key')
            
            if value == 'test_value':
                print("✅ Redis basic operations working")
                
                # Test Redis pub/sub
                pubsub = self.redis_client.pubsub()
                pubsub.subscribe('test_channel')
                
                self.redis_client.publish('test_channel', 'test_message')
                
                print("✅ Redis pub/sub working")
                return True
            else:
                print("❌ Redis basic operations failed")
                return False
                
        except Exception as e:
            print(f"❌ Redis functionality test failed: {e}")
            return False
    
    def test_integration_scenarios(self):
        """Test integration scenarios"""
        print("\n🔍 Testing Integration Scenarios...")
        
        try:
            # Scenario 1: Multilingual conversation with voice
            print("📝 Scenario 1: Multilingual conversation with voice")
            
            # Detect language
            detect_data = {'text': 'Bonjour, comment allez-vous?'}
            response = requests.post(
                f"{self.base_urls['multilingual']}/api/multilingual/detect",
                json=detect_data
            )
            
            if response.status_code == 200:
                lang_result = response.json()
                detected_lang = lang_result.get('language')
                print(f"  ✅ Language detected: {detected_lang}")
                
                # Translate to English
                translate_data = {
                    'text': 'Bonjour, comment allez-vous?',
                    'target_language': 'en'
                }
                response = requests.post(
                    f"{self.base_urls['multilingual']}/api/multilingual/translate",
                    json=translate_data
                )
                
                if response.status_code == 200:
                    translate_result = response.json()
                    translated_text = translate_result.get('translated_text')
                    print(f"  ✅ Translated: {translated_text}")
                    
                    # Convert to speech
                    tts_data = {
                        'text': translated_text,
                        'voice': 'female_voice'
                    }
                    response = requests.post(
                        f"{self.base_urls['voice']}/api/voice/tts",
                        json=tts_data
                    )
                    
                    if response.status_code == 200:
                        print("  ✅ Text-to-speech conversion successful")
                        print("✅ Scenario 1 completed successfully")
                    else:
                        print("  ❌ Text-to-speech conversion failed")
                        return False
                else:
                    print("  ❌ Translation failed")
                    return False
            else:
                print("  ❌ Language detection failed")
                return False
            
            # Scenario 2: Team collaboration with analytics
            print("\n📝 Scenario 2: Team collaboration with analytics")
            
            # Create team
            team_data = {
                'name': 'Integration Test Team',
                'description': 'Team for integration testing'
            }
            response = requests.post(
                f"{self.base_urls['collaboration']}/api/collaboration/teams",
                json=team_data,
                headers={'X-User-ID': 'test_user'}
            )
            
            if response.status_code == 200:
                team_result = response.json()
                team_id = team_result.get('team_id')
                print(f"  ✅ Team created: {team_id}")
                
                # Add team members and tasks (simulate activity)
                for i in range(3):
                    task_data = {
                        'title': f'Integration Task {i+1}',
                        'description': f'Task {i+1} for integration testing',
                        'priority': 'medium'
                    }
                    requests.post(
                        f"{self.base_urls['collaboration']}/api/collaboration/teams/{team_id}/tasks",
                        json=task_data,
                        headers={'X-User-ID': 'test_user'}
                    )
                
                print("  ✅ Tasks created")
                
                # Get analytics
                response = requests.get(
                    f"{self.base_urls['analytics']}/api/analytics/dashboard",
                    headers={'X-User-ID': 'test_user'}
                )
                
                if response.status_code == 200:
                    print("  ✅ Analytics retrieved")
                    print("✅ Scenario 2 completed successfully")
                else:
                    print("  ❌ Analytics retrieval failed")
                    return False
            else:
                print("  ❌ Team creation failed")
                return False
            
            return True
            
        except Exception as e:
            print(f"❌ Integration scenarios test failed: {e}")
            return False
    
    def test_performance(self):
        """Test system performance"""
        print("\n🔍 Testing System Performance...")
        
        try:
            # Test response times
            start_time = time.time()
            
            # Make concurrent requests
            import concurrent.futures
            
            def make_request(url):
                try:
                    response = requests.get(url, timeout=10)
                    return response.status_code == 200
                except:
                    return False
            
            urls = [
                f"{self.base_urls['backend']}/api/health",
                f"{self.base_urls['multilingual']}/api/multilingual/health",
                f"{self.base_urls['voice']}/api/voice/health",
                f"{self.base_urls['collaboration']}/api/collaboration/health",
                f"{self.base_urls['analytics']}/api/analytics/health",
                f"{self.base_urls['training']}/api/training/health"
            ]
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
                results = list(executor.map(make_request, urls))
            
            end_time = time.time()
            total_time = end_time - start_time
            
            success_rate = sum(results) / len(results) * 100
            
            print(f"✅ Concurrent requests completed in {total_time:.2f}s")
            print(f"✅ Success rate: {success_rate:.1f}%")
            
            if success_rate >= 80 and total_time < 10:
                print("✅ Performance test passed")
                return True
            else:
                print("❌ Performance test failed")
                return False
                
        except Exception as e:
            print(f"❌ Performance test failed: {e}")
            return False
    
    def generate_test_report(self):
        """Generate comprehensive test report"""
        print("\n📊 Generating Test Report...")
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'test_results': self.test_results,
            'summary': {
                'total_tests': 0,
                'passed_tests': 0,
                'failed_tests': 0,
                'success_rate': 0
            }
        }
        
        # Calculate summary
        for test_category, results in self.test_results.items():
            if isinstance(results, dict):
                for test_name, result in results.items():
                    report['summary']['total_tests'] += 1
                    if result:
                        report['summary']['passed_tests'] += 1
                    else:
                        report['summary']['failed_tests'] += 1
            elif isinstance(results, bool):
                report['summary']['total_tests'] += 1
                if results:
                    report['summary']['passed_tests'] += 1
                else:
                    report['summary']['failed_tests'] += 1
        
        if report['summary']['total_tests'] > 0:
            report['summary']['success_rate'] = (
                report['summary']['passed_tests'] / report['summary']['total_tests'] * 100
            )
        
        # Save report
        with open('test_report.json', 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"📄 Test report saved to test_report.json")
        print(f"📈 Overall success rate: {report['summary']['success_rate']:.1f}%")
        
        return report
    
    def run_comprehensive_tests(self):
        """Run all comprehensive tests"""
        print("🚀 Starting Comprehensive Test Suite for Personal AI Assistant")
        print("=" * 70)
        
        # Setup
        if not self.setup_redis():
            print("❌ Redis setup failed. Exiting tests.")
            return False
        
        # Run tests
        test_functions = [
            ('Health Checks', self.test_health_endpoints),
            ('Backend API', self.test_backend_api),
            ('Multilingual API', self.test_multilingual_api),
            ('Voice API', self.test_voice_api),
            ('Collaboration API', self.test_collaboration_api),
            ('Analytics API', self.test_analytics_api),
            ('Training API', self.test_training_api),
            ('Redis Functionality', self.test_redis_functionality),
            ('Integration Scenarios', self.test_integration_scenarios),
            ('Performance Tests', self.test_performance)
        ]
        
        for test_name, test_function in test_functions:
            try:
                result = test_function()
                self.test_results[test_name.lower().replace(' ', '_')] = result
            except Exception as e:
                print(f"❌ {test_name} failed with exception: {e}")
                self.test_results[test_name.lower().replace(' ', '_')] = False
        
        # Generate report
        report = self.generate_test_report()
        
        print("\n" + "=" * 70)
        print("🏁 Comprehensive Test Suite Completed")
        print(f"📊 Results: {report['summary']['passed_tests']}/{report['summary']['total_tests']} tests passed")
        print(f"📈 Success Rate: {report['summary']['success_rate']:.1f}%")
        
        if report['summary']['success_rate'] >= 80:
            print("✅ System is ready for deployment!")
            return True
        else:
            print("❌ System needs attention before deployment.")
            return False

if __name__ == '__main__':
    tester = PersonalAIAssistantTester()
    success = tester.run_comprehensive_tests()
    sys.exit(0 if success else 1)
