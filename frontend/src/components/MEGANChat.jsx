import React, { useState, useRef, useEffect, useCallback } from "react";
import "./MEGANChat.css";

const MAX_HISTORY = 50;

export default function MEGANChat({ userId = "user_001" }) {
  const [messages,    setMessages]    = useState([
    {
      id:        0,
      role:      "assistant",
      content:   "Hi, I'm MEGAN. How can I help you today?",
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }
  ]);
  const [input,       setInput]       = useState("");
  const [isLoading,   setIsLoading]   = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [isSpeaking,  setIsSpeaking]  = useState(false);
  const [voiceEnabled, setVoiceEnabled] = useState(false); // Toggle for text-based TTS
  const [showSettings, setShowSettings] = useState(false);
  const [apiKeyInput,  setApiKeyInput]  = useState("");
  const [wsStatus,    setWsStatus]    = useState("disconnected"); // connected | disconnected | error

  const bottomRef   = useRef(null);
  const inputRef    = useRef(null);
  const wsRef       = useRef(null);
  const mediaRef    = useRef(null);
  const audioRef    = useRef(null); // Reference to playing audio
  const audioChunks = useRef([]);
  const msgIdRef    = useRef(1);

  /* ── Auto-scroll ─────────────────────────────────────────────── */
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  /* ── WebSocket ───────────────────────────────────────────────── */
  useEffect(() => {
    connectWS();
    return () => wsRef.current?.close();
  }, [userId]);

  function connectWS() {
    const wsUrl = `ws://${window.location.hostname}:8000/ws/${userId}`;
    const ws    = new WebSocket(wsUrl);

    ws.onopen  = () => setWsStatus("connected");
    ws.onerror = () => setWsStatus("error");
    ws.onclose = () => {
      setWsStatus("disconnected");
      // Reconnect after 3 s
      setTimeout(connectWS, 3000);
    };
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.response) pushMessage("assistant", data.response);
        setIsLoading(false);
      } catch (e) {
        console.error("WS parse error", e);
      }
    };

    wsRef.current = ws;
  }

  /* ── Helpers ─────────────────────────────────────────────────── */
  function pushMessage(role, content) {
    setMessages((prev) => {
      const next = [
        ...prev,
        {
          id:        msgIdRef.current++,
          role,
          content,
          timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        },
      ];
      return next.slice(-MAX_HISTORY);
    });
  }

  /* ── Audio Playback ───────────────────────────────────────────── */
  function playAudioResponse(base64Audio) {
    if (!base64Audio) return;
    
    // Stop currently playing audio if any
    if (audioRef.current) {
      audioRef.current.pause();
    }
    
    setIsSpeaking(true);
    const audio = new Audio("data:audio/mp3;base64," + base64Audio);
    audioRef.current = audio;
    
    audio.onended = () => {
      setIsSpeaking(false);
      audioRef.current = null;
    };
    
    audio.onerror = () => {
      console.error("Error playing audio response");
      setIsSpeaking(false);
    };
    
    audio.play().catch(e => {
      console.error("Browser blocked autoplay:", e);
      setIsSpeaking(false);
    });
  }

  /* ── Send via HTTP POST ─────────────────────────────────────── */
  async function sendMessage(text, forceVoice = false) {
    if (!text.trim()) return;
    const trimmed = text.trim();

    pushMessage("user", trimmed);
    setInput("");
    setIsLoading(true);

    try {
      const res  = await fetch("/chat", {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify({
          user_id:      userId,
          content:      trimmed,
          message_type: forceVoice ? "voice" : "text",
          require_audio: voiceEnabled || forceVoice, // Always ask for audio if using mic
        }),
      });
      const data = await res.json();
      pushMessage("assistant", data.response ?? data.error ?? "No response");
      
      if (data.audio_response) {
        playAudioResponse(data.audio_response);
      }
    } catch (err) {
      pushMessage("assistant", `⚠ Network error: ${err.message}`);
    } finally {
      setIsLoading(false);
      inputRef.current?.focus();
    }
  }

  /* ── Voice Recording (Web Speech API) ────────────────────────── */
  async function toggleVoice() {
    if (isListening) {
      if (mediaRef.current) mediaRef.current.stop();
      setIsListening(false);
      return;
    }

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      pushMessage("assistant", "⚠ Tumhara browser speech recognition support nahi karta. Please use Chrome!");
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.lang = "hi-IN"; // Supports Hinglish/Hindi
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;

    recognition.onstart = () => setIsListening(true);
    
    recognition.onresult = (event) => {
      const transcript = event.results[0][0].transcript;
      sendMessage(transcript, true); // Send the recognized text directly to /chat and force voice response!
    };
    
    recognition.onerror = (event) => {
      pushMessage("assistant", `⚠ Voice error: ${event.error}`);
      setIsListening(false);
    };
    
    recognition.onend = () => setIsListening(false);

    try {
      recognition.start();
      mediaRef.current = recognition;
    } catch (err) {
      pushMessage("assistant", `⚠ Microphone start error: ${err.message}`);
      setIsListening(false);
    }
  }

  /* ── Key handler ─────────────────────────────────────────────── */
  function handleKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage(input);
    }
  }

  /* ── Settings API ────────────────────────────────────────────── */
  async function saveApiKey() {
    if (!apiKeyInput.trim()) return;
    try {
      const res = await fetch("/config/api_key", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ api_key: apiKeyInput.trim() }),
      });
      const data = await res.json();
      if (data.status === "success") {
        pushMessage("assistant", "✅ API Key successfully updated! I am ready to go.");
        setShowSettings(false);
        setApiKeyInput("");
      } else {
        pushMessage("assistant", `⚠ Error updating API key: ${data.error}`);
      }
    } catch (err) {
      pushMessage("assistant", `⚠ Network error: ${err.message}`);
    }
  }

  /* ── Clear chat ──────────────────────────────────────────────── */
  function clearChat() {
    setMessages([{
      id:        msgIdRef.current++,
      role:      "assistant",
      content:   "Chat clear ho gaya! Batao, kya karna chahte hain?",
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    }]);
    fetch(`/user/${userId}/history`, { method: "DELETE" }).catch(() => {});
  }

  /* ── Render ──────────────────────────────────────────────────── */
  return (
    <div className="megan-chat" role="main" aria-label="MEGAN Chat Interface">

      {/* Connection badge & Settings */}
      <div className="header-actions">
        <button 
          className="settings-btn" 
          onClick={() => setShowSettings(!showSettings)}
          title="Settings / API Key"
        >
          ⚙️
        </button>
        <div className={`ws-badge ws-${wsStatus}`}>
          <span className="ws-dot" />
          {wsStatus === "connected" ? "Live" : wsStatus === "error" ? "Error" : "Offline"}
        </div>
      </div>

      {/* Settings Modal */}
      {showSettings && (
        <div className="settings-modal">
          <h4>System Settings</h4>
          <label>Update Gemini API Key:</label>
          <input 
            type="password" 
            placeholder="AIzaSy..." 
            value={apiKeyInput}
            onChange={(e) => setApiKeyInput(e.target.value)}
          />
          <button className="save-btn" onClick={saveApiKey}>Save & Restart Brain</button>
        </div>
      )}

      {/* Messages */}
      <div className="chat-messages" aria-live="polite" aria-label="Conversation">
        {messages.map((msg) => (
          <MessageBubble key={msg.id} message={msg} />
        ))}

        {isLoading && <TypingIndicator />}
        {isSpeaking && (
          <div className="speaking-indicator">
            <span className="audio-wave"></span>
            <span className="audio-wave"></span>
            <span className="audio-wave"></span>
            <small>MEGAN is speaking...</small>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input area */}
      <div className="chat-input-area">
        <textarea
          ref={inputRef}
          id="megan-input"
          className="chat-input"
          placeholder="MEGAN se kuch bhi pucho... (Hindi ya English)"
          value={input}
          rows={1}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={isLoading}
          aria-label="Message input"
        />

        <button
          id="megan-voice-btn"
          className={`action-btn voice-btn ${isListening ? "listening" : ""}`}
          onClick={toggleVoice}
          aria-label={isListening ? "Stop recording" : "Start voice input"}
          title={isListening ? "Stop recording" : "Voice input"}
        >
          {isListening ? <IconStop /> : <IconMic />}
        </button>
        
        <button
          className={`action-btn toggle-voice-btn ${voiceEnabled ? "active" : ""}`}
          onClick={() => setVoiceEnabled(!voiceEnabled)}
          title={voiceEnabled ? "Auto-Speak ON" : "Auto-Speak OFF"}
          style={{ opacity: voiceEnabled ? 1 : 0.5, border: voiceEnabled ? "1px solid var(--accent-primary)" : "none" }}
        >
          <IconSpeaker />
        </button>

        <button
          id="megan-send-btn"
          className="action-btn send-btn"
          onClick={() => sendMessage(input)}
          disabled={isLoading || (!input.trim() && !isListening)}
          aria-label="Send message"
          title="Send (Enter)"
        >
          {isLoading ? <span className="spinner" /> : <IconSend />}
        </button>

        <button
          id="megan-clear-btn"
          className="action-btn clear-btn"
          onClick={clearChat}
          aria-label="Clear conversation"
          title="Clear chat"
        >
          <IconTrash />
        </button>
      </div>
    </div>
  );
}

