# WhatsApp RAG Bot - Production Ready 🚀

A production-ready WhatsApp bot that uses RAG (Retrieval Augmented Generation) and LLM to provide intelligent responses based on your knowledge base.

## ✨ Features

### Core Functionality
- 🤖 WhatsApp Business Cloud API integration
- 📚 RAG-powered responses using ChromaDB vector database
- 🧠 LLM integration (OpenAI GPT-3.5-turbo)
- 💬 Persistent conversation memory with Redis
- 📄 Easy document ingestion and management

### Production Features
- 🐳 **Docker & Docker Compose** - Containerized deployment
- 🔒 **Security** - Rate limiting, input validation, security headers
- 📊 **Monitoring** - Prometheus metrics + Grafana dashboards
- 💾 **Persistent Storage** - Redis (sessions) + PostgreSQL (messages)
- 🔄 **Error Handling** - Retry logic with exponential backoff
- ✅ **Health Checks** - Comprehensive service monitoring
- 🧪 **Testing** - Unit and integration tests with pytest
- 🚀 **CI/CD** - GitHub Actions pipeline
- 📈 **Scalable** - Horizontal scaling ready

## 🚀 Quick Start (Production Deployment)

### One-Command Deployment

```bash
chmod +x start.sh
./start.sh
```

This script will:
1. Validate your environment configuration
2. Ingest documents into the vector store
3. Start all services with Docker Compose
4. Display health status and next steps

### Manual Setup

#### 1. Configure Environment

```bash
cp .env.example .env
# Edit .env with your credentials
```

Required variables:
- `OPENAI_API_KEY` - Your OpenAI API key
- `WHATSAPP_TOKEN` - WhatsApp Business API token
- `PHONE_NUMBER_ID` - Your WhatsApp phone number ID
- `WEBHOOK_VERIFY_TOKEN` - Custom webhook verification token

#### 2. Add Your Knowledge Base

```bash
mkdir -p data/documents
# Place your .txt files in data/documents/
python ingest_documents.py
```

#### 3. Start Services

```bash
docker-compose up -d
```

#### 4. Configure Webhook

Expose your server (for testing, use ngrok):
```bash
ngrok http 8000
```

Then in Meta Developer Console:
- Webhook URL: `https://your-domain.com/webhook`
- Verify Token: (from your `.env` file)
- Subscribe to `messages` field

## 🔧 Development Setup

For local development without Docker:

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Start Redis and PostgreSQL separately
# or use: docker-compose up -d redis postgres

python main.py
```

## How It Works

1. **Message Detection**: Bot monitors WhatsApp Web for unread messages
2. **Context Retrieval**: Searches vector database for relevant knowledge
3. **LLM Generation**: Uses OpenAI to generate contextual responses
4. **Auto Reply**: Sends intelligent responses back to users

## Project Structure

```
whatsapp/
├── main.py                 # Main bot entry point
├── ingest_documents.py     # Document ingestion script
├── requirements.txt        # Python dependencies
├── .env                    # Environment variables (create this)
├── config/
│   └── settings.py        # Configuration settings
├── bot/
│   ├── whatsapp_client.py # WhatsApp Web automation
│   └── llm_handler.py     # LLM and RAG logic
├── rag/
│   └── vector_store.py    # Vector database management
└── data/
    └── documents/         # Your knowledge base files (.txt)
```

## Usage Tips

- **Add more documents**: Just place `.txt` files in `data/documents/` and run `ingest_documents.py` again
- **Session persistence**: The bot saves your WhatsApp Web session in `whatsapp_session/` so you don't need to scan QR every time
- **Conversation memory**: Each contact has separate conversation history
- **Rate limiting**: Bot waits 5 seconds between message checks to avoid detection

## Customization

### Change the LLM model
Edit `bot/llm_handler.py`, line 16:
```python
model="gpt-4"  # or gpt-4-turbo, etc.
```

### Adjust retrieval settings
Edit `config/settings.py`:
```python
RETRIEVAL_TOP_K = 5  # Retrieve more context
```

### Modify the bot personality
Edit the prompt in `bot/llm_handler.py`, lines 23-34

## 📊 Monitoring & Operations

### Health Check
```bash
curl http://localhost:8000/health
```

### Metrics
- Prometheus: `http://localhost:9090`
- Grafana: `http://localhost:3000`
- Metrics endpoint: `http://localhost:8000/metrics`

### Logs
```bash
# View application logs
docker-compose logs -f app

# View all services
docker-compose logs -f
```

### Common Operations
```bash
# Restart services
docker-compose restart app

# Stop all services
docker-compose down

# View running containers
docker-compose ps

# Run tests
pytest tests/ -v --cov
```

## 📚 Documentation

- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Complete deployment guide
- **[PRODUCTION_READY.md](PRODUCTION_READY.md)** - Production readiness checklist
- **[.env.example](.env.example)** - Environment variables reference

## 🏗️ Architecture

Production architecture with Redis, PostgreSQL, and monitoring stack. See [PRODUCTION_READY.md](PRODUCTION_READY.md) for detailed architecture diagram.

## Troubleshooting

**Bot not detecting messages?**
- WhatsApp Web XPaths may have changed - check `bot/whatsapp_client.py`
- Make sure chats are not archived

**ChromaDB errors?**
- Delete `chroma_db/` folder and re-run `ingest_documents.py`

**OpenAI errors?**
- Verify your API key in `.env`
- Check your OpenAI account has credits

## License

MIT
