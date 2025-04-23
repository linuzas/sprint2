# chains/query_router_v2.py
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from utils.classifier import classify_query
from knowledge_base.retriever import get_relevant_documents
from utils.tools import TOOLS, OPENAI_FUNCTIONS 
from chains.rag_chain import process_rag_query
from chains.direct_chain import process_direct_query
from langchain_core.messages import HumanMessage
import json
import os
import re
import streamlit as st
from urllib.parse import urlparse

class QueryRouter:
    def __init__(self):
        self.llm = ChatOpenAI(temperature=0, openai_api_key=st.secrets["OPENAI_API_KEY"])
        self.output_parser = StrOutputParser()
        self.function_llm = ChatOpenAI(temperature=0, model="gpt-4", openai_api_key=st.secrets["OPENAI_API_KEY"])
        self.last_retrieved_docs = []  # To store the last retrieved documents
        
    def route_query(self, query):
        """
        Accepts a single query or full chat history.
        Classifies only the latest user message.
        Uses history only for direct queries (not for RAG or tools).
        """
        if isinstance(query, str):
            query_text = query
            history = []
        elif isinstance(query, list):
            query_text = query[-1]["content"]
            history = query[:-1]
        else:
            raise ValueError("Invalid input: must be string or list of messages")

        query_type = classify_query(query_text)
        source = None
        function_called = None

        try:
            if query_type == "knowledge_base":
                response, source = self._handle_knowledge_base_query(query_text)
            elif query_type == "tool_call":
                response, called_function = self._handle_tool_call_query(query_text)

                # Wrap the function name and parameters if it's a tool call
                if isinstance(called_function, str) and called_function in TOOLS:
                    function_called = {
                        "name": called_function,
                        "parameters": self._last_tool_args if hasattr(self, '_last_tool_args') else {}
                    }
                else:
                    function_called = called_function
            else:
                response = self._handle_direct_query_with_history(history, query_text)
                source = "General Knowledge"
        except Exception as e:
            print(f"Error in query routing: {e}")
            response = self._handle_direct_query(query_text)
            source = "General Knowledge (Fallback)"

        footer = self._create_attribution_footer(source, function_called)
        return f"{response}{footer}"

            
    
    def _handle_knowledge_base_query(self, query_text):
        """Handle queries that should use the knowledge base"""
        try:
            # Get relevant documents
            docs = get_relevant_documents(query_text)
            self.last_retrieved_docs = docs  # Store for attribution
            
            # If we have relevant docs, use RAG
            if docs and len(docs) > 0:
                response = process_rag_query(query_text, docs, self)
                return response, "Knowledge Base"
            else:
                # Fallback to direct answer if no relevant docs
                response = process_direct_query(query_text)
                return response, "General Knowledge (No Relevant Docs Found)"
        except Exception as e:
            # Fallback on error
            print(f"Error in knowledge base retrieval: {e}")
            response = process_direct_query(query_text)
            return response, "General Knowledge (Retrieval Error)"
    
    def _handle_tool_call_query(self, query_text: str):
        """Handle queries using OpenAI function calling."""
        try:
            # Step 1: Ask LLM to call a function based on the query
            response = self.llm.invoke(
                [HumanMessage(content=query_text)],
                functions=OPENAI_FUNCTIONS,
                function_call="auto"
            )

            if not response.additional_kwargs.get("function_call"):
                return self._handle_direct_query(query_text), "General Knowledge (No Tool Match)"

            function_call = response.additional_kwargs["function_call"]
            function_name = function_call["name"]
            raw_args = function_call.get("arguments", "{}")

            try:
                args = json.loads(raw_args)
            except json.JSONDecodeError:
                return self._handle_direct_query(query_text), f"Function call failed to parse args"

            tool_fn = TOOLS.get(function_name)
            if not tool_fn:
                return self._handle_direct_query(query_text), f"Unknown tool: {function_name}"

            # Step 2: Call the actual tool with parsed args
            tool_output = tool_fn(**args)
            self._last_tool_args = args

            # Step 3: Format a natural response using the tool result
            formatting_template = """
            You are a crypto advisor assistant.

            The user asked:
            {query}

            Here is the result from the relevant tool:
            - Function: {function_name}
            - Result: {tool_output}

            Using this data, write a helpful, user-friendly answer.

            If it's a price, explain what the price is and remind the user it's approximate.

            If it's news, summarize the most important points clearly.

            If it's trading signals:
            0. Start by mentioning the cryptocurrency analyzed (symbol) and the time period used (e.g., 14 days of historical data)
            1. Give a brief overview highlighting the current price and overall sentiment (bullish/bearish/neutral)
            2. Emphasize the strongest buy/sell signals if present
            3. Mention any important patterns from the RSI, MACD, or Bollinger Bands
            4. If there are clear trading signals, explain them in simple terms
            5. End with a brief summary of the overall trend direction and volatility

            Keep your response conversational and easy to understand, even when explaining technical indicators.
            Only mention the function name if it helps build credibility.
            Avoid generic disclaimers unless necessary.
            """

            prompt = ChatPromptTemplate.from_template(formatting_template)
            chain = prompt | self.llm | self.output_parser

            final_response = chain.invoke({
                "query": query_text,
                "function_name": function_name,
                "tool_output": tool_output
            })

            return final_response, function_name

        except Exception as e:
            print(f"Error in tool call: {e}")
            return self._handle_direct_query(query_text), "General Knowledge (Tool Call Error)"
    
    def _handle_direct_query(self, messages: list[dict]):
        return process_direct_query(messages)

    
    def _handle_direct_query_with_history(self, history, question):
        messages = history + [{"role": "user", "content": question}]
        return self._handle_direct_query(messages)





    def _create_attribution_footer(self, source=None, function_called=None):
        """Create attribution footer showing the source and/or function called with parameters"""
        parts = []

        # === Source Attribution ===
        if source:
            if source == "Knowledge Base" and hasattr(self, 'last_retrieved_docs') and self.last_retrieved_docs:
                source_names = []
                for doc in self.last_retrieved_docs:
                    if 'source' in doc.metadata:
                        raw_source = doc.metadata['source']
                        if raw_source.startswith('http'):
                            parsed_url = urlparse(raw_source)
                            source_name = f"{parsed_url.netloc}{parsed_url.path}"
                            source_names.append(source_name)
                        else:
                            source_name = os.path.basename(raw_source)
                            source_names.append(source_name)

                if source_names:
                    parts.append(f"\n\n**Source:** {', '.join(set(source_names))}")

        # === Function Attribution ===
        if function_called:
            if isinstance(function_called, dict):
                func_name = function_called.get("name", "unknown_function")
                parameters = function_called.get("parameters", {})
            else:
                func_name = str(function_called)
                parameters = {}

            if parameters:
                param_str = ", ".join(f"{k}={repr(v)}" for k, v in parameters.items())
                parts.append(f"\n\n**Function Called:** `{func_name}({param_str})`")
            else:
                parts.append(f"\n\n**Function Called:** `{func_name}`")

        return "".join(parts)