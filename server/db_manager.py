import os
import sqlite3
import logging
import time
import threading
from pathlib import Path

class DatabaseManager:
    """SQLite database manager for the distributed system services"""
    
    def __init__(self, db_path=None):
        """Initialize the database manager
        
        Args:
            db_path: Path to the SQLite database file. If None, a default path will be used.
        """
        if db_path is None:
            # Create a data directory in the project root if it doesn't exist
            data_dir = Path(__file__).parent.parent / 'data'
            os.makedirs(data_dir, exist_ok=True)
            db_path = data_dir / 'todo.db'
        
        self.db_path = str(db_path)
        
        # Use a connection per thread approach with a lock for safety
        self._connection_lock = threading.RLock()
        self._connection_cache = {}
        
        # Initialize the database structure
        self.initialize()
    
    def initialize(self):
        """Initialize the database and create tables if they don't exist"""
        try:
            # Create a temporary connection just for initialization
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create tasks table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                client_id TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                due_date TEXT,
                priority TEXT DEFAULT 'medium',
                completed INTEGER DEFAULT 0,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            )
            ''')
            
            # Add index for client_id for faster lookups
            cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_tasks_client_id ON tasks (client_id)
            ''')
            
            conn.commit()
            conn.close()
            logging.info(f"Database initialized successfully at {self.db_path}")
        except sqlite3.Error as e:
            logging.error(f"Database initialization error: {str(e)}")
            raise
    
    def get_connection(self):
        """Get a database connection for the current thread"""
        thread_id = threading.get_ident()
        
        with self._connection_lock:
            # Create a new connection if one doesn't exist for this thread
            if thread_id not in self._connection_cache or self._connection_cache[thread_id] is None:
                conn = sqlite3.connect(self.db_path, check_same_thread=False)
                
                # Set up connection to return dictionaries
                def dict_factory(cursor, row):
                    d = {}
                    for idx, col in enumerate(cursor.description):
                        d[col[0]] = row[idx]
                    return d
                    
                conn.row_factory = dict_factory
                self._connection_cache[thread_id] = conn
                logging.debug(f"Created new SQLite connection for thread {thread_id}")
            
            return self._connection_cache[thread_id]
    
    def close(self):
        """Close the database connection for the current thread"""
        thread_id = threading.get_ident()
        
        with self._connection_lock:
            if thread_id in self._connection_cache and self._connection_cache[thread_id] is not None:
                try:
                    self._connection_cache[thread_id].close()
                    self._connection_cache[thread_id] = None
                    logging.debug(f"Closed SQLite connection for thread {thread_id}")
                except Exception as e:
                    logging.error(f"Error closing SQLite connection: {e}")
    
    def close_all(self):
        """Close all database connections (should be called on server shutdown)"""
        with self._connection_lock:
            for thread_id, conn in list(self._connection_cache.items()):
                if conn is not None:
                    try:
                        conn.close()
                        logging.debug(f"Closed SQLite connection for thread {thread_id}")
                    except Exception as e:
                        logging.error(f"Error closing SQLite connection: {e}")
            
            # Clear the connection cache
            self._connection_cache.clear()
            logging.info("All database connections closed")
