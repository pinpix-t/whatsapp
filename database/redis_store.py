"""Redis store for session and cache management"""

import redis
import json
import logging
from typing import Optional, List, Dict, Any
from config.settings import REDIS_URL
from utils.retry import retry_db_operation

logger = logging.getLogger(__name__)


class RedisStore:
    """Redis store for caching and session management"""

    def __init__(self, url: str = REDIS_URL):
        """Initialize Redis connection with connection pooling"""
        try:
            # Create connection pool for better performance
            pool = redis.ConnectionPool.from_url(
                url,
                decode_responses=True,
                max_connections=50,  # Maximum connections in pool
                socket_connect_timeout=5,
                socket_timeout=5,
                socket_keepalive=True,
                socket_keepalive_options={},
                retry_on_timeout=True,
                health_check_interval=30  # Health check every 30 seconds
            )

            self.client = redis.Redis(connection_pool=pool)
            self.client.ping()
            logger.info("✓ Redis connection pool established (max_connections=50)")
        except Exception as e:
            logger.error(f"❌ Failed to connect to Redis: {e}")
            self.client = None

    @retry_db_operation()
    def set_conversation(self, user_id: str, conversation: List[Dict[str, str]], ttl: int = 86400):
        """
        Store conversation history for a user

        Args:
            user_id: User identifier
            conversation: List of conversation messages
            ttl: Time to live in seconds (default 24 hours)
        """
        if not self.client:
            logger.warning("Redis not available, skipping conversation storage")
            return

        try:
            key = f"conversation:{user_id}"
            self.client.setex(
                key,
                ttl,
                json.dumps(conversation)
            )
            logger.debug(f"Stored conversation for {user_id}")
        except Exception as e:
            logger.error(f"Error storing conversation: {e}")
            raise

    @retry_db_operation()
    def get_conversation(self, user_id: str) -> Optional[List[Dict[str, str]]]:
        """
        Retrieve conversation history for a user

        Args:
            user_id: User identifier

        Returns:
            List of conversation messages or None
        """
        if not self.client:
            logger.warning("Redis not available, returning empty conversation")
            return None

        try:
            key = f"conversation:{user_id}"
            data = self.client.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.error(f"Error retrieving conversation: {e}")
            return None

    @retry_db_operation()
    def append_to_conversation(self, user_id: str, role: str, content: str, ttl: int = 86400):
        """
        Append a message to conversation history

        Args:
            user_id: User identifier
            role: Message role (user/assistant)
            content: Message content
            ttl: Time to live in seconds
        """
        if not self.client:
            return

        try:
            conversation = self.get_conversation(user_id) or []
            conversation.append({"role": role, "content": content})

            # Keep only last 10 messages to avoid growing too large
            conversation = conversation[-10:]

            self.set_conversation(user_id, conversation, ttl)
        except Exception as e:
            logger.error(f"Error appending to conversation: {e}")

    @retry_db_operation()
    def cache_response(self, query: str, response: str, ttl: int = 3600):
        """
        Cache a response for a query

        Args:
            query: User query
            response: Bot response
            ttl: Time to live in seconds (default 1 hour)
        """
        if not self.client:
            return

        try:
            key = f"cache:{hash(query)}"
            self.client.setex(key, ttl, response)
            logger.debug(f"Cached response for query: {query[:50]}")
        except Exception as e:
            logger.error(f"Error caching response: {e}")

    @retry_db_operation()
    def get_cached_response(self, query: str) -> Optional[str]:
        """
        Get cached response for a query

        Args:
            query: User query

        Returns:
            Cached response or None
        """
        if not self.client:
            return None

        try:
            key = f"cache:{hash(query)}"
            return self.client.get(key)
        except Exception as e:
            logger.error(f"Error getting cached response: {e}")
            return None

    @retry_db_operation()
    def increment_counter(self, key: str, amount: int = 1) -> int:
        """
        Increment a counter

        Args:
            key: Counter key
            amount: Amount to increment

        Returns:
            New counter value
        """
        if not self.client:
            return 0

        try:
            return self.client.incr(key, amount)
        except Exception as e:
            logger.error(f"Error incrementing counter: {e}")
            return 0

    @retry_db_operation()
    def get_stats(self) -> Dict[str, Any]:
        """Get Redis stats"""
        if not self.client:
            return {"status": "unavailable"}

        try:
            info = self.client.info()
            return {
                "status": "connected",
                "used_memory": info.get("used_memory_human"),
                "connected_clients": info.get("connected_clients"),
                "total_commands": info.get("total_commands_processed")
            }
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {"status": "error", "error": str(e)}

    @retry_db_operation()
    def set_bulk_order_state(self, user_id: str, state: str, data: dict, ttl: int = 3600):
        """
        Store bulk ordering state for a user

        Args:
            user_id: User identifier
            state: Current state in the bulk ordering flow
            data: State data including selections
            ttl: Time to live in seconds (default 1 hour)
        """
        if not self.client:
            logger.warning("Redis not available, skipping bulk order state storage")
            return

        try:
            key = f"bulk_order:{user_id}"
            state_data = {
                "state": state,
                **data
            }
            self.client.setex(
                key,
                ttl,
                json.dumps(state_data)
            )
            logger.debug(f"Stored bulk order state for {user_id}: {state}")
        except Exception as e:
            logger.error(f"Error storing bulk order state: {e}")
            raise

    @retry_db_operation()
    def get_bulk_order_state(self, user_id: str) -> Optional[dict]:
        """
        Retrieve bulk ordering state for a user

        Args:
            user_id: User identifier

        Returns:
            State data dictionary or None
        """
        if not self.client:
            logger.warning("Redis not available, returning None for bulk order state")
            return None

        try:
            key = f"bulk_order:{user_id}"
            data = self.client.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.error(f"Error retrieving bulk order state: {e}")
            return None

    @retry_db_operation()
    def clear_bulk_order_state(self, user_id: str):
        """Clear bulk ordering state for a user"""
        if not self.client:
            return

        try:
            key = f"bulk_order:{user_id}"
            self.client.delete(key)
            logger.debug(f"Cleared bulk order state for {user_id}")
        except Exception as e:
            logger.error(f"Error clearing bulk order state: {e}")

    @retry_db_operation()
    def clear_conversation(self, user_id: str):
        """Clear conversation history for a user"""
        if not self.client:
            return

        try:
            key = f"conversation:{user_id}"
            self.client.delete(key)
            logger.debug(f"Cleared conversation history for {user_id}")
        except Exception as e:
            logger.error(f"Error clearing conversation history: {e}")

    @retry_db_operation()
    def set_image_creation_state(self, user_id: str, state: str, data: dict = None, ttl: int = 3600):
        """
        Store image creation state for a user

        Args:
            user_id: User identifier
            state: Current state in the image creation flow
            data: State data
            ttl: Time to live in seconds (default 1 hour)
        """
        if not self.client:
            logger.warning("Redis not available, skipping image creation state storage")
            return

        try:
            key = f"image_creation:{user_id}"
            state_data = {
                "state": state,
                **(data or {})
            }
            self.client.setex(
                key,
                ttl,
                json.dumps(state_data)
            )
            logger.debug(f"Stored image creation state for {user_id}: {state}")
        except Exception as e:
            logger.error(f"Error storing image creation state: {e}")
            raise

    @retry_db_operation()
    def get_image_creation_state(self, user_id: str) -> Optional[dict]:
        """
        Retrieve image creation state for a user

        Args:
            user_id: User identifier

        Returns:
            State data dictionary or None
        """
        if not self.client:
            logger.warning("Redis not available, returning None for image creation state")
            return None

        try:
            key = f"image_creation:{user_id}"
            data = self.client.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.error(f"Error retrieving image creation state: {e}")
            return None

    @retry_db_operation()
    def clear_image_creation_state(self, user_id: str):
        """Clear image creation state for a user"""
        if not self.client:
            return

        try:
            key = f"image_creation:{user_id}"
            self.client.delete(key)
            logger.debug(f"Cleared image creation state for {user_id}")
        except Exception as e:
            logger.error(f"Error clearing image creation state: {e}")

    def close(self):
        """Close Redis connection"""
        if self.client:
            self.client.close()
            logger.info("Redis connection closed")


# Global instance
redis_store = RedisStore()
