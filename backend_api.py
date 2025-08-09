from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import threading
import queue
import time
import sys
import os

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Global variables to manage chat sessions
chat_sessions = {}
session_counter = 0

class ChatSession:
    def __init__(self, session_id):
        self.session_id = session_id
        self.messages = []
        self.is_active = False
        self.response_queue = queue.Queue()
        
    def add_message(self, message_type, content):
        message = {
            "id": len(self.messages) + 1,
            "type": message_type,
            "content": content,
            "timestamp": time.time()
        }
        self.messages.append(message)
        return message

@app.route('/api/chat/start', methods=['POST'])
def start_chat():
    """Bắt đầu một phiên chat mới"""
    global session_counter
    session_counter += 1
    session_id = f"session_{session_counter}"
    
    chat_sessions[session_id] = ChatSession(session_id)
    
    # Add welcome message
    welcome_message = chat_sessions[session_id].add_message(
        "assistant", 
        "Xin chào! Tôi là trợ lý AI cá nhân của bạn. Tôi có thể giúp bạn quản lý công việc, tạo nội dung, đăng bài lên mạng xã hội và nhiều việc khác. Bạn cần tôi giúp gì?"
    )
    
    return jsonify({
        "session_id": session_id,
        "message": welcome_message
    })

@app.route('/api/chat/<session_id>/messages', methods=['GET'])
def get_messages(session_id):
    """Lấy tất cả tin nhắn trong phiên chat"""
    if session_id not in chat_sessions:
        return jsonify({"error": "Session not found"}), 404
    
    return jsonify({
        "messages": chat_sessions[session_id].messages
    })

@app.route('/api/chat/<session_id>/send', methods=['POST'])
def send_message(session_id):
    """Gửi tin nhắn và nhận phản hồi từ AI"""
    if session_id not in chat_sessions:
        return jsonify({"error": "Session not found"}), 404
    
    data = request.get_json()
    user_message = data.get('message', '').strip()
    
    if not user_message:
        return jsonify({"error": "Message cannot be empty"}), 400
    
    session = chat_sessions[session_id]
    
    # Add user message
    user_msg = session.add_message("user", user_message)
    
    # Simulate AI processing (in real implementation, this would use the actual AI agent)
    # For now, we'll create a simple response
    try:
        # This is a simplified response. In a real implementation, you would:
        # 1. Initialize the AutoGen conversation with the user message
        # 2. Let the AI agent process and respond
        # 3. Capture the response and any tool executions
        
        ai_response = f"Tôi đã nhận được yêu cầu của bạn: \"{user_message}\". "
        
        # Simple keyword-based responses for demonstration
        if any(keyword in user_message.lower() for keyword in ['tác vụ', 'task', 'công việc', 'việc']):
            ai_response += "Tôi sẽ giúp bạn tạo và quản lý tác vụ. Để thực hiện điều này, tôi cần kết nối với hệ thống quản lý tác vụ của bạn thông qua Make.com. Bạn có muốn tôi thiết lập kết nối này không?"
        elif any(keyword in user_message.lower() for keyword in ['facebook', 'mạng xã hội', 'đăng bài', 'post']):
            ai_response += "Tôi có thể giúp bạn tạo nội dung và đăng bài lên mạng xã hội. Tôi sẽ soạn thảo nội dung phù hợp và sau khi bạn xác nhận, tôi sẽ đăng lên các nền tảng mạng xã hội đã kết nối."
        elif any(keyword in user_message.lower() for keyword in ['email', 'mail', 'gửi']):
            ai_response += "Tôi có thể giúp bạn soạn thảo và gửi email. Tôi sẽ tạo nội dung email phù hợp và gửi đến người nhận thông qua Gmail API đã được cấu hình."
        else:
            ai_response += "Đây là một phản hồi mẫu. Trong phiên bản thực tế, tôi sẽ xử lý yêu cầu này thông qua các công cụ tích hợp như Make.com, Gmail API, và các dịch vụ khác."
        
        # Add AI response
        ai_msg = session.add_message("assistant", ai_response)
        
        return jsonify({
            "user_message": user_msg,
            "ai_response": ai_msg
        })
        
    except Exception as e:
        error_msg = session.add_message("assistant", f"Xin lỗi, đã có lỗi xảy ra khi xử lý yêu cầu của bạn: {str(e)}")
        return jsonify({
            "user_message": user_msg,
            "ai_response": error_msg
        })

@app.route('/api/config/apps', methods=['GET'])
def get_app_configs():
    """Lấy danh sách các ứng dụng đã cấu hình"""
    try:
        # Simple file reading for demonstration
        config_path = os.path.join(os.path.dirname(__file__), "config.json")
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config = json.load(f)
                return jsonify(config)
        else:
            return jsonify({"applications": []})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/config/apps', methods=['POST'])
def add_app_config():
    """Thêm cấu hình ứng dụng mới"""
    try:
        data = request.get_json()
        config_path = os.path.join(os.path.dirname(__file__), "config.json")
        
        # Load existing config
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config = json.load(f)
        else:
            config = {"applications": []}
        
        # Check if app already exists
        app_name = data.get("app_name")
        for app in config["applications"]:
            if app.get("app_name") == app_name:
                return jsonify({"error": "App already exists"}), 400
        
        # Add new app
        config["applications"].append(data)
        
        # Save config
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=4)
        
        return jsonify({"message": "App configuration added successfully"})
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "timestamp": time.time(),
        "active_sessions": len(chat_sessions)
    })

if __name__ == '__main__':
    print("Starting Personal AI Assistant Backend...")
    print("API endpoints:")
    print("- POST /api/chat/start - Start new chat session")
    print("- GET /api/chat/<session_id>/messages - Get chat messages")
    print("- POST /api/chat/<session_id>/send - Send message to AI")
    print("- GET /api/config/apps - Get app configurations")
    print("- POST /api/config/apps - Add app configuration")
    print("- GET /api/health - Health check")
    
    app.run(host='0.0.0.0', port=5000, debug=True)

