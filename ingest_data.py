# Script to run ONCE to load data into AstraDB

import os
import pandas as pd
from dotenv import load_dotenv
from langchain.schema import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_ollama import OllamaEmbeddings
from langchain_astradb import AstraDBVectorStore

print("Starting data ingestion process...")

# Load environment variables
load_dotenv()
ASTRA_DB_API_ENDPOINT = os.getenv("ASTRA_DB_API_ENDPOINT")
ASTRA_DB_TOKEN = os.getenv("ASTRA_DB_TOKEN")

# --- Essential Setup ---
if not all([ASTRA_DB_API_ENDPOINT, ASTRA_DB_TOKEN]):
    print("ERROR: Missing AstraDB credentials in .env file.")
    exit()

print("Initializing embeddings model...")
# Initialize the embeddings with the desired model
embeddings = OllamaEmbeddings(model="all-minilm:latest")

print("Connecting to AstraDB vector store...")
vector_store = AstraDBVectorStore(
    embedding=embeddings,
    api_endpoint=ASTRA_DB_API_ENDPOINT,
    collection_name="dantelcsv",
    token=ASTRA_DB_TOKEN
)

# --- Load, Process, and Ingest Data ---
try:
    print("Loading data...")
    df = pd.read_csv("combined.csv")
    docs = [Document(page_content=", ".join(f"{col}: {row[col]}" for col in df.columns)) for _, row in df.iterrows()]
    
    print(f"Loaded {len(docs)} documents.")

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    all_splits = text_splitter.split_documents(docs)

    print(f"Split documents into {len(all_splits)} chunks.")
    print("Adding documents to AstraDB vector store... (This may take a moment)")
    
    vector_store.add_documents(all_splits)
    
    print("\n-----------------------------------------")
    print("✅ Data ingestion complete!")
    print(f"Total chunks added: {len(all_splits)}")
    print("You can now run the main application using 'python app.py'")
    print("-----------------------------------------")

except FileNotFoundError:
    print("\nERROR: 'Sample Tickets - Copy of Sheet1.csv' not found.")
    print("Please make sure the CSV file is in the same directory as this script.")
except Exception as e:
    print(f"\nAn unexpected error occurred: {e}")