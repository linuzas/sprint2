import streamlit as st
import os
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain.schema import Document

st.set_page_config(page_title="Knowledge Base Dashboard", page_icon="🧠", layout="wide")

if os.path.basename(__file__) == "dashboard.py":
    st.markdown("""
        <style>
        [data-testid="stSidebarNav"] { display: none !important; }
        </style>
    """, unsafe_allow_html=True)


# --- Require login ---
if "user" not in st.session_state:
    st.error("🔒 Please log in to access the Knowledge Base Dashboard.")
    st.stop()

# --- Custom Sidebar ---
with st.sidebar:
    st.markdown("## 🧠 Navigation")
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

# --- Init Vector Store ---
db = Chroma(
    persist_directory="knowledge_base/embeddings",
    embedding_function=OpenAIEmbeddings(openai_api_key=st.secrets["OPENAI_API_KEY"])
)

# --- Helper Functions ---
def get_all_docs():
    raw = db.get()
    return [
        Document(page_content=doc, metadata=meta)
        for doc, meta in zip(raw["documents"], raw["metadatas"])
    ]

def count_chunks_by_source(docs):
    counts = {}
    for doc in docs:
        source = doc.metadata.get("source", "unknown")
        counts[source] = counts.get(source, 0) + 1
    return counts

# --- Load Data ---
docs = get_all_docs()
chunk_count = len(docs)
chunk_by_source = count_chunks_by_source(docs)

# --- UI ---
st.title("🧠 Knowledge Base Dashboard")
st.markdown("Overview of your vector store contents:")

st.subheader("📦 Total Chunks")
st.markdown(f"### `{chunk_count}` chunks")

st.subheader("📁 Source List")
if chunk_by_source:
    for source, count in chunk_by_source.items():
        is_url = source.startswith("http")
        label = f"[{source}]({source})" if is_url else f"`{os.path.basename(source)}`"
        st.markdown(f"- {label} — **{count} chunks**")
else:
    st.info("No chunks found.")
