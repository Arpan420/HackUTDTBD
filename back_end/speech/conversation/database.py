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
    
    def get_person_name(self, person_id: Optional[str]) -> Optional[str]:
        """Get person name from database.
        
        For now, this attempts to extract a name from person_memories.
        If no person_id is provided or no name is found, returns None.
        In the future, this could query a dedicated persons table.
        
        Args:
            person_id: Person identifier
            
        Returns:
            Person name if found, None otherwise
        """
        if not person_id:
            return None
        
        conn = self._get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Try to find a name in memories (look for memory_text that might contain a name)
                # For now, we'll use a simple heuristic: if person_id looks like a name, use it
                # Otherwise, try to find a memory that might contain the name
                cur.execute(
                    """
                    SELECT person_id, memory_text, created_at
                    FROM person_memories
                    WHERE person_id = %s
                    ORDER BY created_at DESC
                    LIMIT 1
                    """,
                    (person_id,)
                )
                row = cur.fetchone()
                
                if row:
                    # For now, use person_id as name if it looks like a name (not a UUID)
                    # In production, this would query a persons table
                    if len(person_id) < 50 and not person_id.startswith(('{', '[')):
                        return person_id
                
                # Mock fallback: if person_id exists but no name found, return a mock name
                # This is a placeholder until proper person management is implemented
                return f"Person {person_id[:8]}"
        except Exception as e:
            # If database query fails, return mock name
            print(f"Warning: Failed to get person name: {e}")
            if person_id and len(person_id) < 50:
                return person_id
            return f"Person {person_id[:8] if person_id else 'Unknown'}"
        finally:
            self._return_connection(conn)
    
    # Face operations
    def get_face_by_person_id(self, person_id: str) -> Optional[Dict[str, Any]]:
        """Get face record for a specific person.
        
        Args:
            person_id: Person identifier
            
        Returns:
            Face dictionary or None if not found
        """
        conn = self._get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT person_id, embedding, count, socials, recap
                    FROM faces
                    WHERE person_id = %s
                    """,
                    (person_id,)
                )
                row = cur.fetchone()
                return dict(row) if row else None
        except Exception as e:
            raise RuntimeError(f"Failed to get face: {e}")
        finally:
            self._return_connection(conn)
    
    def create_or_update_face(
        self,
        person_id: str,
        embedding: Optional[bytes] = None,
        count: Optional[int] = None,
        socials: Optional[Dict[str, Any]] = None,
        recap: Optional[str] = None
    ) -> None:
        """Create or update face record.
        
        Args:
            person_id: Person identifier
            embedding: Face embedding bytes (optional)
            count: Detection count (optional)
            socials: Social information as JSON dict (optional)
            recap: Recap text (optional)
        """
        if recap:
            print(f"[Database] Preview update: Updating recap/preview for person {person_id}")
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                # Use PostgreSQL JSONB for socials
                import json as json_lib
                socials_json = json_lib.dumps(socials) if socials else None
                
                cur.execute(
                    """
                    INSERT INTO faces (person_id, embedding, count, socials, recap)
                    VALUES (%s, %s, %s, %s::jsonb, %s)
                    ON CONFLICT (person_id) DO UPDATE SET
                        embedding = COALESCE(EXCLUDED.embedding, faces.embedding),
                        count = COALESCE(EXCLUDED.count, faces.count),
                        socials = COALESCE(EXCLUDED.socials, faces.socials),
                        recap = COALESCE(EXCLUDED.recap, faces.recap)
                    """,
                    (person_id, embedding, count, socials_json, recap)
                )
                conn.commit()
                if recap:
                    print(f"[Database] Preview update: Recap/preview updated successfully for person {person_id}")
        except Exception as e:
            conn.rollback()
            if recap:
                print(f"[Database] Preview update: Failed to update recap/preview for person {person_id}: {e}")
            raise RuntimeError(f"Failed to create or update face: {e}")
        finally:
            self._return_connection(conn)
    
    def person_exists(self, person_id: str) -> bool:
        """Check if person exists in faces table.
        
        Args:
            person_id: Person identifier
            
        Returns:
            True if person exists, False otherwise
        """
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT 1 FROM faces WHERE person_id = %s
                    """,
                    (person_id,)
                )
                return cur.fetchone() is not None
        except Exception as e:
            raise RuntimeError(f"Failed to check if person exists: {e}")
        finally:
            self._return_connection(conn)
    
    # Summary operations
    def add_summary(self, person_id: str, summary_text: str) -> int:
        """Add a summary to the database.
        
        Args:
            person_id: Person identifier
            summary_text: Summary text content
            
        Returns:
            ID of the created summary
        """
        print(f"[Database] DB call: Inserting summary for person {person_id}")
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO summaries (person_id, summary_text)
                    VALUES (%s, %s)
                    RETURNING summary_id
                    """,
                    (person_id, summary_text)
                )
                summary_id = cur.fetchone()[0]
                conn.commit()
                print(f"[Database] DB call: Summary inserted successfully with ID {summary_id} for person {person_id}")
                return summary_id
        except Exception as e:
            conn.rollback()
            print(f"[Database] DB call: Failed to insert summary for person {person_id}: {e}")
            raise RuntimeError(f"Failed to add summary: {e}")
        finally:
            self._return_connection(conn)
    
    def get_latest_summary(self, person_id: str) -> Optional[str]:
        """Get the most recent summary for a person.
        
        Args:
            person_id: Person identifier
            
        Returns:
            Latest summary text or None if not found
        """
        print(f"[Database] Summary fetch request: Fetching latest summary for person {person_id}")
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT summary_text
                    FROM summaries
                    WHERE person_id = %s
                    ORDER BY created_at DESC
                    LIMIT 1
                    """,
                    (person_id,)
                )
                row = cur.fetchone()
                if row:
                    print(f"[Database] Summary fetched: Found summary for person {person_id}")
                else:
                    print(f"[Database] Summary fetched: No summary found for person {person_id}")
                return row[0] if row else None
        except Exception as e:
            print(f"[Database] Summary fetch request: Failed to fetch summary for person {person_id}: {e}")
            raise RuntimeError(f"Failed to get latest summary: {e}")
        finally:
            self._return_connection(conn)
    
    def close(self) -> None:
        """Close all database connections."""
        if self.connection_pool:
            self.connection_pool.closeall()
            self.connection_pool = None