/* ── Sub-components ───────────────────────────────────────────────────────── */

function MessageBubble({ message }) {
  const isUser = message.role === "user";
  return (
    <div className={`message-row ${isUser ? "user-row" : "megan-row"}`}>
      {!isUser && (
        <div className="avatar megan-avatar" aria-label="MEGAN">
          <IconHexagon />
        </div>
      )}
      <div className={`bubble ${isUser ? "user-bubble" : "megan-bubble"}`}>
        <p className="bubble-content">{message.content}</p>
        <span className="bubble-time">{message.timestamp}</span>
      </div>
      {isUser && (
        <div className="avatar user-avatar" aria-label="You">
          <IconUser />
        </div>
      )}
    </div>
  );
}

function TypingIndicator() {
  return (
    <div className="message-row megan-row" aria-label="MEGAN is thinking">
      <div className="avatar megan-avatar"><IconHexagon /></div>
      <div className="bubble megan-bubble typing-bubble">
        <span className="dot" />
        <span className="dot" />
        <span className="dot" />
      </div>
    </div>
  );
}

function IconMic() {
  return <svg width='18' height='18' viewBox='0 0 24 24' fill='none' stroke='currentColor' strokeWidth='2' strokeLinecap='round' strokeLinejoin='round'><path d='M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z'/><path d='M19 10v2a7 7 0 0 1-14 0v-2'/><line x1='12' x2='12' y1='19' y2='22'/></svg>;
}
function IconStop() {
  return <svg width='18' height='18' viewBox='0 0 24 24' fill='none' stroke='currentColor' strokeWidth='2' strokeLinecap='round' strokeLinejoin='round'><rect width='14' height='14' x='5' y='5' rx='2' ry='2'/></svg>;
}
function IconSend() {
  return <svg width='18' height='18' viewBox='0 0 24 24' fill='none' stroke='currentColor' strokeWidth='2' strokeLinecap='round' strokeLinejoin='round'><path d='m22 2-7 20-4-9-9-4Z'/><path d='M22 2 11 13'/></svg>;
}
function IconTrash() {
  return <svg width='18' height='18' viewBox='0 0 24 24' fill='none' stroke='currentColor' strokeWidth='2' strokeLinecap='round' strokeLinejoin='round'><path d='M3 6h18'/><path d='M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6'/><path d='M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2'/></svg>;
}
function IconHexagon() {
  return <svg width='20' height='20' viewBox='0 0 24 24' fill='none' stroke='currentColor' strokeWidth='2' strokeLinecap='round' strokeLinejoin='round'><path d='M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z'/></svg>;
}
function IconUser() {
  return <svg width='18' height='18' viewBox='0 0 24 24' fill='none' stroke='currentColor' strokeWidth='2' strokeLinecap='round' strokeLinejoin='round'><path d='M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2'/><circle cx='12' cy='7' r='4'/></svg>;
}
function IconSpeaker() {
  return <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon><path d="M15.54 8.46a5 5 0 0 1 0 7.07"></path><path d="M19.07 4.93a10 10 0 0 1 0 14.14"></path></svg>;
}

