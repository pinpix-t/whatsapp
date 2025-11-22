"""
Extended Analytics API endpoints
Abandonments, stage transitions, and funnel metrics
"""

import logging
from typing import Optional
from fastapi import Query, HTTPException
from sqlalchemy import text
from database.postgres_store import postgres_store
from api.analytics import router, parse_jsonb_data

logger = logging.getLogger(__name__)


@router.get("/abandonments")
async def get_abandonments(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    state: Optional[str] = Query(None, description="Filter by state where abandoned"),
    flow: Optional[str] = Query(None, description="Filter by flow"),
    limit: int = Query(100, ge=1, le=1000, description="Limit results"),
    offset: int = Query(0, ge=0, description="Offset for pagination")
):
    """Get abandonment events"""
    session = postgres_store.get_session()
    if not session:
        raise HTTPException(status_code=503, detail="Database not available")
    
    try:
        query = text("""
            SELECT id, event_type, user_id, email, data, created_at
            FROM analytics
            WHERE event_type = 'conversation_abandoned'
        """)
        
        params = {}
        if start_date:
            query = text(str(query) + " AND created_at >= :start_date")
            params["start_date"] = start_date
        if end_date:
            query = text(str(query) + " AND created_at <= :end_date")
            params["end_date"] = end_date + " 23:59:59"
        if state:
            query = text(str(query) + " AND data->>'state' = :state")
            params["state"] = state
        if flow:
            query = text(str(query) + " AND data->>'flow' = :flow")
            params["flow"] = flow
        
        query = text(str(query) + " ORDER BY created_at DESC LIMIT :limit OFFSET :offset")
        params["limit"] = limit
        params["offset"] = offset
        
        result = session.execute(query, params)
        
        abandonments = []
        for row in result:
            data_json = parse_jsonb_data(row.data)
            abandonments.append({
                "id": row.id,
                "user_id": row.user_id,
                "email": row.email,
                "flow": data_json.get("flow", "unknown"),
                "state": data_json.get("state", "unknown"),
                "last_message": data_json.get("last_message", ""),
                "time_since_last_message_seconds": data_json.get("time_since_last_message_seconds"),
                "selections": data_json.get("selections", {}),
                "created_at": row.created_at.isoformat()
            })
        
        return {"success": True, "count": len(abandonments), "abandonments": abandonments}
    except Exception as e:
        logger.error(f"Error fetching abandonments: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error fetching abandonments: {str(e)}")
    finally:
        session.close()


@router.get("/abandonments/stats")
async def get_abandonment_stats(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)")
):
    """Get abandonment statistics"""
    session = postgres_store.get_session()
    if not session:
        raise HTTPException(status_code=503, detail="Database not available")
    
    try:
        base_query = """
            SELECT 
                COUNT(*) as total_abandonments,
                AVG((data->>'time_since_last_message_seconds')::float) as avg_time_before_abandonment
            FROM analytics
            WHERE event_type = 'conversation_abandoned'
        """
        
        params = {}
        if start_date:
            base_query += " AND created_at >= :start_date"
            params["start_date"] = start_date
        if end_date:
            base_query += " AND created_at <= :end_date"
            params["end_date"] = end_date + " 23:59:59"
        
        result = session.execute(text(base_query), params).fetchone()
        total_abandonments = result.total_abandonments or 0
        avg_time = float(result.avg_time_before_abandonment) if result.avg_time_before_abandonment else 0.0
        
        state_query = """
            SELECT data->>'state' as state, COUNT(*) as count
            FROM analytics
            WHERE event_type = 'conversation_abandoned'
        """
        if start_date:
            state_query += " AND created_at >= :start_date"
        if end_date:
            state_query += " AND created_at <= :end_date"
        state_query += " GROUP BY data->>'state' ORDER BY count DESC"
        
        state_result = session.execute(text(state_query), params)
        abandonments_by_state = [{"state": row.state or "unknown", "count": row.count} for row in state_result]
        
        return {
            "success": True,
            "total_abandonments": total_abandonments,
            "avg_time_before_abandonment_seconds": avg_time,
            "abandonments_by_state": abandonments_by_state
        }
    except Exception as e:
        logger.error(f"Error fetching abandonment stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error fetching abandonment stats: {str(e)}")
    finally:
        session.close()


