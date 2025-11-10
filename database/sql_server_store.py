"""SQL Server store for Azure SQL Database"""

import logging
from typing import Optional, List, Dict, Any
from urllib.parse import quote_plus
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError
import pandas as pd
from config.settings import (
    SQL_SERVER, SQL_DATABASE, SQL_USER, SQL_PASSWORD
)
from utils.retry import retry_db_operation

logger = logging.getLogger(__name__)


class SQLServerStore:
    """SQL Server store for Azure SQL Database queries"""
    
    def __init__(self):
        """Initialize SQL Server connection with connection pooling"""
        try:
            # URL-encode password to handle special characters (!, @, etc.)
            encoded_password = quote_plus(SQL_PASSWORD) if SQL_PASSWORD else ""
            
            # Build connection string
            connection_string = (
                f"mssql+pyodbc://{SQL_USER}:{encoded_password}@{SQL_SERVER}/{SQL_DATABASE}"
                "?driver=ODBC+Driver+18+for+SQL+Server"
                "&Encrypt=yes&TrustServerCertificate=yes"
                "&Connection+Timeout=5"
            )
            
            # Production-grade connection pool (similar to PostgresStore)
            pool_config = {
                'pool_size': 10,
                'max_overflow': 20,
                'pool_timeout': 30,
                'pool_recycle': 3600,
                'pool_pre_ping': True,
                'echo': False,
                'echo_pool': False,
            }
            
            self.engine = create_engine(connection_string, **pool_config)
            self.SessionLocal = sessionmaker(
                bind=self.engine,
                autocommit=False,
                autoflush=False,
                expire_on_commit=False
            )
            
            logger.info("✓ SQL Server connection pool established (size=10, max_overflow=20)")
        except Exception as e:
            logger.error(f"❌ Failed to connect to SQL Server: {e}")
            self.engine = None
            self.SessionLocal = None
    
    def get_session(self) -> Optional[Session]:
        """Get database session"""
        if not self.SessionLocal:
            return None
        return self.SessionLocal()
    
    @retry_db_operation()
    def query_product_page(self, canonical_product_page_id: str) -> Optional[Dict[str, Any]]:
        """
        Query product page by canonicalProductPageId
        
        Args:
            canonical_product_page_id: GUID string (e.g., "bc3e9ee3-84b4-452e-9559-3283a6b1a20e")
            
        Returns:
            Dictionary with product page data or None if not found
        """
        session = self.get_session()
        if not session:
            logger.warning("SQL Server not available")
            return None
        
        try:
            sql = text("""
                SELECT TOP (1) *
                FROM [dbo].[SynComs.Products.ProductPage]
                WHERE canonicalProductPageId = TRY_CONVERT(uniqueidentifier, :guid);
            """)
            
            result = session.execute(sql, {"guid": canonical_product_page_id}).fetchone()
            
            if result:
                # Convert row to dict
                return dict(result._mapping)
            return None
            
        except SQLAlchemyError as e:
            logger.error(f"Error querying product page: {e}")
            return None
        finally:
            session.close()
    
    def query_to_dataframe(self, sql: str, params: Optional[Dict] = None) -> pd.DataFrame:
        """
        Execute query and return as pandas DataFrame
        
        Args:
            sql: SQL query string
            params: Optional dictionary of parameters for parameterized queries
            
        Returns:
            pandas DataFrame with query results
        """
        if not self.engine:
            logger.warning("SQL Server not available")
            return pd.DataFrame()
        
        try:
            with self.engine.begin() as conn:
                if params:
                    df = pd.read_sql(text(sql), conn, params=params)
                else:
                    df = pd.read_sql(text(sql), conn)
                return df
        except Exception as e:
            logger.error(f"Error executing query: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return pd.DataFrame()
    
    def execute_query(self, sql: str, params: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """
        Execute query and return list of dictionaries
        
        Args:
            sql: SQL query string
            params: Optional dictionary of parameters for parameterized queries
            
        Returns:
            List of dictionaries with query results
        """
        session = self.get_session()
        if not session:
            logger.warning("SQL Server not available")
            return []
        
        try:
            if params:
                result = session.execute(text(sql), params)
            else:
                result = session.execute(text(sql))
            
            rows = result.fetchall()
            return [dict(row._mapping) for row in rows]
            
        except SQLAlchemyError as e:
            logger.error(f"Error executing query: {e}")
            return []
        finally:
            session.close()
    
    def get_pool_stats(self) -> Dict[str, Any]:
        """Get connection pool statistics"""
        if not self.engine:
            return {"status": "unavailable"}
        
        try:
            pool = self.engine.pool
            return {
                "status": "connected",
                "pool_size": pool.size(),
                "checked_in": pool.checkedin(),
                "checked_out": pool.checkedout(),
                "overflow": pool.overflow(),
                "total_connections": pool.size() + pool.overflow()
            }
        except Exception as e:
            logger.error(f"Error getting pool stats: {e}")
            return {"status": "error", "error": str(e)}
    
    def close(self):
        """Close database connection and cleanup pool"""
        if self.engine:
            self.engine.dispose()
            logger.info("SQL Server connection pool closed")


# Global instance
sql_server_store = SQLServerStore()

