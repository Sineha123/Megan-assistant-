"""
MEGAN Memory System
Stores and retrieves:
- User profiles
- Voice profiles
- Mood history
- Preferences
- Interaction history
"""

import json
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from pathlib import Path

class MemoryManager:
    """
    Manages MEGAN's memory:
    - Remembers user preferences
    - Tracks mood changes
    - Maintains interaction history
    - Stores voice profiles
    """
    
    def __init__(self, db_path: str = "megan_memory.db"):
        self.db_path = db_path
        self.connection = None
        self._initialize_database()
    
    def initialize(self):
        """Initialize memory system"""
        print("[MEMORY] Initializing Memory System...")
        self._create_tables()
        print("[MEMORY] Memory System ready")
    
    def _initialize_database(self):
        """Create database connection"""
        try:
            self.connection = sqlite3.connect(self.db_path)
            self.connection.row_factory = sqlite3.Row
            print(f"[MEMORY] Database connected: {self.db_path}")
        except Exception as e:
            print(f"[ERROR] Database connection failed: {str(e)}")
    
    def _create_tables(self):
        """Create necessary database tables"""
        cursor = self.connection.cursor()
        
        # Users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                name TEXT,
                created_at TIMESTAMP,
                last_interaction TIMESTAMP,
                voice_profile_path TEXT
            )
        """)
        
        # User preferences
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS preferences (
                id INTEGER PRIMARY KEY,
                user_id TEXT,
                key TEXT,
                value TEXT,
                FOREIGN KEY(user_id) REFERENCES users(user_id)
            )
        """)
        
        # Mood history
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS mood_history (
                id INTEGER PRIMARY KEY,
                user_id TEXT,
                mood TEXT,
                confidence FLOAT,
                timestamp TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(user_id)
            )
        """)
        
        # Interactions
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS interactions (
                id INTEGER PRIMARY KEY,
                user_id TEXT,
                message TEXT,
                response TEXT,
                message_type TEXT,
                timestamp TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(user_id)
            )
        """)
        
        # Habits (learned patterns)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS habits (
                id INTEGER PRIMARY KEY,
                user_id TEXT,
                habit_type TEXT,
                pattern TEXT,
                frequency INTEGER,
                FOREIGN KEY(user_id) REFERENCES users(user_id)
            )
        """)
        
        # Contacts
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS contacts (
                id INTEGER PRIMARY KEY,
                user_id TEXT,
                contact_name TEXT,
                contact_info TEXT,
                contact_type TEXT,
                FOREIGN KEY(user_id) REFERENCES users(user_id)
            )
        """)
        
        self.connection.commit()
        print("[MEMORY] Database tables created")
    
    def save_user_profile(self, profile: Dict) -> bool:
        """Save user profile"""
        try:
            cursor = self.connection.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO users 
                (user_id, name, created_at, last_interaction)
                VALUES (?, ?, ?, ?)
            """, (
                profile.get('user_id'),
                profile.get('name'),
                datetime.now().isoformat(),
                datetime.now().isoformat()
            ))
            
            # Save preferences
            if 'preferences' in profile:
                for key, value in profile['preferences'].items():
                    cursor.execute("""
                        INSERT OR REPLACE INTO preferences
                        (user_id, key, value)
                        VALUES (?, ?, ?)
                    """, (profile['user_id'], key, json.dumps(value)))
            
            self.connection.commit()
            print(f"[MEMORY] User profile saved: {profile.get('user_id')}")
            return True
        
        except Exception as e:
            print(f"[ERROR] Failed to save user profile: {str(e)}")
            return False
    
    def get_user_context(self, user_id: str) -> Dict:
        """
        Retrieve comprehensive user context for personalization
        """
        try:
            cursor = self.connection.cursor()
            
            context = {
                "user_id": user_id,
                "user_name": None,
                "last_mood": None,
                "preferences": {},
                "recent_activities": [],
                "favorite_contacts": [],
                "last_interaction": None
            }
            
            # Get user info
            cursor.execute("SELECT name, last_interaction FROM users WHERE user_id = ?", (user_id,))
            user = cursor.fetchone()
            if user:
                context["user_name"] = user["name"]
                context["last_interaction"] = user["last_interaction"]
            
            # Get preferences
            cursor.execute("SELECT key, value FROM preferences WHERE user_id = ?", (user_id,))
            for row in cursor.fetchall():
                context["preferences"][row["key"]] = json.loads(row["value"])
            
            # Get last mood
            cursor.execute("""
                SELECT mood FROM mood_history 
                WHERE user_id = ? 
                ORDER BY timestamp DESC 
                LIMIT 1
            """, (user_id,))
            mood = cursor.fetchone()
            if mood:
                context["last_mood"] = mood["mood"]
            
            # Get recent activities
            cursor.execute("""
                SELECT message FROM interactions 
                WHERE user_id = ? 
                ORDER BY timestamp DESC 
                LIMIT 5
            """, (user_id,))
            context["recent_activities"] = [row["message"] for row in cursor.fetchall()]
            
            # Get favorite contacts
            cursor.execute("""
                SELECT contact_name FROM contacts 
                WHERE user_id = ? 
                ORDER BY rowid DESC 
                LIMIT 5
            """, (user_id,))
            context["favorite_contacts"] = [row["contact_name"] for row in cursor.fetchall()]
            
            return context
        
        except Exception as e:
            print(f"[ERROR] Failed to get user context: {str(e)}")
            return {}
    
    def save_interaction(
        self,
        user_id: str,
        message: str,
        response: str,
        message_type: str = "text"
    ) -> bool:
        """Save interaction to history"""
        try:
            cursor = self.connection.cursor()
            
            cursor.execute("""
                INSERT INTO interactions
                (user_id, message, response, message_type, timestamp)
                VALUES (?, ?, ?, ?, ?)
            """, (
                user_id,
                message,
                response,
                message_type,
                datetime.now().isoformat()
            ))
            
            # Update last interaction
            cursor.execute("""
                UPDATE users SET last_interaction = ?
                WHERE user_id = ?
            """, (datetime.now().isoformat(), user_id))
            
            self.connection.commit()
            return True
        
        except Exception as e:
            print(f"[ERROR] Failed to save interaction: {str(e)}")
            return False
    
    def save_mood(
        self,
        user_id: str,
        mood: str,
        confidence: float = 1.0
    ) -> bool:
        """Save mood detection"""
        try:
            cursor = self.connection.cursor()
            
            cursor.execute("""
                INSERT INTO mood_history
                (user_id, mood, confidence, timestamp)
                VALUES (?, ?, ?, ?)
            """, (
                user_id,
                mood,
                confidence,
                datetime.now().isoformat()
            ))
            
            self.connection.commit()
            print(f"[MEMORY] Mood saved for {user_id}: {mood}")
            return True
        
        except Exception as e:
            print(f"[ERROR] Failed to save mood: {str(e)}")
            return False
    
    def get_mood_history(
        self,
        user_id: str,
        days: int = 7
    ) -> List[Dict]:
        """Get mood history for past N days"""
        try:
            cursor = self.connection.cursor()
            
            cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
            
            cursor.execute("""
                SELECT mood, confidence, timestamp
                FROM mood_history
                WHERE user_id = ? AND timestamp > ?
                ORDER BY timestamp DESC
            """, (user_id, cutoff_date))
            
            history = []
            for row in cursor.fetchall():
                history.append({
                    "mood": row["mood"],
                    "confidence": row["confidence"],
                    "timestamp": row["timestamp"]
                })
            
            return history
        
        except Exception as e:
            print(f"[ERROR] Failed to get mood history: {str(e)}")
            return []
    
    def save_preference(self, user_id: str, key: str, value: any) -> bool:
        """Save or update a user preference"""
        try:
            cursor = self.connection.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO preferences
                (user_id, key, value)
                VALUES (?, ?, ?)
            """, (user_id, key, json.dumps(value)))
            
            self.connection.commit()
            print(f"[MEMORY] Preference saved: {key} = {value}")
            return True
        
        except Exception as e:
            print(f"[ERROR] Failed to save preference: {str(e)}")
            return False
    
    def add_contact(
        self,
        user_id: str,
        contact_name: str,
        contact_info: str,
        contact_type: str = "general"
    ) -> bool:
        """Save a contact"""
        try:
            cursor = self.connection.cursor()
            
            cursor.execute("""
                INSERT INTO contacts
                (user_id, contact_name, contact_info, contact_type)
                VALUES (?, ?, ?, ?)
            """, (user_id, contact_name, contact_info, contact_type))
            
            self.connection.commit()
            return True
        
        except Exception as e:
            print(f"[ERROR] Failed to add contact: {str(e)}")
            return False
    
    def save_all(self):
        """Save all data to disk"""
        try:
            self.connection.commit()
            print("[MEMORY] All data saved")
        except Exception as e:
            print(f"[ERROR] Failed to save data: {str(e)}")
    
    def close(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
            print("[MEMORY] Database connection closed")


# Test
if __name__ == "__main__":
    memory = MemoryManager()
    memory.initialize()
    
    # Test saving user
    memory.save_user_profile({
        "user_id": "user_001",
        "name": "Ahmed",
        "preferences": {
            "language": "en",
            "location": "Hyderabad"
        }
    })
    
    # Test saving interaction
    memory.save_interaction(
        "user_001",
        "What's the weather?",
        "It's sunny and 28°C"
    )
    
    # Test getting context
    context = memory.get_user_context("user_001")
    print(json.dumps(context, indent=2))
    
    # Test mood
    memory.save_mood("user_001", "happy", 0.85)
    
    memory.close()