@router.get("/stage-transitions")
async def get_stage_transitions(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    flow: Optional[str] = Query(None, description="Filter by flow"),
    from_state: Optional[str] = Query(None, description="Filter by from_state"),
    to_state: Optional[str] = Query(None, description="Filter by to_state"),
    limit: int = Query(100, ge=1, le=1000, description="Limit results"),
    offset: int = Query(0, ge=0, description="Offset for pagination")
):
    """Get stage transition events"""
    session = postgres_store.get_session()
    if not session:
        raise HTTPException(status_code=503, detail="Database not available")
    
    try:
        query = text("""
            SELECT id, event_type, user_id, email, data, created_at
            FROM analytics
            WHERE event_type = 'stage_transition'
        """)
        
        params = {}
        if start_date:
            query = text(str(query) + " AND created_at >= :start_date")
            params["start_date"] = start_date
        if end_date:
            query = text(str(query) + " AND created_at <= :end_date")
            params["end_date"] = end_date + " 23:59:59"
        if flow:
            query = text(str(query) + " AND data->>'flow' = :flow")
            params["flow"] = flow
        if from_state:
            query = text(str(query) + " AND data->>'from_state' = :from_state")
            params["from_state"] = from_state
        if to_state:
            query = text(str(query) + " AND data->>'to_state' = :to_state")
            params["to_state"] = to_state
        
        query = text(str(query) + " ORDER BY created_at DESC LIMIT :limit OFFSET :offset")
        params["limit"] = limit
        params["offset"] = offset
        
        result = session.execute(query, params)
        
        transitions = []
        for row in result:
            data_json = parse_jsonb_data(row.data)
            transitions.append({
                "id": row.id,
                "user_id": row.user_id,
                "from_state": data_json.get("from_state"),
                "to_state": data_json.get("to_state"),
                "flow": data_json.get("flow", "bulk_ordering"),
                "duration_seconds": data_json.get("duration_seconds"),
                "selections": data_json.get("selections", {}),
                "created_at": row.created_at.isoformat()
            })
        
        return {"success": True, "count": len(transitions), "transitions": transitions}
    except Exception as e:
        logger.error(f"Error fetching stage transitions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error fetching stage transitions: {str(e)}")
    finally:
        session.close()


@router.get("/stage-transitions/stats")
async def get_stage_transition_stats(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)")
):
    """Get stage transition statistics"""
    session = postgres_store.get_session()
    if not session:
        raise HTTPException(status_code=503, detail="Database not available")
    
    try:
        params = {}
        base_where = "WHERE event_type = 'stage_transition'"
        
        if start_date:
            base_where += " AND created_at >= :start_date"
            params["start_date"] = start_date
        if end_date:
            base_where += " AND created_at <= :end_date"
            params["end_date"] = end_date + " 23:59:59"
        
        transitions_query = f"""
            SELECT 
                data->>'to_state' as state,
                COUNT(*) as transition_count,
                AVG((data->>'duration_seconds')::float) as avg_duration
            FROM analytics
            {base_where}
            GROUP BY data->>'to_state'
            ORDER BY transition_count DESC
        """
        
        result = session.execute(text(transitions_query), params)
        transitions_per_stage = [
            {
                "state": row.state or "unknown",
                "transition_count": row.transition_count,
                "avg_duration_seconds": float(row.avg_duration) if row.avg_duration else None
            }
            for row in result
        ]
        
        paths_query = f"""
            SELECT 
                data->>'from_state' as from_state,
                data->>'to_state' as to_state,
                COUNT(*) as count
            FROM analytics
            {base_where}
            GROUP BY data->>'from_state', data->>'to_state'
            ORDER BY count DESC
            LIMIT 20
        """
        
        paths_result = session.execute(text(paths_query), params)
        common_paths = [
            {"from_state": row.from_state, "to_state": row.to_state, "count": row.count}
            for row in paths_result
        ]
        
        return {
            "success": True,
            "transitions_per_stage": transitions_per_stage,
            "common_paths": common_paths
        }
    except Exception as e:
        logger.error(f"Error fetching stage transition stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error fetching stage transition stats: {str(e)}")
    finally:
        session.close()


