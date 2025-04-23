import streamlit as st
import time, random, json
from database.supabase_helpers import (
    create_new_chat_session,
    update_chat_messages,
    load_chat_messages,
    delete_chat,
    get_user_chats,
    get_api_key_for_user
)

from utils.export_helpers import generate_pdf, generate_txt

# --- Title and App Description ---
def show_title_and_description():
    st.title("Crypto Advisor")
    st.markdown("""
    💡 This chatbot combines a knowledge base of crypto psychology and strategy with real-time price data.  
    💬 Ask questions about crypto concepts, trading strategies, news, or current prices.
    """)

# --- Custom Sidebar ---
def show_sidebar():
    st.markdown("""
    <style>
    /* Clean up and slightly increase sidebar font size */
    section[data-testid="stSidebar"] {
        font-size: 0.95rem;
        line-height: 1.4;
    }

    .sidebar-button {
        text-align: left;
        padding: 0.4rem 1rem;
        border: none;
        border-radius: 6px;
        background-color: #f0f2f6;
        cursor: pointer;
        width: 100%;
        margin-bottom: 0.4rem;
    }

    .sidebar-button:hover {
        background-color: #e3e6ec;
    }
    </style>
    """, unsafe_allow_html=True)

    with st.sidebar:
        st.markdown("## 🧭 Navigation")

        if st.button("🏠 ChatBot", use_container_width=True):
            st.switch_page("app.py")
        if st.button("📊 Knowledge Base", use_container_width=True):
            st.switch_page("pages/dashboard.py")

        st.markdown("---")
        st.markdown("### 🔐 Account")
        user = st.session_state.get("user")
        if user:
            st.markdown(f"**Logged in as:** `{user.email}`")
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.clear()
            st.success("Logged out!")
            st.switch_page("pages/login.py")

        st.markdown("---")
        st.markdown("### 💬 Ask Me About")

        st.markdown("""
**🧠 Strategy & Psychology**
- FOMO in crypto trading  
- Dollar-cost averaging  
- Bull market biases  

**📊 Crypto Analysis**
- RSI & MACD for Solana  
- Should I buy Ethereum?  
- Technical trends for Bitcoin  

**📰 Latest News**
- What's new with Bitcoin?  
- Crypto ETF updates  
- Regulation buzz  

**💡 General**
- Bull vs. bear markets  
- How hardware wallets work  
- What is blockchain?
""")

# --- Main Chat + History UI ---

def render_chat_interface(user_id, router):
    chat_col, history_col = st.columns([3, 1])

    with chat_col:
        # Simple title and description
        st.title("Crypto Advisor")
        st.write("Ask questions about crypto concepts, trading strategies, news, or current prices.")
        
        # Display messages using Streamlit's native chat components
        for message in st.session_state.messages:
            if message["role"] != "system":
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])

        # Simple chat input with default Streamlit styling
        if prompt := st.chat_input("Type a crypto question or analysis request...", key="chat_input"):
            # Rate limiting logic
            now = time.time()
            if "last_requests" not in st.session_state:
                st.session_state.last_requests = []
            st.session_state.last_requests = [t for t in st.session_state.last_requests if now - t < 60]

            if len(st.session_state.last_requests) >= 5:
                st.error("⏱️ Too many messages. Please wait a moment.")
                st.stop()

            st.session_state.last_requests.append(now)

            # Add user message
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            # Generate response
            last_messages = st.session_state.messages[-10:]
            with st.chat_message("assistant"):
                placeholder = st.empty()
                with st.spinner("Analyzing..."):
                    response = router.route_query(last_messages)
                    placeholder.markdown(response)

            # Save message history
            st.session_state.messages.append({"role": "assistant", "content": response})
            update_chat_messages(st.session_state["conversation_id"], st.session_state["messages"])
            st.rerun()

    # --- Chat History Column ---
    with history_col:
        st.subheader("💾 Export Chat")
        col_export_pdf, col_export_txt = st.columns(2)

        with col_export_pdf:
            if st.button("PDF"):
                try:
                    pdf_bytes = generate_pdf(st.session_state["messages"])
                    st.download_button(
                        label="Download PDF",
                        data=pdf_bytes,
                        file_name="chat_export.pdf",
                        mime="application/pdf",
                    )
                except Exception as e:
                    st.error(f"Export failed: {e}")

        with col_export_txt:
            if st.button("TXT"):
                try:
                    txt = generate_txt(st.session_state["messages"])
                    st.download_button(
                        label="Download TXT",
                        data=txt,
                        file_name="chat_export.txt",
                        mime="text/plain",
                    )
                except Exception as e:
                    st.error(f"Export failed: {e}")

        st.subheader("📁 Chat History")
        for chat_id, chat in sorted(
            st.session_state["chat_history"].items(),
            key=lambda x: x[1].get("created_at", ""),
            reverse=True
        ):
            if not chat.get("description") or chat["description"].lower() == "new chat":
                label = f"Chat {list(st.session_state['chat_history']).index(chat_id) + 1}"
            else:
                label = chat["description"]
            col1, col2 = st.columns([3, 1])
            with col1:
                if st.button(label, key=f"load_{chat_id}"):
                    st.session_state["conversation_id"] = chat_id
                    st.session_state["messages"] = json.loads(chat["messages"])
                    st.rerun()
            with col2:
                if st.button("🗑️", key=f"delete_{chat_id}"):
                    delete_chat(chat_id)
                    st.session_state["chat_history"].pop(chat_id)
                    st.rerun()

        if st.button("➕ New Chat"):
            new_id, _ = create_new_chat_session(user_id, expert_type="crypto", messages=[])
            st.session_state["conversation_id"] = new_id
            st.session_state["messages"] = []
            updated_chats = get_user_chats(user_id)
            st.session_state["chat_history"] = {chat['id']: chat for chat in updated_chats}
            st.rerun()