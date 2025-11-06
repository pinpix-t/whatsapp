"""
Script to ingest documents into the vector store.
Place your documents in the data/documents/ folder and run this script.
"""

import os
from rag.vector_store import VectorStore
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    # Create data/documents directory if it doesn't exist
    docs_dir = "./data/documents"
    os.makedirs(docs_dir, exist_ok=True)

    logger.info("🔄 Starting document ingestion...")

    # Initialize vector store
    vector_store = VectorStore()

    # Check if documents directory has files
    if not os.listdir(docs_dir):
        logger.warning(f"⚠️  No documents found in {docs_dir}")
        logger.info("Please add .txt or .json files to the data/documents/ folder and run this script again.")

        # Create a sample document
        sample_file = os.path.join(docs_dir, "sample_knowledge.txt")
        with open(sample_file, "w") as f:
            f.write("""Sample Knowledge Base

This is a sample document for your WhatsApp RAG bot.

Common Questions:
Q: What services do you offer?
A: We offer customer support, product information, and general assistance.

Q: What are your business hours?
A: We are available 24/7 through this automated assistant.

Q: How can I get help?
A: Simply send me a message with your question, and I'll do my best to help!

Product Information:
- Product A: High-quality widget for everyday use
- Product B: Premium widget with advanced features
- Product C: Budget-friendly option for basic needs

Replace this file with your own knowledge base documents!
""")
        logger.info(f"✓ Created sample document: {sample_file}")

    # Ingest all documents
    try:
        total_chunks = vector_store.add_documents(docs_dir)
        logger.info(f"✅ Successfully ingested documents!")
        logger.info(f"📊 Total chunks in database: {total_chunks}")
    except Exception as e:
        logger.error(f"❌ Error ingesting documents: {e}")

    logger.info("\n" + "="*60)
    logger.info("Next steps:")
    logger.info("1. Add your own .txt files to data/documents/")
    logger.info("2. Run this script again to update the knowledge base")
    logger.info("3. Run 'python main.py' to start the bot")
    logger.info("="*60)


if __name__ == "__main__":
    main()
