# Technical Overview: Base Agent Deployment

## 1. Architecture Overview

### 1.1 Deployment Architecture

The base agent is a **production-ready WhatsApp RAG (Retrieval Augmented Generation) bot** deployed using a microservices architecture with containerization.

**Core Stack:**
- **Runtime**: Python 3.11 (slim container)
- **Web Framework**: FastAPI with Uvicorn
- **Deployment**: Docker + Docker Compose (production), Railway (cloud)
- **Reverse Proxy**: Nginx (optional, for production)

**Services Architecture:**
```
┌─────────────────┐
│   WhatsApp API   │
│   (Meta/Facebook)│
└────────┬────────┘
         │ Webhook
         │
┌────────▼────────┐
│  FastAPI App   │  ◄─── Main Application
│  (Port 8000)   │
└────────┬────────┘
         │
    ┌────┴────┬─────────────┬─────────────┐
    │         │             │             │
┌───▼───┐ ┌──▼───┐   ┌──────▼──────┐ ┌───▼────┐
│ Redis │ │PostgreSQL│ │ ChromaDB   │ │OpenAI │
│Session│ │Messages  │ │Vector Store│ │ LLM   │
└───────┘ └─────────┘ └────────────┘ └───────┘
```

### 1.2 Entry Point

**Main Application**: `main.py`
- Starts Uvicorn server on port 8000 (configurable)
- Loads FastAPI app from `api/webhook.py`
- Auto-ingests documents into vector store on startup if empty

**Webhook Server**: `api/webhook.py`
- FastAPI application handling WhatsApp webhook callbacks
- Routes:
  - `GET /` - Health check
  - `GET /webhook` - Webhook verification
  - `POST /webhook` - Message processing
  - `GET /health` - Detailed health check
  - `GET /test-vector-store` - Vector store testing

---

## 2. Current Functionality

### 2.1 Core Messaging Features

#### Message Processing Pipeline
1. **Webhook Reception** (`POST /webhook`)
   - Receives incoming WhatsApp messages from Meta
   - Extracts message data (sender, text, interactive elements)
   - Asynchronously processes messages (non-blocking)

2. **Message Types Supported**:
   - **Text Messages**: Standard text-based queries
   - **Interactive Buttons**: Button clicks (up to 3 buttons)
   - **Interactive Lists**: Dropdown menu selections

3. **Response Generation**:
   - Immediate typing indicator feedback
   - Context-aware responses using RAG
   - Interactive button/menu options
   - Conversation memory management

#### Conversation Management
- **Per-User Sessions**: Redis-backed conversation history
- **Memory Window**: Last 6-10 messages per user
- **TTL**: 24 hours default expiration
- **Reset Commands**: `restart`, `reset`, `cancel`, `end`, `stop`, `exit`, `start over`, `new order`, `bye`

### 2.2 RAG (Retrieval Augmented Generation) System

**Vector Store**: ChromaDB with OpenAI embeddings
- **Embedding Model**: OpenAI Embeddings (via LangChain)
- **Chunking**: RecursiveCharacterTextSplitter (1000 chars, 200 overlap)
- **Retrieval**: Top-K similarity search (default k=3)
- **Documents Supported**:
  - `.txt` files (plain text)
  - `.json` files (product catalogs)
  - `.csv` files (sales data)

**Knowledge Base Structure**:
```
data/documents/
├── company_info.txt      # Company information
├── faq.txt               # Frequently asked questions
├── policies.txt          # Company policies
├── products_catalog.txt  # Product descriptions
├── products.json         # Structured product data
└── hmm.csv              # Sales/pricing data
```

**RAG Workflow**:
1. User query → Vector similarity search
2. Retrieve top-K relevant chunks
3. Format context for LLM
4. Generate response with retrieved context
5. Validate response to prevent hallucinations

### 2.3 LLM Integration

**Model**: OpenAI GPT-4o-mini (configurable)
- **Temperature**: 0.7
- **Timeout**: 30 seconds
- **Prompt Engineering**: Anti-hallucination rules enforced

