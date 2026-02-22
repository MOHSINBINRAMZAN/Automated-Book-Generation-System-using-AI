"""
Database Module for the Automated Book Generation System.
Supports SQLite (default) and Supabase.
"""

import sqlite3
import json
from datetime import datetime
from typing import Optional, List, Dict, Any
from abc import ABC, abstractmethod

import config

# =============================================================================
# ABSTRACT DATABASE INTERFACE
# =============================================================================

class DatabaseInterface(ABC):
    """Abstract base class for database operations."""
    
    @abstractmethod
    def initialize(self):
        """Initialize the database and create tables."""
        pass
    
    @abstractmethod
    def create_book(self, title: str, notes_on_outline_before: str = "") -> int:
        """Create a new book entry."""
        pass
    
    @abstractmethod
    def get_book(self, book_id: int) -> Optional[Dict[str, Any]]:
        """Get a book by ID."""
        pass
    
    @abstractmethod
    def get_all_books(self) -> List[Dict[str, Any]]:
        """Get all books."""
        pass
    
    @abstractmethod
    def update_book(self, book_id: int, **kwargs) -> bool:
        """Update book fields."""
        pass
    
    @abstractmethod
    def create_chapter(self, book_id: int, chapter_number: int, title: str) -> int:
        """Create a new chapter."""
        pass
    
    @abstractmethod
    def get_chapter(self, chapter_id: int) -> Optional[Dict[str, Any]]:
        """Get a chapter by ID."""
        pass
    
    @abstractmethod
    def get_chapters_by_book(self, book_id: int) -> List[Dict[str, Any]]:
        """Get all chapters for a book."""
        pass
    
    @abstractmethod
    def update_chapter(self, chapter_id: int, **kwargs) -> bool:
        """Update chapter fields."""
        pass
    
    @abstractmethod
    def log_event(self, book_id: int, event_type: str, message: str, data: Dict = None):
        """Log an event."""
        pass
    
    @abstractmethod
    def get_logs(self, book_id: int = None) -> List[Dict[str, Any]]:
        """Get logs, optionally filtered by book_id."""
        pass


# =============================================================================
# SQLITE IMPLEMENTATION
# =============================================================================

