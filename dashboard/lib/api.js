/**
 * API client for calling FastAPI backend analytics endpoints
 */

import axios from 'axios';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

/**
 * Get bulk quotes with filtering
 * @param {Object} params - Query parameters
 * @param {string} params.start_date - Start date (YYYY-MM-DD)
 * @param {string} params.end_date - End date (YYYY-MM-DD)
 * @param {string} params.product - Filter by product name
 * @param {number} params.limit - Limit results (default: 100)
 * @param {number} params.offset - Offset for pagination (default: 0)
 * @returns {Promise<Object>} Response with quotes array
 */
export async function getQuotes(params = {}) {
  try {
    const response = await api.get('/api/analytics/quotes', { params });
    return response.data;
  } catch (error) {
    console.error('Error fetching quotes:', error);
    throw error;
  }
}

/**
 * Get aggregated statistics
 * @param {Object} params - Query parameters
 * @param {string} params.start_date - Start date (YYYY-MM-DD)
 * @param {string} params.end_date - End date (YYYY-MM-DD)
 * @returns {Promise<Object>} Statistics object
 */
export async function getStats(params = {}) {
  try {
    const response = await api.get('/api/analytics/stats', { params });
    return response.data;
  } catch (error) {
    console.error('Error fetching stats:', error);
    throw error;
  }
}

/**
 * Get quotes grouped by product
 * @param {Object} params - Query parameters
 * @param {string} params.start_date - Start date (YYYY-MM-DD)
 * @param {string} params.end_date - End date (YYYY-MM-DD)
 * @returns {Promise<Object>} Response with products array
 */
export async function getProducts(params = {}) {
  try {
    const response = await api.get('/api/analytics/products', { params });
    return response.data;
  } catch (error) {
    console.error('Error fetching products:', error);
    throw error;
  }
}

/**
 * Get quotes over time (timeline)
 * @param {Object} params - Query parameters
 * @param {string} params.start_date - Start date (YYYY-MM-DD)
 * @param {string} params.end_date - End date (YYYY-MM-DD)
 * @param {string} params.group_by - Group by 'day', 'week', or 'month' (default: 'day')
 * @returns {Promise<Object>} Response with timeline array
 */
export async function getTimeline(params = {}) {
  try {
    const response = await api.get('/api/analytics/timeline', { params });
    return response.data;
  } catch (error) {
    console.error('Error fetching timeline:', error);
    throw error;
  }
}

/**
 * Get abandonment events
 * @param {Object} params - Query parameters
 * @param {string} params.start_date - Start date (YYYY-MM-DD)
 * @param {string} params.end_date - End date (YYYY-MM-DD)
 * @param {string} params.state - Filter by state
 * @param {string} params.flow - Filter by flow
 * @param {number} params.limit - Limit results
 * @param {number} params.offset - Offset for pagination
 * @returns {Promise<Object>} Response with abandonments array
 */
export async function getAbandonments(params = {}) {
  try {
    const response = await api.get('/api/analytics/abandonments', { params });
    return response.data;
  } catch (error) {
    console.error('Error fetching abandonments:', error);
    throw error;
  }
}

/**
 * Get abandonment statistics
 * @param {Object} params - Query parameters
 * @param {string} params.start_date - Start date (YYYY-MM-DD)
 * @param {string} params.end_date - End date (YYYY-MM-DD)
 * @returns {Promise<Object>} Abandonment statistics
 */
export async function getAbandonmentStats(params = {}) {
  try {
    const response = await api.get('/api/analytics/abandonments/stats', { params });
    return response.data;
  } catch (error) {
    console.error('Error fetching abandonment stats:', error);
    throw error;
  }
}

/**
 * Get stage transition events
 * @param {Object} params - Query parameters
 * @param {string} params.start_date - Start date (YYYY-MM-DD)
 * @param {string} params.end_date - End date (YYYY-MM-DD)
 * @param {string} params.flow - Filter by flow
 * @param {string} params.from_state - Filter by from_state
 * @param {string} params.to_state - Filter by to_state
 * @param {number} params.limit - Limit results
 * @param {number} params.offset - Offset for pagination
 * @returns {Promise<Object>} Response with transitions array
 */
export async function getStageTransitions(params = {}) {
  try {
    const response = await api.get('/api/analytics/stage-transitions', { params });
    return response.data;
  } catch (error) {
    console.error('Error fetching stage transitions:', error);
    throw error;
  }
}

/**
 * Get stage transition statistics
 * @param {Object} params - Query parameters
 * @param {string} params.start_date - Start date (YYYY-MM-DD)
 * @param {string} params.end_date - End date (YYYY-MM-DD)
 * @returns {Promise<Object>} Stage transition statistics
 */
export async function getStageTransitionStats(params = {}) {
  try {
    const response = await api.get('/api/analytics/stage-transitions/stats', { params });
    return response.data;
  } catch (error) {
    console.error('Error fetching stage transition stats:', error);
    throw error;
  }
}

/**
 * Get funnel metrics
 * @param {Object} params - Query parameters
 * @param {string} params.start_date - Start date (YYYY-MM-DD)
 * @param {string} params.end_date - End date (YYYY-MM-DD)
 * @returns {Promise<Object>} Funnel metrics
 */
export async function getFunnel(params = {}) {
  try {
    const response = await api.get('/api/analytics/funnel', { params });
    return response.data;
  } catch (error) {
    console.error('Error fetching funnel:', error);
    throw error;
  }
}

/**
 * Get detailed funnel with time analysis
 * @param {Object} params - Query parameters
 * @param {string} params.start_date - Start date (YYYY-MM-DD)
 * @param {string} params.end_date - End date (YYYY-MM-DD)
 * @returns {Promise<Object>} Detailed funnel data
 */
export async function getFunnelDetailed(params = {}) {
  try {
    const response = await api.get('/api/analytics/funnel/detailed', { params });
    return response.data;
  } catch (error) {
    console.error('Error fetching detailed funnel:', error);
    throw error;
  }
}

