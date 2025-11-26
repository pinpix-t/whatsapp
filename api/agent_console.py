"""
Agent Console API endpoints
Allows agents to claim conversations, send messages, and view conversation history
"""

import logging
import asyncio
import json
from datetime import datetime
from typing import Optional, List, Dict, Any, Set
from fastapi import APIRouter, HTTPException, Body, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from database.redis_store import redis_store
from database.postgres_store import postgres_store
from bot.whatsapp_api import WhatsAppAPI

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/agent", tags=["agent"])

# Initialize WhatsApp API for sending messages
whatsapp_api = WhatsAppAPI()


# Message broadcaster for live streaming
class MessageBroadcaster:
    """Broadcasts messages to connected agents via SSE"""
    
    def __init__(self):
        # Map of user_id -> set of agent queues
        self.connections: Dict[str, Set[asyncio.Queue]] = {}
        self.lock = asyncio.Lock()
    
    async def subscribe(self, user_id: str) -> asyncio.Queue:
        """Subscribe to messages for a user_id"""
        async with self.lock:
            if user_id not in self.connections:
                self.connections[user_id] = set()
            queue = asyncio.Queue()
            self.connections[user_id].add(queue)
            logger.info(f"Agent subscribed to {user_id}, total connections: {len(self.connections[user_id])}")
            return queue
    
    async def unsubscribe(self, user_id: str, queue: asyncio.Queue):
        """Unsubscribe from messages"""
        async with self.lock:
            if user_id in self.connections:
                self.connections[user_id].discard(queue)
                if len(self.connections[user_id]) == 0:
                    del self.connections[user_id]
                logger.info(f"Agent unsubscribed from {user_id}")
    
    async def broadcast(self, user_id: str, message: Dict[str, Any]):
        """Broadcast a message to all subscribed agents"""
        async with self.lock:
            if user_id not in self.connections:
                return
            
            # Send to all connected agents
            disconnected = set()
            for queue in self.connections[user_id]:
                try:
                    await queue.put(message)
                except Exception as e:
                    logger.error(f"Error broadcasting to agent: {e}")
                    disconnected.add(queue)
            
            # Clean up disconnected queues
            for queue in disconnected:
                self.connections[user_id].discard(queue)
            
            if len(self.connections[user_id]) == 0:
                del self.connections[user_id]


# Global broadcaster instance
message_broadcaster = MessageBroadcaster()


class ClaimRequest(BaseModel):
    agent_id: str


class SendMessageRequest(BaseModel):
    message: str
    agent_id: Optional[str] = None


@router.post("/claim/{user_id}")
async def claim_conversation(user_id: str, request: ClaimRequest):
    """
    Claim a conversation for agent handling
    Returns 409 if already claimed by a different agent
    """
    try:
        # Check if already claimed
        existing_handoff = redis_store.get_agent_handoff(user_id)
        
        if existing_handoff:
            existing_agent_id = existing_handoff.get("agent_id")
            if existing_agent_id != request.agent_id:
                raise HTTPException(
                    status_code=409,
                    detail={
                        "status": "already_claimed",
                        "user_id": user_id,
                        "agent_id": existing_agent_id,
                        "message": f"Conversation already claimed by agent {existing_agent_id}"
                    }
                )
            else:
                # Same agent claiming again - just return success
                return {
                    "status": "claimed",
                    "user_id": user_id,
                    "agent_id": request.agent_id,
                    "message": "Conversation already claimed by you"
                }
        
        # Claim the conversation
        redis_store.set_agent_handoff(user_id, request.agent_id)
        logger.info(f"Agent {request.agent_id} claimed conversation for {user_id}")
        
        return {
            "status": "claimed",
            "user_id": user_id,
            "agent_id": request.agent_id,
            "message": "Conversation claimed successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error claiming conversation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error claiming conversation: {str(e)}")


@router.post("/release/{user_id}")
async def release_conversation(user_id: str):
    """
    Release a conversation back to the bot
    """
    try:
        handoff_info = redis_store.get_agent_handoff(user_id)
        
        if not handoff_info:
            return {
                "status": "not_claimed",
                "user_id": user_id,
                "agent_id": None,
                "message": "Conversation is not currently claimed"
            }
        
        agent_id = handoff_info.get("agent_id")
        redis_store.clear_agent_handoff(user_id)
        logger.info(f"Agent {agent_id} released conversation for {user_id}")
        
        return {
            "status": "released",
            "user_id": user_id,
            "agent_id": agent_id,
            "message": "Conversation released successfully"
        }
    except Exception as e:
        logger.error(f"Error releasing conversation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error releasing conversation: {str(e)}")


