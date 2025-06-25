"""Episodic Memory - Long-term conversation history with compression.

This module provides the EpisodicMemory class that stores and retrieves
conversation history across sessions with automatic compression when
conversations become too long.
"""

import os
import json
import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Union
from pathlib import Path
import hashlib

logger = logging.getLogger(__name__)


class EpisodicMemory:
    """Episodic Memory for long-term conversation history storage.
    
    Manages conversation history across sessions with:
    - Persistent SQLite storage
    - Automatic compression when conversations exceed token threshold
    - Semantic search capabilities
    - Temporal filtering and organization
    """
    
    def __init__(
        self,
        user_id: str = "default",
        storage_path: str = "/tmp/memory_data/episodic",
        compression_threshold: int = 1000
    ) -> None:
        """Initialize Episodic Memory.
        
        Args:
            user_id: User identifier for scoped storage
            storage_path: Path for SQLite database storage
            compression_threshold: Token threshold for automatic compression
        """
        self.user_id = user_id
        self.storage_path = Path(storage_path)
        self.compression_threshold = compression_threshold
        
        # Create storage directory
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize SQLite database
        self.db_path = self.storage_path / f"episodic_{user_id}.db"
        self._init_database()
        
        logger.info(f"EpisodicMemory initialized for user {user_id}")
    
    def _init_database(self) -> None:
        """Initialize SQLite database with conversation tables."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    user_query TEXT NOT NULL,
                    agent_response TEXT NOT NULL,
                    metadata TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    tokens INTEGER DEFAULT 0,
                    compressed BOOLEAN DEFAULT FALSE,
                    compression_summary TEXT
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS conversation_summaries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    original_conversations TEXT,
                    compression_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                    token_savings INTEGER DEFAULT 0
                )
            """)
            
            # Create indexes for efficient querying
            conn.execute("CREATE INDEX IF NOT EXISTS idx_session_id ON conversations(session_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON conversations(timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_compressed ON conversations(compressed)")
            
            conn.commit()
    
    def store_conversation(
        self,
        user_query: str,
        agent_response: str,
        metadata: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None
    ) -> int:
        """Store a conversation interaction.
        
        Args:
            user_query: User's input query
            agent_response: Agent's response
            metadata: Optional metadata about the interaction
            session_id: Session identifier (auto-generated if not provided)
            
        Returns:
            Conversation ID
        """
        if not session_id:
            session_id = self._generate_session_id()
        
        # Estimate token count
        total_text = f"{user_query} {agent_response}"
        tokens = self._estimate_tokens(total_text)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO conversations 
                (session_id, user_query, agent_response, metadata, tokens)
                VALUES (?, ?, ?, ?, ?)
            """, (
                session_id,
                user_query,
                agent_response,
                json.dumps(metadata) if metadata else None,
                tokens
            ))
            
            conversation_id = cursor.lastrowid
            conn.commit()
        
        # Check if session needs compression
        self._check_and_compress_session(session_id)
        
        logger.debug(f"Conversation stored with ID {conversation_id}")
        return conversation_id
    
    def search_conversations(
        self,
        query: str,
        limit: int = 10,
        since: Optional[datetime] = None,
        session_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Search conversations by query text.
        
        Args:
            query: Search query
            limit: Maximum number of results
            since: Only return conversations after this date
            session_id: Filter by specific session
            
        Returns:
            List of matching conversations
        """
        sql_query = """
            SELECT id, session_id, user_query, agent_response, metadata, timestamp, tokens, compressed
            FROM conversations
            WHERE (user_query LIKE ? OR agent_response LIKE ?)
        """
        params = [f"%{query}%", f"%{query}%"]
        
        if since:
            sql_query += " AND timestamp >= ?"
            params.append(since.isoformat())
        
        if session_id:
            sql_query += " AND session_id = ?"
            params.append(session_id)
        
        sql_query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(sql_query, params)
            
            results = []
            for row in cursor.fetchall():
                result = dict(row)
                if result['metadata']:
                    result['metadata'] = json.loads(result['metadata'])
                results.append(result)
        
        logger.debug(f"Found {len(results)} conversations for query: {query}")
        return results
    
    def get_session_conversations(
        self,
        session_id: str,
        include_compressed: bool = True
    ) -> List[Dict[str, Any]]:
        """Get all conversations for a specific session.
        
        Args:
            session_id: Session identifier
            include_compressed: Whether to include compressed conversations
            
        Returns:
            List of conversations in chronological order
        """
        sql_query = """
            SELECT id, session_id, user_query, agent_response, metadata, timestamp, tokens, compressed
            FROM conversations
            WHERE session_id = ?
        """
        params = [session_id]
        
        if not include_compressed:
            sql_query += " AND compressed = FALSE"
        
        sql_query += " ORDER BY timestamp ASC"
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(sql_query, params)
            
            results = []
            for row in cursor.fetchall():
                result = dict(row)
                if result['metadata']:
                    result['metadata'] = json.loads(result['metadata'])
                results.append(result)
        
        return results
    
    def get_recent_conversations(
        self,
        hours: int = 24,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get recent conversations within specified time window.
        
        Args:
            hours: Number of hours to look back
            limit: Maximum number of conversations
            
        Returns:
            List of recent conversations
        """
        since = datetime.now() - timedelta(hours=hours)
        return self.search_conversations("", limit=limit, since=since)
    
    def _check_and_compress_session(self, session_id: str) -> None:
        """Check if session needs compression and compress if necessary.
        
        Args:
            session_id: Session to check for compression
        """
        # Get total tokens for uncompressed conversations in session
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT SUM(tokens) as total_tokens, COUNT(*) as conversation_count
                FROM conversations
                WHERE session_id = ? AND compressed = FALSE
            """, (session_id,))
            
            result = cursor.fetchone()
            total_tokens = result[0] or 0
            conversation_count = result[1] or 0
        
        # Compress if over threshold and has multiple conversations
        if total_tokens > self.compression_threshold and conversation_count > 1:
            self._compress_session(session_id)
    
    def _compress_session(self, session_id: str) -> None:
        """Compress conversations in a session.
        
        Args:
            session_id: Session to compress
        """
        # Get uncompressed conversations
        conversations = self.get_session_conversations(session_id, include_compressed=False)
        
        if len(conversations) <= 1:
            return  # Nothing to compress
        
        # Keep the most recent conversation, compress the rest
        to_compress = conversations[:-1]  # All except the last one
        
        # Create compression summary
        summary_text = self._create_compression_summary(to_compress)
        
        # Store compression summary
        with sqlite3.connect(self.db_path) as conn:
            # Calculate token savings
            original_tokens = sum(conv['tokens'] for conv in to_compress)
            summary_tokens = self._estimate_tokens(summary_text)
            token_savings = original_tokens - summary_tokens
            
            # Insert summary
            conn.execute("""
                INSERT INTO conversation_summaries
                (session_id, summary, original_conversations, token_savings)
                VALUES (?, ?, ?, ?)
            """, (
                session_id,
                summary_text,
                json.dumps([conv['id'] for conv in to_compress]),
                token_savings
            ))
            
            # Mark conversations as compressed
            conversation_ids = [conv['id'] for conv in to_compress]
            placeholders = ','.join('?' * len(conversation_ids))
            conn.execute(f"""
                UPDATE conversations
                SET compressed = TRUE, compression_summary = ?
                WHERE id IN ({placeholders})
            """, [summary_text] + conversation_ids)
            
            conn.commit()
        
        logger.info(f"Compressed {len(to_compress)} conversations in session {session_id}, saved {token_savings} tokens")
    
    def _create_compression_summary(self, conversations: List[Dict[str, Any]]) -> str:
        """Create a summary of conversations for compression.
        
        Args:
            conversations: List of conversations to summarize
            
        Returns:
            Compressed summary text
        """
        # Simple summarization - extract key topics and outcomes
        topics = set()
        key_points = []
        
        for conv in conversations:
            # Extract potential topics from queries
            query_words = conv['user_query'].lower().split()
            topics.update(word for word in query_words if len(word) > 4)
            
            # Extract key points from responses (first sentence)
            response_sentences = conv['agent_response'].split('.')
            if response_sentences:
                key_points.append(response_sentences[0].strip())
        
        # Create summary
        summary_parts = []
        if topics:
            summary_parts.append(f"Topics discussed: {', '.join(list(topics)[:5])}")
        if key_points:
            summary_parts.append(f"Key outcomes: {' | '.join(key_points[:3])}")
        
        summary = ". ".join(summary_parts)
        return summary if summary else "Conversation history compressed"
    
    def _generate_session_id(self) -> str:
        """Generate a session ID based on current time.
        
        Returns:
            Session ID string
        """
        timestamp = datetime.now().isoformat()
        return hashlib.md5(timestamp.encode()).hexdigest()[:8]
    
    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count for text.
        
        Args:
            text: Text to estimate tokens for
            
        Returns:
            Estimated token count
        """
        # Simple estimation: ~4 characters per token
        return len(text) // 4
    
    def get_stats(self) -> Dict[str, Any]:
        """Get episodic memory statistics.
        
        Returns:
            Dictionary with memory statistics
        """
        with sqlite3.connect(self.db_path) as conn:
            # Total conversations
            cursor = conn.execute("SELECT COUNT(*) FROM conversations")
            total_conversations = cursor.fetchone()[0]
            
            # Compressed conversations
            cursor = conn.execute("SELECT COUNT(*) FROM conversations WHERE compressed = TRUE")
            compressed_conversations = cursor.fetchone()[0]
            
            # Total tokens
            cursor = conn.execute("SELECT SUM(tokens) FROM conversations")
            total_tokens = cursor.fetchone()[0] or 0
            
            # Token savings from compression
            cursor = conn.execute("SELECT SUM(token_savings) FROM conversation_summaries")
            token_savings = cursor.fetchone()[0] or 0
            
            # Unique sessions
            cursor = conn.execute("SELECT COUNT(DISTINCT session_id) FROM conversations")
            unique_sessions = cursor.fetchone()[0]
        
        return {
            'total_conversations': total_conversations,
            'compressed_conversations': compressed_conversations,
            'compression_ratio': compressed_conversations / max(total_conversations, 1),
            'total_tokens': total_tokens,
            'token_savings': token_savings,
            'unique_sessions': unique_sessions,
            'compression_threshold': self.compression_threshold
        }
    
    def clear(self) -> bool:
        """Clear all episodic memory data.
        
        Returns:
            True if successful
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM conversations")
                conn.execute("DELETE FROM conversation_summaries")
                conn.commit()
            
            logger.info("Episodic memory cleared")
            return True
        except Exception as e:
            logger.error(f"Failed to clear episodic memory: {e}")
            return False
    
    def export_conversations(
        self,
        output_path: str,
        format_type: str = "json",
        session_id: Optional[str] = None
    ) -> bool:
        """Export conversations to file.
        
        Args:
            output_path: Path for output file
            format_type: Export format (json, csv)
            session_id: Optional session filter
            
        Returns:
            True if successful
        """
        try:
            if session_id:
                conversations = self.get_session_conversations(session_id)
            else:
                conversations = self.search_conversations("", limit=10000)
            
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            if format_type.lower() == "json":
                with open(output_file, 'w') as f:
                    json.dump(conversations, f, indent=2, default=str)
            elif format_type.lower() == "csv":
                import csv
                with open(output_file, 'w', newline='') as f:
                    if conversations:
                        writer = csv.DictWriter(f, fieldnames=conversations[0].keys())
                        writer.writeheader()
                        writer.writerows(conversations)
            
            logger.info(f"Exported {len(conversations)} conversations to {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export conversations: {e}")
            return False 