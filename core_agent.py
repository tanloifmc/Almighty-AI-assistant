import autogen
import google.generativeai as genai
import os
from personal_ai_assistant.tools import send_to_make_webhook, get_app_webhook_url, create_task, post_to_social_media, send_gmail_message

# Cấu hình Gemini API Key
# Đảm bảo rằng biến môi trường GOOGLE_API_KEY đã được thiết lập
GEMINI_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GOOGLE_API_KEY environment variable not set.")
genai.configure(api_key=GEMINI_API_KEY)

# Cấu hình AutoGen
config_list = [
    {
        "model": "gemini-pro",
        "api_key": GEMINI_API_KEY,
    }
]

llm_config = {
    "timeout": 600,
    "cache_seed": 42,
    "config_list": config_list,
    "temperature": 0,
}

# Khởi tạo User Proxy Agent
user_proxy = autogen.UserProxyAgent(
    name="user_proxy",
    human_input_mode="ALWAYS",
    max_consecutive_auto_reply=10,
    is_termination_msg=lambda x: x.get("content", "").rstrip().endswith("exit"),
    code_execution_config={"work_dir": "web"},
    llm_config=llm_config,
    system_message="""A human admin. Interact with the AI assistant to get tasks done. 
    You can ask the assistant to perform various tasks, such as managing your schedule, 
    drafting emails, or posting on social media. Type 'exit' to terminate the conversation.
    """,
)

# Khởi tạo AI Assistant Agent
assistant = autogen.AssistantAgent(
    name="assistant",
    llm_config=llm_config,
    system_message="""You are a personal AI assistant capable of managing tasks, 
    connecting to various applications, and automating workflows. 
    You can draft content for social media, manage schedules, and interact with other tools. 
    Always ask for confirmation before performing any action that modifies external systems.
    """,
)

# Đăng ký công cụ với user_proxy
user_proxy.register_function(
    function_map={
        "send_to_make_webhook": send_to_make_webhook,
        "get_app_webhook_url": get_app_webhook_url,
        "create_task": create_task,
        "post_to_social_media": post_to_social_media,
        "send_gmail_message": send_gmail_message,
    }
)

# Bắt đầu cuộc trò chuyện
# if __name__ == "__main__":
#     user_proxy.initiate_chat(
#         assistant,
#         message="Chào trợ lý, tôi muốn bạn giúp tôi quản lý công việc và tương tác với các ứng dụng của tôi."
#     )


