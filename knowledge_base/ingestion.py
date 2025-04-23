import os
import json
import tiktoken
import bs4
from pathlib import Path
from typing import Optional, List
from dotenv import load_dotenv

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import (
    TextLoader, PyPDFLoader, WebBaseLoader
)
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain.schema import Document

# === Config ===
load_dotenv()
RAW_DOCS_DIR = "knowledge_base/raw_docs"
VECTOR_DB_DIR = "knowledge_base/embeddings"
INGESTED_LOG = "knowledge_base/ingested_sources.json"

# === Token Counter ===
def num_tokens_from_string(string: str, encoding_name: str = "cl100k_base") -> int:
    encoding = tiktoken.get_encoding(encoding_name)
    return len(encoding.encode(string))

# === Helpers ===
def normalize_route_name(filename: str) -> str:
    name = os.path.splitext(os.path.basename(filename))[0]
    return name.strip().lower().replace(" ", "_").replace("-", "_")

def clean_page_content(text: str) -> str:
    import re
    text = re.sub(r"\s*\n\s*", " ", text)
    text = re.sub(r"\s{2,}", " ", text)
    return text.strip()

def load_ingested_sources():
    if os.path.exists(INGESTED_LOG):
        with open(INGESTED_LOG, "r") as f:
            return set(json.load(f))
    return set()

def save_ingested_sources(sources: set):
    with open(INGESTED_LOG, "w") as f:
        json.dump(sorted(list(sources)), f, indent=2)

# === Load documents ===
def load_all_documents_from_folder(folder: str) -> List[Document]:
    documents = []
    for root, _, files in os.walk(folder):
        for file in files:
            path = os.path.join(root, file)
            resolved_path = str(Path(path).resolve())
            if file.endswith(".txt"):
                loader = TextLoader(resolved_path)
            elif file.endswith(".pdf"):
                loader = PyPDFLoader(resolved_path)
            else:
                continue

            file_docs = loader.load()
            total_words = 0
            for doc in file_docs:
                doc.page_content = clean_page_content(doc.page_content)
                total_words += len(doc.page_content.split())
                doc.metadata["source"] = resolved_path
                doc.metadata["title"] = os.path.basename(resolved_path)
                doc.metadata["route"] = normalize_route_name(resolved_path)
            print(f"📘 {file}: {total_words:,} words")
            documents.extend(file_docs)
    return documents

def load_document_from_url(url: str) -> List[Document]:
    try:
        print(f"🌐 Loading from URL: {url}")
        loader = WebBaseLoader(
            web_paths=(url,),
            bs_kwargs=dict(parse_only=bs4.SoupStrainer(class_=("post-content", "post-title", "post-header")))
        )
        docs = loader.load()
        if not docs or len(docs[0].page_content.strip()) < 50:
            print("🔁 Not enough content. Retrying with full page...")
            loader = WebBaseLoader(web_paths=(url,))
            docs = loader.load()

        for doc in docs:
            doc.page_content = clean_page_content(doc.page_content)
            doc.metadata["source"] = url
            doc.metadata["title"] = "Web Page"
            doc.metadata["route"] = normalize_route_name(url)

        print(f"🌐 Loaded {len(docs)} docs from URL.")
        return docs

    except Exception as e:
        print(f"❌ Error loading from URL: {e}")
        return []

# === Main ingestion ===
def ingest_all(local: bool = True, url: Optional[str] = None) -> bool:
    all_documents = []

    if local:
        print(f"📁 Scanning folder: {RAW_DOCS_DIR}")
        local_docs = load_all_documents_from_folder(RAW_DOCS_DIR)
        print(f"📄 Loaded {len(local_docs)} local document(s)")
        all_documents.extend(local_docs)

    if url:
        url_docs = load_document_from_url(url)
        print(f"🌍 Loaded {len(url_docs)} document(s) from URL")
        all_documents.extend(url_docs)

    if not all_documents:
        print("❌ No documents to process. Aborting.")
        return False

    splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
        chunk_size=500,
        chunk_overlap=50
    )
    chunks = splitter.split_documents(all_documents)
    print(f"✂️ Split into {len(chunks)} chunks.")

    total_tokens = sum(num_tokens_from_string(c.page_content) for c in chunks)
    print(f"🔢 Estimated total tokens: {total_tokens:,}")

    print("📊 Chunks per source:")
    by_route = {}
    for c in chunks:
        route = c.metadata.get("route", "unknown")
        by_route[route] = by_route.get(route, 0) + 1
    for route, count in by_route.items():
        print(f" - {route}: {count} chunks")

    existing_sources = load_ingested_sources()
    new_chunks = [c for c in chunks if c.metadata.get("source") not in existing_sources]

    if not new_chunks:
        print("✅ No new documents to add. All sources already ingested.")
        return True

    embeddings = OpenAIEmbeddings()
    db = Chroma(
        persist_directory=VECTOR_DB_DIR,
        embedding_function=embeddings
    )
    db.add_documents(new_chunks)
    

    new_sources = {c.metadata["source"] for c in new_chunks}
    save_ingested_sources(existing_sources.union(new_sources))

    print(f"✅ Added {len(new_chunks)} new chunks to vector DB.")
    return True

# === Entry point ===
if __name__ == "__main__":
    ingest_all(local=True, url="https://ethereum.org/en/whitepaper/")
