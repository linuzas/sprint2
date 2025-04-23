# chains/rag_chain_v2.py
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser

def process_rag_query(query, docs, router=None):
    """Process a query using RAG with retrieved documents"""
    # Initialize components
    llm = ChatOpenAI(temperature=0.2)
    output_parser = StrOutputParser()
    
    # Store the retrieved docs in the router for source attribution
    if router:
        router.last_retrieved_docs = docs
    
    # Create a context string from retrieved documents
    context = "\n\n".join([f"Document {i+1}:\n{doc.page_content}" for i, doc in enumerate(docs)])
    
    # Create the RAG prompt
    template = """
    You are a helpful crypto advisor with expertise in cryptocurrency markets, psychology, and strategies.
    
    Answer the user's question based on the following retrieved information.
    If the information doesn't fully answer the query, use your general knowledge but make it clear
    which parts are from your knowledge and which are from the retrieved information.
    
    Retrieved Information:
    {context}
    
    User Question: {query}
    
    Answer:
    """
    
    # Create and invoke the chain
    prompt = ChatPromptTemplate.from_template(template)
    rag_chain = prompt | llm | output_parser
    
    response = rag_chain.invoke({
        "context": context,
        "query": query
    })
    
    return response