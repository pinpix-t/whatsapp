"""PostgreSQL store for persistent data"""

import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, JSON, Boolean, text
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
    is_archived = Column(Boolean, default=False)
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

            # Ensure is_archived column exists in conversations table
            try:
                with self.engine.begin() as conn:
                    # Check if is_archived column exists, if not add it
                    result = conn.execute(text("""
                        SELECT column_name 
                        FROM information_schema.columns 
                        WHERE table_name='conversations' AND column_name='is_archived'
                    """))
                    if not result.fetchone():
                        logger.info("📦 Adding is_archived column to conversations table...")
                        conn.execute(text("ALTER TABLE conversations ADD COLUMN IF NOT EXISTS is_archived BOOLEAN DEFAULT FALSE"))
                        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_conversations_is_archived ON conversations(is_archived)"))
                        logger.info("✅ is_archived column added to conversations table")
            except Exception as e:
                logger.warning(f"⚠️ Could not verify/add is_archived column: {e}")

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
            # Get both inbound (from user) and outbound (to user) messages
            from sqlalchemy import or_
            messages = (
                session.query(Message)
                .filter(
                    or_(
                        Message.from_number == user_id,  # Inbound messages from user
                        Message.to_number == user_id     # Outbound messages to user
                    )
                )
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

    @retry_db_operation()
    def get_all_conversations(self, limit: int = 100, offset: int = 0, date_from: Optional[str] = None, date_to: Optional[str] = None, include_archived: bool = False) -> List[Dict[str, Any]]:
        """
        Get all unique conversations (users who have sent messages)
        
        Args:
            limit: Maximum number of conversations to return
            offset: Offset for pagination
            date_from: Filter conversations from this date (ISO format)
            date_to: Filter conversations to this date (ISO format)
            include_archived: If True, include archived conversations
            
        Returns:
            List of conversation summaries with user_id, last_message_time, message_count, is_archived
        """
        session = self.get_session()
        if not session:
            return []

        try:
            from sqlalchemy import func, distinct
            
            # Base query - get distinct from_number with latest message time and count
            # Exclude bot messages (from_number = "bot" or starts with "agent_")
            query = (
                session.query(
                    Message.from_number,
                    func.max(Message.created_at).label('last_message_time'),
                    func.count(Message.id).label('message_count')
                )
                .filter(~Message.from_number.like('bot%'))
                .filter(~Message.from_number.like('agent_%'))
                .group_by(Message.from_number)
            )
            
            # Filter out archived conversations unless include_archived is True
            if not include_archived:
                # Get list of archived user_ids from conversations table
                archived_user_ids = [
                    row[0] for row in 
                    session.query(Conversation.user_id)
                    .filter(Conversation.is_archived == True)
                    .all()
                ]
                if archived_user_ids:
                    # Exclude archived conversations
                    query = query.filter(~Message.from_number.in_(archived_user_ids))
            
            # Apply date filters if provided
            if date_from:
                try:
                    from datetime import datetime
                    date_from_dt = datetime.fromisoformat(date_from.replace('Z', '+00:00'))
                    query = query.filter(Message.created_at >= date_from_dt)
                except:
                    pass
            
            if date_to:
                try:
                    from datetime import datetime
                    date_to_dt = datetime.fromisoformat(date_to.replace('Z', '+00:00'))
                    query = query.filter(Message.created_at <= date_to_dt)
                except:
                    pass
            
            # Order by last message time (most recent first)
            query = query.order_by(func.max(Message.created_at).desc())
            
            # Apply limit and offset
            results = query.limit(limit).offset(offset).all()
            
            # Get archive status for returned conversations
            user_ids = [result.from_number for result in results]
            archive_status_map = {}
            if user_ids:
                archived = session.query(Conversation.user_id).filter(
                    Conversation.user_id.in_(user_ids),
                    Conversation.is_archived == True
                ).all()
                archive_status_map = {row[0]: True for row in archived}
            
            conversations = []
            for result in results:
                conversations.append({
                    "user_id": result.from_number,
                    "last_message_time": result.last_message_time.isoformat() if result.last_message_time else None,
                    "message_count": result.message_count,
                    "is_archived": archive_status_map.get(result.from_number, False)
                })
            
            return conversations
        except SQLAlchemyError as e:
            logger.error(f"Error getting all conversations: {e}")
            return []
        finally:
            session.close()

    @retry_db_operation()
    def get_conversation_summary(self, user_id: str) -> Dict[str, Any]:
        """
        Get summary statistics for a specific conversation
        
        Args:
            user_id: User identifier (phone number)
            
        Returns:
            Dictionary with conversation summary including message_count, first_message, last_message, etc.
        """
        session = self.get_session()
        if not session:
            return {}

        try:
            from sqlalchemy import func, or_
            
            # Get message count (both inbound and outbound)
            message_count = (
                session.query(Message)
                .filter(
                    or_(
                        Message.from_number == user_id,  # Inbound from user
                        Message.to_number == user_id     # Outbound to user
                    )
                )
                .count()
            )
            
            # Get first and last message
            first_message = (
                session.query(Message)
                .filter(
                    or_(
                        Message.from_number == user_id,
                        Message.to_number == user_id
                    )
                )
                .order_by(Message.created_at.asc())
                .first()
            )
            
            last_message = (
                session.query(Message)
                .filter(
                    or_(
                        Message.from_number == user_id,
                        Message.to_number == user_id
                    )
                )
                .order_by(Message.created_at.desc())
                .first()
            )
            
            # Get inbound/outbound counts
            inbound_count = (
                session.query(Message)
                .filter(Message.from_number == user_id, Message.direction == "inbound")
                .count()
            )
            
            outbound_count = (
                session.query(Message)
                .filter(Message.to_number == user_id, Message.direction == "outbound")
                .count()
            )
            
            return {
                "user_id": user_id,
                "message_count": message_count,
                "inbound_count": inbound_count,
                "outbound_count": outbound_count,
                "first_message_time": first_message.created_at.isoformat() if first_message else None,
                "last_message_time": last_message.created_at.isoformat() if last_message else None,
                "last_message_content": last_message.content[:100] if last_message else None
            }
        except SQLAlchemyError as e:
            logger.error(f"Error getting conversation summary: {e}")
            return {}
        finally:
            session.close()

    @retry_db_operation()
    def archive_conversation(self, user_id: str) -> bool:
        """Archive a conversation"""
        session = self.get_session()
        if not session:
            return False
        
        try:
            conversation = session.query(Conversation).filter(Conversation.user_id == user_id).first()
            if conversation:
                conversation.is_archived = True
            else:
                # Create conversation record if it doesn't exist
                conversation = Conversation(user_id=user_id, is_archived=True)
                session.add(conversation)
            session.commit()
            logger.info(f"Archived conversation for {user_id}")
            return True
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Error archiving conversation: {e}")
            return False
        finally:
            session.close()

    @retry_db_operation()
    def unarchive_conversation(self, user_id: str) -> bool:
        """Unarchive a conversation"""
        session = self.get_session()
        if not session:
            return False
        
        try:
            conversation = session.query(Conversation).filter(Conversation.user_id == user_id).first()
            if conversation:
                conversation.is_archived = False
                session.commit()
                logger.info(f"Unarchived conversation for {user_id}")
                return True
            # If conversation doesn't exist, it's effectively not archived (return True)
            return True
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Error unarchiving conversation: {e}")
            return False
        finally:
            session.close()

    def close(self):
        """Close database connection and cleanup pool"""
        if self.engine:
            self.engine.dispose()
            logger.info("PostgreSQL connection pool closed")


# Global instance
postgres_store = PostgresStore()