**Response Optimization**:
- **Fast Path**: Greetings bypass RAG (instant response)
- **Caching**: Redis cache for common queries (1 hour TTL)
- **Parallel Processing**: Conversation history + vector retrieval run concurrently

**Anti-Hallucination Measures**:
- Strict context-only responses
- Validation checks for unsupported claims
- "I don't know" responses when context is insufficient
- Response length limits (1-3 sentences recommended)

### 2.4 Specialized Features

#### A. Welcome Flow
- **First Message Detection**: Sends interactive buttons on initial contact
- **Welcome Buttons**:
  1. General FAQ
  2. Track My Order
  3. Bulk Ordering

#### B. Bulk Ordering Service (`services/bulk_ordering.py`)
**State Machine Flow**:
```
1. Product Selection (Interactive List)
   ↓
2. Product Specifications (Buttons/Lists)
   ↓
3. Quantity Input (Text)
   ↓
4. Email Collection (Text)
   ↓
5. Postcode (Optional Text)
   ↓
6. Discount Code Offer (Interactive Buttons)
   ├─→ Accept → Complete
   └─→ Reject → Rejection Options
       ├─→ Price Concern → Second Discount
       ├─→ Delivery Time → RAG Response
       └─→ Talk to Agent → Human Handoff
```

**Features**:
- Multi-step conversation flow
- Product configuration via interactive elements
- Discount code generation and delivery
- Email/postcode collection
- Agent handoff capability

#### C. Order Tracking Service (`services/order_tracking.py`)
**API Integration**: PrinterPix Order Tracking API
- **Endpoint**: `https://ediapi.printerpix.com/track-my-order/website`
- **Supported Countries**: UK, US, FR, ES, IT, NL, DE, AE, IN
- **Order Number Format**: 8-10 digits with country code prefix

**Features**:
- Automatic order number extraction from messages
- Multi-package tracking support
- Natural language status formatting
- Error handling with user-friendly messages

### 2.5 Interactive UI Components

#### Interactive Buttons
- Up to 3 buttons per message
- Button click handling
- State management for button flows

#### Interactive Lists (Dropdowns)
- Multi-section lists
- Product selection menus
- Configuration options

### 2.6 Error Handling & Resilience

**Retry Logic** (`utils/retry.py`):
- Exponential backoff for API calls
- Database operation retries
- Configurable max attempts

**Error Handlers** (`utils/error_handler.py`):
- Custom exception classes:
  - `WhatsAppAPIError`
  - `LLMError`
  - `OrderTrackingError`
- Graceful degradation
- User-friendly error messages
- Comprehensive logging

---

## 3. Integration Points

### 3.1 External APIs

#### A. WhatsApp Business Cloud API
**Base URL**: `https://graph.facebook.com/v18.0`
**Authentication**: Bearer token
**Endpoints Used**:
- `POST /{PHONE_NUMBER_ID}/messages` - Send messages
- `POST /{PHONE_NUMBER_ID}/messages` (status=read) - Mark as read

**Message Types Supported**:
- Text messages
- Template messages (for initial conversations)
- Interactive buttons
- Interactive lists

**Implementation**: `bot/whatsapp_api.py`
- Async HTTP client (httpx)
- Retry logic with exponential backoff
- Error handling with detailed logging

#### B. OpenAI API
**Services Used**:
1. **Embeddings API**: For vector store embeddings
   - Used in: `rag/vector_store.py`
   - Model: OpenAI Embeddings (default)

2. **Chat Completions API**: For LLM responses
   - Model: `gpt-4o-mini` (configurable)
   - Used in: `bot/llm_handler.py`
   - Features: Async invocation, streaming support (future)

**Configuration**:
- API Key: `OPENAI_API_KEY` environment variable
- Rate limiting handled by OpenAI SDK
- Timeout: 30 seconds

#### C. PrinterPix Order Tracking API
**Base URL**: `https://ediapi.printerpix.com/track-my-order/website`
**Method**: GET
**Parameters**:
- `webSiteCode`: Country code (4=UK, 6=US, etc.)
- `orderNo`: Order number (8-10 digits)

