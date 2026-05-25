import React, { useState, useEffect, useRef } from 'react';
import './MEGANChat.css';

/**
 * MEGAN Chat Interface Component
 * Main UI for interacting with MEGAN
 * 
 * Features:
 * - Text input for chat
 * - Voice input/output
 * - Real-time responses
 * - Message history
 * - System status
 */

const MEGANChat = () => {
  const [messages, setMessages] = useState([
    {
      id: 1,
      text: "Hello! I'm MEGAN, your AI assistant. How can I help you today?",
      sender: 'bot',
      timestamp: new Date()
    }
  ]);
  
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [systemStatus, setSystemStatus] = useState('online');
  const [userId, setUserId] = useState('user_' + Date.now());
  const messagesEndRef = useRef(null);
  const recognitionRef = useRef(null);

  const API_BASE = 'http://localhost:8000';

  // Auto-scroll to bottom
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Initialize speech recognition
  useEffect(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRecognition) {
      recognitionRef.current = new SpeechRecognition();
      recognitionRef.current.onstart = () => setIsListening(true);
      recognitionRef.current.onend = () => setIsListening(false);
      recognitionRef.current.onresult = (event) => {
        const transcript = Array.from(event.results)
          .map(result => result[0].transcript)
          .join('');
        setInputValue(transcript);
      };
    }
  }, []);

  // Check system status
  useEffect(() => {
    const checkStatus = async () => {
      try {
        const response = await fetch(`${API_BASE}/system/status`);
        const data = await response.json();
        setSystemStatus(data.status === 'active' ? 'online' : 'offline');
      } catch (error) {
        setSystemStatus('offline');
      }
    };

    checkStatus();
    const interval = setInterval(checkStatus, 5000);
    return () => clearInterval(interval);
  }, []);

  // Send message to MEGAN
  const sendMessage = async (e) => {
    e.preventDefault();
    
    if (!inputValue.trim() || isLoading) return;

    // Add user message to chat
    const userMessage = {
      id: Date.now(),
      text: inputValue,
      sender: 'user',
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputValue('');
    setIsLoading(true);

    try {
      // Send to MEGAN backend
      const response = await fetch(`${API_BASE}/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          user_id: userId,
          content: inputValue,
          message_type: 'text'
        })
      });

      const data = await response.json();

      if (data.status === 'success') {
        // Add bot response
        const botMessage = {
          id: Date.now() + 1,
          text: data.response,
          sender: 'bot',
          timestamp: new Date()
        };
        setMessages(prev => [...prev, botMessage]);

        // Optionally speak response
        if ('speechSynthesis' in window) {
          const utterance = new SpeechSynthesisUtterance(data.response);
          window.speechSynthesis.speak(utterance);
        }
      } else {
        const errorMessage = {
          id: Date.now() + 1,
          text: `Error: ${data.error}`,
          sender: 'bot',
          timestamp: new Date()
        };
        setMessages(prev => [...prev, errorMessage]);
      }
    } catch (error) {
      const errorMessage = {
        id: Date.now() + 1,
        text: `Connection error: ${error.message}`,
        sender: 'bot',
        timestamp: new Date()
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  // Voice input
  const toggleVoiceInput = () => {
    if (recognitionRef.current) {
      if (isListening) {
        recognitionRef.current.stop();
      } else {
        recognitionRef.current.start();
      }
    }
  };

  // Format timestamp
  const formatTime = (date) => {
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  return (
    <div className="megan-chat-container">
      {/* Header */}
      <div className="megan-header">
        <div className="megan-brand">
          <h1>🤖 MEGAN</h1>
          <p>Your AI Assistant</p>
        </div>
        <div className="system-status">
          <div className={`status-indicator ${systemStatus}`}></div>
          <span>{systemStatus === 'online' ? 'Online' : 'Offline'}</span>
        </div>
      </div>

      {/* Messages */}
      <div className="messages-container">
        {messages.map((message) => (
          <div key={message.id} className={`message message-${message.sender}`}>
            <div className="message-content">
              <p>{message.text}</p>
              <span className="message-time">{formatTime(message.timestamp)}</span>
            </div>
          </div>
        ))}
        {isLoading && (
          <div className="message message-bot">
            <div className="message-content">
              <div className="typing-indicator">
                <span></span>
                <span></span>
                <span></span>
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="input-area">
        <form onSubmit={sendMessage} className="input-form">
          <input
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            placeholder="Type your message or click 🎤 to speak..."
            disabled={isLoading}
            className="message-input"
          />
          
          <button
            type="button"
            onClick={toggleVoiceInput}
            className={`voice-btn ${isListening ? 'listening' : ''}`}
            title="Voice input"
          >
            🎤
          </button>

          <button
            type="submit"
            disabled={isLoading || !inputValue.trim()}
            className="send-btn"
            title="Send message"
          >
            ➤
          </button>
        </form>
      </div>

      {/* Footer */}
      <div className="megan-footer">
        <p>💡 Try: "Search for weather", "Find my files", "Send a message"</p>
      </div>
    </div>
  );
};

export default MEGANChat;
