import requests
import json
from personal_ai_assistant.app_connector import AppConnector

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from email.mime.text import MIMEText
import base64
import os

# Khởi tạo AppConnector. Đảm bảo đường dẫn đến config.json là chính xác.
# Giả sử config.json nằm ở thư mục gốc của dự án (personal_ai_assistant)
app_connector = AppConnector(config_file="personal_ai_assistant/config.json")

def send_to_make_webhook(webhook_url: str, payload: dict) -> str:
    """
    Gửi dữ liệu đến một Webhook của Make.com.

    Args:
        webhook_url (str): URL của Webhook Make.com.
        payload (dict): Dữ liệu (dưới dạng dictionary) để gửi đến Webhook.

    Returns:
        str: Phản hồi từ Webhook Make.com.
    """
    try:
        headers = {"Content-Type": "application/json"}
        response = requests.post(webhook_url, data=json.dumps(payload), headers=headers)
        response.raise_for_status()  # Nâng lỗi cho các mã trạng thái HTTP xấu (4xx hoặc 5xx)
        return f"Dữ liệu đã được gửi thành công đến Make.com. Phản hồi: {response.text}"
    except requests.exceptions.RequestException as e:
        return f"Lỗi khi gửi dữ liệu đến Make.com: {e}"

def get_app_webhook_url(app_name: str) -> str or None:
    """
    Lấy URL Webhook của một ứng dụng đã cấu hình.

    Args:
        app_name (str): Tên của ứng dụng (ví dụ: "facebook_post").

    Returns:
        str or None: URL Webhook nếu tìm thấy, ngược lại là None.
    """
    app_config = app_connector.get_app_config(app_name)
    if app_config and app_config.get("connection_type") == "make_webhook":
        return app_config["config"].get("webhook_url")
    return None

def create_task(task_name: str, due_date: str = None, description: str = None, assignee: str = None) -> str:
    """
    Tạo một tác vụ mới trong hệ thống quản lý tác vụ thông qua Make.com.

    Args:
        task_name (str): Tên của tác vụ.
        due_date (str, optional): Ngày đáo hạn của tác vụ (ví dụ: '2025-07-30').
        description (str, optional): Mô tả chi tiết tác vụ.
        assignee (str, optional): Người được giao tác vụ.

    Returns:
        str: Kết quả của việc tạo tác vụ.
    """
    app_config = app_connector.get_app_config("task_manager")
    if not app_config or app_config.get("connection_type") != "make_webhook":
        return "Lỗi: Cấu hình 'task_manager' không tìm thấy hoặc không đúng loại kết nối."

    webhook_url = app_config["config"]["webhook_url"]
    payload = {
        "action": "create_task",
        "task_name": task_name,
        "due_date": due_date,
        "description": description,
        "assignee": assignee
    }
    return send_to_make_webhook(webhook_url, payload)

def post_to_social_media(content: str, platform: str, image_url: str = None) -> str:
    """
    Đăng nội dung lên mạng xã hội thông qua Make.com.

    Args:
        content (str): Nội dung bài đăng.
        platform (str): Nền tảng mạng xã hội (ví dụ: "facebook", "twitter").
        image_url (str, optional): URL của hình ảnh đính kèm.

    Returns:
        str: Kết quả của việc đăng bài.
    """
    app_config = app_connector.get_app_config("social_media_poster")
    if not app_config or app_config.get("connection_type") != "make_webhook":
        return "Lỗi: Cấu hình 'social_media_poster' không tìm thấy hoặc không đúng loại kết nối."

    webhook_url = app_config["config"]["webhook_url"]
    payload = {
        "action": "post_content",
        "content": content,
        "platform": platform,
        "image_url": image_url
    }
    return send_to_make_webhook(webhook_url, payload)

# Nếu sửa đổi phạm vi, xóa tệp token.json.
SCOPES = ["https://www.googleapis.com/auth/gmail.send"]

def send_gmail_message(to: str, subject: str, message_text: str) -> str:
    """
    Gửi email qua Gmail API.

    Args:
        to (str): Địa chỉ email người nhận.
        subject (str): Chủ đề email.
        message_text (str): Nội dung email.

    Returns:
        str: Kết quả của việc gửi email.
    """
    app_config = app_connector.get_app_config("gmail_send_email")
    if not app_config or app_config.get("connection_type") != "direct_api":
        return "Lỗi: Cấu hình 'gmail_send_email' không tìm thấy hoặc không đúng loại kết nối."

    creds_data = app_config["credentials"]
    # Để đơn giản hóa, giả định creds_data chứa tất cả thông tin cần thiết
    # Trong thực tế, bạn cần một quy trình OAuth đầy đủ để lấy refresh_token và access_token
    # Dưới đây là một ví dụ đơn giản, bạn cần thay thế bằng logic xác thực thực tế của mình
    # Ví dụ: Tải token từ file token.json nếu đã ủy quyền
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    # Nếu không có (hoặc token hết hạn), cho phép người dùng đăng nhập
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # Đây là phần cần sự can thiệp của người dùng để ủy quyền lần đầu
            # Trong môi trường không có GUI, điều này sẽ phức tạp
            # Bạn có thể cần một server OAuth để xử lý callback
            return "Lỗi: Cần ủy quyền Gmail API. Vui lòng thiết lập token.json hoặc thực hiện quy trình OAuth."
        # Lưu token cho lần chạy tiếp theo
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    try:
        service = build("gmail", "v1", credentials=creds)
        message = MIMEText(message_text)
        message["to"] = to
        message["subject"] = subject
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        body = {"raw": raw_message}
        send_message = service.users().messages().send(userId="me", body=body).execute()
        return f"Email đã được gửi thành công. ID tin nhắn: {send_message["id"]}"
    except Exception as e:
        return f"Lỗi khi gửi email: {e}"