class SQLiteDatabase(DatabaseInterface):
    """SQLite database implementation."""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or config.SQLITE_DB_PATH
        self.conn = None
        
    def _get_connection(self):
        """Get database connection."""
        if self.conn is None:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row
        return self.conn
    
    def _execute(self, query: str, params: tuple = ()):
        """Execute a query and commit."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()
        return cursor
    
    def _fetch_one(self, query: str, params: tuple = ()) -> Optional[Dict]:
        """Fetch one result as dictionary."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def _fetch_all(self, query: str, params: tuple = ()) -> List[Dict]:
        """Fetch all results as list of dictionaries."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    
    def initialize(self):
        """Create database tables."""
        # Books table
        self._execute("""
            CREATE TABLE IF NOT EXISTS books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                notes_on_outline_before TEXT DEFAULT '',
                outline TEXT DEFAULT '',
                notes_on_outline_after TEXT DEFAULT '',
                status_outline_notes TEXT DEFAULT 'no' CHECK(status_outline_notes IN ('yes', 'no', 'no_notes_needed')),
                chapter_notes_status TEXT DEFAULT 'no' CHECK(chapter_notes_status IN ('yes', 'no', 'no_notes_needed')),
                final_review_notes_status TEXT DEFAULT 'no' CHECK(final_review_notes_status IN ('yes', 'no', 'no_notes_needed')),
                final_review_notes TEXT DEFAULT '',
                book_output_status TEXT DEFAULT 'pending' CHECK(book_output_status IN ('pending', 'in_progress', 'paused', 'completed', 'error')),
                output_file_path TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Chapters table
        self._execute("""
            CREATE TABLE IF NOT EXISTS chapters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                book_id INTEGER NOT NULL,
                chapter_number INTEGER NOT NULL,
                title TEXT NOT NULL,
                content TEXT DEFAULT '',
                summary TEXT DEFAULT '',
                chapter_notes TEXT DEFAULT '',
                status TEXT DEFAULT 'pending' CHECK(status IN ('pending', 'generating', 'review', 'approved', 'regenerating')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE
            )
        """)
        
        # Event logs table
        self._execute("""
            CREATE TABLE IF NOT EXISTS event_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                book_id INTEGER,
                event_type TEXT NOT NULL,
                message TEXT NOT NULL,
                data TEXT DEFAULT '{}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE
            )
        """)
        
        # Outline drafts table (for storing multiple outline versions)
        self._execute("""
            CREATE TABLE IF NOT EXISTS outline_drafts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                book_id INTEGER NOT NULL,
                outline_content TEXT NOT NULL,
                notes_used TEXT DEFAULT '',
                version INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE
            )
        """)
        
        print("✓ Database initialized successfully")
        return True
    
    def create_book(self, title: str, notes_on_outline_before: str = "") -> int:
        """Create a new book entry."""
        cursor = self._execute(
            "INSERT INTO books (title, notes_on_outline_before) VALUES (?, ?)",
            (title, notes_on_outline_before)
        )
        return cursor.lastrowid
    
    def get_book(self, book_id: int) -> Optional[Dict[str, Any]]:
        """Get a book by ID."""
        return self._fetch_one("SELECT * FROM books WHERE id = ?", (book_id,))
    
    def get_all_books(self) -> List[Dict[str, Any]]:
        """Get all books."""
        return self._fetch_all("SELECT * FROM books ORDER BY created_at DESC")
    
    def update_book(self, book_id: int, **kwargs) -> bool:
        """Update book fields."""
        if not kwargs:
            return False
        
        # Add updated_at timestamp
        kwargs['updated_at'] = datetime.now().isoformat()
        
        set_clause = ", ".join([f"{key} = ?" for key in kwargs.keys()])
        values = list(kwargs.values()) + [book_id]
        
        self._execute(f"UPDATE books SET {set_clause} WHERE id = ?", tuple(values))
        return True
    
    def create_chapter(self, book_id: int, chapter_number: int, title: str) -> int:
        """Create a new chapter."""
        cursor = self._execute(
            "INSERT INTO chapters (book_id, chapter_number, title) VALUES (?, ?, ?)",
            (book_id, chapter_number, title)
        )
        return cursor.lastrowid
    
    def get_chapter(self, chapter_id: int) -> Optional[Dict[str, Any]]:
        """Get a chapter by ID."""
        return self._fetch_one("SELECT * FROM chapters WHERE id = ?", (chapter_id,))
    
    def get_chapters_by_book(self, book_id: int) -> List[Dict[str, Any]]:
        """Get all chapters for a book ordered by chapter number."""
        return self._fetch_all(
            "SELECT * FROM chapters WHERE book_id = ? ORDER BY chapter_number",
            (book_id,)
        )
    
    def update_chapter(self, chapter_id: int, **kwargs) -> bool:
        """Update chapter fields."""
        if not kwargs:
            return False
        
        kwargs['updated_at'] = datetime.now().isoformat()
        set_clause = ", ".join([f"{key} = ?" for key in kwargs.keys()])
        values = list(kwargs.values()) + [chapter_id]
        
        self._execute(f"UPDATE chapters SET {set_clause} WHERE id = ?", tuple(values))
        return True
    
    def save_outline_draft(self, book_id: int, outline_content: str, notes_used: str = "") -> int:
        """Save an outline draft version."""
        # Get current max version
        result = self._fetch_one(
            "SELECT MAX(version) as max_version FROM outline_drafts WHERE book_id = ?",
            (book_id,)
        )
        version = (result['max_version'] or 0) + 1 if result else 1
        
        cursor = self._execute(
            "INSERT INTO outline_drafts (book_id, outline_content, notes_used, version) VALUES (?, ?, ?, ?)",
            (book_id, outline_content, notes_used, version)
        )
        return cursor.lastrowid
    
    def get_outline_drafts(self, book_id: int) -> List[Dict[str, Any]]:
        """Get all outline drafts for a book."""
        return self._fetch_all(
            "SELECT * FROM outline_drafts WHERE book_id = ? ORDER BY version DESC",
            (book_id,)
        )
    
    def log_event(self, book_id: int, event_type: str, message: str, data: Dict = None):
        """Log an event."""
        self._execute(
            "INSERT INTO event_logs (book_id, event_type, message, data) VALUES (?, ?, ?, ?)",
            (book_id, event_type, message, json.dumps(data or {}))
        )
    
    def get_logs(self, book_id: int = None) -> List[Dict[str, Any]]:
        """Get logs, optionally filtered by book_id."""
        if book_id:
            return self._fetch_all(
                "SELECT * FROM event_logs WHERE book_id = ? ORDER BY created_at DESC",
                (book_id,)
            )
        return self._fetch_all("SELECT * FROM event_logs ORDER BY created_at DESC")
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None


# =============================================================================
# SUPABASE IMPLEMENTATION
# =============================================================================

