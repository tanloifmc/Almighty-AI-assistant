import React, { useState, useEffect, useRef } from 'react';
import { Send, Bot, User, Globe, Settings, LogOut, Menu, X } from 'lucide-react';
import { LanguageProvider, useLanguage, LanguageSelector } from './i18n';
import VoiceInterface from './components/VoiceInterface';
import './App.css';

// Chat Message Component
const ChatMessage = ({ message, isUser, timestamp }) => {
  const { formatDate } = useLanguage();
  
  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4`}>
      <div className={`flex max-w-xs lg:max-w-md ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>
        <div className={`flex-shrink-0 ${isUser ? 'ml-2' : 'mr-2'}`}>
          <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
            isUser ? 'bg-blue-500' : 'bg-gray-500'
          }`}>
            {isUser ? <User size={16} className="text-white" /> : <Bot size={16} className="text-white" />}
          </div>
        </div>
        <div className={`px-4 py-2 rounded-lg ${
          isUser 
            ? 'bg-blue-500 text-white rounded-br-none' 
            : 'bg-gray-200 text-gray-800 rounded-bl-none'
        }`}>
          <p className="text-sm">{message}</p>
          {timestamp && (
            <p className="text-xs mt-1 opacity-70">
              {formatDate(timestamp, { hour: '2-digit', minute: '2-digit' })}
            </p>
          )}
        </div>
      </div>
    </div>
  );
};

// Language Detection Badge
const LanguageDetectionBadge = ({ detectedLanguage, userLanguage }) => {
  const { t } = useLanguage();
  
  if (!detectedLanguage || detectedLanguage === userLanguage) return null;
  
  return (
    <div className="mb-2 text-xs text-gray-500 flex items-center">
      <Globe size={12} className="mr-1" />
      {t('chat.detectedLanguage', { language: detectedLanguage })}
    </div>
  );
};

// Main Chat Interface
const ChatInterface = () => {
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [user, setUser] = useState(null);
  const [showSidebar, setShowSidebar] = useState(false);
  const messagesEndRef = useRef(null);
  const { t, currentLanguage, changeLanguage } = useLanguage();

  // Scroll to bottom when new messages arrive
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Check authentication status
  useEffect(() => {
    const token = localStorage.getItem('access_token');
    if (token) {
      fetchUserProfile(token);
    }
  }, []);

  // Add welcome message
  useEffect(() => {
    if (messages.length === 0) {
      setMessages([{
        id: 1,
        text: t('chat.welcome'),
        isUser: false,
        timestamp: new Date()
      }]);
    }
  }, [t]);

  const fetchUserProfile = async (token) => {
    try {
      const response = await fetch('/api/user/profile', {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Accept-Language': currentLanguage
        }
      });
      
      if (response.ok) {
        const userData = await response.json();
        setUser(userData);
        setIsAuthenticated(true);
        
        // Update language if different from server
        if (userData.language && userData.language !== currentLanguage) {
          changeLanguage(userData.language);
        }
      } else {
        localStorage.removeItem('access_token');
      }
    } catch (error) {
      console.error('Error fetching user profile:', error);
      localStorage.removeItem('access_token');
    }
  };

  const handleSendMessage = async () => {
    if (!inputMessage.trim()) return;

    const userMessage = {
      id: Date.now(),
      text: inputMessage,
      isUser: true,
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputMessage('');
    setIsLoading(true);

    try {
      const token = localStorage.getItem('access_token');
      const headers = {
        'Content-Type': 'application/json',
        'Accept-Language': currentLanguage
      };
      
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      const response = await fetch('/api/chat', {
        method: 'POST',
        headers,
        body: JSON.stringify({
          message: inputMessage,
          context: {
            language: currentLanguage
          }
        })
      });

      if (response.ok) {
        const data = await response.json();
        
        const aiMessage = {
          id: Date.now() + 1,
          text: data.response,
          isUser: false,
          timestamp: new Date(),
          detectedLanguage: data.detected_language,
          originalResponse: data.original_response
        };

        setMessages(prev => [...prev, aiMessage]);
      } else {
        const errorData = await response.json();
        const errorMessage = {
          id: Date.now() + 1,
          text: errorData.error || t('chat.error'),
          isUser: false,
          timestamp: new Date(),
          isError: true
        };
        setMessages(prev => [...prev, errorMessage]);
      }
    } catch (error) {
      console.error('Error sending message:', error);
      const errorMessage = {
        id: Date.now() + 1,
        text: t('chat.error'),
        isUser: false,
        timestamp: new Date(),
        isError: true
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('access_token');
    setIsAuthenticated(false);
    setUser(null);
    setMessages([{
      id: 1,
      text: t('chat.welcome'),
      isUser: false,
      timestamp: new Date()
    }]);
  };

  return (
    <div className="flex h-screen bg-gray-100">
      {/* Sidebar */}
      <div className={`${showSidebar ? 'translate-x-0' : '-translate-x-full'} fixed inset-y-0 left-0 z-50 w-64 bg-white shadow-lg transform transition-transform duration-300 ease-in-out lg:translate-x-0 lg:static lg:inset-0`}>
        <div className="flex items-center justify-between h-16 px-4 border-b">
          <h1 className="text-xl font-semibold text-gray-800">{t('chat.title')}</h1>
          <button
            onClick={() => setShowSidebar(false)}
            className="lg:hidden p-2 rounded-md text-gray-400 hover:text-gray-600"
          >
            <X size={20} />
          </button>
        </div>
        
        <div className="p-4 space-y-4">
          {/* Language Selector */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              {t('language.select')}
            </label>
            <LanguageSelector />
          </div>
          
          {/* User Info */}
          {isAuthenticated && user && (
            <div className="border-t pt-4">
              <div className="flex items-center space-x-3">
                <div className="w-8 h-8 bg-blue-500 rounded-full flex items-center justify-center">
                  <User size={16} className="text-white" />
                </div>
                <div>
                  <p className="text-sm font-medium text-gray-900">{user.username}</p>
                  <p className="text-xs text-gray-500">{user.role}</p>
                </div>
              </div>
              
              <div className="mt-4 space-y-2">
                <button className="w-full text-left px-3 py-2 text-sm text-gray-700 hover:bg-gray-100 rounded-md flex items-center">
                  <Settings size={16} className="mr-2" />
                  {t('nav.settings')}
                </button>
                <button 
                  onClick={handleLogout}
                  className="w-full text-left px-3 py-2 text-sm text-red-600 hover:bg-red-50 rounded-md flex items-center"
                >
                  <LogOut size={16} className="mr-2" />
                  {t('nav.logout')}
                </button>
              </div>
            </div>
          )}
          
          {/* Login prompt for unauthenticated users */}
          {!isAuthenticated && (
            <div className="border-t pt-4">
              <p className="text-sm text-gray-600 mb-3">
                {t('auth.loginPrompt', { default: 'Sign in to access all features' })}
              </p>
              <button className="w-full bg-blue-500 text-white px-4 py-2 rounded-md text-sm hover:bg-blue-600">
                {t('auth.login')}
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <div className="bg-white shadow-sm border-b h-16 flex items-center justify-between px-4">
          <div className="flex items-center">
            <button
              onClick={() => setShowSidebar(true)}
              className="lg:hidden p-2 rounded-md text-gray-400 hover:text-gray-600 mr-2"
            >
              <Menu size={20} />
            </button>
            <h2 className="text-lg font-semibold text-gray-800">{t('chat.title')}</h2>
          </div>
          
          <div className="flex items-center space-x-2">
            <Globe size={16} className="text-gray-400" />
            <span className="text-sm text-gray-600">
              {currentLanguage.toUpperCase()}
            </span>
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.map((message) => (
            <div key={message.id}>
              <LanguageDetectionBadge 
                detectedLanguage={message.detectedLanguage}
                userLanguage={currentLanguage}
              />
              <ChatMessage
                message={message.text}
                isUser={message.isUser}
                timestamp={message.timestamp}
              />
              {message.originalResponse && message.originalResponse !== message.text && (
                <div className="text-xs text-gray-500 ml-10 mb-2">
                  <details>
                    <summary className="cursor-pointer hover:text-gray-700">
                      {t('chat.showOriginal', { default: 'Show original response' })}
                    </summary>
                    <div className="mt-1 p-2 bg-gray-50 rounded text-gray-600">
                      {message.originalResponse}
                    </div>
                  </details>
                </div>
              )}
            </div>
          ))}
          
          {isLoading && (
            <div className="flex justify-start mb-4">
              <div className="flex max-w-xs lg:max-w-md">
                <div className="flex-shrink-0 mr-2">
                  <div className="w-8 h-8 rounded-full bg-gray-500 flex items-center justify-center">
                    <Bot size={16} className="text-white" />
                  </div>
                </div>
                <div className="px-4 py-2 bg-gray-200 rounded-lg rounded-bl-none">
                  <div className="flex space-x-1">
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{animationDelay: '0.1s'}}></div>
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{animationDelay: '0.2s'}}></div>
                  </div>
                  <p className="text-xs text-gray-500 mt-1">{t('chat.thinking')}</p>
                </div>
              </div>
            </div>
          )}
          
          <div ref={messagesEndRef} />
        </div>

        {/* Input Area */}
        <div className="bg-white border-t p-4">
          {/* Voice Interface */}
          <div className="mb-4">
            <VoiceInterface
              userId={user?.id || 'guest'}
              onVoiceMessage={(transcribedText, aiResponse) => {
                // Add voice message to chat
                const voiceMessage = {
                  id: Date.now(),
                  text: transcribedText,
                  isUser: true,
                  timestamp: new Date(),
                  isVoice: true
                };
                
                const aiMessage = {
                  id: Date.now() + 1,
                  text: aiResponse,
                  isUser: false,
                  timestamp: new Date(),
                  isVoice: true
                };
                
                setMessages(prev => [...prev, voiceMessage, aiMessage]);
              }}
              isAuthenticated={isAuthenticated}
            />
          </div>
          
          <div className="flex space-x-2">
            <textarea
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder={t('chat.placeholder')}
              className="flex-1 resize-none border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              rows="1"
              style={{
                minHeight: '40px',
                maxHeight: '120px',
                height: 'auto'
              }}
              onInput={(e) => {
                e.target.style.height = 'auto';
                e.target.style.height = e.target.scrollHeight + 'px';
              }}
            />
            <button
              onClick={handleSendMessage}
              disabled={!inputMessage.trim() || isLoading}
              className="bg-blue-500 text-white px-4 py-2 rounded-lg hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center"
            >
              <Send size={16} />
            </button>
          </div>
          
          <div className="mt-2 text-xs text-gray-500 flex items-center justify-between">
            <span>{t('chat.pressEnter', { default: 'Press Enter to send, Shift+Enter for new line' })}</span>
            {currentLanguage !== 'en' && (
              <span className="flex items-center">
                <Globe size={12} className="mr-1" />
                {t('chat.autoTranslate', { default: 'Auto-translate enabled' })}
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Overlay for mobile sidebar */}
      {showSidebar && (
        <div 
          className="fixed inset-0 bg-black bg-opacity-50 z-40 lg:hidden"
          onClick={() => setShowSidebar(false)}
        />
      )}
    </div>
  );
};

// Main App Component
function App() {
  return (
    <LanguageProvider>
      <div className="App">
        <ChatInterface />
      </div>
    </LanguageProvider>
  );
}

export default App;

