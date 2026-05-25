"""
MEGAN Brain - Central AI Coordinator
Processes requests and routes to appropriate agents
"""

import json
from typing import Dict, Optional, Any
from datetime import datetime
import anthropic
import asyncio

class MEGANBrain:
    """
    Central brain that:
    - Understands user intent
    - Routes to appropriate agents
    - Coordinates multi-step tasks
    - Maintains conversation context
    """
    
    def __init__(self):
        self.client = anthropic.Anthropic()
        self.model = "claude-3-5-sonnet-20241022"
        self.agents = {
            "browser": None,
            "messaging": None,
            "file": None,
            "vision": None,
            "voice": None,
            "system": None
        }
        self.conversation_history = {}
        self.system_prompt = self._load_system_prompt()
    
    async def initialize(self):
        """Initialize brain and load agents"""
        print("[BRAIN] Initializing MEGAN Brain...")
        # Agents will be injected later
        print("[BRAIN] Brain online. Ready to think.")
    
    def _load_system_prompt(self) -> str:
        """Load MEGAN's system prompt"""
        return """You are MEGAN, an advanced AI assistant system inspired by JARVIS. You are the central brain that:

1. UNDERSTANDS USER INTENT: Parse requests and determine what the user actually wants
2. ROUTES TASKS: Decide which agent(s) to use (browser, messaging, file, vision, voice, system)
3. COORDINATES: Manage multi-step tasks across different components
4. LEARNS: Remember preferences and past interactions
5. RESPONDS: Provide helpful, natural responses

AVAILABLE AGENTS:
- Browser Agent: Search, navigate websites, click, fill forms, extract data
- Messaging Agent: Send messages (WhatsApp/Email), find contacts, schedule messages
- File Agent: Find files, delete, organize, edit, create files
- Vision Module: See screen, read text (OCR), analyze images
- Voice Module: Speech-to-text, text-to-speech, mood detection, voice recognition
- System Agent: Control brightness, volume, type text, manage apps

YOUR RULES:
1. Always understand the request clearly before acting
2. Ask for confirmation on sensitive/dangerous operations
3. Respect user privacy - never access without permission
4. Be honest about limitations
5. Keep responses concise and natural
6. Remember to use context from previous messages
7. Break complex tasks into steps
8. Always consider if there are security/privacy concerns

RESPONSE FORMAT:
When you need to delegate to an agent, respond with clear action items.
When you're done, provide a helpful summary to the user.

TONE: Professional, helpful, respectful, occasionally witty. Talk naturally."""
    
    async def process_message(
        self,
        user_id: str,
        content: str,
        message_type: str = "text",
        context: Optional[Dict] = None
    ) -> str:
        """
        Main method to process user message
        
        Args:
            user_id: User identifier
            content: User's message
            message_type: 'text', 'voice', or 'command'
            context: User context from memory
        
        Returns:
            Response from MEGAN
        """
        
        # Initialize conversation history for user if needed
        if user_id not in self.conversation_history:
            self.conversation_history[user_id] = []
        
        # Build context-aware message
        user_message = self._build_context_message(
            user_id=user_id,
            content=content,
            message_type=message_type,
            context=context
        )
        
        # Add to conversation history
        self.conversation_history[user_id].append({
            "role": "user",
            "content": user_message
        })
        
        # Get response from Claude
        response = self._get_brain_response(
            user_id=user_id,
            messages=self.conversation_history[user_id]
        )
        
        # Add assistant response to history
        self.conversation_history[user_id].append({
            "role": "assistant",
            "content": response
        })
        
        # Keep history manageable (last 20 messages)
        if len(self.conversation_history[user_id]) > 20:
            self.conversation_history[user_id] = \
                self.conversation_history[user_id][-20:]
        
        return response
    
    def _build_context_message(
        self,
        user_id: str,
        content: str,
        message_type: str,
        context: Optional[Dict]
    ) -> str:
        """Build message with user context"""
        
        msg = f"User ({message_type}): {content}"
        
        # Add context information
        if context:
            if context.get("user_name"):
                msg = f"[User: {context['user_name']}] " + msg
            
            if context.get("last_mood"):
                msg += f"\n[Last detected mood: {context['last_mood']}]"
            
            if context.get("recent_activities"):
                msg += f"\n[Recent context: {', '.join(context['recent_activities'][-3:])}]"
        
        return msg
    
    def _get_brain_response(
        self,
        user_id: str,
        messages: list
    ) -> str:
        """
        Get response from Claude API
        This is where the actual thinking happens
        """
        
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                system=self.system_prompt,
                messages=messages
            )
            
            return response.content[0].text
        
        except Exception as e:
            print(f"[ERROR] Brain response error: {str(e)}")
            return f"I apologize, I'm having trouble thinking right now. Error: {str(e)}"
    
    async def execute_agent_task(
        self,
        agent_name: str,
        task: str,
        parameters: Dict,
        priority: str = "normal",
        confirm_first: bool = False
    ) -> Dict:
        """
        Execute a task through specific agent
        """
        
        print(f"[BRAIN] Executing task: {task} (Agent: {agent_name})")
        
        # This would be implemented with actual agent classes
        # For now, return a template response
        
        return {
            "agent": agent_name,
            "task": task,
            "status": "executing",
            "parameters": parameters,
            "timestamp": datetime.now().isoformat()
        }
    
    def set_agent(self, agent_name: str, agent_instance):
        """Register an agent"""
        if agent_name in self.agents:
            self.agents[agent_name] = agent_instance
            print(f"[BRAIN] Agent registered: {agent_name}")
    
    def get_conversation_history(self, user_id: str) -> list:
        """Get conversation history for user"""
        return self.conversation_history.get(user_id, [])
    
    def clear_conversation_history(self, user_id: str):
        """Clear conversation history for user"""
        if user_id in self.conversation_history:
            del self.conversation_history[user_id]
            print(f"[BRAIN] Conversation history cleared for {user_id}")


# Example usage and testing
if __name__ == "__main__":
    import asyncio
    
    async def test_brain():
        brain = MEGANBrain()
        await brain.initialize()
        
        # Test simple message
        response = await brain.process_message(
            user_id="user_001",
            content="What's the weather like today?",
            message_type="text"
        )
        
        print(f"\n[RESPONSE] {response}")
        
        # Test follow-up (should remember context)
        response2 = await brain.process_message(
            user_id="user_001",
            content="Okay, so should I bring an umbrella?",
            message_type="text"
        )
        
        print(f"\n[RESPONSE] {response2}")
    
    asyncio.run(test_brain())
