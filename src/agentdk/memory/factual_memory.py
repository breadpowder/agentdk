"""Factual Memory implementation for AgentDK.

Factual Memory provides persistent storage for user preferences, settings, and structured knowledge.
It supports mutable facts with conflict resolution and categorical organization.
"""

import asyncio
import sqlite3
import uuid
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import threading

from .base import BaseMemory, MemoryEntry, MemoryConfig
from ..core.logging_config import get_logger


class FactualMemory(BaseMemory):
    """Factual Memory for persistent user preferences and structured knowledge.
    
    Features:
    - Persistent SQLite storage for user preferences
    - Categorical organization (ui, agent, system)
    - Mutable facts with conflict resolution
    - User scoping for multi-user support
    - Type validation and schema enforcement
    """
    
    def __init__(self, user_id: Optional[str] = None, config: Optional[MemoryConfig] = None):
        """Initialize Factual Memory.
        
        Args:
            user_id: Optional user identifier for scoping
            config: Optional memory configuration
        """
        super().__init__(user_id, config.to_dict() if config else None)
        self.logger = get_logger()
        self.memory_config = config or MemoryConfig()
        
        # Database setup
        self.db_path = Path(self.memory_config.storage_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._db_lock = threading.Lock()
        
        # User scoping
        self.effective_user_id = user_id or self.memory_config.default_user_id
        
        self.logger.info(f"FactualMemory initialized for user {self.effective_user_id}")
    
    async def initialize(self) -> None:
        """Initialize factual memory system and database."""
        if self._initialized:
            return
        
        self.logger.info("Initializing FactualMemory database")
        
        # Create database tables
        await self._create_tables()
        
        self._initialized = True
        self.logger.info("FactualMemory initialization complete")
    
    async def _create_tables(self) -> None:
        """Create necessary database tables."""
        with self._db_lock:
            conn = sqlite3.connect(self.db_path)
            try:
                cursor = conn.cursor()
                
                # Preferences table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS preferences (
                        id TEXT PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        category TEXT NOT NULL,
                        key TEXT NOT NULL,
                        value TEXT NOT NULL,
                        value_type TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        metadata TEXT,
                        UNIQUE(user_id, category, key)
                    )
                """)
                
                # Facts table for structured knowledge
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS facts (
                        id TEXT PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        content TEXT NOT NULL,
                        fact_type TEXT,
                        confidence REAL DEFAULT 1.0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        metadata TEXT
                    )
                """)
                
                # Create indexes for performance
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_preferences_user_category ON preferences(user_id, category)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_facts_user_type ON facts(user_id, fact_type)")
                
                conn.commit()
                self.logger.debug("Database tables created successfully")
                
            except Exception as e:
                self.logger.error(f"Failed to create database tables: {e}")
                raise
            finally:
                conn.close()
    
    async def store(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Store factual content in memory.
        
        Args:
            content: The factual content to store
            metadata: Optional metadata (fact_type, confidence, etc.)
            
        Returns:
            Unique identifier for the stored fact
        """
        fact_id = str(uuid.uuid4())
        metadata = metadata or {}
        
        with self._db_lock:
            conn = sqlite3.connect(self.db_path)
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO facts (id, user_id, content, fact_type, confidence, metadata)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    fact_id,
                    self.effective_user_id,
                    content,
                    metadata.get('fact_type', 'general'),
                    metadata.get('confidence', 1.0),
                    json.dumps(metadata)
                ))
                conn.commit()
                
                self.logger.debug(f"Stored fact in FactualMemory: {fact_id}")
                return fact_id
                
            except Exception as e:
                self.logger.error(f"Failed to store fact: {e}")
                raise
            finally:
                conn.close()
    
    async def retrieve(self, query: str, limit: int = 10) -> List[MemoryEntry]:
        """Retrieve factual content from memory.
        
        Args:
            query: Search query or fact type
            limit: Maximum number of entries to return
            
        Returns:
            List of matching memory entries
        """
        with self._db_lock:
            conn = sqlite3.connect(self.db_path)
            try:
                cursor = conn.cursor()
                
                # Search in content and fact_type
                cursor.execute("""
                    SELECT id, content, created_at, fact_type, confidence, metadata
                    FROM facts
                    WHERE user_id = ? AND (content LIKE ? OR fact_type LIKE ?)
                    ORDER BY updated_at DESC
                    LIMIT ?
                """, (self.effective_user_id, f'%{query}%', f'%{query}%', limit))
                
                entries = []
                for row in cursor.fetchall():
                    metadata = json.loads(row[5]) if row[5] else {}
                    metadata.update({
                        'fact_type': row[3],
                        'confidence': row[4]
                    })
                    
                    entry = MemoryEntry(
                        id=row[0],
                        content=row[1],
                        timestamp=datetime.fromisoformat(row[2]),
                        metadata=metadata,
                        user_id=self.effective_user_id
                    )
                    entries.append(entry)
                
                return entries
                
            except Exception as e:
                self.logger.error(f"Failed to retrieve facts: {e}")
                return []
            finally:
                conn.close()
    
    async def update(self, entry_id: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Update existing fact entry.
        
        Args:
            entry_id: Identifier of the entry to update
            content: New content
            metadata: Optional new metadata
            
        Returns:
            True if update was successful, False otherwise
        """
        with self._db_lock:
            conn = sqlite3.connect(self.db_path)
            try:
                cursor = conn.cursor()
                
                # Check if fact exists and belongs to user
                cursor.execute("SELECT id FROM facts WHERE id = ? AND user_id = ?", 
                             (entry_id, self.effective_user_id))
                if not cursor.fetchone():
                    self.logger.warning(f"Fact not found or access denied: {entry_id}")
                    return False
                
                # Update fact
                metadata = metadata or {}
                cursor.execute("""
                    UPDATE facts 
                    SET content = ?, fact_type = ?, confidence = ?, metadata = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ? AND user_id = ?
                """, (
                    content,
                    metadata.get('fact_type', 'general'),
                    metadata.get('confidence', 1.0),
                    json.dumps(metadata),
                    entry_id,
                    self.effective_user_id
                ))
                
                conn.commit()
                success = cursor.rowcount > 0
                
                if success:
                    self.logger.debug(f"Updated fact: {entry_id}")
                else:
                    self.logger.warning(f"Failed to update fact: {entry_id}")
                
                return success
                
            except Exception as e:
                self.logger.error(f"Failed to update fact: {e}")
                return False
            finally:
                conn.close()
    
    async def delete(self, entry_id: str) -> bool:
        """Delete fact entry.
        
        Args:
            entry_id: Identifier of the entry to delete
            
        Returns:
            True if deletion was successful, False otherwise
        """
        with self._db_lock:
            conn = sqlite3.connect(self.db_path)
            try:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM facts WHERE id = ? AND user_id = ?", 
                             (entry_id, self.effective_user_id))
                conn.commit()
                
                success = cursor.rowcount > 0
                if success:
                    self.logger.debug(f"Deleted fact: {entry_id}")
                else:
                    self.logger.warning(f"Fact not found for deletion: {entry_id}")
                
                return success
                
            except Exception as e:
                self.logger.error(f"Failed to delete fact: {e}")
                return False
            finally:
                conn.close()
    
    async def clear(self, confirm: bool = False) -> bool:
        """Clear all factual memory entries.
        
        Args:
            confirm: Safety confirmation flag
            
        Returns:
            True if clearing was successful, False otherwise
        """
        if not confirm:
            self.logger.warning("Clear operation requires confirmation")
            return False
        
        with self._db_lock:
            conn = sqlite3.connect(self.db_path)
            try:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM facts WHERE user_id = ?", (self.effective_user_id,))
                cursor.execute("DELETE FROM preferences WHERE user_id = ?", (self.effective_user_id,))
                conn.commit()
                
                self.logger.info(f"Cleared all factual memory for user {self.effective_user_id}")
                return True
                
            except Exception as e:
                self.logger.error(f"Failed to clear factual memory: {e}")
                return False
            finally:
                conn.close()
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get factual memory statistics.
        
        Returns:
            Dictionary containing memory usage statistics
        """
        with self._db_lock:
            conn = sqlite3.connect(self.db_path)
            try:
                cursor = conn.cursor()
                
                # Count facts
                cursor.execute("SELECT COUNT(*) FROM facts WHERE user_id = ?", (self.effective_user_id,))
                facts_count = cursor.fetchone()[0]
                
                # Count preferences
                cursor.execute("SELECT COUNT(*) FROM preferences WHERE user_id = ?", (self.effective_user_id,))
                preferences_count = cursor.fetchone()[0]
                
                # Get fact types distribution
                cursor.execute("""
                    SELECT fact_type, COUNT(*) 
                    FROM facts 
                    WHERE user_id = ? 
                    GROUP BY fact_type
                """, (self.effective_user_id,))
                fact_types = dict(cursor.fetchall())
                
                # Get preference categories distribution
                cursor.execute("""
                    SELECT category, COUNT(*) 
                    FROM preferences 
                    WHERE user_id = ? 
                    GROUP BY category
                """, (self.effective_user_id,))
                preference_categories = dict(cursor.fetchall())
                
                return {
                    'type': 'factual_memory',
                    'facts_count': facts_count,
                    'preferences_count': preferences_count,
                    'fact_types_distribution': fact_types,
                    'preference_categories_distribution': preference_categories,
                    'user_id': self.effective_user_id,
                    'database_path': str(self.db_path)
                }
                
            except Exception as e:
                self.logger.error(f"Failed to get factual memory stats: {e}")
                return {'type': 'factual_memory', 'error': str(e)}
            finally:
                conn.close()
    
    # User Preference Methods
    
    async def set_preference(self, category: str, key: str, value: Any, value_type: Optional[str] = None) -> bool:
        """Set user preference.
        
        Args:
            category: Preference category (ui, agent, system)
            key: Preference key
            value: Preference value
            value_type: Optional type specification
            
        Returns:
            True if preference was set successfully
        """
        if category not in self.memory_config.preference_categories:
            self.logger.warning(f"Invalid preference category: {category}")
            return False
        
        # Determine value type
        if value_type is None:
            value_type = type(value).__name__
        
        # Serialize value
        if isinstance(value, (dict, list)):
            serialized_value = json.dumps(value)
        else:
            serialized_value = str(value)
        
        preference_id = str(uuid.uuid4())
        
        with self._db_lock:
            conn = sqlite3.connect(self.db_path)
            try:
                cursor = conn.cursor()
                
                # Use INSERT OR REPLACE for upsert behavior
                cursor.execute("""
                    INSERT OR REPLACE INTO preferences 
                    (id, user_id, category, key, value, value_type, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (preference_id, self.effective_user_id, category, key, serialized_value, value_type))
                
                conn.commit()
                
                self.logger.debug(f"Set preference: {category}.{key} = {value}")
                return True
                
            except Exception as e:
                self.logger.error(f"Failed to set preference: {e}")
                return False
            finally:
                conn.close()
    
    async def get_preference(self, category: str, key: str, default: Any = None) -> Any:
        """Get user preference.
        
        Args:
            category: Preference category
            key: Preference key
            default: Default value if preference not found
            
        Returns:
            Preference value or default
        """
        with self._db_lock:
            conn = sqlite3.connect(self.db_path)
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT value, value_type 
                    FROM preferences 
                    WHERE user_id = ? AND category = ? AND key = ?
                """, (self.effective_user_id, category, key))
                
                result = cursor.fetchone()
                if not result:
                    return default
                
                value, value_type = result
                
                # Deserialize value based on type
                if value_type in ('dict', 'list'):
                    return json.loads(value)
                elif value_type == 'int':
                    return int(value)
                elif value_type == 'float':
                    return float(value)
                elif value_type == 'bool':
                    return value.lower() == 'true'
                else:
                    return value
                
            except Exception as e:
                self.logger.error(f"Failed to get preference: {e}")
                return default
            finally:
                conn.close()
    
    async def list_preferences(self, category: Optional[str] = None) -> Dict[str, Any]:
        """List user preferences.
        
        Args:
            category: Optional category filter
            
        Returns:
            Dictionary of preferences
        """
        with self._db_lock:
            conn = sqlite3.connect(self.db_path)
            try:
                cursor = conn.cursor()
                
                if category:
                    cursor.execute("""
                        SELECT category, key, value, value_type 
                        FROM preferences 
                        WHERE user_id = ? AND category = ?
                        ORDER BY category, key
                    """, (self.effective_user_id, category))
                else:
                    cursor.execute("""
                        SELECT category, key, value, value_type 
                        FROM preferences 
                        WHERE user_id = ?
                        ORDER BY category, key
                    """, (self.effective_user_id,))
                
                preferences = {}
                for row in cursor.fetchall():
                    cat, key, value, value_type = row
                    
                    if cat not in preferences:
                        preferences[cat] = {}
                    
                    # Deserialize value
                    if value_type in ('dict', 'list'):
                        preferences[cat][key] = json.loads(value)
                    elif value_type == 'int':
                        preferences[cat][key] = int(value)
                    elif value_type == 'float':
                        preferences[cat][key] = float(value)
                    elif value_type == 'bool':
                        preferences[cat][key] = value.lower() == 'true'
                    else:
                        preferences[cat][key] = value
                
                return preferences
                
            except Exception as e:
                self.logger.error(f"Failed to list preferences: {e}")
                return {}
            finally:
                conn.close()
    
    async def delete_preference(self, category: str, key: str) -> bool:
        """Delete user preference.
        
        Args:
            category: Preference category
            key: Preference key
            
        Returns:
            True if preference was deleted successfully
        """
        with self._db_lock:
            conn = sqlite3.connect(self.db_path)
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    DELETE FROM preferences 
                    WHERE user_id = ? AND category = ? AND key = ?
                """, (self.effective_user_id, category, key))
                
                conn.commit()
                success = cursor.rowcount > 0
                
                if success:
                    self.logger.debug(f"Deleted preference: {category}.{key}")
                else:
                    self.logger.warning(f"Preference not found: {category}.{key}")
                
                return success
                
            except Exception as e:
                self.logger.error(f"Failed to delete preference: {e}")
                return False
            finally:
                conn.close()