**Implementation**: `services/order_tracking.py`
- Synchronous requests (could be async-ified)
- Retry logic for transient failures
- Response parsing and formatting

### 3.2 Data Stores

#### A. Redis (`database/redis_store.py`)
**Purpose**: Session management and caching
**Connection**: Connection pool (max 50 connections)
**Use Cases**:
1. **Conversation History**:
   - Key: `conversation:{user_id}`
   - TTL: 24 hours (86400s)
   - Structure: List of message dicts `[{"role": "user|assistant", "content": "..."}]`

2. **Response Caching**:
   - Key: `cache:{hash(query)}`
   - TTL: 1 hour (3600s)
   - Purpose: Cache common queries for performance

3. **Bulk Order State**:
   - Key: `bulk_order:{user_id}`
   - TTL: 1 hour (3600s)
   - Structure: `{"state": "...", "selections": {...}, "discount_offers": [...]}`

**Configuration**:
- URL: `REDIS_URL` environment variable
- Default: `redis://localhost:6379/0`
- Health checks: 30-second intervals

#### B. PostgreSQL (`database/postgres_store.py`)
**Purpose**: Persistent message storage (currently minimal usage)
**Schema**: Defined in `init.sql`
**Usage**: 
- Message logging (potential)
- Analytics (potential)
- Currently Redis is primary storage

**Configuration**:
- URL: `DATABASE_URL` environment variable
- Default: `postgresql://botuser:changeme123@localhost:5432/whatsapp_bot`

#### C. ChromaDB (`rag/vector_store.py`)
**Purpose**: Vector database for RAG
**Storage**: Local filesystem (persistent directory)
**Path**: `CHROMA_DB_PATH` (default: `./chroma_db`)
**Features**:
- Persistent embeddings
- Similarity search
- Document metadata

**Deployment Note**:
- Railway deployment uses volume mount: `/app/chroma_db`
- Auto-ingestion on startup if vector store is empty

### 3.3 Configuration Management

**Settings File**: `config/settings.py`
**Environment Variables** (loaded from `.env`):

```python
# LLM
OPENAI_API_KEY
ANTHROPIC_API_KEY (optional, for future Claude support)

# WhatsApp
WHATSAPP_TOKEN
PHONE_NUMBER_ID
BUSINESS_ID
WEBHOOK_VERIFY_TOKEN

# Databases
REDIS_URL
DATABASE_URL

# Vector Store
CHROMA_DB_PATH

# Bot Configuration
BOT_NAME
MAX_CONTEXT_LENGTH = 4000
RETRIEVAL_TOP_K = 3
PORT = 8000

# Environment
ENVIRONMENT (development/production)
DEBUG

# Security
APP_SECRET
ALLOWED_IPS
ENABLE_WEBHOOK_VERIFICATION
```

### 3.4 Deployment Integrations

#### A. Docker Deployment
**Files**:
- `Dockerfile`: Multi-stage build (builder + production)
- `docker-compose.production.yml`: Production orchestration

**Services**:
1. **App Container**: Main application
2. **Redis Container**: Session store
3. **PostgreSQL Container**: Persistent storage
4. **Nginx Container**: Reverse proxy (optional)

**Features**:
- Health checks for all services
- Resource limits (CPU/Memory)
- Volume mounts for persistent data
- Network isolation

#### B. Railway Deployment
**Configuration**: `railway.json`
**Features**:
- GitHub integration for auto-deployment
- Auto-detection of Dockerfile
- Environment variable management
- Volume mounts for ChromaDB
- Auto-generated database URLs

**Deployment Steps**:
1. Connect GitHub repository
2. Add Postgres + Redis services
3. Configure environment variables
4. Add volume for ChromaDB persistence
5. Deploy

#### C. Health Monitoring
**Endpoints**:
- `GET /health`: Comprehensive health check
  - Vector store status
  - Redis connectivity
  - OpenAI API key presence
  - WhatsApp API configuration

**Logging**:
- Structured logging with timestamps
- Log levels: INFO, ERROR, WARNING, DEBUG
- Request/response logging
- Error stack traces

