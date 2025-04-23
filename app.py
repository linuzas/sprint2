import sys
import pysqlite3
sys.modules['sqlite3'] = pysqlite3

import streamlit as st
import os
from pathlib import Path
from typing import Optional, Dict, Any
from chains.query_router import QueryRouter
from database.supabase_helpers import (
    supabase,
    restore_user_session,
    create_new_chat_session,
    load_chat_messages,
    get_user_chats,
    update_chat_messages
)
from frontend.streamlit_ui import show_sidebar, render_chat_interface
from utils.logger import logger

# Constants
PAGE_TITLE = "Crypto Advisor"
LAYOUT = "wide"
INITIAL_SIDEBAR_STATE = "expanded"
DEFAULT_EXPERT_TYPE = "crypto"

class CryptoAssistant:
    """Main application class for the Crypto Advisor."""
    
    def __init__(self):
        self._setup_page_config()
        self._hide_sidebar_nav()
        self.user: Optional[Dict[str, Any]] = None
        self.user_id: Optional[str] = None
        self.router: Optional[QueryRouter] = None
    
    def _setup_page_config(self) -> None:
        """Configure the Streamlit page settings."""
        st.set_page_config(
            page_title=PAGE_TITLE,
            layout=LAYOUT,
            initial_sidebar_state=INITIAL_SIDEBAR_STATE,
            menu_items={
                'Get Help': None,
                'Report a Bug': None,
                'About': None
            }
        )
    
    def _hide_sidebar_nav(self) -> None:
        """Hide the default Streamlit sidebar navigation."""
        if Path(__file__).name == "app.py":
            st.markdown("""
                <style>
                [data-testid="stSidebarNav"] { display: none !important; }
                </style>
            """, unsafe_allow_html=True)
    
    def _check_authentication(self) -> None:
        """Check if user is authenticated and redirect if not."""
        if "user" not in st.session_state:
            logger.info("User not authenticated, redirecting to login")
            st.switch_page("pages/login.py")
        
        self.user = st.session_state["user"]
        self.user_id = self.user.id
        logger.info(
            f"User authenticated: {self.user.email}",
            extra={"user_id": self.user_id}
        )
    
    def _restore_session(self) -> None:
        """Restore user session with Supabase."""
        try:
            restore_user_session(
                supabase,
                access_token=st.session_state["access_token"],
                refresh_token=st.session_state["refresh_token"]
            )
            logger.info("User session restored successfully")
        except Exception as e:
            logger.error("Session restoration failed", extra={"error": str(e)})
            st.warning("Your session expired or is invalid. Please log in again.")
            st.session_state.clear()
            st.switch_page("pages/login.py")
    
    def _setup_chat(self) -> None:
        """Initialize or restore chat session."""
        if "conversation_id" not in st.session_state:
            new_id, _ = create_new_chat_session(
                self.user_id,
                expert_type=DEFAULT_EXPERT_TYPE,
                messages=[]
            )
            logger.info(
                "New chat session created",
                extra={"conversation_id": new_id}
            )
            st.session_state["conversation_id"] = new_id
            st.session_state["messages"] = []
            update_chat_messages(new_id, [])
        elif "messages" not in st.session_state:
            st.session_state["messages"] = load_chat_messages(
                st.session_state["conversation_id"]
            )
            logger.info(
                "Existing chat session loaded",
                extra={"conversation_id": st.session_state["conversation_id"]}
            )
    
    def _load_chat_history(self) -> None:
        """Load user's chat history."""
        if "chat_history" not in st.session_state:
            chats = get_user_chats(self.user_id)
            st.session_state["chat_history"] = {
                chat['id']: chat for chat in chats
            }
            logger.info(
                "Chat history loaded",
                extra={"chat_count": len(chats)}
            )
    
    def run(self) -> None:
        """Run the main application."""
        try:
            self._check_authentication()
            self._restore_session()
            
            self.router = QueryRouter()
            logger.info("Query router initialized")
            
            self._setup_chat()
            self._load_chat_history()
            
            show_sidebar()
            render_chat_interface(self.user_id, self.router)
            
        except Exception as e:
            logger.critical(
                "Application error",
                extra={"error": str(e), "traceback": e.__traceback__}
            )
            st.error("An unexpected error occurred. Please try again later.")

if __name__ == "__main__":
    app = CryptoAssistant()
    app.run()