class SupabaseDatabase(DatabaseInterface):
    """Supabase database implementation."""
    
    def __init__(self, url: str = None, key: str = None):
        self.url = url or config.SUPABASE_URL
        self.key = key or config.SUPABASE_KEY
        self.client = None
        
    def _get_client(self):
        """Get Supabase client."""
        if self.client is None:
            try:
                from supabase import create_client
                self.client = create_client(self.url, self.key)
            except ImportError:
                raise ImportError("Please install supabase: pip install supabase")
        return self.client
    
    def initialize(self):
        """
        Initialize Supabase tables.
        Note: Tables should be created manually in Supabase Dashboard or via migrations.
        This method verifies the connection.
        """
        try:
            client = self._get_client()
            # Test connection by fetching from books table
            client.table('books').select('id').limit(1).execute()
            print("✓ Supabase connection verified")
            return True
        except Exception as e:
            print(f"✗ Supabase connection failed: {e}")
            print("Please create the required tables in Supabase Dashboard.")
            return False
    
    def create_book(self, title: str, notes_on_outline_before: str = "") -> int:
        """Create a new book entry."""
        client = self._get_client()
        result = client.table('books').insert({
            'title': title,
            'notes_on_outline_before': notes_on_outline_before
        }).execute()
        return result.data[0]['id'] if result.data else None
    
    def get_book(self, book_id: int) -> Optional[Dict[str, Any]]:
        """Get a book by ID."""
        client = self._get_client()
        result = client.table('books').select('*').eq('id', book_id).execute()
        return result.data[0] if result.data else None
    
    def get_all_books(self) -> List[Dict[str, Any]]:
        """Get all books."""
        client = self._get_client()
        result = client.table('books').select('*').order('created_at', desc=True).execute()
        return result.data or []
    
    def update_book(self, book_id: int, **kwargs) -> bool:
        """Update book fields."""
        if not kwargs:
            return False
        client = self._get_client()
        kwargs['updated_at'] = datetime.now().isoformat()
        client.table('books').update(kwargs).eq('id', book_id).execute()
        return True
    
    def create_chapter(self, book_id: int, chapter_number: int, title: str) -> int:
        """Create a new chapter."""
        client = self._get_client()
        result = client.table('chapters').insert({
            'book_id': book_id,
            'chapter_number': chapter_number,
            'title': title
        }).execute()
        return result.data[0]['id'] if result.data else None
    
    def get_chapter(self, chapter_id: int) -> Optional[Dict[str, Any]]:
        """Get a chapter by ID."""
        client = self._get_client()
        result = client.table('chapters').select('*').eq('id', chapter_id).execute()
        return result.data[0] if result.data else None
    
    def get_chapters_by_book(self, book_id: int) -> List[Dict[str, Any]]:
        """Get all chapters for a book."""
        client = self._get_client()
        result = client.table('chapters').select('*').eq('book_id', book_id).order('chapter_number').execute()
        return result.data or []
    
    def update_chapter(self, chapter_id: int, **kwargs) -> bool:
        """Update chapter fields."""
        if not kwargs:
            return False
        client = self._get_client()
        kwargs['updated_at'] = datetime.now().isoformat()
        client.table('chapters').update(kwargs).eq('id', chapter_id).execute()
        return True
    
    def save_outline_draft(self, book_id: int, outline_content: str, notes_used: str = "") -> int:
        """Save an outline draft version."""
        client = self._get_client()
        # Get current max version
        result = client.table('outline_drafts').select('version').eq('book_id', book_id).order('version', desc=True).limit(1).execute()
        version = (result.data[0]['version'] + 1) if result.data else 1
        
        result = client.table('outline_drafts').insert({
            'book_id': book_id,
            'outline_content': outline_content,
            'notes_used': notes_used,
            'version': version
        }).execute()
        return result.data[0]['id'] if result.data else None
    
    def get_outline_drafts(self, book_id: int) -> List[Dict[str, Any]]:
        """Get all outline drafts for a book."""
        client = self._get_client()
        result = client.table('outline_drafts').select('*').eq('book_id', book_id).order('version', desc=True).execute()
        return result.data or []
    
    def log_event(self, book_id: int, event_type: str, message: str, data: Dict = None):
        """Log an event."""
        client = self._get_client()
        client.table('event_logs').insert({
            'book_id': book_id,
            'event_type': event_type,
            'message': message,
            'data': json.dumps(data or {})
        }).execute()
    
    def get_logs(self, book_id: int = None) -> List[Dict[str, Any]]:
        """Get logs, optionally filtered by book_id."""
        client = self._get_client()
        query = client.table('event_logs').select('*')
        if book_id:
            query = query.eq('book_id', book_id)
        result = query.order('created_at', desc=True).execute()
        return result.data or []
    
    def close(self):
        """Close client (no-op for Supabase)."""
        pass


# =============================================================================
# DATABASE FACTORY
# =============================================================================

def get_database() -> DatabaseInterface:
    """Factory function to get the appropriate database instance."""
    if config.DATABASE_TYPE == "supabase":
        return SupabaseDatabase()
    else:
        return SQLiteDatabase()


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def init_database():
    """Initialize the database."""
    db = get_database()
    db.initialize()
    return db
