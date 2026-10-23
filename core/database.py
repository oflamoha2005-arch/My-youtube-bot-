import os
import sqlite3
from datetime import datetime, date
from typing import List, Dict, Any, Optional

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "youtube_bot.db")

class Database:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Sniped Videos (tracking which videos were detected & which accounts posted)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sniped_videos (
                    video_id TEXT PRIMARY KEY,
                    channel_name TEXT,
                    video_title TEXT,
                    video_url TEXT,
                    published_at TEXT,
                    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Comments Posted (Sniper & direct comments)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS comments_posted (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    video_id TEXT,
                    account_id TEXT,
                    account_name TEXT,
                    comment_type TEXT, -- 'sniper' or 'custom'
                    comment_text TEXT,
                    posted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'success',
                    FOREIGN KEY(video_id) REFERENCES sniped_videos(video_id)
                )
            """)

            # Intent Hunter Auto-Replies
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS intent_replies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    comment_id TEXT UNIQUE,
                    video_id TEXT,
                    video_title TEXT,
                    target_author TEXT,
                    original_comment TEXT,
                    account_id TEXT,
                    reply_text TEXT,
                    replied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'success'
                )
            """)

            # Warmer History (Watch time, Likes, Subscriptions)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS warmer_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    account_id TEXT,
                    video_id TEXT,
                    video_title TEXT,
                    watch_time_seconds INTEGER,
                    liked BOOLEAN,
                    subscribed BOOLEAN,
                    warmed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Account Activity / Daily Counters
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS daily_activity (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    account_id TEXT,
                    activity_date DATE,
                    sniper_comments_count INTEGER DEFAULT 0,
                    replies_count INTEGER DEFAULT 0,
                    warmer_views_count INTEGER DEFAULT 0,
                    UNIQUE(account_id, activity_date)
                )
            """)

            # Community Polls
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS community_polls (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    account_id TEXT,
                    question TEXT,
                    options TEXT,
                    cta_text TEXT,
                    posted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'success'
                )
            """)

            # Smart Playlists Created
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS playlists_created (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    account_id TEXT,
                    playlist_title TEXT,
                    target_niche TEXT,
                    videos_count INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Live Stream Chats History
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS livestream_chats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    account_id TEXT,
                    stream_id TEXT,
                    stream_title TEXT,
                    user_replied_to TEXT,
                    message_sent TEXT,
                    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Top Comments Vault (Reverse-Engineered Million-View Patterns)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS top_comments_vault (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    video_id TEXT,
                    video_title TEXT,
                    author TEXT,
                    likes_count INTEGER DEFAULT 0,
                    comment_text TEXT UNIQUE,
                    pattern_type TEXT,
                    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Scouted Channels Pool (Automated Discovery)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS scouted_channels (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    channel_name TEXT,
                    channel_url TEXT UNIQUE,
                    channel_id TEXT,
                    niche_query TEXT,
                    added_to_config BOOLEAN DEFAULT 1,
                    discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Multi-Account Comment Boosts (Cross-Upvoting)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS comment_boosts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    video_id TEXT,
                    target_comment_text TEXT,
                    booster_account_id TEXT,
                    action_type TEXT, -- 'like' or 'reply'
                    boosted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            conn.commit()

    # --- Sniper Queries ---
    def is_video_sniped_by_account(self, video_id: str, account_id: str) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 1 FROM comments_posted 
                WHERE video_id = ? AND account_id = ? AND status = 'success'
            """, (video_id, account_id))
            return cursor.fetchone() is not None

    def register_sniped_video(self, video_id: str, channel_name: str, title: str, url: str, published_at: str):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR IGNORE INTO sniped_videos (video_id, channel_name, video_title, video_url, published_at)
                VALUES (?, ?, ?, ?, ?)
            """, (video_id, channel_name, title, url, published_at))
            conn.commit()

    def log_comment(self, video_id: str, account_id: str, account_name: str, comment_text: str, comment_type: str = 'sniper'):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO comments_posted (video_id, account_id, account_name, comment_type, comment_text)
                VALUES (?, ?, ?, ?, ?)
            """, (video_id, account_id, account_name, comment_type, comment_text))
            
            # Update daily count
            today = date.today().isoformat()
            cursor.execute("""
                INSERT INTO daily_activity (account_id, activity_date, sniper_comments_count)
                VALUES (?, ?, 1)
                ON CONFLICT(account_id, activity_date) DO UPDATE SET
                sniper_comments_count = sniper_comments_count + 1
            """, (account_id, today))
            conn.commit()

    # --- Intent Replier Queries ---
    def is_comment_replied(self, comment_id: str) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM intent_replies WHERE comment_id = ?", (comment_id,))
            return cursor.fetchone() is not None

    def is_person_replied(self, target_author: str) -> bool:
        """Global check: ensures NO account ever replies to the same person twice."""
        if not target_author:
            return False
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM intent_replies WHERE LOWER(target_author) = LOWER(?)", (target_author.strip(),))
            return cursor.fetchone() is not None

    def log_intent_reply(self, comment_id: str, video_id: str, video_title: str, target_author: str,
                         original_comment: str, account_id: str, reply_text: str):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR IGNORE INTO intent_replies 
                (comment_id, video_id, video_title, target_author, original_comment, account_id, reply_text)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (comment_id, video_id, video_title, target_author, original_comment, account_id, reply_text))

            today = date.today().isoformat()
            cursor.execute("""
                INSERT INTO daily_activity (account_id, activity_date, replies_count)
                VALUES (?, ?, 1)
                ON CONFLICT(account_id, activity_date) DO UPDATE SET
                replies_count = replies_count + 1
            """, (account_id, today))
            conn.commit()

    # --- Warmer Queries ---
    def is_video_warmed_by_account(self, video_id: str, account_id: str) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM warmer_history WHERE video_id = ? AND account_id = ?", (video_id, account_id))
            return cursor.fetchone() is not None

    def is_video_warmed_globally(self, video_id: str) -> bool:
        """
        Global check: If ANY account has watched/warmed this video,
        no other account will ever watch it again!
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM warmer_history WHERE video_id = ?", (video_id,))
            return cursor.fetchone() is not None

    def log_warmer_session(self, account_id: str, video_id: str, video_title: str,
                           watch_time_seconds: int, liked: bool, subscribed: bool):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO warmer_history (account_id, video_id, video_title, watch_time_seconds, liked, subscribed)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (account_id, video_id, video_title, watch_time_seconds, liked, subscribed))

            today = date.today().isoformat()
            cursor.execute("""
                INSERT INTO daily_activity (account_id, activity_date, warmer_views_count)
                VALUES (?, ?, 1)
                ON CONFLICT(account_id, activity_date) DO UPDATE SET
                warmer_views_count = warmer_views_count + 1
            """, (account_id, today))
            conn.commit()

    # --- Stats & Activity Checks ---
    def get_account_daily_activity(self, account_id: str) -> Dict[str, int]:
        today = date.today().isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT sniper_comments_count, replies_count, warmer_views_count
                FROM daily_activity 
                WHERE account_id = ? AND activity_date = ?
            """, (account_id, today))
            row = cursor.fetchone()
            if row:
                return {
                    "sniper_comments": row["sniper_comments_count"],
                    "replies": row["replies_count"],
                    "warmer_views": row["warmer_views_count"]
                }
            return {"sniper_comments": 0, "replies": 0, "warmer_views": 0}

    # --- Community Polls Queries ---
    def log_community_poll(self, account_id: str, question: str, options: str, cta_text: str, status: str = "success"):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO community_polls (account_id, question, options, cta_text, status)
                VALUES (?, ?, ?, ?, ?)
            """, (account_id, question, options, cta_text, status))
            conn.commit()

    # --- Playlist Queries ---
    def log_playlist(self, account_id: str, playlist_title: str, target_niche: str, videos_count: int):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO playlists_created (account_id, playlist_title, target_niche, videos_count)
                VALUES (?, ?, ?, ?)
            """, (account_id, playlist_title, target_niche, videos_count))
            conn.commit()

    # --- Live Stream Queries ---
    def log_livestream_chat(self, account_id: str, stream_id: str, stream_title: str, user_replied_to: str, message_sent: str):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO livestream_chats (account_id, stream_id, stream_title, user_replied_to, message_sent)
                VALUES (?, ?, ?, ?, ?)
            """, (account_id, stream_id, stream_title, user_replied_to, message_sent))
            conn.commit()

    # --- Top Comments Vault Queries ---
    def save_top_comment(self, video_id: str, video_title: str, author: str, likes_count: int, comment_text: str, pattern_type: str = "viral_hook"):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR IGNORE INTO top_comments_vault (video_id, video_title, author, likes_count, comment_text, pattern_type)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (video_id, video_title, author, likes_count, comment_text, pattern_type))
            conn.commit()

    def get_top_comments_examples(self, limit: int = 5) -> List[str]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT comment_text FROM top_comments_vault 
                ORDER BY likes_count DESC, id DESC LIMIT ?
            """, (limit,))
            return [row["comment_text"] for row in cursor.fetchall()]

    # --- Scouted Channels Queries ---
    def log_scouted_channel(self, channel_name: str, channel_url: str, channel_id: str, niche_query: str):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR IGNORE INTO scouted_channels (channel_name, channel_url, channel_id, niche_query)
                VALUES (?, ?, ?, ?)
            """, (channel_name, channel_url, channel_id, niche_query))
            conn.commit()

    def is_channel_scouted(self, channel_url: str) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM scouted_channels WHERE channel_url = ?", (channel_url,))
            return cursor.fetchone() is not None

    # --- Comment Boosts Queries ---
    def log_comment_boost(self, video_id: str, target_comment_text: str, booster_account_id: str, action_type: str = "like"):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO comment_boosts (video_id, target_comment_text, booster_account_id, action_type)
                VALUES (?, ?, ?, ?)
            """, (video_id, target_comment_text, booster_account_id, action_type))
            conn.commit()

    def get_recent_sniped_comments(self, limit: int = 5) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT cp.video_id, cp.account_id, cp.comment_text, sv.video_url, sv.video_title
                FROM comments_posted cp
                JOIN sniped_videos sv ON cp.video_id = sv.video_id
                ORDER BY cp.posted_at DESC LIMIT ?
            """, (limit,))
            return [dict(r) for r in cursor.fetchall()]

    def get_total_stats(self) -> Dict[str, Any]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as total_sniped FROM comments_posted")
            total_sniped = cursor.fetchone()["total_sniped"]

            cursor.execute("SELECT COUNT(*) as total_replies FROM intent_replies")
            total_replies = cursor.fetchone()["total_replies"]

            cursor.execute("SELECT COUNT(*) as total_views, SUM(liked) as total_likes, SUM(subscribed) as total_subs FROM warmer_history")
            warmer_row = cursor.fetchone()

            cursor.execute("SELECT COUNT(*) as total_polls FROM community_polls")
            total_polls = cursor.fetchone()["total_polls"]

            cursor.execute("SELECT COUNT(*) as total_chats FROM livestream_chats")
            total_chats = cursor.fetchone()["total_chats"]

            cursor.execute("SELECT COUNT(*) as total_top_patterns FROM top_comments_vault")
            total_patterns = cursor.fetchone()["total_top_patterns"]

            cursor.execute("SELECT COUNT(*) as total_scouted FROM scouted_channels")
            total_scouted = cursor.fetchone()["total_scouted"]

            cursor.execute("SELECT COUNT(*) as total_boosts FROM comment_boosts")
            total_boosts = cursor.fetchone()["total_boosts"]

            cursor.execute("""
                SELECT video_title, account_name, comment_text, posted_at 
                FROM comments_posted 
                ORDER BY posted_at DESC LIMIT 5
            """)
            recent_comments = [dict(r) for r in cursor.fetchall()]

            return {
                "total_sniped_comments": total_sniped,
                "total_intent_replies": total_replies,
                "total_warmed_views": warmer_row["total_views"] or 0,
                "total_likes_given": warmer_row["total_likes"] or 0,
                "total_subs_given": warmer_row["total_subs"] or 0,
                "total_community_polls": total_polls or 0,
                "total_livestream_messages": total_chats or 0,
                "total_reverse_engineered_patterns": total_patterns or 0,
                "total_scouted_channels": total_scouted or 0,
                "total_comment_boosts": total_boosts or 0,
                "recent_comments": recent_comments
            }
