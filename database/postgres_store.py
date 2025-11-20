"""PostgreSQL store for persistent data"""

import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, JSON, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError
from config.settings import DATABASE_URL
from utils.retry import retry_db_operation

logger = logging.getLogger(__name__)

Base = declarative_base()


class Message(Base):
    """Message model"""
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True)
    message_id = Column(String(255), unique=True, nullable=False)
    from_number = Column(String(50), nullable=False)
    to_number = Column(String(50))
    message_type = Column(String(50), default="text")
    content = Column(Text)
    direction = Column(String(10))  # inbound/outbound
    status = Column(String(50), default="sent")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Conversation(Base):
    """Conversation model"""
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True)
    user_id = Column(String(50), unique=True, nullable=False)
    context = Column(JSON, default=list)
    meta_data = Column("metadata", JSON, default=dict)  # Renamed to avoid SQLAlchemy reserved word
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Analytics(Base):
    """Analytics model"""
    __tablename__ = "analytics"

    id = Column(Integer, primary_key=True)
    event_type = Column(String(100), nullable=False)
    user_id = Column(String(50))
    email = Column(String(255), nullable=True)
    data = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)


class PostgresStore:
    """PostgreSQL store for persistent data"""

    def __init__(self, database_url: str = DATABASE_URL):
        """Initialize database connection with production-ready pooling"""
        try:
            # Production-grade connection pool configuration
            pool_config = {
                # Pool settings
                'pool_size': 20,  # Number of connections to maintain
                'max_overflow': 40,  # Maximum overflow connections
                'pool_timeout': 30,  # Seconds to wait for connection
                'pool_recycle': 3600,  # Recycle connections after 1 hour
                'pool_pre_ping': True,  # Verify connections before using

                # Performance settings
                'echo': False,  # Disable SQL echo in production
                'echo_pool': False,  # Disable pool logging
                'pool_use_lifo': True,  # Use most recently returned connections first

                # Connection settings
                'connect_args': {
                    'connect_timeout': 10,
                    'application_name': 'whatsapp_bot',
                    'options': '-c statement_timeout=30000'  # 30 second query timeout
                }
            }

            self.engine = create_engine(database_url, **pool_config)
            self.SessionLocal = sessionmaker(
                bind=self.engine,
                autocommit=False,
                autoflush=False,
                expire_on_commit=False
            )

            # Create tables if they don't exist
            Base.metadata.create_all(self.engine)
            
            # Ensure email column exists (for existing tables)
            try:
                with self.engine.begin() as conn:
                    # Check if email column exists, if not add it
                    result = conn.execute(text("""
                        SELECT column_name 
                        FROM information_schema.columns 
                        WHERE table_name='analytics' AND column_name='email'
                    """))
                    if not result.fetchone():
                        logger.info("📧 Adding email column to analytics table...")
                        conn.execute(text("ALTER TABLE analytics ADD COLUMN IF NOT EXISTS email VARCHAR(255)"))
                        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_analytics_email ON analytics(email)"))
                        logger.info("✅ Email column added to analytics table")
            except Exception as e:
                logger.warning(f"⚠️ Could not verify/add email column: {e}")

            logger.info("✓ PostgreSQL connection pool established (size=20, max_overflow=40)")
        except Exception as e:
            logger.error(f"❌ Failed to connect to PostgreSQL: {e}")
            self.engine = None
            self.SessionLocal = None

    def get_session(self) -> Optional[Session]:
        """Get database session"""
        if not self.SessionLocal:
            return None
        return self.SessionLocal()

    @retry_db_operation()
    def save_message(
        self,
        message_id: str,
        from_number: str,
        to_number: Optional[str],
        content: str,
        direction: str,
        message_type: str = "text",
        status: str = "sent"
    ):
        """Save a message to database"""
        session = self.get_session()
        if not session:
            logger.warning("Database not available")
            return

        try:
            message = Message(
                message_id=message_id,
                from_number=from_number,
                to_number=to_number,
                message_type=message_type,
                content=content,
                direction=direction,
                status=status
            )
            session.add(message)
            session.commit()
            logger.debug(f"Saved message {message_id}")
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Error saving message: {e}")
            raise
        finally:
            session.close()

    @retry_db_operation()
    def get_conversation_history(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get conversation history for a user"""
        session = self.get_session()
        if not session:
            return []

        try:
            messages = (
                session.query(Message)
                .filter(Message.from_number == user_id)
                .order_by(Message.created_at.desc())
                .limit(limit)
                .all()
            )

            return [
                {
                    "message_id": msg.message_id,
                    "content": msg.content,
                    "direction": msg.direction,
                    "created_at": msg.created_at.isoformat()
                }
                for msg in reversed(messages)
            ]
        except SQLAlchemyError as e:
            logger.error(f"Error getting conversation history: {e}")
            return []
        finally:
            session.close()

    @retry_db_operation()
    def save_analytics_event(self, event_type: str, user_id: Optional[str], data: Dict[str, Any], email: Optional[str] = None):
        """Save an analytics event"""
        if not self.engine:
            logger.warning("⚠️ PostgreSQL not available - cannot save analytics event")
            return
        
        session = self.get_session()
        if not session:
            logger.warning("⚠️ Could not get database session - cannot save analytics event")
            return

        try:
            event = Analytics(
                event_type=event_type,
                user_id=user_id,
                email=email,
                data=data
            )
            session.add(event)
            session.commit()
            logger.info(f"✅ Saved analytics event: {event_type} for user {user_id}")
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"❌ Error saving analytics event: {e}", exc_info=True)
        except Exception as e:
            session.rollback()
            logger.error(f"❌ Unexpected error saving analytics event: {e}", exc_info=True)
        finally:
            session.close()

    @retry_db_operation()
    def get_user_stats(self, user_id: str) -> Dict[str, Any]:
        """Get statistics for a user"""
        session = self.get_session()
        if not session:
            return {}

        try:
            message_count = (
                session.query(Message)
                .filter(Message.from_number == user_id)
                .count()
            )

            conversation = (
                session.query(Conversation)
                .filter(Conversation.user_id == user_id)
                .first()
            )

            return {
                "message_count": message_count,
                "first_message": conversation.created_at.isoformat() if conversation else None,
                "last_updated": conversation.updated_at.isoformat() if conversation else None
            }
        except SQLAlchemyError as e:
            logger.error(f"Error getting user stats: {e}")
            return {}
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
            logger.info("PostgreSQL connection pool closed")


# Global instance
postgres_store = PostgresStore()
