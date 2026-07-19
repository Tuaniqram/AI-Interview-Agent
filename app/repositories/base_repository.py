"""
Base repository class for database operations.
Provides common patterns for all repository implementations.
"""
import logging
from typing import Any, Optional
from pydantic import BaseModel
from app.exceptions import RecordNotFoundException, DatabaseException
logger = logging.getLogger(__name__)


class BaseRepository:
    """
    Base repository for database access.
    All repository implementations should inherit from this.
    """
    
    def __init__(self, db):
        """
        Initialize repository with database client.
        
        Args:
            db: Database client (Supabase client)
        """
        self.db = db
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    async def get(
        self,
        id: str,
        table: str
    ) -> dict:
        """
        Get a single record by ID.
        
        Args:
            id: Record ID
            table: Table name
            
        Returns:
            dict: The fetched record
            
        Raises:
            RecordNotFoundException: If record not found
            DatabaseException: If database operation fails
        """
        try:
            response = self.db.table(table).select("*").eq("id", id).execute()
            
            if not response.data or len(response.data) == 0:
                raise RecordNotFoundException(
                    table=table,
                    identifier="id",
                    value=id
                )
            
            return response.data[0]
            
        except Exception as e:
            self.logger.error(
                f"Database error: {e}",
                extra={"table": table, "id": id}
            )
            raise DatabaseException(f"Failed to get record: {str(e)}")
    
    async def create(
        self,
        data: dict,
        table: str
    ) -> dict:
        """
        Create a new record.
        
        Args:
            data: Record data
            table: Table name
            
        Returns:
            dict: The created record
        """
        try:
            response = self.db.table(table).insert(data).execute()
            return response.data[0] if response.data else None
            
        except Exception as e:
            self.logger.error(
                f"Database error creating record: {e}",
                extra={"table": table, "data": data}
            )
            raise DatabaseException(f"Failed to create record: {str(e)}")
    
    async def update(
        self,
        id: str,
        updates: dict,
        table: str
    ) -> dict:
        """
        Update a record.
        
        Args:
            id: Record ID
            updates: Fields to update
            table: Table name
            
        Returns:
            dict: The updated record
        """
        try:
            response = self.db.table(table).update(updates).eq("id", id).execute()
            
            if not response.data or len(response.data) == 0:
                raise RecordNotFoundException(
                    table=table,
                    identifier="id",
                    value=id
                )
            
            return response.data[0]
            
        except RecordNotFoundException:
            raise
        except Exception as e:
            self.logger.error(
                f"Database error updating record: {e}",
                extra={"table": table, "id": id}
            )
            raise DatabaseException(f"Failed to update record: {str(e)}")
    
    async def delete(
        self,
        id: str,
        table: str
    ) -> bool:
        """
        Delete a record.
        
        Args:
            id: Record ID
            table: Table name
            
        Returns:
            bool: True if deleted
            
        Raises:
            RecordNotFoundException: If record not found
        """
        try:
            response = self.db.table(table).delete().eq("id", id).execute()
            return response.data is not None
            
        except Exception as e:
            self.logger.error(
                f"Database error deleting record: {e}",
                extra={"table": table, "id": id}
            )
            raise DatabaseException(f"Failed to delete record: {str(e)}")
    
    async def list_by_session(
        self,
        session_id: str,
        table: str,
        order_by: Optional[str] = None
    ) -> list[dict]:
        """
        List all records by session ID with optional ordering.
        
        Args:
            session_id: Session ID
            table: Table name
            order_by: Field to order by (e.g., "created_at")
            
        Returns:
            list[dict]: List of records
        """
        try:
            query = self.db.table(table).select("*").eq("session_id", session_id)
            
            if order_by:
                query = query.order(order_by, ascending=True)
            
            response = query.execute()
            return response.data if response.data else []
            
        except Exception as e:
            self.logger.error(
                f"Database error listing records: {e}",
                extra={"table": table, "session_id": session_id}
            )
            raise DatabaseException(f"Failed to list records: {str(e)}")
    
    async def exists(
        self,
        id: str,
        table: str
    ) -> bool:
        """
        Check if a record exists.
        
        Args:
            id: Record ID
            table: Table name
            
        Returns:
            bool: True if exists
        """
        try:
            response = self.db.table(table).select("id").eq("id", id).limit(1).execute()
            return response.data is not None and len(response.data) > 0
            
        except Exception as e:
            self.logger.error(
                f"Database error checking existence: {e}",
                extra={"table": table, "id": id}
            )
            raise DatabaseException(f"Failed to check existence: {str(e)}")