@router.post("/send-message/{user_id}")
async def send_agent_message(user_id: str, request: SendMessageRequest):
    """
    Send a message as an agent
    Requires conversation to be claimed first
    """
    try:
        # Check if conversation is claimed
        handoff_info = redis_store.get_agent_handoff(user_id)
        if not handoff_info:
            raise HTTPException(
                status_code=403,
                detail="Conversation must be claimed before sending messages"
            )
        
        # Use agent_id from request or from handoff
        agent_id = request.agent_id or handoff_info.get("agent_id")
        if not agent_id:
            raise HTTPException(
                status_code=400,
                detail="agent_id is required"
            )
        
        # Send message via WhatsApp API
        response = await whatsapp_api.send_message(user_id, request.message)
        
        # Extract message_id from WhatsApp API response
        message_id = response.get("messages", [{}])[0].get("id") if response.get("messages") else f"agent_{datetime.utcnow().timestamp()}"
        
        # Store message in database with agent identifier
        from_number = f"agent_{agent_id}"
        try:
            postgres_store.save_message(
                message_id=message_id,
                from_number=from_number,
                to_number=user_id,
                content=request.message,
                direction="outbound",
                message_type="text",
                status="sent"
            )
        except Exception as e:
            logger.error(f"Error storing agent message: {e}")
        
        # Broadcast to connected agents via SSE
        try:
            await message_broadcaster.broadcast(user_id, {
                "type": "agent_message",
                "user_id": user_id,
                "message_id": message_id,
                "content": request.message,
                "agent_id": agent_id,
                "direction": "outbound",
                "timestamp": datetime.utcnow().isoformat()
            })
        except Exception as e:
            logger.error(f"Error broadcasting agent message: {e}")
        
        logger.info(f"Agent {agent_id} sent message to {user_id}")
        
        return {
            "status": "sent",
            "user_id": user_id,
            "message_id": message_id,
            "agent_id": agent_id,
            "message": "Message sent successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending agent message: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error sending message: {str(e)}")


@router.get("/stream/{user_id}")
async def stream_messages(user_id: str):
    """
    SSE endpoint for live message streaming
    Requires conversation to be claimed
    """
    # Check if conversation is claimed
    handoff_info = redis_store.get_agent_handoff(user_id)
    if not handoff_info:
        raise HTTPException(
            status_code=403,
            detail="Conversation must be claimed before streaming"
        )
    
    async def event_generator():
        queue = None
        try:
            # Subscribe to messages
            queue = await message_broadcaster.subscribe(user_id)
            
            # Send initial connected event
            yield f"data: {json.dumps({'type': 'connected', 'user_id': user_id})}\n\n"
            
            # Send heartbeat every 30 seconds
            last_heartbeat = asyncio.get_event_loop().time()
            heartbeat_interval = 30
            
            while True:
                try:
                    # Check for heartbeat
                    current_time = asyncio.get_event_loop().time()
                    if current_time - last_heartbeat >= heartbeat_interval:
                        yield f"data: {json.dumps({'type': 'heartbeat', 'timestamp': datetime.utcnow().isoformat()})}\n\n"
                        last_heartbeat = current_time
                    
                    # Wait for message with timeout
                    try:
                        message = await asyncio.wait_for(queue.get(), timeout=1.0)
                        yield f"data: {json.dumps(message)}\n\n"
                    except asyncio.TimeoutError:
                        continue
                        
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Error in event generator: {e}")
                    break
        finally:
            # Unsubscribe when done
            if queue:
                await message_broadcaster.unsubscribe(user_id, queue)
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.get("/conversation/{user_id}")
async def get_conversation(user_id: str, view_only: bool = Query(False)):
    """
    Get conversation history and state for a user
    Works without claiming - view-only access for managers
    """
    try:
        # Get handoff status
        handoff_info = redis_store.get_agent_handoff(user_id)
        handoff_status = {
            "is_claimed": handoff_info is not None,
            "agent_id": handoff_info.get("agent_id") if handoff_info else None,
            "claimed_at": handoff_info.get("claimed_at") if handoff_info else None
        }
        
        # Get conversation history from database
        conversation_history = postgres_store.get_conversation_history(user_id, limit=50)
        
        # Get bulk ordering state
        bulk_state = redis_store.get_bulk_order_state(user_id)
        
        # Get Redis conversation
        redis_conversation = redis_store.get_conversation(user_id)
        
        # Get message count
        user_stats = postgres_store.get_user_stats(user_id)
        message_count = user_stats.get("message_count", 0)
        
        return {
            "user_id": user_id,
            "handoff_status": handoff_status,
            "conversation_history": conversation_history,
            "bulk_ordering_state": bulk_state,
            "redis_conversation": redis_conversation,
            "message_count": message_count
        }
    except Exception as e:
        logger.error(f"Error getting conversation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error getting conversation: {str(e)}")


