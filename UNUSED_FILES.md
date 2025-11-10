# Unused Code Files Analysis

## ✅ Files That ARE Used (Keep These)

### Core Application Files
- `main.py` - Entry point
- `api/webhook.py` - Main webhook handler
- `bot/whatsapp_api.py` - WhatsApp API client
- `bot/llm_handler.py` - LLM handler
- `rag/vector_store.py` - Vector store
- `database/redis_store.py` - Redis store
- `database/sql_server_store.py` - SQL Server store (NEW)
- `utils/error_handler.py` - Error handling
- `utils/retry.py` - Retry logic
- `config/settings.py` - Settings
- `ingest_documents.py` - Document ingestion (used on startup)

### Services (All Used)
- `services/bulk_ordering.py` - Bulk ordering flow ✅
- `services/bulk_pricing.py` - Bulk pricing ✅
- `services/freshdesk_service.py` - Freshdesk tickets ✅
- `services/region_lookup.py` - Region lookup ✅
- `services/order_tracking.py` - Order tracking ✅

### Config Files (All Used)
- `config/bulk_products.py` - Product config ✅
- `config/bulk_product_mapping.py` - Product mapping ✅
- `config/bulk_product_page_ids.py` - Page IDs ✅
- `config/bulk_base_prices.py` - Base prices fallback ✅

---

## ❌ Files That Are NOT Used (Can Delete)

### Test/Exploration Scripts (Not Used in Production)
1. `test_sql_server_connection.py` - Test script
2. `test_bulk_pricing_flow.py` - Test script
3. `test_freshdesk.py` - Test script
4. `test_freshdesk_fallback.py` - Test script
5. `test_freshdesk_real.py` - Test script
6. `test_pricing_from_sql.py` - Test script
7. `test_send_message.py` - Test script
8. `check_pricing_capabilities.py` - Exploration script
9. `check_pricing_table.py` - Exploration script
10. `check_sherpa_baby_price.py` - Exploration script
11. `explore_sql_server_pricing.py` - Exploration script
12. `explain_pricing_flow.py` - Explanation script

### Utility Scripts (One-Time Use)
13. `parse_pricing_files.py` - Used to parse Excel files (one-time)
14. `update_base_prices.py` - Used to update base prices (one-time)
15. `check_pricing_table.py` - Used to check Supabase table structure (one-time)

### Potentially Unused
16. `services/intent_classifier.py` - **NOT IMPORTED ANYWHERE** ❌
17. `database/postgres_store.py` - **NOT IMPORTED ANYWHERE** ❌

---

## ⚠️ Files to Verify

### 1. `services/intent_classifier.py`
- **Status**: Not imported anywhere
- **Action**: Check if this was meant to be used but isn't
- **Recommendation**: Delete if not needed, or integrate if it should be used

### 2. `database/postgres_store.py`
- **Status**: Not imported anywhere
- **Action**: Check if PostgreSQL is actually used
- **Recommendation**: Keep if you plan to use it, delete if not

---

## 📋 Summary

**Files to Delete (Safe to Remove):**
- All `test_*.py` files (12 files)
- All `check_*.py` files (3 files)
- All `explore_*.py` files (1 file)
- All `explain_*.py` files (1 file)
- `parse_pricing_files.py` (one-time use)
- `update_base_prices.py` (one-time use)

**Files to Verify:**
- `services/intent_classifier.py` - Not used anywhere
- `database/postgres_store.py` - Not used anywhere

**Total Unused Files: ~18 files**