### 3.5 Service Integrations

#### A. Bulk Ordering Service Integration
**Entry Points**:
- Interactive button: `btn_bulk`
- State management: Redis-backed
- WhatsApp API: Interactive buttons/lists for UI
- LLM Handler: Delivery time questions (RAG)

**Flow Coordination**:
- `api/webhook.py` → `services/bulk_ordering.py`
- State transitions tracked in Redis
- User input validation and processing

#### B. Order Tracking Service Integration
**Entry Points**:
- Message pattern matching (order tracking keywords)
- Order number extraction via regex
- LLM Handler routing: `_is_order_tracking_request()`

**Flow**:
- User asks about order → LLM Handler detects → Order Tracking Service → API call → Formatted response

#### C. LLM Handler Integration
**Components Integrated**:
- Vector Store: Context retrieval
- Redis Store: Conversation memory
- WhatsApp API: Interactive UI elements
- Order Tracking Service: Special routing

**Response Pipeline**:
1. Check conversation state (first message?)
2. Check cache
3. Detect message type (greeting/order tracking/vague)
4. Retrieve context (parallel: history + vector search)
5. Generate response
6. Validate response
7. Store in conversation history + cache

---

## 4. Data Flow

### 4.1 Message Processing Flow

```
WhatsApp User
    │
    │ Sends Message
    ▼
Meta WhatsApp API
    │
    │ Webhook POST
    ▼
FastAPI /webhook (POST)
    │
    │ Extract message data
    ▼
process_message() [async]
    │
    │ Route by type
    ├─→ Interactive Button/List → Bulk Ordering Service
    │
    ├─→ Text Message
    │   │
    │   ├─→ First Message? → Send Welcome Buttons
    │   │
    │   ├─→ Reset Command? → Clear State + Goodbye
    │   │
    │   ├─→ In Bulk Flow? → Bulk Ordering Handler
    │   │
    │   └─→ Normal Message → LLM Handler
    │       │
    │       ├─→ Check Cache
    │       │
    │       ├─→ Greeting? → Fast Response
    │       │
    │       ├─→ Order Tracking? → Order Tracking Service
    │       │
    │       └─→ RAG Flow
    │           │
    │           ├─→ Get Conversation History (Redis)
    │           │
    │           ├─→ Retrieve Context (ChromaDB) [Parallel]
    │           │
    │           ├─→ Generate Response (OpenAI)
    │           │
    │           ├─→ Validate Response
    │           │
    │           └─→ Store in History + Cache
    │
    └─→ Send Response (WhatsApp API)
```

### 4.2 RAG Response Generation

```
User Query
    │
    ├─→ Vector Store Similarity Search (ChromaDB)
    │   └─→ Top-K Relevant Chunks (k=3)
    │
    ├─→ Conversation History (Redis)
    │   └─→ Last 6-10 Messages
    │
    ├─→ Format Prompt
    │   ├─→ History
    │   ├─→ Context (retrieved chunks)
    │   └─→ User Message
    │
    └─→ LLM Generation (OpenAI)
        ├─→ Response Generation
        ├─→ Validation
        └─→ Cache + Store
```

---

## 5. Security & Configuration

### 5.1 Security Features

1. **Webhook Verification**:
   - Token-based verification (`WEBHOOK_VERIFY_TOKEN`)
   - GET request challenge/response

2. **API Authentication**:
   - WhatsApp: Bearer token
   - OpenAI: API key

3. **CORS Configuration**:
   - Configurable origins (currently `*` for development)
   - Should be restricted in production

4. **Input Validation**:
   - Message content validation
   - Order number format validation
   - Email format validation

5. **Error Handling**:
   - No sensitive data in error messages
   - Structured error responses
   - Comprehensive logging (no secrets)

### 5.2 Environment Configuration

**Production Checklist**:
- [ ] `ENVIRONMENT=production`
- [ ] `DEBUG=false`
- [ ] `WEBHOOK_VERIFY_TOKEN` set to strong value
- [ ] `APP_SECRET` configured
- [ ] CORS origins restricted
- [ ] `ALLOWED_IPS` configured if needed
- [ ] Database URLs use secure credentials
- [ ] SSL/TLS enabled (via Nginx or Railway)

