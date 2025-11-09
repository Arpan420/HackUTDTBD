"""PostgreSQL database layer for conversation agent."""

import os
from typing import List, Dict, Any, Optional
from datetime import datetime
from dotenv import load_dotenv

try:
    import psycopg2
    from psycopg2 import pool, sql
    from psycopg2.extras import RealDictCursor
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False

load_dotenv()


class DatabaseManager:
    """Manages PostgreSQL database connections and operations."""
    
    def __init__(self, database_url: Optional[str] = None):
        """Initialize database manager.
        
        Args:
            database_url: PostgreSQL connection string. If None, reads from DATABASE_URL env var.
        """
        if not PSYCOPG2_AVAILABLE:
            raise ImportError(
                "psycopg2-binary is not installed. "
                "Install it with: pip install psycopg2-binary"
            )
        
        self.database_url = database_url or os.getenv("DATABASE_URL")
        if not self.database_url:
            raise ValueError(
                "DATABASE_URL not found in environment variables or .env file. "
                "Set DATABASE_URL=postgresql://user:password@localhost:5432/dbname"
            )
        
        self.connection_pool: Optional[pool.ThreadedConnectionPool] = None
        self._initialize_pool()
    
    def _initialize_pool(self) -> None:
        """Initialize connection pool."""
        try:
            # Parse connection string
            self.connection_pool = pool.ThreadedConnectionPool(
                minconn=1,
                maxconn=5,
                dsn=self.database_url
            )
        except Exception as e:
            raise ConnectionError(f"Failed to create database connection pool: {e}")
    
    def _get_connection(self):
        """Get a connection from the pool."""
        if not self.connection_pool:
            self._initialize_pool()
        return self.connection_pool.getconn()
    
    def _return_connection(self, conn):
        """Return a connection to the pool."""
        if self.connection_pool:
            self.connection_pool.putconn(conn)
    
    def initialize_schema(self) -> None:
        """Initialize database schema by running migration SQL."""
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                # Read and execute migration SQL
                migration_path = os.path.join(
                    os.path.dirname(__file__),
                    "migrations",
                    "init_schema.sql"
                )
                with open(migration_path, 'r') as f:
                    migration_sql = f.read()
                cur.execute(migration_sql)
                conn.commit()
        except Exception as e:
            conn.rollback()
            raise RuntimeError(f"Failed to initialize schema: {e}")
        finally:
            self._return_connection(conn)
    
    # Memory operations
    def add_memory(
        self,
        memory_text: str,
        person_id: Optional[str] = None,
        context: Optional[str] = None,
        conversation_id: Optional[str] = None
    ) -> int:
        """Add a memory to the database.
        
        Args:
            memory_text: The memory content
            person_id: Optional person identifier
            context: Optional context about the memory
            conversation_id: Optional conversation ID where memory was created
            
        Returns:
            ID of the created memory
        """
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO person_memories (person_id, memory_text, context, conversation_id)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id
                    """,
                    (person_id, memory_text, context, conversation_id)
                )
                memory_id = cur.fetchone()[0]
                conn.commit()
                return memory_id
        except Exception as e:
            conn.rollback()
            raise RuntimeError(f"Failed to add memory: {e}")
        finally:
            self._return_connection(conn)
    
    def get_memories_for_person(self, person_id: str) -> List[Dict[str, Any]]:
        """Get all memories for a specific person.
        
        Args:
            person_id: Person identifier
            
        Returns:
            List of memory dictionaries
        """
        conn = self._get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT id, person_id, memory_text, context, created_at, updated_at, conversation_id
                    FROM person_memories
                    WHERE person_id = %s
                    ORDER BY created_at DESC
                    """,
                    (person_id,)
                )
                return [dict(row) for row in cur.fetchall()]
        except Exception as e:
            raise RuntimeError(f"Failed to get memories: {e}")
        finally:
            self._return_connection(conn)
    
    def get_all_memories(self) -> List[Dict[str, Any]]:
        """Get all memories.
        
        Returns:
            List of memory dictionaries
        """
        conn = self._get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT id, person_id, memory_text, context, created_at, updated_at, conversation_id
                    FROM person_memories
                    ORDER BY created_at DESC
                    """
                )
                return [dict(row) for row in cur.fetchall()]
        except Exception as e:
            raise RuntimeError(f"Failed to get all memories: {e}")
        finally:
            self._return_connection(conn)
    
    # Todo operations
    def add_todo(
        self,
        description: str,
        person_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
        status: str = "pending"
    ) -> int:
        """Add a todo to the database.
        
        Args:
            description: Todo description
            person_id: Optional person identifier
            conversation_id: Optional conversation ID where todo was created
            status: Todo status (default: 'pending')
            
        Returns:
            ID of the created todo
        """
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO todos (description, person_id, conversation_id, status)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id
                    """,
                    (description, person_id, conversation_id, status)
                )
                todo_id = cur.fetchone()[0]
                conn.commit()
                return todo_id
        except Exception as e:
            conn.rollback()
            raise RuntimeError(f"Failed to add todo: {e}")
        finally:
            self._return_connection(conn)
    
    def get_todos(
        self,
        status: Optional[str] = None,
        person_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get todos with optional filters.
        
        Args:
            status: Filter by status (e.g., 'pending', 'completed')
            person_id: Filter by person ID
            
        Returns:
            List of todo dictionaries
        """
        conn = self._get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                query = "SELECT id, description, status, person_id, created_at, completed_at, conversation_id FROM todos WHERE 1=1"
                params = []
                
                if status:
                    query += " AND status = %s"
                    params.append(status)
                
                if person_id:
                    query += " AND person_id = %s"
                    params.append(person_id)
                
                query += " ORDER BY created_at DESC"
                
                cur.execute(query, params)
                return [dict(row) for row in cur.fetchall()]
        except Exception as e:
            raise RuntimeError(f"Failed to get todos: {e}")
        finally:
            self._return_connection(conn)
    
    def update_todo_status(self, todo_id: int, status: str) -> None:
        """Update todo status.
        
        Args:
            todo_id: Todo ID
            status: New status
        """
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                completed_at = datetime.now() if status == "completed" else None
                cur.execute(
                    """
                    UPDATE todos
                    SET status = %s, completed_at = %s
                    WHERE id = %s
                    """,
                    (status, completed_at, todo_id)
                )
                conn.commit()
        except Exception as e:
            conn.rollback()
            raise RuntimeError(f"Failed to update todo status: {e}")
        finally:
            self._return_connection(conn)
    
    def get_todo_by_id(self, todo_id: int) -> Optional[Dict[str, Any]]:
        """Get a todo by ID.
        
        Args:
            todo_id: Todo ID
            
        Returns:
            Todo dictionary or None if not found
        """
        conn = self._get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT id, description, status, person_id, created_at, completed_at, conversation_id
                    FROM todos
                    WHERE id = %s
                    """,
                    (todo_id,)
                )
                row = cur.fetchone()
                return dict(row) if row else None
        except Exception as e:
            raise RuntimeError(f"Failed to get todo: {e}")
        finally:
            self._return_connection(conn)
    
    def close(self) -> None:
        """Close all database connections."""
        if self.connection_pool:
            self.connection_pool.closeall()
            self.connection_pool = None

