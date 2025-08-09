import React, { useState, useRef, useEffect } from 'react';
import { Mic, MicOff, Volume2, VolumeX, Settings, Play, Pause, Square } from 'lucide-react';

const VoiceInterface = ({ userId, onVoiceMessage, isAuthenticated }) => {
  const [isRecording, setIsRecording] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const [voiceSettings, setVoiceSettings] = useState({
    language: 'en-US',
    gender: 'female',
    speed: 1.0,
    pitch: 1.0,
    volume: 1.0
  });
  const [conversationActive, setConversationActive] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [supportedLanguages, setSupportedLanguages] = useState([]);
  const [transcribedText, setTranscribedText] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState('');

  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const audioRef = useRef(null);

  // Load supported languages on component mount
  useEffect(() => {
    if (isAuthenticated) {
      loadSupportedLanguages();
      loadUserVoiceSettings();
    }
  }, [isAuthenticated, userId]);

  const loadSupportedLanguages = async () => {
    try {
      const response = await fetch('/api/voice/languages');
      const data = await response.json();
      if (data.success) {
        setSupportedLanguages(data.languages);
      }
    } catch (error) {
      console.error('Error loading supported languages:', error);
    }
  };

  const loadUserVoiceSettings = async () => {
    try {
      const token = localStorage.getItem('auth_token');
      const response = await fetch(`/api/voice/settings/${userId}`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      const data = await response.json();
      if (data.success) {
        setVoiceSettings(data.settings);
      }
    } catch (error) {
      console.error('Error loading voice settings:', error);
    }
  };

  const saveVoiceSettings = async (newSettings) => {
    try {
      const token = localStorage.getItem('auth_token');
      const response = await fetch(`/api/voice/settings/${userId}`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(newSettings)
      });
      const data = await response.json();
      if (data.success) {
        setVoiceSettings(newSettings);
        setError('');
      } else {
        setError(data.error || 'Failed to save settings');
      }
    } catch (error) {
      console.error('Error saving voice settings:', error);
      setError('Failed to save settings');
    }
  };

  const startVoiceConversation = async () => {
    try {
      const token = localStorage.getItem('auth_token');
      const response = await fetch('/api/voice/conversation/start', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          language: voiceSettings.language
        })
      });
      const data = await response.json();
      if (data.success) {
        setConversationActive(true);
        setError('');
        
        // Play welcome audio if available
        if (data.welcome_audio) {
          playAudioFile(data.welcome_audio);
        }
      } else {
        setError(data.error || 'Failed to start conversation');
      }
    } catch (error) {
      console.error('Error starting voice conversation:', error);
      setError('Failed to start conversation');
    }
  };

  const endVoiceConversation = async () => {
    try {
      const token = localStorage.getItem('auth_token');
      const response = await fetch('/api/voice/conversation/end', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      const data = await response.json();
      if (data.success) {
        setConversationActive(false);
        setError('');
        
        // Play goodbye audio if available
        if (data.goodbye_audio) {
          playAudioFile(data.goodbye_audio);
        }
      }
    } catch (error) {
      console.error('Error ending voice conversation:', error);
    }
  };

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        audioChunksRef.current.push(event.data);
      };

      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/wav' });
        await processVoiceInput(audioBlob);
        
        // Stop all tracks to release microphone
        stream.getTracks().forEach(track => track.stop());
      };

      mediaRecorder.start();
      setIsRecording(true);
      setError('');
    } catch (error) {
      console.error('Error starting recording:', error);
      setError('Failed to access microphone');
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  };

  const processVoiceInput = async (audioBlob) => {
    try {
      setIsProcessing(true);
      const token = localStorage.getItem('auth_token');
      
      const formData = new FormData();
      formData.append('audio', audioBlob, 'voice_input.wav');

      const response = await fetch('/api/voice/conversation/process', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        },
        body: formData
      });

      const data = await response.json();
      if (data.success) {
        setTranscribedText(data.transcribed_text);
        setError('');
        
        // Send transcribed text to parent component
        if (onVoiceMessage) {
          onVoiceMessage(data.transcribed_text, data.ai_response);
        }
        
        // Play AI response audio if available
        if (data.response_audio) {
          playAudioFile(data.response_audio);
        }
      } else {
        setError(data.error || 'Failed to process voice input');
      }
    } catch (error) {
      console.error('Error processing voice input:', error);
      setError('Failed to process voice input');
    } finally {
      setIsProcessing(false);
    }
  };

  const playAudioFile = (audioPath) => {
    if (audioRef.current) {
      audioRef.current.src = audioPath;
      audioRef.current.play()
        .then(() => setIsPlaying(true))
        .catch(error => console.error('Error playing audio:', error));
    }
  };

  const playAudioData = async (audioBase64) => {
    try {
      const audioData = atob(audioBase64);
      const audioArray = new Uint8Array(audioData.length);
      for (let i = 0; i < audioData.length; i++) {
        audioArray[i] = audioData.charCodeAt(i);
      }
      
      const audioBlob = new Blob([audioArray], { type: 'audio/wav' });
      const audioUrl = URL.createObjectURL(audioBlob);
      
      if (audioRef.current) {
        audioRef.current.src = audioUrl;
        audioRef.current.play()
          .then(() => setIsPlaying(true))
          .catch(error => console.error('Error playing audio:', error));
      }
    } catch (error) {
      console.error('Error playing audio data:', error);
    }
  };

  const testVoiceSystem = async () => {
    try {
      const token = localStorage.getItem('auth_token');
      const response = await fetch('/api/voice/test', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          text: 'Hello, this is a test of the voice system. Can you hear me clearly?'
        })
      });

      const data = await response.json();
      if (data.success && data.audio_data) {
        playAudioData(data.audio_data);
        setError('');
      } else {
        setError('Voice test failed');
      }
    } catch (error) {
      console.error('Error testing voice system:', error);
      setError('Voice test failed');
    }
  };

  const handleSettingsChange = (key, value) => {
    const newSettings = { ...voiceSettings, [key]: value };
    saveVoiceSettings(newSettings);
  };

  if (!isAuthenticated) {
    return (
      <div className="voice-interface-disabled">
        <p>Please log in to use voice features</p>
      </div>
    );
  }

  return (
    <div className="voice-interface">
      <audio
        ref={audioRef}
        onEnded={() => setIsPlaying(false)}
        onError={() => setIsPlaying(false)}
      />

      {/* Voice Controls */}
      <div className="voice-controls">
        {!conversationActive ? (
          <button
            onClick={startVoiceConversation}
            className="btn btn-primary"
            disabled={isProcessing}
          >
            <Mic className="w-4 h-4 mr-2" />
            Start Voice Chat
          </button>
        ) : (
          <div className="conversation-controls">
            <button
              onClick={isRecording ? stopRecording : startRecording}
              className={`btn ${isRecording ? 'btn-danger' : 'btn-success'}`}
              disabled={isProcessing}
            >
              {isRecording ? (
                <>
                  <MicOff className="w-4 h-4 mr-2" />
                  Stop Recording
                </>
              ) : (
                <>
                  <Mic className="w-4 h-4 mr-2" />
                  {isProcessing ? 'Processing...' : 'Start Recording'}
                </>
              )}
            </button>

            <button
              onClick={endVoiceConversation}
              className="btn btn-secondary ml-2"
            >
              <Square className="w-4 h-4 mr-2" />
              End Chat
            </button>
          </div>
        )}

        <button
          onClick={() => setShowSettings(!showSettings)}
          className="btn btn-outline ml-2"
        >
          <Settings className="w-4 h-4" />
        </button>

        <button
          onClick={testVoiceSystem}
          className="btn btn-outline ml-2"
          disabled={isProcessing}
        >
          <Volume2 className="w-4 h-4 mr-2" />
          Test Voice
        </button>
      </div>

      {/* Voice Status */}
      <div className="voice-status mt-4">
        {isRecording && (
          <div className="recording-indicator">
            <div className="recording-dot"></div>
            <span>Recording...</span>
          </div>
        )}

        {isProcessing && (
          <div className="processing-indicator">
            <div className="spinner"></div>
            <span>Processing voice input...</span>
          </div>
        )}

        {isPlaying && (
          <div className="playing-indicator">
            <Volume2 className="w-4 h-4" />
            <span>Playing response...</span>
          </div>
        )}

        {transcribedText && (
          <div className="transcribed-text">
            <strong>You said:</strong> {transcribedText}
          </div>
        )}
      </div>

      {/* Error Display */}
      {error && (
        <div className="error-message mt-2">
          <span className="text-red-500">{error}</span>
        </div>
      )}

      {/* Voice Settings Panel */}
      {showSettings && (
        <div className="voice-settings mt-4 p-4 border rounded">
          <h3 className="text-lg font-semibold mb-4">Voice Settings</h3>

          {/* Language Selection */}
          <div className="setting-group mb-4">
            <label className="block text-sm font-medium mb-2">Language</label>
            <select
              value={voiceSettings.language}
              onChange={(e) => handleSettingsChange('language', e.target.value)}
              className="w-full p-2 border rounded"
            >
              {supportedLanguages.map((lang) => (
                <option key={lang.code} value={lang.code}>
                  {lang.display_name}
                </option>
              ))}
            </select>
          </div>

          {/* Gender Selection */}
          <div className="setting-group mb-4">
            <label className="block text-sm font-medium mb-2">Voice Gender</label>
            <select
              value={voiceSettings.gender}
              onChange={(e) => handleSettingsChange('gender', e.target.value)}
              className="w-full p-2 border rounded"
            >
              <option value="female">Female</option>
              <option value="male">Male</option>
              <option value="neutral">Neutral</option>
            </select>
          </div>

          {/* Speed Control */}
          <div className="setting-group mb-4">
            <label className="block text-sm font-medium mb-2">
              Speed: {voiceSettings.speed}x
            </label>
            <input
              type="range"
              min="0.5"
              max="2.0"
              step="0.1"
              value={voiceSettings.speed}
              onChange={(e) => handleSettingsChange('speed', parseFloat(e.target.value))}
              className="w-full"
            />
          </div>

          {/* Pitch Control */}
          <div className="setting-group mb-4">
            <label className="block text-sm font-medium mb-2">
              Pitch: {voiceSettings.pitch}x
            </label>
            <input
              type="range"
              min="0.5"
              max="2.0"
              step="0.1"
              value={voiceSettings.pitch}
              onChange={(e) => handleSettingsChange('pitch', parseFloat(e.target.value))}
              className="w-full"
            />
          </div>

          {/* Volume Control */}
          <div className="setting-group mb-4">
            <label className="block text-sm font-medium mb-2">
              Volume: {Math.round(voiceSettings.volume * 100)}%
            </label>
            <input
              type="range"
              min="0.0"
              max="1.0"
              step="0.1"
              value={voiceSettings.volume}
              onChange={(e) => handleSettingsChange('volume', parseFloat(e.target.value))}
              className="w-full"
            />
          </div>
        </div>
      )}

      <style jsx>{`
        .voice-interface {
          padding: 1rem;
          border: 1px solid #e2e8f0;
          border-radius: 0.5rem;
          background: #f8fafc;
        }

        .voice-controls {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          flex-wrap: wrap;
        }

        .btn {
          display: inline-flex;
          align-items: center;
          padding: 0.5rem 1rem;
          border-radius: 0.375rem;
          font-weight: 500;
          transition: all 0.2s;
          border: 1px solid transparent;
          cursor: pointer;
        }

        .btn-primary {
          background: #3b82f6;
          color: white;
        }

        .btn-primary:hover {
          background: #2563eb;
        }

        .btn-success {
          background: #10b981;
          color: white;
        }

        .btn-success:hover {
          background: #059669;
        }

        .btn-danger {
          background: #ef4444;
          color: white;
        }

        .btn-danger:hover {
          background: #dc2626;
        }

        .btn-secondary {
          background: #6b7280;
          color: white;
        }

        .btn-secondary:hover {
          background: #4b5563;
        }

        .btn-outline {
          background: transparent;
          color: #374151;
          border-color: #d1d5db;
        }

        .btn-outline:hover {
          background: #f3f4f6;
        }

        .btn:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }

        .recording-indicator {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          color: #ef4444;
          font-weight: 500;
        }

        .recording-dot {
          width: 8px;
          height: 8px;
          background: #ef4444;
          border-radius: 50%;
          animation: pulse 1s infinite;
        }

        .processing-indicator {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          color: #3b82f6;
        }

        .playing-indicator {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          color: #10b981;
        }

        .spinner {
          width: 16px;
          height: 16px;
          border: 2px solid #e5e7eb;
          border-top: 2px solid #3b82f6;
          border-radius: 50%;
          animation: spin 1s linear infinite;
        }

        .transcribed-text {
          padding: 0.75rem;
          background: #e0f2fe;
          border-radius: 0.375rem;
          border-left: 4px solid #0284c7;
        }

        .error-message {
          padding: 0.75rem;
          background: #fef2f2;
          border-radius: 0.375rem;
          border-left: 4px solid #ef4444;
        }

        .voice-settings {
          background: white;
        }

        .setting-group label {
          color: #374151;
        }

        .setting-group select,
        .setting-group input {
          border: 1px solid #d1d5db;
        }

        .setting-group select:focus,
        .setting-group input:focus {
          outline: none;
          border-color: #3b82f6;
          box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
        }

        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.5; }
        }

        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
};

export default VoiceInterface;

