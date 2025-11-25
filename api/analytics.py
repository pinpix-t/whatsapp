"""
Analytics API endpoints for bulk quote dashboard
Provides endpoints to query bulk quote events from PostgreSQL analytics table
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Query, HTTPException
from sqlalchemy import text, func
from database.postgres_store import postgres_store
import json

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


def parse_jsonb_data(data: Any) -> Dict[str, Any]:
    """Parse JSONB data field from database"""
    if isinstance(data, dict):
        return data
    elif isinstance(data, str):
        try:
            return json.loads(data)
        except:
            return {}
    return {}


@router.get("/quotes")
async def get_quotes(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    product: Optional[str] = Query(None, description="Filter by product name"),
    limit: int = Query(100, ge=1, le=1000, description="Limit results"),
    offset: int = Query(0, ge=0, description="Offset for pagination")
):
    """
    Get bulk quotes with filtering options
    Returns list of quote events with parsed data
    """
    session = postgres_store.get_session()
    if not session:
        raise HTTPException(status_code=503, detail="Database not available")
    
    try:
        # Build query
        query = text("""
            SELECT 
                id,
                event_type,
                user_id,
                email,
                data,
                created_at
            FROM analytics
            WHERE event_type = 'bulk_quote_generated'
        """)
        
        params = {}
        
        # Add date filters
        if start_date:
            query = text(str(query) + " AND created_at >= :start_date")
            params["start_date"] = start_date
        if end_date:
            query = text(str(query) + " AND created_at <= :end_date")
            params["end_date"] = end_date + " 23:59:59"
        
        # Add product filter
        if product:
            query = text(str(query) + " AND data->>'product' = :product")
            params["product"] = product
        
        # Add ordering and pagination
        query = text(str(query) + " ORDER BY created_at DESC LIMIT :limit OFFSET :offset")
        params["limit"] = limit
        params["offset"] = offset
        
        result = session.execute(query, params)
        
        quotes = []
        for row in result:
            data_json = parse_jsonb_data(row.data)
            quotes.append({
                "id": row.id,
                "user_id": row.user_id,
                "email": row.email or data_json.get("email"),
                "product": data_json.get("product", "Unknown"),
                "product_key": data_json.get("product_key", ""),
                "quantity": data_json.get("quantity", 0),
                "discount_code": data_json.get("discount_code"),
                "discount_percent": data_json.get("discount_percent"),
                "base_price": data_json.get("base_price"),
                "unit_price": data_json.get("unit_price"),
                "total_price": data_json.get("total_price"),
                "formatted_unit_price": data_json.get("formatted_unit_price"),
                "formatted_total_price": data_json.get("formatted_total_price"),
                "offer_type": data_json.get("offer_type", ""),
                "postcode": data_json.get("postcode"),
                "selections": data_json.get("selections", {}),
                "created_at": row.created_at.isoformat()
            })
        
        return {
            "success": True,
            "count": len(quotes),
            "quotes": quotes
        }
    except Exception as e:
        logger.error(f"Error fetching quotes: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error fetching quotes: {str(e)}")
    finally:
        session.close()


@router.get("/stats")
async def get_stats(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)")
):
    """
    Get aggregated statistics for bulk quotes
    Returns total quotes, total quantity, total revenue, averages, etc.
    """
    session = postgres_store.get_session()
    if not session:
        raise HTTPException(status_code=503, detail="Database not available")
    
    try:
        # Build base query
        base_query = """
            SELECT 
                COUNT(*) as total_quotes,
                SUM((data->>'quantity')::int) as total_quantity,
                SUM((data->>'total_price')::float) as total_revenue,
                AVG((data->>'quantity')::int) as avg_quantity,
                AVG((data->>'total_price')::float) as avg_revenue,
                AVG((data->>'discount_percent')::float) as avg_discount
            FROM analytics
            WHERE event_type = 'bulk_quote_generated'
        """
        
        params = {}
        
        if start_date:
            base_query += " AND created_at >= :start_date"
            params["start_date"] = start_date
        if end_date:
            base_query += " AND created_at <= :end_date"
            params["end_date"] = end_date + " 23:59:59"
        
        query = text(base_query)
        result = session.execute(query, params).fetchone()
        
        if not result:
            return {
                "success": True,
                "total_quotes": 0,
                "total_quantity": 0,
                "total_revenue": 0.0,
                "avg_quantity": 0.0,
                "avg_revenue": 0.0,
                "avg_discount": 0.0
            }
        
        return {
            "success": True,
            "total_quotes": result.total_quotes or 0,
            "total_quantity": int(result.total_quantity) if result.total_quantity else 0,
            "total_revenue": float(result.total_revenue) if result.total_revenue else 0.0,
            "avg_quantity": float(result.avg_quantity) if result.avg_quantity else 0.0,
            "avg_revenue": float(result.avg_revenue) if result.avg_revenue else 0.0,
            "avg_discount": float(result.avg_discount) if result.avg_discount else 0.0
        }
    except Exception as e:
        logger.error(f"Error fetching stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error fetching stats: {str(e)}")
    finally:
        session.close()


@router.get("/products")
async def get_products(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)")
):
    """
    Get quotes grouped by product
    Returns statistics per product
    """
    session = postgres_store.get_session()
    if not session:
        raise HTTPException(status_code=503, detail="Database not available")
    
    try:
        base_query = """
            SELECT 
                data->>'product' as product,
                COUNT(*) as quote_count,
                SUM((data->>'quantity')::int) as total_quantity,
                SUM((data->>'total_price')::float) as total_revenue,
                AVG((data->>'quantity')::int) as avg_quantity,
                AVG((data->>'total_price')::float) as avg_revenue,
                AVG((data->>'discount_percent')::float) as avg_discount
            FROM analytics
            WHERE event_type = 'bulk_quote_generated'
        """
        
        params = {}
        
        if start_date:
            base_query += " AND created_at >= :start_date"
            params["start_date"] = start_date
        if end_date:
            base_query += " AND created_at <= :end_date"
            params["end_date"] = end_date + " 23:59:59"
        
        base_query += " GROUP BY data->>'product' ORDER BY quote_count DESC"
        
        query = text(base_query)
        result = session.execute(query, params)
        
        products = []
        for row in result:
            products.append({
                "product": row.product or "Unknown",
                "quote_count": row.quote_count,
                "total_quantity": int(row.total_quantity) if row.total_quantity else 0,
                "total_revenue": float(row.total_revenue) if row.total_revenue else 0.0,
                "avg_quantity": float(row.avg_quantity) if row.avg_quantity else 0.0,
                "avg_revenue": float(row.avg_revenue) if row.avg_revenue else 0.0,
                "avg_discount": float(row.avg_discount) if row.avg_discount else 0.0
            })
        
        return {
            "success": True,
            "count": len(products),
            "products": products
        }
    except Exception as e:
        logger.error(f"Error fetching products: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error fetching products: {str(e)}")
    finally:
        session.close()


@router.get("/timeline")
async def get_timeline(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    group_by: str = Query("day", regex="^(day|week|month)$", description="Group by day, week, or month")
):
    """
    Get quotes over time with aggregation
    Returns daily, weekly, or monthly aggregated data
    """
    session = postgres_store.get_session()
    if not session:
        raise HTTPException(status_code=503, detail="Database not available")
    
    try:
        # Determine date truncation based on group_by
        if group_by == "day":
            date_trunc = "DATE(created_at)"
        elif group_by == "week":
            date_trunc = "DATE_TRUNC('week', created_at)"
        elif group_by == "month":
            date_trunc = "DATE_TRUNC('month', created_at)"
        else:
            date_trunc = "DATE(created_at)"
        
        base_query = f"""
            SELECT 
                {date_trunc} as date,
                COUNT(*) as quote_count,
                SUM((data->>'quantity')::int) as total_quantity,
                SUM((data->>'total_price')::float) as total_revenue
            FROM analytics
            WHERE event_type = 'bulk_quote_generated'
        """
        
        params = {}
        
        if start_date:
            base_query += " AND created_at >= :start_date"
            params["start_date"] = start_date
        if end_date:
            base_query += " AND created_at <= :end_date"
            params["end_date"] = end_date + " 23:59:59"
        
        base_query += f" GROUP BY {date_trunc} ORDER BY date DESC"
        
        query = text(base_query)
        result = session.execute(query, params)
        
        timeline = []
        for row in result:
            date_value = row.date
            if isinstance(date_value, datetime):
                date_str = date_value.isoformat()
            else:
                date_str = str(date_value)
            
            timeline.append({
                "date": date_str,
                "quote_count": row.quote_count,
                "total_quantity": int(row.total_quantity) if row.total_quantity else 0,
                "total_revenue": float(row.total_revenue) if row.total_revenue else 0.0
            })
        
        return {
            "success": True,
            "group_by": group_by,
            "count": len(timeline),
            "timeline": timeline
        }
    except Exception as e:
        logger.error(f"Error fetching timeline: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error fetching timeline: {str(e)}")
    finally:
        session.close()



