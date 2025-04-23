# utils/classifier_v2.py
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

def classify_query(query_text):
    """
    Classify query as one of:
    - knowledge_base: Requires knowledge base lookup
    - tool_call: Requires tool/function call for current data
    - direct: Can be answered directly or is off-topic
    """

    llm = ChatOpenAI(temperature=0)

    # Early validation
    if not query_text.strip():
        return "direct"
    if len(set(query_text.lower())) <= 2 or len(query_text.strip()) < 5:
        return "direct"

    template = template = """
    Classify the user's query into one of these categories:
    - knowledge_base: For questions about crypto psychology, strategies, concepts, or terminology that would benefit from static or specialized knowledge (not real-time).
    - tool_call: For questions about current crypto prices, technical analysis (RSI, MACD, trends), buy/sell advice, news updates, or real-time data.
    - direct: For general questions or anything NOT related to cryptocurrency (e.g., weather, food, politics).

    Examples:
    Query: "What is the psychology behind FOMO in crypto trading?"
    Classification: knowledge_base

    Query: "What's the current price of Bitcoin?"
    Classification: tool_call

    Query: "Should I buy Ethereum?"
    Classification: tool_call

    Query: "Give me RSI and MACD for Solana"
    Classification: tool_call

    Query: "Tell me the latest crypto news"
    Classification: tool_call

    Query: "Any updates about Solana?"
    Classification: tool_call

    Query: "What does HODL mean?"
    Classification: knowledge_base

    Query: "How do I use this app?"
    Classification: direct

    User query: {query}

    Classification (just return the category name):
    """


    prompt = ChatPromptTemplate.from_template(template)
    chain = prompt | llm | StrOutputParser()

    result = chain.invoke({"query": query_text}).strip().lower()

    # Ensure we return one of our expected categories
    valid_categories = ["knowledge_base", "tool_call", "direct"]
    if result not in valid_categories:
        return "direct"  # fallback for off-topic or invalid

    return result
