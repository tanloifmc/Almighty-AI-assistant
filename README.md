# Trợ lý AI Cá nhân Toàn năng

Một hệ thống trợ lý AI cá nhân hoàn chỉnh với khả năng trò chuyện, tự động hóa tác vụ, kết nối ứng dụng và quản lý mạng xã hội.

## 🚀 Tính năng chính

- **Trò chuyện thông minh**: Sử dụng Gemini AI để hiểu và phản hồi tự nhiên
- **Tự động hóa tác vụ**: Tích hợp Make.com để tự động hóa quy trình làm việc
- **Quản lý ứng dụng**: Kết nối linh hoạt với 500+ ứng dụng phổ biến
- **Mạng xã hội**: Tạo và đăng nội dung tự động lên Facebook, Twitter, LinkedIn
- **Email thông minh**: Soạn thảo và gửi email qua Gmail API
- **Giao diện đẹp**: React UI hiện đại và responsive

## 🏗️ Kiến trúc hệ thống

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   React UI      │    │   Flask API     │    │   AI Agent      │
│   (Frontend)    │◄──►│   (Backend)     │◄──►│   (AutoGen)     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │                        │
                                ▼                        ▼
                       ┌─────────────────┐    ┌─────────────────┐
                       │   Make.com      │    │   Gemini AI     │
                       │   (Automation)  │    │   (LLM)         │
                       └─────────────────┘    └─────────────────┘
```

## 📁 Cấu trúc dự án

```
personal_ai_assistant/
├── ai-assistant-ui/          # React frontend
│   ├── src/
│   │   ├── components/       # UI components
│   │   ├── App.jsx          # Main app component
│   │   └── ...
│   └── package.json
├── core_agent.py            # AutoGen AI agent
├── tools.py                 # AI tools và integrations
├── app_connector.py         # App configuration manager
├── backend_api.py           # Flask API server
├── config.json              # App configurations
└── requirements.txt         # Python dependencies
```

## 🛠️ Cài đặt

### Yêu cầu hệ thống

- Python 3.11+
- Node.js 20+
- npm hoặc pnpm

### Bước 1: Clone repository

```bash
git clone <repository-url>
cd personal_ai_assistant
```

### Bước 2: Cài đặt Python dependencies

```bash
python3.11 -m venv venv
source venv/bin/activate  # Linux/Mac
# hoặc venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

### Bước 3: Cài đặt Frontend dependencies

```bash
cd ai-assistant-ui
npm install
# hoặc pnpm install
```

### Bước 4: Cấu hình environment variables

```bash
export GOOGLE_API_KEY="your_gemini_api_key"
export OPENAI_API_KEY="your_openai_key"  # Optional
```

## 🚀 Chạy ứng dụng

### Development mode

**Terminal 1 - Backend:**
```bash
cd personal_ai_assistant
source venv/bin/activate
python backend_api.py
```

**Terminal 2 - Frontend:**
```bash
cd personal_ai_assistant/ai-assistant-ui
npm run dev
```

Truy cập:
- Frontend: http://localhost:5173
- Backend API: http://localhost:5000

### Production mode

```bash
# Build frontend
cd ai-assistant-ui
npm run build

# Deploy backend với production WSGI server
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 backend_api:app
```

## ⚙️ Cấu hình

### 1. Gemini AI API

1. Truy cập [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Tạo API key mới
3. Thiết lập environment variable:
   ```bash
   export GOOGLE_API_KEY="your_api_key_here"
   ```

### 2. Make.com Integration

1. Tạo tài khoản tại [Make.com](https://make.com)
2. Tạo scenario mới với Webhook trigger
3. Copy Webhook URL
4. Thêm vào `config.json`:
   ```json
   {
     "applications": [
       {
         "app_name": "task_manager",
         "connection_type": "make_webhook",
         "credentials": {},
         "config": {
           "webhook_url": "https://hook.eu1.make.com/your_webhook_id"
         }
       }
     ]
   }
   ```

### 3. Gmail API (Optional)

1. Tạo project tại [Google Cloud Console](https://console.cloud.google.com)
2. Bật Gmail API
3. Tạo OAuth 2.0 credentials
4. Download credentials.json
5. Chạy OAuth flow để lấy token.json

## 📚 API Documentation

### Chat Endpoints

- `POST /api/chat/start` - Bắt đầu phiên chat mới
- `GET /api/chat/{session_id}/messages` - Lấy tin nhắn
- `POST /api/chat/{session_id}/send` - Gửi tin nhắn

### Configuration Endpoints

- `GET /api/config/apps` - Lấy cấu hình ứng dụng
- `POST /api/config/apps` - Thêm ứng dụng mới
- `PUT /api/config/apps/{app_name}` - Cập nhật ứng dụng
- `DELETE /api/config/apps/{app_name}` - Xóa ứng dụng

### Health Check

- `GET /api/health` - Kiểm tra trạng thái hệ thống

## 🔧 Sử dụng

### Tạo tác vụ mới

```
Người dùng: "Tạo tác vụ: Chuẩn bị báo cáo hàng tháng, hạn chót 30/7"
AI: "Tôi sẽ tạo tác vụ mới cho bạn..."
```

### Đăng bài mạng xã hội

```
Người dùng: "Viết bài đăng Facebook về lợi ích của AI"
AI: "Tôi sẽ soạn nội dung và đăng lên Facebook sau khi bạn xác nhận..."
```

### Gửi email

```
Người dùng: "Gửi email cảm ơn khách hàng"
AI: "Tôi sẽ soạn email và gửi qua Gmail..."
```

## 🧪 Testing

### Unit Tests

```bash
python -m pytest tests/
```

### Integration Tests

```bash
# Test API endpoints
curl http://localhost:5000/api/health

# Test frontend
npm run test
```

## 📈 Monitoring

### Health Check

```bash
curl http://localhost:5000/api/health
```

### Logs

```bash
# Backend logs
tail -f backend.log

# Frontend logs
npm run dev  # Console logs
```

## 🔒 Security

- Input validation và sanitization
- CORS properly configured
- Environment variables cho sensitive data
- OAuth 2.0 cho Google services
- HTTPS ready cho production

## 🚀 Deployment

### Docker

```dockerfile
# Dockerfile example
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 5000
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "backend_api:app"]
```

### Cloud Deployment

- **Frontend**: Vercel, Netlify, hoặc AWS S3
- **Backend**: Heroku, AWS EC2, hoặc Google Cloud Run
- **Database**: PostgreSQL, MongoDB Atlas

## 🤝 Contributing

1. Fork repository
2. Tạo feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Tạo Pull Request

## 📄 License

MIT License - xem file [LICENSE](LICENSE) để biết thêm chi tiết.

## 🆘 Support

- 📧 Email: support@ai-assistant.com
- 💬 Discord: [Join our community](https://discord.gg/ai-assistant)
- 📖 Documentation: [docs.ai-assistant.com](https://docs.ai-assistant.com)

## 🗺️ Roadmap

- [ ] Multi-language support
- [ ] Voice interface
- [ ] Mobile app
- [ ] Advanced analytics
- [ ] Team collaboration features
- [ ] Enterprise SSO
- [ ] Custom AI model training

---

**Được phát triển với ❤️ bởi Manus AI Team**

