import chromadb
from chromadb.config import Settings
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import TextLoader, DirectoryLoader
from config.settings import CHROMA_DB_PATH, RETRIEVAL_TOP_K, OPENAI_API_KEY
import os
import json
import csv
import pandas as pd


class VectorStore:
    def __init__(self):
        self.embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)
        self.vector_store = None
        self._initialize_store()

    def _initialize_store(self):
        """Initialize or load existing ChromaDB vector store"""
        if os.path.exists(CHROMA_DB_PATH):
            self.vector_store = Chroma(
                persist_directory=CHROMA_DB_PATH,
                embedding_function=self.embeddings
            )
            print(f"✓ Loaded existing vector store from {CHROMA_DB_PATH}")
        else:
            self.vector_store = Chroma(
                persist_directory=CHROMA_DB_PATH,
                embedding_function=self.embeddings
            )
            print(f"✓ Created new vector store at {CHROMA_DB_PATH}")

    def add_documents(self, file_path):
        """Add documents from a file or directory to the vector store"""
        if os.path.isdir(file_path):
            # Handle both .txt and .json files
            documents = []
            
            # Load .txt files
            txt_loader = DirectoryLoader(file_path, glob="**/*.txt", loader_cls=TextLoader)
            txt_docs = txt_loader.load()
            documents.extend(txt_docs)
            
            # Load .json files
            json_files = []
            for root, dirs, files in os.walk(file_path):
                for file in files:
                    if file.endswith('.json'):
                        json_files.append(os.path.join(root, file))
            
            for json_file in json_files:
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    # Convert JSON to text format for vector store
                    if 'products' in data:
                        text_content = self._json_to_text(data)
                        # Create a document-like object
                        from langchain.schema import Document
                        doc = Document(
                            page_content=text_content,
                            metadata={"source": json_file, "type": "products"}
                        )
                        documents.append(doc)
                except Exception as e:
                    print(f"⚠️  Error loading {json_file}: {e}")
            
            # Load .csv files
            csv_files = []
            for root, dirs, files in os.walk(file_path):
                for file in files:
                    if file.endswith('.csv'):
                        csv_files.append(os.path.join(root, file))
            
            for csv_file in csv_files:
                try:
                    text_content = self._csv_to_text(csv_file)
                    if text_content:
                        from langchain.schema import Document
                        doc = Document(
                            page_content=text_content,
                            metadata={"source": csv_file, "type": "sales_data"}
                        )
                        documents.append(doc)
                except Exception as e:
                    print(f"⚠️  Error loading {csv_file}: {e}")
        else:
            if file_path.endswith('.json'):
                # Handle single JSON file
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    if 'products' in data:
                        text_content = self._json_to_text(data)
                        from langchain.schema import Document
                        doc = Document(
                            page_content=text_content,
                            metadata={"source": file_path, "type": "products"}
                        )
                        documents = [doc]
                    else:
                        documents = []
                except Exception as e:
                    print(f"⚠️  Error loading {file_path}: {e}")
                    documents = []
            elif file_path.endswith('.csv'):
                # Handle single CSV file
                try:
                    text_content = self._csv_to_text(file_path)
                    if text_content:
                        from langchain.schema import Document
                        doc = Document(
                            page_content=text_content,
                            metadata={"source": file_path, "type": "sales_data"}
                        )
                        documents = [doc]
                    else:
                        documents = []
                except Exception as e:
                    print(f"⚠️  Error loading {file_path}: {e}")
                    documents = []
            else:
                loader = TextLoader(file_path)
                documents = loader.load()

        if not documents:
            print("⚠️  No documents to process")
            return 0

        # Split documents into chunks
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )
        splits = text_splitter.split_documents(documents)

        # Add to vector store
        self.vector_store.add_documents(splits)
        print(f"✓ Added {len(splits)} document chunks to vector store")

        return len(splits)

    def _json_to_text(self, data):
        """Convert JSON product data to searchable text format"""
        text_parts = []
        
        if 'products' in data:
            text_parts.append("PRODUCT CATALOG\n")
            
            for product in data['products']:
                # Product name and category
                text_parts.append(f"Product: {product.get('name', 'Unknown')}")
                text_parts.append(f"Category: {product.get('category', 'Unknown')}")
                
                # Description
                if 'description' in product:
                    text_parts.append(f"Description: {product['description']}")
                
                # Key features
                if 'key_features' in product:
                    features = ", ".join(product['key_features'])
                    text_parts.append(f"Features: {features}")
                
                # Sizes and prices
                if 'sizes' in product:
                    for size in product['sizes']:
                        size_info = f"Size: {size.get('name', 'Unknown')}"
                        if 'dimensions' in size:
                            size_info += f" ({size['dimensions']})"
                        if 'price_range' in size:
                            size_info += f" - {size['price_range']}"
                        text_parts.append(size_info)
                
                # Best for
                if 'best_for' in product:
                    best_for = ", ".join(product['best_for'])
                    text_parts.append(f"Best for: {best_for}")
                
                # Materials
                if 'materials' in product:
                    text_parts.append(f"Materials: {product['materials']}")
                
                text_parts.append("")  # Empty line between products
        
        if 'categories' in data:
            text_parts.append("\nCATEGORIES\n")
            for category in data['categories']:
                text_parts.append(f"{category.get('name', 'Unknown')}: {category.get('description', '')}")
        
        if 'shipping_info' in data:
            text_parts.append("\nSHIPPING INFORMATION\n")
            shipping = data['shipping_info']
            for key, value in shipping.items():
                text_parts.append(f"{key.replace('_', ' ').title()}: {value}")
        
        return "\n".join(text_parts)

    def _csv_to_text(self, csv_file):
        """Convert CSV sales data to searchable text format"""
        try:
            df = pd.read_csv(csv_file)
            text_parts = []
            
            text_parts.append("SALES DATA & PRICING\n")
            text_parts.append(f"Total products: {len(df)}")
            text_parts.append(f"Regions: {', '.join(df['Region'].unique())}")
            text_parts.append("")
            
            # Group by region for better searchability
            for region in df['Region'].unique():
                region_data = df[df['Region'] == region]
                text_parts.append(f"REGION: {region}")
                text_parts.append(f"Products available: {len(region_data)}")
                
                # Top selling products in this region
                top_sellers = region_data.nlargest(5, 'items_sold_last_30_days')
                if not top_sellers.empty:
                    text_parts.append("Top selling products:")
                    for _, row in top_sellers.iterrows():
                        product = row['mpn'].replace('_', ' ').title()
                        price = f"£{row['price']:.2f}" if region in ['UK'] else f"€{row['price']:.2f}" if region in ['FR', 'ES', 'IT', 'DE', 'NL'] else f"${row['price']:.2f}"
                        shipping = f"£{row['shipping']:.2f}" if region in ['UK'] else f"€{row['shipping']:.2f}" if region in ['FR', 'ES', 'IT', 'DE', 'NL'] else f"${row['shipping']:.2f}"
                        sold = int(row['items_sold_last_30_days'])
                        text_parts.append(f"  - {product}: {price} + {shipping} shipping ({sold} sold)")
                
                # Price ranges
                min_price = region_data['price'].min()
                max_price = region_data['price'].max()
                currency = "£" if region in ['UK'] else "€" if region in ['FR', 'ES', 'IT', 'DE', 'NL'] else "$"
                text_parts.append(f"Price range: {currency}{min_price:.2f} - {currency}{max_price:.2f}")
                text_parts.append("")
            
            # Product categories analysis
            text_parts.append("PRODUCT CATEGORIES")
            df['category'] = df['mpn'].str.split('_').str[0]
            category_stats = df.groupby('category').agg({
                'price': ['mean', 'min', 'max'],
                'items_sold_last_30_days': 'sum'
            }).round(2)
            
            for category in category_stats.index:
                mean_price = category_stats.loc[category, ('price', 'mean')]
                min_price = category_stats.loc[category, ('price', 'min')]
                max_price = category_stats.loc[category, ('price', 'max')]
                total_sold = int(category_stats.loc[category, ('items_sold_last_30_days', 'sum')])
                
                text_parts.append(f"{category.title()}: £{mean_price:.2f} avg (£{min_price:.2f}-£{max_price:.2f}), {total_sold} sold")
            
            text_parts.append("")
            
            # Popular products globally
            global_popular = df.nlargest(10, 'items_sold_last_30_days')
            text_parts.append("MOST POPULAR PRODUCTS GLOBALLY")
            for _, row in global_popular.iterrows():
                product = row['mpn'].replace('_', ' ').title()
                region = row['Region']
                price = f"£{row['price']:.2f}" if region in ['UK'] else f"€{row['price']:.2f}" if region in ['FR', 'ES', 'IT', 'DE', 'NL'] else f"${row['price']:.2f}"
                sold = int(row['items_sold_last_30_days'])
                text_parts.append(f"  - {product} ({region}): {price} - {sold} sold")
            
            return "\n".join(text_parts)
            
        except Exception as e:
            print(f"Error processing CSV {csv_file}: {e}")
            return ""

    def retrieve(self, query: str, k: int = 3):
        """Retrieve relevant documents for a query (optimized: default k=3 for speed)"""
        if not self.vector_store:
            return []

        results = self.vector_store.similarity_search(query, k=k)
        return results

    def retrieve_with_scores(self, query: str, k: int = RETRIEVAL_TOP_K):
        """Retrieve relevant documents with similarity scores"""
        if not self.vector_store:
            return []

        results = self.vector_store.similarity_search_with_score(query, k=k)
        return results
