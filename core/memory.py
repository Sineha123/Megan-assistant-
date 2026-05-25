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

from core.config import DB_PATH


class MemoryManager:
    """
    Manages MEGAN's persistent memory:
    - Remembers user preferences
    - Tracks mood changes
    - Maintains interaction history
    - Stores contact book
    """

    def __init__(self, db_path: Optional[str] = None):
        self.db_path   = db_path or DB_PATH
        self.connection: Optional[sqlite3.Connection] = None
        self._initialize_database()

    # ─── Setup ───────────────────────────────────────────────────────────────

    def initialize(self):
        """Initialize memory system (called at startup)."""
        print("[MEMORY] Initializing Memory System...")
        self._create_tables()
        print("[MEMORY] Memory System ready")

    def _initialize_database(self):
        """Create database connection."""
        try:
            self.connection = sqlite3.connect(self.db_path, check_same_thread=False)
            self.connection.row_factory = sqlite3.Row
            print(f"[MEMORY] Database connected: {self.db_path}")
        except Exception as e:
            print(f"[ERROR] Database connection failed: {str(e)}")

    def _create_tables(self):
        """Create necessary database tables if they don't exist."""
        cursor = self.connection.cursor()

        cursor.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                user_id          TEXT PRIMARY KEY,
                name             TEXT,
                created_at       TIMESTAMP,
                last_interaction TIMESTAMP,
                voice_profile_path TEXT
            );

            CREATE TABLE IF NOT EXISTS preferences (
                id      INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                key     TEXT,
                value   TEXT,
                UNIQUE(user_id, key),
                FOREIGN KEY(user_id) REFERENCES users(user_id)
            );

            CREATE TABLE IF NOT EXISTS mood_history (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id    TEXT,
                mood       TEXT,
                confidence FLOAT,
                timestamp  TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(user_id)
            );

            CREATE TABLE IF NOT EXISTS interactions (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id      TEXT,
                message      TEXT,
                response     TEXT,
                message_type TEXT,
                timestamp    TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(user_id)
            );

            CREATE TABLE IF NOT EXISTS habits (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id    TEXT,
                habit_type TEXT,
                pattern    TEXT,
                frequency  INTEGER DEFAULT 1,
                FOREIGN KEY(user_id) REFERENCES users(user_id)
            );

            CREATE TABLE IF NOT EXISTS contacts (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id      TEXT,
                contact_name TEXT,
                contact_info TEXT,
                contact_type TEXT DEFAULT 'general',
                FOREIGN KEY(user_id) REFERENCES users(user_id)
            );
        """)

        self.connection.commit()
        print("[MEMORY] Database tables ready")

    # ─── User Profile ────────────────────────────────────────────────────────

    def save_user_profile(self, profile: Dict) -> bool:
        """Save or update a user profile."""
        try:
            cursor = self.connection.cursor()

            cursor.execute("""
                INSERT OR REPLACE INTO users
                (user_id, name, created_at, last_interaction)
                VALUES (?, ?, ?, ?)
            """, (
                profile.get("user_id"),
                profile.get("name"),
                datetime.now().isoformat(),
                datetime.now().isoformat(),
            ))

            # Save preferences
            if "preferences" in profile:
                for key, value in profile["preferences"].items():
                    cursor.execute("""
                        INSERT OR REPLACE INTO preferences (user_id, key, value)
                        VALUES (?, ?, ?)
                    """, (profile["user_id"], key, json.dumps(value)))

            self.connection.commit()
            print(f"[MEMORY] User profile saved: {profile.get('user_id')}")
            return True

        except Exception as e:
            print(f"[ERROR] Failed to save user profile: {str(e)}")
            return False

    def get_user_context(self, user_id: str) -> Dict:
        """Retrieve comprehensive user context for personalisation."""
        try:
            cursor = self.connection.cursor()

            context: Dict = {
                "user_id":          user_id,
                "user_name":        None,
                "last_mood":        None,
                "preferences":      {},
                "recent_activities": [],
                "favorite_contacts": [],
                "last_interaction": None,
            }

            # Basic user info
            cursor.execute(
                "SELECT name, last_interaction FROM users WHERE user_id = ?",
                (user_id,),
            )
            user = cursor.fetchone()
            if user:
                context["user_name"]        = user["name"]
                context["last_interaction"] = user["last_interaction"]

            # Preferences
            cursor.execute(
                "SELECT key, value FROM preferences WHERE user_id = ?",
                (user_id,),
            )
            for row in cursor.fetchall():
                context["preferences"][row["key"]] = json.loads(row["value"])

            # Last mood
            cursor.execute("""
                SELECT mood FROM mood_history
                WHERE user_id = ?
                ORDER BY timestamp DESC
                LIMIT 1
            """, (user_id,))
            mood = cursor.fetchone()
            if mood:
                context["last_mood"] = mood["mood"]

            # Recent activities (last 5 messages)
            cursor.execute("""
                SELECT message FROM interactions
                WHERE user_id = ?
                ORDER BY timestamp DESC
                LIMIT 5
            """, (user_id,))
            context["recent_activities"] = [r["message"] for r in cursor.fetchall()]

            # Favourite contacts
            cursor.execute("""
                SELECT contact_name FROM contacts
                WHERE user_id = ?
                ORDER BY rowid DESC
                LIMIT 5
            """, (user_id,))
            context["favorite_contacts"] = [r["contact_name"] for r in cursor.fetchall()]

            return context

        except Exception as e:
            print(f"[ERROR] Failed to get user context: {str(e)}")
            return {}

    # ─── Interactions ────────────────────────────────────────────────────────

    def save_interaction(
        self,
        user_id: str,
        message: str,
        response: str,
        message_type: str = "text",
    ) -> bool:
        """Save a user↔MEGAN interaction."""
        try:
            cursor = self.connection.cursor()

            cursor.execute("""
                INSERT INTO interactions
                (user_id, message, response, message_type, timestamp)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, message, response, message_type, datetime.now().isoformat()))

            # Ensure user row exists before updating last_interaction
            cursor.execute("""
                INSERT OR IGNORE INTO users (user_id, created_at, last_interaction)
                VALUES (?, ?, ?)
            """, (user_id, datetime.now().isoformat(), datetime.now().isoformat()))

            cursor.execute("""
                UPDATE users SET last_interaction = ? WHERE user_id = ?
            """, (datetime.now().isoformat(), user_id))

            self.connection.commit()
            return True

        except Exception as e:
            print(f"[ERROR] Failed to save interaction: {str(e)}")
            return False

    # ─── Mood ────────────────────────────────────────────────────────────────

    def save_mood(self, user_id: str, mood: str, confidence: float = 1.0) -> bool:
        """Save a mood detection event."""
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                INSERT INTO mood_history (user_id, mood, confidence, timestamp)
                VALUES (?, ?, ?, ?)
            """, (user_id, mood, confidence, datetime.now().isoformat()))
            self.connection.commit()
            print(f"[MEMORY] Mood saved for {user_id}: {mood}")
            return True

        except Exception as e:
            print(f"[ERROR] Failed to save mood: {str(e)}")
            return False

    def get_mood_history(self, user_id: str, days: int = 7) -> List[Dict]:
        """Get mood history for the past N days."""
        try:
            cursor = self.connection.cursor()
            cutoff = (datetime.now() - timedelta(days=days)).isoformat()
            cursor.execute("""
                SELECT mood, confidence, timestamp FROM mood_history
                WHERE user_id = ? AND timestamp > ?
                ORDER BY timestamp DESC
            """, (user_id, cutoff))
            return [
                {"mood": r["mood"], "confidence": r["confidence"], "timestamp": r["timestamp"]}
                for r in cursor.fetchall()
            ]
        except Exception as e:
            print(f"[ERROR] Failed to get mood history: {str(e)}")
            return []

    # ─── Preferences ─────────────────────────────────────────────────────────

    def save_preference(self, user_id: str, key: str, value) -> bool:
        """Save or update a single user preference."""
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO preferences (user_id, key, value)
                VALUES (?, ?, ?)
            """, (user_id, key, json.dumps(value)))
            self.connection.commit()
            print(f"[MEMORY] Preference saved: {key} = {value}")
            return True

        except Exception as e:
            print(f"[ERROR] Failed to save preference: {str(e)}")
            return False

    # ─── Contacts ────────────────────────────────────────────────────────────

    def add_contact(
        self,
        user_id: str,
        contact_name: str,
        contact_info: str,
        contact_type: str = "general",
    ) -> bool:
        """Save a contact."""
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                INSERT INTO contacts (user_id, contact_name, contact_info, contact_type)
                VALUES (?, ?, ?, ?)
            """, (user_id, contact_name, contact_info, contact_type))
            self.connection.commit()
            return True

        except Exception as e:
            print(f"[ERROR] Failed to add contact: {str(e)}")
            return False

    # ─── Persistence ─────────────────────────────────────────────────────────

    def save_all(self):
        """Flush all pending writes to disk."""
        try:
            self.connection.commit()
            print("[MEMORY] All data saved")
        except Exception as e:
            print(f"[ERROR] Failed to save data: {str(e)}")

    def close(self):
        """Close database connection."""
        if self.connection:
            self.connection.close()
            print("[MEMORY] Database connection closed")


# ─── Standalone Test ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    import json as _json

    mem = MemoryManager()
    mem.initialize()

    mem.save_user_profile({
        "user_id": "user_001",
        "name":    "Ahmed",
        "preferences": {"language": "en", "location": "Hyderabad"},
    })

    mem.save_interaction("user_001", "What's the weather?", "It's sunny and 28°C")
    ctx = mem.get_user_context("user_001")
    print(_json.dumps(ctx, indent=2))

    mem.save_mood("user_001", "happy", 0.85)
    mem.close()
