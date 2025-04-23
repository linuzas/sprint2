from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough, RunnableParallel
from operator import itemgetter
from typing import List, Tuple, Dict, Any
import os
import heapq
import streamlit as st
from collections import defaultdict

# Modify this path to point to your Chroma DB
CHROMA_DB_PATH = os.environ.get("CHROMA_DB_PATH", "knowledge_base/embeddings")

def get_retriever(top_k=3):
    """Creates a retriever function that uses Chroma DB"""
    try:
        # Connect to existing Chroma DB
        embeddings = OpenAIEmbeddings(openai_api_key=st.secrets["OPENAI_API_KEY"])
        db = Chroma(persist_directory=CHROMA_DB_PATH, embedding_function=embeddings)
        
        # Create a retriever
        return db.as_retriever(search_kwargs={"k": top_k})
    except Exception as e:
        print(f"Error connecting to Chroma DB: {e}")
        return None

def reciprocal_rank_fusion(results_list: List[List[Any]], k=60) -> List[Any]:
    """
    Implements Reciprocal Rank Fusion to combine multiple search results.
    
    Args:
        results_list: List of lists containing search results from different queries
        k: A constant to prevent points from being overly weighted to documents ranked first
        
    Returns:
        Combined and reranked list of documents
    """
    # Track document scores in a dictionary
    doc_scores = defaultdict(float)
    
    # Process each result list
    for results in results_list:
        # Process each document in the result
        for rank, doc in enumerate(results):
            # Calculate RRF score: 1 / (rank + k)
            # Using document content as a key for deduplication
            doc_key = doc.page_content
            doc_scores[doc_key] = doc_scores[doc_key] + 1.0 / (rank + k)
    
    # Create a list of (score, document_key) pairs
    scored_results = [(score, key) for key, score in doc_scores.items()]
    
    # Sort by score in descending order
    scored_results.sort(reverse=True)
    
    # Extract the original documents in the new order
    # Create a mapping from content to document for lookup
    content_to_doc = {}
    for results in results_list:
        for doc in results:
            content_to_doc[doc.page_content] = doc
    
    # Get the reranked documents
    reranked_docs = [content_to_doc[key] for _, key in scored_results]
    
    return reranked_docs

def generate_query_variations(question: str, model_name: str = "gpt-3.5-turbo") -> List[str]:
    """
    Generate different versions of the user question to improve retrieval.
    
    Args:
        question: The original user question
        model_name: The model to use for query generation
        
    Returns:
        List of query variations including the original query
    """
    multi_q_prompt = ChatPromptTemplate.from_template("""You are an AI language model assistant. Your task is to generate four 
different versions of the given user question to retrieve relevant documents from a vector 
database. Provide these alternative questions separated by newlines. Original question: {question}
""")
    
    generate_queries = (
        multi_q_prompt
        | ChatOpenAI(model_name=model_name, temperature=0)
        | StrOutputParser()
        | (lambda x: [q.strip() for q in x.split("\n") if q.strip()])
    )
    
    # Add the original query and the variations
    all_queries = [question] + generate_queries.invoke({"question": question})
    return all_queries

def get_relevant_documents_with_fusion(query: str, top_k: int = 3, model_name: str = "gpt-3.5-turbo") -> List[Any]:
    """
    Enhanced retrieval function that uses query variations and rank fusion.
    
    Args:
        query: The user query
        top_k: Number of documents to retrieve
        model_name: Model to use for query generation
        
    Returns:
        List of retrieved documents
    """
    try:
        # Generate query variations
        query_variations = generate_query_variations(query, model_name)
        
        # Get the retriever
        retriever = get_retriever(top_k * 2)  # Get more docs than needed for fusion
        if not retriever:
            return []
        
        # Get results for each query variation
        all_results = []
        for variation in query_variations:
            results = retriever.invoke(variation)
            all_results.append(results)
        
        # Combine results using reciprocal rank fusion
        fused_results = reciprocal_rank_fusion(all_results)
        
        # Return the top k results
        return fused_results[:top_k]
    except Exception as e:
        print(f"Error in enhanced retrieval: {e}")
        return []

# For backward compatibility
def get_relevant_documents(query, top_k=3):
    """Legacy function that uses the enhanced retrieval"""
    return get_relevant_documents_with_fusion(query, top_k)