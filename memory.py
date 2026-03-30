# memory.py - SQLite-based memory system
import sqlite3
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from contextlib import contextmanager
import os

logger = logging.getLogger(__name__)

class BotMemory:
    """
    SQLite-based memory system for the Twitter bot.
    Tracks past tweets, topics, interactions, and user relationships.
    """
    
    def __init__(self, db_path: str = "data/bot_memory.db"):
        self.db_path = db_path
        self._ensure_db_directory()
        self._init_database()
    
    def _ensure_db_directory(self):
        """Ensure the database directory exists."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
    
    @contextmanager
    def _get_connection(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def _init_database(self):
        """Initialize database tables."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Store past tweets
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tweets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tweet_id TEXT UNIQUE,
                    content TEXT,
                    tweet_type TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    engagement_score INTEGER DEFAULT 0,
                    topics TEXT
                )
            """)
            
            # Store topics used
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS topics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    topic TEXT UNIQUE,
                    last_used TIMESTAMP,
                    usage_count INTEGER DEFAULT 0
                )
            """)
            
            # Store user interactions
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_interactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT,
                    username TEXT,
                    interaction_type TEXT,
                    last_interaction TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    interaction_count INTEGER DEFAULT 1,
                    UNIQUE(user_id, interaction_type)
                )
            """)
            
            # Store daily action counts (for rate limiting)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS daily_actions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT UNIQUE,
                    tweets_count INTEGER DEFAULT 0,
                    replies_count INTEGER DEFAULT 0,
                    retweets_count INTEGER DEFAULT 0,
                    likes_count INTEGER DEFAULT 0
                )
            """)
            
            # Store engagement targets
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS engagement_targets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tweet_id TEXT UNIQUE,
                    author_id TEXT,
                    content_preview TEXT,
                    engagement_score INTEGER,
                    found_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    engaged BOOLEAN DEFAULT 0
                )
            """)
            
            conn.commit()
            logger.info("Database initialized successfully")
    
    # === Tweet Memory ===
    
    def store_tweet(self, tweet_id: str, content: str, tweet_type: str = "original", 
                    topics: List[str] = None, engagement_score: int = 0):
        """Store a tweet in memory."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            topics_json = json.dumps(topics) if topics else None
            cursor.execute("""
                INSERT OR REPLACE INTO tweets (tweet_id, content, tweet_type, topics, engagement_score)
                VALUES (?, ?, ?, ?, ?)
            """, (tweet_id, content, tweet_type, topics_json, engagement_score))
            conn.commit()
            
            # Update topic usage
            if topics:
                for topic in topics:
                    self._update_topic_usage(topic)
            
            logger.debug(f"Stored tweet {tweet_id}")
    
    def get_recent_tweets(self, hours: int = 24, tweet_type: Optional[str] = None) -> List[Dict]:
        """Get tweets posted in the last N hours."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            since = datetime.now() - timedelta(hours=hours)
            
            if tweet_type:
                cursor.execute("""
                    SELECT * FROM tweets 
                    WHERE created_at > ? AND tweet_type = ?
                    ORDER BY created_at DESC
                """, (since.isoformat(), tweet_type))
            else:
                cursor.execute("""
                    SELECT * FROM tweets 
                    WHERE created_at > ?
                    ORDER BY created_at DESC
                """, (since.isoformat(),))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def is_similar_tweet_exists(self, content: str, similarity_threshold: float = 0.8) -> bool:
        """
        Check if a similar tweet was recently posted.
        Simple implementation using substring matching.
        """
        recent_tweets = self.get_recent_tweets(hours=72)
        content_lower = content.lower()
        
        for tweet in recent_tweets:
            stored_content = tweet['content'].lower()
            # Check for significant overlap
            if len(content) > 0:
                similarity = len(set(content_lower.split()) & set(stored_content.split())) / len(set(content_lower.split()))
                if similarity > similarity_threshold:
                    return True
        return False
    
    # === Topic Memory ===
    
    def _update_topic_usage(self, topic: str):
        """Update topic usage count."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO topics (topic, last_used, usage_count)
                VALUES (?, ?, 1)
                ON CONFLICT(topic) DO UPDATE SET
                    last_used = excluded.last_used,
                    usage_count = topics.usage_count + 1
            """, (topic, datetime.now().isoformat()))
            conn.commit()
    
    def get_recently_used_topics(self, hours: int = 48) -> List[str]:
        """Get topics used in the last N hours."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            since = datetime.now() - timedelta(hours=hours)
            cursor.execute("""
                SELECT topic FROM topics 
                WHERE last_used > ?
            """, (since.isoformat(),))
            return [row['topic'] for row in cursor.fetchall()]
    
    def get_frequently_used_topics(self, limit: int = 10) -> List[Tuple[str, int]]:
        """Get most frequently used topics."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT topic, usage_count FROM topics 
                ORDER BY usage_count DESC
                LIMIT ?
            """, (limit,))
            return [(row['topic'], row['usage_count']) for row in cursor.fetchall()]
    
    # === User Interaction Memory ===
    
    def record_interaction(self, user_id: str, username: str, interaction_type: str):
        """Record an interaction with a user."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO user_interactions (user_id, username, interaction_type, last_interaction)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(user_id, interaction_type) DO UPDATE SET
                    last_interaction = excluded.last_interaction,
                    interaction_count = user_interactions.interaction_count + 1
            """, (user_id, username, interaction_type, datetime.now().isoformat()))
            conn.commit()
    
    def get_user_interaction_count(self, user_id: str, hours: int = 24) -> int:
        """Get number of interactions with a user in the last N hours."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            since = datetime.now() - timedelta(hours=hours)
            cursor.execute("""
                SELECT SUM(interaction_count) as total FROM user_interactions 
                WHERE user_id = ? AND last_interaction > ?
            """, (user_id, since.isoformat()))
            result = cursor.fetchone()
            return result['total'] or 0
    
    def get_recently_interacted_users(self, hours: int = 24) -> List[str]:
        """Get list of users interacted with recently."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            since = datetime.now() - timedelta(hours=hours)
            cursor.execute("""
                SELECT DISTINCT user_id FROM user_interactions 
                WHERE last_interaction > ?
            """, (since.isoformat(),))
            return [row['user_id'] for row in cursor.fetchall()]
    
    # === Rate Limiting ===
    
    def get_todays_action_counts(self) -> Dict[str, int]:
        """Get today's action counts."""
        today = datetime.now().strftime("%Y-%m-%d")
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM daily_actions WHERE date = ?
            """, (today,))
            row = cursor.fetchone()
            
            if row:
                return {
                    'tweets': row['tweets_count'],
                    'replies': row['replies_count'],
                    'retweets': row['retweets_count'],
                    'likes': row['likes_count']
                }
            else:
                # Initialize today's record
                cursor.execute("""
                    INSERT INTO daily_actions (date) VALUES (?)
                """, (today,))
                conn.commit()
                return {'tweets': 0, 'replies': 0, 'retweets': 0, 'likes': 0}
    
    def increment_action_count(self, action_type: str):
        """Increment the count for a specific action type."""
        today = datetime.now().strftime("%Y-%m-%d")
        valid_actions = ['tweets', 'replies', 'retweets', 'likes']
        
        if action_type not in valid_actions:
            raise ValueError(f"Invalid action type: {action_type}")
        
        column = f"{action_type}_count"
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"""
                INSERT INTO daily_actions (date, {column})
                VALUES (?, 1)
                ON CONFLICT(date) DO UPDATE SET
                    {column} = {column} + 1
            """, (today,))
            conn.commit()
    
    def can_perform_action(self, action_type: str, max_per_hour: int) -> bool:
        """Check if an action can be performed based on rate limits."""
        counts = self.get_todays_action_counts()
        # Simple hourly check (assumes actions spread across day)
        current_count = counts.get(action_type, 0)
        return current_count < max_per_hour * 24  # Daily limit
    
    # === Engagement Targets ===
    
    def store_engagement_target(self, tweet_id: str, author_id: str, 
                               content_preview: str, engagement_score: int):
        """Store a potential tweet to engage with."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR IGNORE INTO engagement_targets 
                (tweet_id, author_id, content_preview, engagement_score)
                VALUES (?, ?, ?, ?)
            """, (tweet_id, author_id, content_preview, engagement_score))
            conn.commit()
    
    def get_high_engagement_targets(self, min_score: int = 10, limit: int = 10) -> List[Dict]:
        """Get high-engagement tweets to interact with."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM engagement_targets 
                WHERE engaged = 0 AND engagement_score >= ?
                ORDER BY engagement_score DESC
                LIMIT ?
            """, (min_score, limit))
            return [dict(row) for row in cursor.fetchall()]
    
    def mark_engaged(self, tweet_id: str):
        """Mark a target as engaged."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE engagement_targets SET engaged = 1 WHERE tweet_id = ?
            """, (tweet_id,))
            conn.commit()
    
    # === Maintenance ===
    
    def cleanup_old_data(self, days: int = 30):
        """Clean up old data to prevent database bloat."""
        cutoff = datetime.now() - timedelta(days=days)
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM tweets WHERE created_at < ?", (cutoff.isoformat(),))
            cursor.execute("DELETE FROM engagement_targets WHERE found_at < ?", (cutoff.isoformat(),))
            cursor.execute("DELETE FROM daily_actions WHERE date < ?", (cutoff.strftime("%Y-%m-%d"),))
            conn.commit()
            logger.info(f"Cleaned up data older than {days} days")
    
    def get_stats(self) -> Dict:
        """Get memory statistics."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            stats = {}
            cursor.execute("SELECT COUNT(*) FROM tweets")
            stats['total_tweets'] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM topics")
            stats['unique_topics'] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM user_interactions")
            stats['total_interactions'] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM engagement_targets WHERE engaged = 0")
            stats['pending_targets'] = cursor.fetchone()[0]
            
            return stats