@router.get("/conversations")
async def list_conversations(all: bool = False):
    """
    List conversations
    - If all=false (default): List only claimed conversations
    - If all=true: List all conversations from database
    """
    try:
        if all:
            # Get all conversations from database
            all_conversations = postgres_store.get_all_conversations(limit=1000)
            
            # Enrich with handoff and bulk state info
            enriched = []
            for conv in all_conversations:
                user_id = conv["user_id"]
                
                # Check if claimed
                handoff_info = redis_store.get_agent_handoff(user_id) if redis_store.client else None
                
                # Get bulk ordering state
                bulk_state = redis_store.get_bulk_order_state(user_id) if redis_store.client else None
                
                # Determine status
                status = "claimed" if handoff_info else "active"
                
                enriched.append({
                    "user_id": user_id,
                    "last_message_time": conv["last_message_time"],
                    "message_count": conv["message_count"],
                    "is_claimed": handoff_info is not None,
                    "agent_id": handoff_info.get("agent_id") if handoff_info else None,
                    "claimed_at": handoff_info.get("claimed_at") if handoff_info else None,
                    "has_bulk_ordering": bulk_state is not None,
                    "bulk_state": bulk_state.get("state") if bulk_state else None,
                    "status": status
                })
            
            return {
                "status": "success",
                "count": len(enriched),
                "conversations": enriched
            }
        else:
            # Original behavior: only claimed conversations
            if not redis_store.client:
                return {
                    "status": "success",
                    "count": 0,
                    "conversations": []
                }
            
            # Scan for all agent_handoff keys
            cursor = 0
            conversations = []
            
            while True:
                cursor, keys = redis_store.client.scan(cursor, match="agent_handoff:*", count=100)
                
                for key in keys:
                    try:
                        user_id = key.replace("agent_handoff:", "")
                        handoff_info = redis_store.get_agent_handoff(user_id)
                        
                        if handoff_info:
                            # Get bulk ordering state
                            bulk_state = redis_store.get_bulk_order_state(user_id)
                            
                            # Get last message time from database
                            conversation_history = postgres_store.get_conversation_history(user_id, limit=1)
                            last_message_time = conversation_history[0].get("created_at") if conversation_history else None
                            
                            conversations.append({
                                "user_id": user_id,
                                "agent_id": handoff_info.get("agent_id"),
                                "claimed_at": handoff_info.get("claimed_at"),
                                "has_bulk_ordering": bulk_state is not None,
                                "bulk_state": bulk_state.get("state") if bulk_state else None,
                                "last_message_time": last_message_time
                            })
                    except Exception as e:
                        logger.error(f"Error processing conversation {key}: {e}")
                        continue
                
                if cursor == 0:
                    break
            
            return {
                "status": "success",
                "count": len(conversations),
                "conversations": conversations
            }
    except Exception as e:
        logger.error(f"Error listing conversations: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error listing conversations: {str(e)}")


@router.get("/all-conversations")
async def get_all_conversations(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None)
):
    """
    List all conversations with metadata
    Returns all users who have sent messages, not just claimed ones
    """
    try:
        # Get all conversations from database
        conversations = postgres_store.get_all_conversations(
            limit=limit,
            offset=offset,
            date_from=date_from,
            date_to=date_to
        )
        
        # Enrich with handoff and bulk state info
        enriched = []
        for conv in conversations:
            user_id = conv["user_id"]
            
            # Check if claimed
            handoff_info = redis_store.get_agent_handoff(user_id) if redis_store.client else None
            
            # Get bulk ordering state
            bulk_state = redis_store.get_bulk_order_state(user_id) if redis_store.client else None
            
            # Determine status
            status = "claimed" if handoff_info else "active"
            
            enriched.append({
                "user_id": user_id,
                "last_message_time": conv["last_message_time"],
                "message_count": conv["message_count"],
                "is_claimed": handoff_info is not None,
                "agent_id": handoff_info.get("agent_id") if handoff_info else None,
                "claimed_at": handoff_info.get("claimed_at") if handoff_info else None,
                "has_bulk_ordering": bulk_state is not None,
                "bulk_state": bulk_state.get("state") if bulk_state else None,
                "status": status
            })
        
        return {
            "status": "success",
            "count": len(enriched),
            "conversations": enriched,
            "limit": limit,
            "offset": offset
        }
    except Exception as e:
        logger.error(f"Error getting all conversations: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error getting all conversations: {str(e)}")


@router.get("/conversation-stats")
async def get_conversation_stats():
    """
    Get overview statistics for all conversations
    """
    try:
        # Get all conversations
        all_conversations = postgres_store.get_all_conversations(limit=10000)
        
        # Count claimed conversations
        claimed_count = 0
        if redis_store.client:
            cursor = 0
            while True:
                cursor, keys = redis_store.client.scan(cursor, match="agent_handoff:*", count=100)
                claimed_count += len(keys)
                if cursor == 0:
                    break
        
        total_count = len(all_conversations)
        active_count = total_count - claimed_count
        
        # Calculate recent activity (last 24 hours)
        from datetime import datetime, timedelta
        yesterday = (datetime.utcnow() - timedelta(days=1)).isoformat()
        recent_conversations = postgres_store.get_all_conversations(
            limit=10000,
            date_from=yesterday
        )
        recent_count = len(recent_conversations)
        
        # Calculate total messages
        total_messages = sum(conv.get("message_count", 0) for conv in all_conversations)
        
        return {
            "status": "success",
            "stats": {
                "total_conversations": total_count,
                "active_conversations": active_count,
                "claimed_conversations": claimed_count,
                "recent_conversations_24h": recent_count,
                "total_messages": total_messages
            }
        }
    except Exception as e:
        logger.error(f"Error getting conversation stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error getting conversation stats: {str(e)}")