---

## 6. Scalability Considerations

### 6.1 Current Limitations

- **Single Instance**: No horizontal scaling yet
- **Synchronous Components**: Some services use sync requests
- **Redis**: Single instance (can be clustered)
- **ChromaDB**: Local filesystem (not distributed)

### 6.2 Scalability Options

1. **Horizontal Scaling**:
   - Multiple FastAPI instances behind load balancer
   - Shared Redis cluster
   - Distributed ChromaDB (future: cloud vector DB)

2. **Async Improvements**:
   - Convert Order Tracking Service to async
   - Use async HTTP clients throughout

3. **Caching Strategy**:
   - Expand Redis caching
   - CDN for static assets (future)

4. **Database Optimization**:
   - PostgreSQL connection pooling (already configured)
   - Redis connection pooling (already configured)

---

## 7. Monitoring & Observability

### 7.1 Health Checks

- **Basic**: `GET /` - Quick status
- **Detailed**: `GET /health` - Component-level status
- **Vector Store**: `GET /test-vector-store` - Data availability

### 7.2 Logging

**Log Levels**:
- INFO: Normal operations
- WARNING: Recoverable issues
- ERROR: Failures requiring attention
- DEBUG: Detailed debugging (development only)

**Log Output**:
- Structured format: `timestamp - logger - level - message`
- Request/response logging
- Error stack traces

### 7.3 Metrics (Future)

- Request count
- Response times
- Error rates
- LLM token usage
- Cache hit rates

---

## 8. Dependencies

**Core Dependencies** (`requirements.txt`):
- `fastapi` - Web framework
- `uvicorn` - ASGI server
- `langchain` - LLM orchestration
- `langchain-openai` - OpenAI integration
- `langchain-community` - Community integrations
- `chromadb` - Vector database
- `redis` - Session store
- `httpx` - Async HTTP client
- `openai` - OpenAI SDK
- `psycopg2` - PostgreSQL adapter
- `python-dotenv` - Environment management

---

## 9. Development & Testing

### 9.1 Local Development

```bash
# Setup
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run
python main.py

# Ingest documents
python ingest_documents.py
```

### 9.2 Testing Endpoints

- Health: `http://localhost:8000/health`
- Webhook: `http://localhost:8000/webhook`
- Vector Store: `http://localhost:8000/test-vector-store`

### 9.3 Testing Tools

- `test_send_message.py` - Manual message testing
- Webhook verification: `curl` commands
- Health checks: Automated monitoring

---

## 10. Future Enhancements

### 10.1 Planned Features

1. **Multi-Language Support**: Locale detection and responses
2. **Analytics Dashboard**: User metrics and insights
3. **Agent Handoff**: Seamless human agent transfer
4. **File/Media Handling**: Image/document processing
5. **Voice Messages**: Voice input/output support

### 10.2 Technical Improvements

1. **Full Async Migration**: Convert all sync operations
2. **Distributed Vector Store**: Cloud vector DB integration
3. **Enhanced Caching**: Multi-layer caching strategy
4. **Rate Limiting**: Per-user and global rate limits
5. **Monitoring Integration**: Prometheus + Grafana

---

## Summary

The base agent deployment is a **production-ready WhatsApp RAG bot** with:

✅ **Core Functionality**: RAG-powered responses, conversation memory, specialized services
✅ **Integrations**: WhatsApp API, OpenAI, Order Tracking, Bulk Ordering
✅ **Deployment**: Docker + Railway ready
✅ **Resilience**: Error handling, retries, health checks
✅ **Scalability**: Architecture supports horizontal scaling
✅ **Security**: Webhook verification, input validation, secure configuration

**Key Strengths**:
- Modular architecture (easy to extend)
- Comprehensive error handling
- State management for complex flows
- Performance optimizations (caching, parallel processing)

**Areas for Enhancement**:
- Full async migration
- Distributed vector store
- Enhanced monitoring
- Multi-language support