@router.get("/funnel")
async def get_funnel(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)")
):
    """Get funnel metrics"""
    session = postgres_store.get_session()
    if not session:
        raise HTTPException(status_code=503, detail="Database not available")
    
    try:
        params = {}
        base_where = ""
        
        if start_date:
            base_where += " AND created_at >= :start_date"
            params["start_date"] = start_date
        if end_date:
            base_where += " AND created_at <= :end_date"
            params["end_date"] = end_date + " 23:59:59"
        
        starts_query = f"""
            SELECT COUNT(DISTINCT user_id) as count
            FROM analytics
            WHERE event_type = 'flow_started' {base_where}
        """
        starts_result = session.execute(text(starts_query), params).fetchone()
        total_starts = starts_result.count if starts_result else 0
        
        stages_query = f"""
            SELECT 
                data->>'to_state' as state,
                COUNT(DISTINCT user_id) as user_count
            FROM analytics
            WHERE event_type = 'stage_transition' {base_where}
            GROUP BY data->>'to_state'
            ORDER BY user_count DESC
        """
        
        stages_result = session.execute(text(stages_query), params)
        
        funnel_stages = []
        previous_count = total_starts
        
        for row in stages_result:
            state = row.state or "unknown"
            user_count = row.user_count
            
            drop_off_rate = 0.0
            if previous_count > 0:
                drop_off_rate = ((previous_count - user_count) / previous_count) * 100
            
            conversion_rate = 0.0
            if total_starts > 0:
                conversion_rate = (user_count / total_starts) * 100
            
            funnel_stages.append({
                "state": state,
                "user_count": user_count,
                "drop_off_rate": round(drop_off_rate, 2),
                "conversion_rate": round(conversion_rate, 2)
            })
            
            previous_count = user_count
        
        completions_query = f"""
            SELECT COUNT(DISTINCT user_id) as count
            FROM analytics
            WHERE event_type = 'user_action' 
            AND data->>'action_type' = 'button_click'
            AND data->>'action_value' = 'discount_accept'
            {base_where}
        """
        completions_result = session.execute(text(completions_query), params).fetchone()
        total_completions = completions_result.count if completions_result else 0
        
        completion_rate = 0.0
        if total_starts > 0:
            completion_rate = (total_completions / total_starts) * 100
        
        return {
            "success": True,
            "total_starts": total_starts,
            "total_completions": total_completions,
            "completion_rate": round(completion_rate, 2),
            "funnel_stages": funnel_stages
        }
    except Exception as e:
        logger.error(f"Error fetching funnel: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error fetching funnel: {str(e)}")
    finally:
        session.close()


@router.get("/funnel/detailed")
async def get_funnel_detailed(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)")
):
    """Get detailed funnel with time analysis"""
    session = postgres_store.get_session()
    if not session:
        raise HTTPException(status_code=503, detail="Database not available")
    
    try:
        params = {}
        base_where = ""
        
        if start_date:
            base_where += " AND created_at >= :start_date"
            params["start_date"] = start_date
        if end_date:
            base_where += " AND created_at <= :end_date"
            params["end_date"] = end_date + " 23:59:59"
        
        time_query = f"""
            SELECT 
                data->>'to_state' as state,
                AVG((data->>'duration_seconds')::float) as avg_duration,
                COUNT(*) as transition_count
            FROM analytics
            WHERE event_type = 'stage_transition' 
            AND data->>'duration_seconds' IS NOT NULL
            {base_where}
            GROUP BY data->>'to_state'
            ORDER BY avg_duration DESC
        """
        
        time_result = session.execute(text(time_query), params)
        time_per_stage = [
            {
                "state": row.state or "unknown",
                "avg_duration_seconds": float(row.avg_duration) if row.avg_duration else 0.0,
                "transition_count": row.transition_count
            }
            for row in time_result
        ]
        
        dropoff_query = f"""
            SELECT 
                data->>'state' as state,
                COUNT(*) as abandonment_count,
                AVG((data->>'time_since_last_message_seconds')::float) as avg_time_before_abandonment
            FROM analytics
            WHERE event_type = 'conversation_abandoned' {base_where}
            GROUP BY data->>'state'
            ORDER BY abandonment_count DESC
        """
        
        dropoff_result = session.execute(text(dropoff_query), params)
        drop_off_points = [
            {
                "state": row.state or "unknown",
                "abandonment_count": row.abandonment_count,
                "avg_time_before_abandonment_seconds": float(row.avg_time_before_abandonment) if row.avg_time_before_abandonment else 0.0
            }
            for row in dropoff_result
        ]
        
        return {
            "success": True,
            "time_per_stage": time_per_stage,
            "drop_off_points": drop_off_points
        }
    except Exception as e:
        logger.error(f"Error fetching detailed funnel: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error fetching detailed funnel: {str(e)}")
    finally:
        session.close()

