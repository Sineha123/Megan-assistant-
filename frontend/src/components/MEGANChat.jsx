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
  const [wsStatus,    setWsStatus]    = useState("disconnected"); // connected | disconnected | error

  const bottomRef   = useRef(null);
  const inputRef    = useRef(null);
  const wsRef       = useRef(null);
  const mediaRef    = useRef(null);
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

  /* ── Send via HTTP POST ─────────────────────────────────────── */
  async function sendMessage(text) {
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
          message_type: "text",
        }),
      });
      const data = await res.json();
      pushMessage("assistant", data.response ?? data.error ?? "No response");
    } catch (err) {
      pushMessage("assistant", `⚠ Network error: ${err.message}`);
    } finally {
      setIsLoading(false);
      inputRef.current?.focus();
    }
  }

  /* ── Voice Recording ─────────────────────────────────────────── */
  async function toggleVoice() {
    if (isListening) {
      // Stop recording
      mediaRef.current?.stop();
      setIsListening(false);
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      audioChunks.current = [];

      recorder.ondataavailable = (e) => audioChunks.current.push(e.data);
      recorder.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop());
        const blob   = new Blob(audioChunks.current, { type: "audio/wav" });
        const buffer = await blob.arrayBuffer();
        const b64    = btoa(
          new Uint8Array(buffer).reduce((acc, b) => acc + String.fromCharCode(b), "")
        );

        setIsLoading(true);
        pushMessage("user", "🎤 [Voice message]");

        try {
          const res  = await fetch("/voice/upload", {
            method:  "POST",
            headers: { "Content-Type": "application/json" },
            body:    JSON.stringify({ user_id: userId, audio_base64: b64, language: "hi-IN" }),
          });
          const data = await res.json();
          if (data.transcribed_text) {
            setMessages((prev) => {
              const updated = [...prev];
              const last    = updated.findLastIndex((m) => m.role === "user");
              if (last >= 0) updated[last] = { ...updated[last], content: `🎤 "${data.transcribed_text}"` };
              return updated;
            });
          }
          pushMessage("assistant", data.response ?? data.error ?? "No response");
        } catch (err) {
          pushMessage("assistant", `⚠ Voice error: ${err.message}`);
        } finally {
          setIsLoading(false);
        }
      };

      recorder.start();
      mediaRef.current = recorder;
      setIsListening(true);
    } catch (err) {
      pushMessage("assistant", `⚠ Microphone error: ${err.message}. Please allow microphone access.`);
    }
  }

  /* ── Key handler ─────────────────────────────────────────────── */
  function handleKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage(input);
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

      {/* Connection badge */}
      <div className={`ws-badge ws-${wsStatus}`}>
        <span className="ws-dot" />
        {wsStatus === "connected" ? "Live" : wsStatus === "error" ? "Error" : "Offline"}
      </div>

      {/* Messages */}
      <div className="chat-messages" aria-live="polite" aria-label="Conversation">
        {messages.map((msg) => (
          <MessageBubble key={msg.id} message={msg} />
        ))}

        {isLoading && <TypingIndicator />}
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
          id="megan-send-btn"
          className="action-btn send-btn"
          onClick={() => sendMessage(input)}
          disabled={isLoading || !input.trim()}
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

