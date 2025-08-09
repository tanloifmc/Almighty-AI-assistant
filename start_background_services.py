#!/usr/bin/env python3
"""
Start Background Services for AI Assistant
Starts all background services including Celery workers, scheduler, and event system
"""

import os
import sys
import time
import signal
import subprocess
import logging
from multiprocessing import Process
import redis

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class BackgroundServiceManager:
    """Manages all background services for the AI Assistant"""
    
    def __init__(self):
        self.processes = []
        self.running = False
        
    def start_redis_server(self):
        """Start Redis server if not running"""
        try:
            # Check if Redis is already running
            redis_client = redis.Redis(host='localhost', port=6379, db=0)
            redis_client.ping()
            logger.info("Redis server is already running")
            return True
        except:
            logger.info("Starting Redis server...")
            try:
                # Try to start Redis server
                redis_process = subprocess.Popen(
                    ['redis-server', '--daemonize', 'yes'],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                time.sleep(2)  # Give Redis time to start
                
                # Verify Redis is running
                redis_client = redis.Redis(host='localhost', port=6379, db=0)
                redis_client.ping()
                logger.info("Redis server started successfully")
                return True
            except Exception as e:
                logger.error(f"Failed to start Redis server: {str(e)}")
                return False
    
    def start_celery_worker(self):
        """Start Celery worker process"""
        def run_celery():
            os.system('cd /home/ubuntu/personal_ai_assistant && source venv/bin/activate && celery -A background_worker worker --loglevel=info')
        
        process = Process(target=run_celery, name="celery_worker")
        process.start()
        self.processes.append(process)
        logger.info("Started Celery worker")
        return process
    
    def start_celery_beat(self):
        """Start Celery beat scheduler"""
        def run_celery_beat():
            os.system('cd /home/ubuntu/personal_ai_assistant && source venv/bin/activate && celery -A background_worker beat --loglevel=info')
        
        process = Process(target=run_celery_beat, name="celery_beat")
        process.start()
        self.processes.append(process)
        logger.info("Started Celery beat scheduler")
        return process
    
    def start_event_system(self):
        """Start event system"""
        def run_event_system():
            from event_system import start_event_system
            start_event_system()
        
        process = Process(target=run_event_system, name="event_system")
        process.start()
        self.processes.append(process)
        logger.info("Started event system")
        return process
    
    def start_scheduler(self):
        """Start APScheduler"""
        def run_scheduler():
            from scheduler import start_scheduler
            start_scheduler()
        
        process = Process(target=run_scheduler, name="scheduler")
        process.start()
        self.processes.append(process)
        logger.info("Started APScheduler")
        return process
    
    def start_all_services(self):
        """Start all background services"""
        logger.info("Starting AI Assistant background services...")
        
        # Start Redis first
        if not self.start_redis_server():
            logger.error("Failed to start Redis server. Exiting.")
            return False
        
        # Start all other services
        try:
            self.start_celery_worker()
            time.sleep(2)  # Give worker time to start
            
            self.start_celery_beat()
            time.sleep(2)
            
            self.start_event_system()
            time.sleep(2)
            
            self.start_scheduler()
            time.sleep(2)
            
            self.running = True
            logger.info("All background services started successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error starting services: {str(e)}")
            self.stop_all_services()
            return False
    
    def stop_all_services(self):
        """Stop all background services"""
        logger.info("Stopping AI Assistant background services...")
        
        self.running = False
        
        # Terminate all processes
        for process in self.processes:
            try:
                if process.is_alive():
                    logger.info(f"Terminating {process.name}")
                    process.terminate()
                    process.join(timeout=5)
                    
                    if process.is_alive():
                        logger.warning(f"Force killing {process.name}")
                        process.kill()
                        process.join()
            except Exception as e:
                logger.error(f"Error stopping {process.name}: {str(e)}")
        
        self.processes.clear()
        logger.info("All background services stopped")
    
    def monitor_services(self):
        """Monitor running services and restart if needed"""
        while self.running:
            try:
                # Check if all processes are still alive
                dead_processes = []
                for process in self.processes:
                    if not process.is_alive():
                        dead_processes.append(process)
                
                # Restart dead processes
                for process in dead_processes:
                    logger.warning(f"Process {process.name} died, restarting...")
                    self.processes.remove(process)
                    
                    if process.name == "celery_worker":
                        self.start_celery_worker()
                    elif process.name == "celery_beat":
                        self.start_celery_beat()
                    elif process.name == "event_system":
                        self.start_event_system()
                    elif process.name == "scheduler":
                        self.start_scheduler()
                
                time.sleep(10)  # Check every 10 seconds
                
            except Exception as e:
                logger.error(f"Error monitoring services: {str(e)}")
                time.sleep(10)
    
    def get_service_status(self):
        """Get status of all services"""
        status = {
            'redis': False,
            'celery_worker': False,
            'celery_beat': False,
            'event_system': False,
            'scheduler': False
        }
        
        # Check Redis
        try:
            redis_client = redis.Redis(host='localhost', port=6379, db=0)
            redis_client.ping()
            status['redis'] = True
        except:
            pass
        
        # Check other processes
        for process in self.processes:
            if process.is_alive():
                status[process.name] = True
        
        return status

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info("Received shutdown signal")
    service_manager.stop_all_services()
    sys.exit(0)

def main():
    """Main function"""
    global service_manager
    service_manager = BackgroundServiceManager()
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Start services
    if service_manager.start_all_services():
        logger.info("AI Assistant background services are running")
        
        # Monitor services
        try:
            service_manager.monitor_services()
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt")
        finally:
            service_manager.stop_all_services()
    else:
        logger.error("Failed to start background services")
        sys.exit(1)

if __name__ == '__main__':
    main()

