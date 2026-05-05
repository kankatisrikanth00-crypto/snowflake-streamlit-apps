"""
RAG Chatbot  —  rag_chatbot.py
Run:  streamlit run rag_chatbot.py

Requires:
  pip install streamlit openai pinecone-client pypdf langchain-text-splitters python-dotenv

Set in .env or Streamlit secrets:
  OPENAI_API_KEY     = "sk-..."
  PINECONE_API_KEY   = "..."
  PINECONE_INDEX     = "rag-chatbot"   (create in Pinecone console, dim=1536)
"""

import os, time, hashlib, textwrap
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# ── Page config ─────────────────────────────────────────────
st.set_page_config(
    page_title="RAG Document Chat",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS ──────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&family=JetBrains+Mono:wght@300;400;500&display=swap');

html, body, [class*="css"] { font-family: 'Outfit', sans-serif; }
.stApp { background: #07090f; color: #dde1f0; }
section[data-testid="stSidebar"] {
    background: #0c0f1a;
    border-right: 1px solid #161d35;
}

/* Chat messages */
.msg-user {
    background: linear-gradient(135deg, #1a2744, #111d38);
    border: 1px solid #1e3060;
    border-radius: 16px 16px 4px 16px;
    padding: 14px 18px;
    margin: 8px 0;
    max-width: 80%;
    margin-left: auto;
}
.msg-bot {
    background: linear-gradient(135deg, #0f1a14, #0c1610);
    border: 1px solid #163025;
    border-radius: 16px 16px 16px 4px;
    padding: 14px 18px;
    margin: 8px 0;
    max-width: 85%;
}
.msg-label {
    font-family: 'JetBrains Mono', monospace;
    font-size: 10px;
    letter-spacing: 2px;
    text-transform: uppercase;
    color: #4a5568;
    margin-bottom: 6px;
}
.msg-text { font-size: 15px; line-height: 1.6; color: #dde1f0; }

/* Sources */
.source-chip {
    display: inline-block;
    background: #111827;
    border: 1px solid #1e2d4a;
    border-radius: 6px;
    padding: 4px 10px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    color: #60a5fa;
    margin: 3px 3px 0 0;
}

/* Status chips */
.status-ok   { background:#0d2a1a; border:1px solid #1a5c35; color:#34d399; border-radius:6px; padding:4px 12px; font-family:'JetBrains Mono',monospace; font-size:11px; }
.status-warn { background:#2a1a0d; border:1px solid #5c3a1a; color:#fb923c; border-radius:6px; padding:4px 12px; font-family:'JetBrains Mono',monospace; font-size:11px; }
.status-err  { background:#2a0d0d; border:1px solid #5c1a1a; color:#f87171; border-radius:6px; padding:4px 12px; font-family:'JetBrains Mono',monospace; font-size:11px; }

/* Upload zone */
.upload-hint {
    text-align: center;
    padding: 20px;
    border: 1px dashed #1e2d4a;
    border-radius: 12px;
    color: #4a5568;
    font-size: 13px;
    font-family: 'JetBrains Mono', monospace;
}

/* Chunk preview */
.chunk-box {
    background: #0c0f1a;
    border: 1px solid #161d35;
    border-left: 3px solid #60a5fa;
    border-radius: 0 8px 8px 0;
    padding: 10px 14px;
    margin: 6px 0;
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    color: #6b7fa8;
    line-height: 1.5;
}
</style>
""", unsafe_allow_html=True)

# ── Lazy imports (graceful degradation) ──────────────────────
def check_deps():
    missing = []
    try: import openai
    except ImportError: missing.append("openai")
    try: from pinecone import Pinecone
    except ImportError: missing.append("pinecone-client")
    try: from pypdf import PdfReader
    except ImportError: missing.append("pypdf")
    try: from langchain_text_splitters import RecursiveCharacterTextSplitter
    except ImportError: missing.append("langchain-text-splitters")
    return missing

MISSING = check_deps()

# ── Sidebar: config + status ──────────────────────────────────
with st.sidebar:
    st.markdown("## 🧠 RAG Document Chat")
    st.markdown("---")

    # API keys
    st.markdown("**CONFIGURATION**")
    openai_key   = st.text_input("OpenAI API Key",   value=os.getenv("OPENAI_API_KEY",""),   type="password", placeholder="sk-...")
    pinecone_key = st.text_input("Pinecone API Key", value=os.getenv("PINECONE_API_KEY",""), type="password", placeholder="...")
    pinecone_idx = st.text_input("Pinecone Index",   value=os.getenv("PINECONE_INDEX","rag-chatbot"), placeholder="rag-chatbot")

    st.markdown("---")
    # System status
    st.markdown("**STATUS**")
    if MISSING:
        st.markdown(f'<span class="status-err">Missing: {", ".join(MISSING)}</span>', unsafe_allow_html=True)
        st.code("pip install " + " ".join(MISSING), language="bash")
    else:
        st.markdown('<span class="status-ok">✓ All packages installed</span>', unsafe_allow_html=True)

    openai_ok = bool(openai_key)
    pinecone_ok = bool(pinecone_key and pinecone_idx)
    st.markdown(f'<span class="{"status-ok" if openai_ok else "status-warn"}">{"✓" if openai_ok else "○"} OpenAI</span>', unsafe_allow_html=True)
    st.markdown(f'<span class="{"status-ok" if pinecone_ok else "status-warn"}">{"✓" if pinecone_ok else "○"} Pinecone</span>', unsafe_allow_html=True)

    st.markdown("---")
    # Chunking settings
    st.markdown("**CHUNKING SETTINGS**")
    chunk_size    = st.slider("Chunk size (chars)",    200, 2000, 800, 100)
    chunk_overlap = st.slider("Chunk overlap (chars)",  0,  400, 100,  50)
    top_k         = st.slider("Retrieved chunks (k)",   1,   10,   4,   1)
    model_choice  = st.selectbox("LLM Model", ["gpt-4o-mini", "gpt-4o", "gpt-3.5-turbo"], index=0)

    st.markdown("---")
    if st.button("🗑️  Clear chat history"):
        st.session_state.messages = []
        st.rerun()

# ── Helper functions ─────────────────────────────────────────
def get_openai_client(key):
    if not key or MISSING: return None
    try:
        import openai
        return openai.OpenAI(api_key=key)
    except Exception:
        return None

def get_pinecone_index(api_key, index_name):
    if not api_key or not index_name or MISSING: return None
    try:
        from pinecone import Pinecone
        pc = Pinecone(api_key=api_key)
        return pc.Index(index_name)
    except Exception as e:
        st.error(f"Pinecone connection error: {e}")
        return None

def extract_text_from_pdf(file_bytes) -> str:
    from pypdf import PdfReader
    import io
    reader = PdfReader(io.BytesIO(file_bytes))
    return "\n".join(page.extract_text() or "" for page in reader.pages)

def chunk_text(text: str, size: int, overlap: int) -> list[str]:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=size,
        chunk_overlap=overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    return splitter.split_text(text)

def embed_text(client, text: str) -> list[float]:
    resp = client.embeddings.create(input=text, model="text-embedding-3-small")
    return resp.data[0].embedding

def upsert_chunks(index, chunks: list[str], source_name: str, client):
    vectors = []
    for i, chunk in enumerate(chunks):
        vec_id  = hashlib.md5(f"{source_name}_{i}".encode()).hexdigest()
        embedding = embed_text(client, chunk)
        vectors.append({
            "id": vec_id,
            "values": embedding,
            "metadata": {
                "text": chunk,
                "source": source_name,
                "chunk_idx": i,
            }
        })
    # Upsert in batches of 100
    for i in range(0, len(vectors), 100):
        index.upsert(vectors=vectors[i:i+100])
    return len(vectors)

def retrieve_chunks(index, client, query: str, k: int) -> list[dict]:
    q_vec = embed_text(client, query)
    result = index.query(vector=q_vec, top_k=k, include_metadata=True)
    return [m.metadata for m in result.matches]

def build_prompt(context_chunks: list[dict], question: str) -> list[dict]:
    context_text = "\n\n---\n\n".join(
        f"[Source: {c.get('source','?')} | Chunk {c.get('chunk_idx','?')}]\n{c.get('text','')}"
        for c in context_chunks
    )
    system = textwrap.dedent("""
        You are a precise document assistant. Answer questions based ONLY on the provided context chunks.
        If the answer is not in the context, say "I couldn't find that in the uploaded documents."
        Be concise, accurate, and cite which source/chunk your answer comes from.
        Format your answer clearly using markdown when helpful.
    """).strip()
    return [
        {"role": "system",  "content": system},
        {"role": "user",    "content": f"Context:\n{context_text}\n\nQuestion: {question}"},
    ]

# ── Session state ────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []
if "indexed_files" not in st.session_state:
    st.session_state.indexed_files = []

# ── Main layout ──────────────────────────────────────────────
st.markdown("""
<div style="display:flex;align-items:baseline;gap:16px;margin-bottom:4px">
  <span style="font-size:26px;font-weight:700;color:#dde1f0;letter-spacing:-0.5px">🧠 RAG Document Chat</span>
  <span style="font-family:'JetBrains Mono',monospace;font-size:12px;color:#3a4568;letter-spacing:2px">PDF → CHUNKS → EMBEDDINGS → ANSWER</span>
</div>
<div style="font-family:'JetBrains Mono',monospace;font-size:12px;color:#4a5568;margin-bottom:20px">
  Powered by OpenAI Embeddings · Pinecone Vector Search · GPT
</div>
""", unsafe_allow_html=True)

tab_ingest, tab_chat = st.tabs(["📄  Ingest Documents", "💬  Chat"])

# ─────────────────────────────────────────────────────────────
# TAB 1 — INGEST
# ─────────────────────────────────────────────────────────────
with tab_ingest:
    col_upload, col_preview = st.columns([1, 1])

    with col_upload:
        st.markdown("### Upload PDFs")
        if MISSING:
            st.warning(f"Install missing packages first: `pip install {' '.join(MISSING)}`")
        else:
            uploaded_files = st.file_uploader(
                "Drop PDF files here",
                type=["pdf"],
                accept_multiple_files=True,
                label_visibility="collapsed",
            )

            if uploaded_files:
                for uf in uploaded_files:
                    st.markdown(f"**{uf.name}** — {uf.size:,} bytes")

                col_btn1, col_btn2 = st.columns(2)
                preview_only = col_btn1.button("🔍  Preview Chunks", use_container_width=True)
                do_index     = col_btn2.button("⚡  Index to Pinecone", use_container_width=True, type="primary")

                if preview_only or do_index:
                    oai_client = get_openai_client(openai_key)
                    pc_index   = get_pinecone_index(pinecone_key, pinecone_idx) if do_index else None

                    for uf in uploaded_files:
                        with st.spinner(f"Processing {uf.name}..."):
                            raw_text = extract_text_from_pdf(uf.read())
                            chunks   = chunk_text(raw_text, chunk_size, chunk_overlap)

                        st.markdown(f"#### {uf.name}")
                        st.markdown(f"<span style='font-family:JetBrains Mono,monospace;font-size:12px;color:#60a5fa'>{len(raw_text):,} chars → {len(chunks)} chunks</span>", unsafe_allow_html=True)

                        if do_index:
                            if not oai_client:
                                st.error("OpenAI key required for indexing.")
                            elif not pc_index:
                                st.error("Pinecone connection failed — check key/index.")
                            else:
                                progress = st.progress(0, text="Embedding chunks...")
                                n = len(chunks)
                                vectors = []
                                import openai as _oai
                                for i, chunk in enumerate(chunks):
                                    vec_id = hashlib.md5(f"{uf.name}_{i}".encode()).hexdigest()
                                    emb    = embed_text(oai_client, chunk)
                                    vectors.append({"id": vec_id, "values": emb,
                                                    "metadata": {"text": chunk, "source": uf.name, "chunk_idx": i}})
                                    progress.progress((i+1)/n, text=f"Embedding {i+1}/{n}...")
                                for i in range(0, len(vectors), 100):
                                    pc_index.upsert(vectors=vectors[i:i+100])
                                progress.empty()
                                st.success(f"✅ {len(vectors)} chunks indexed to Pinecone!")
                                if uf.name not in st.session_state.indexed_files:
                                    st.session_state.indexed_files.append(uf.name)

                        # Show chunk preview
                        with st.expander(f"Preview chunks ({min(5, len(chunks))} of {len(chunks)})", expanded=do_index is False):
                            for i, chunk in enumerate(chunks[:5]):
                                st.markdown(
                                    f'<div class="chunk-box"><span style="color:#3a4a6a">CHUNK {i+1}</span><br>{chunk[:300]}{"..." if len(chunk)>300 else ""}</div>',
                                    unsafe_allow_html=True
                                )

    with col_preview:
        st.markdown("### Indexed Documents")
        if st.session_state.indexed_files:
            for f in st.session_state.indexed_files:
                st.markdown(f'<div style="display:flex;align-items:center;gap:8px;padding:8px 0;border-bottom:1px solid #161d35"><span style="color:#34d399">✓</span><span style="font-family:JetBrains Mono,monospace;font-size:13px">{f}</span></div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="upload-hint">No documents indexed yet.<br>Upload PDFs on the left to get started.</div>', unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("### How It Works")
        steps = [
            ("1", "#60a5fa", "Upload PDF", "Drop any PDF — technical docs, reports, papers."),
            ("2", "#a78bfa", "Chunking",   "Text is split into overlapping chunks using RecursiveCharacterTextSplitter."),
            ("3", "#34d399", "Embedding",  "Each chunk is embedded using OpenAI text-embedding-3-small (1536 dims)."),
            ("4", "#fb923c", "Indexing",   "Vectors + metadata are upserted into your Pinecone index."),
            ("5", "#f472b6", "Retrieval",  "Your question is embedded → top-k similar chunks retrieved."),
            ("6", "#60a5fa", "Generation", "GPT answers using only the retrieved context."),
        ]
        for num, color, title, desc in steps:
            st.markdown(f"""
            <div style="display:flex;gap:12px;padding:8px 0;border-bottom:1px solid #0f1420">
              <span style="width:22px;height:22px;border-radius:50%;background:{color}22;border:1px solid {color}44;color:{color};font-family:JetBrains Mono,monospace;font-size:11px;display:flex;align-items:center;justify-content:center;flex-shrink:0">{num}</span>
              <div><div style="font-weight:600;font-size:13px;color:#c0c8e0">{title}</div><div style="font-size:12px;color:#4a5568">{desc}</div></div>
            </div>""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────
# TAB 2 — CHAT
# ─────────────────────────────────────────────────────────────
with tab_chat:
    # Render history
    chat_container = st.container()
    with chat_container:
        if not st.session_state.messages:
            st.markdown("""
            <div style="text-align:center;padding:60px 20px;color:#2a3558">
              <div style="font-size:40px;margin-bottom:12px">🧠</div>
              <div style="font-size:16px;font-weight:600;color:#3a4a70">Ready to answer questions</div>
              <div style="font-size:13px;font-family:'JetBrains Mono',monospace;margin-top:8px">
                Upload and index documents first,<br>then ask anything about them.
              </div>
            </div>""", unsafe_allow_html=True)

        for msg in st.session_state.messages:
            if msg["role"] == "user":
                st.markdown(f'<div class="msg-user"><div class="msg-label">You</div><div class="msg-text">{msg["content"]}</div></div>', unsafe_allow_html=True)
            else:
                sources_html = ""
                if msg.get("sources"):
                    chips = "".join(
                        f'<span class="source-chip">📄 {s["source"]} · chunk {s["chunk_idx"]}</span>'
                        for s in msg["sources"]
                    )
                    sources_html = f'<div style="margin-top:10px">{chips}</div>'
                st.markdown(
                    f'<div class="msg-bot"><div class="msg-label">Assistant</div><div class="msg-text">{msg["content"]}</div>{sources_html}</div>',
                    unsafe_allow_html=True
                )

    # Input
    st.markdown("<br>", unsafe_allow_html=True)
    user_input = st.chat_input("Ask a question about your documents...")

    if user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})

        oai_client = get_openai_client(openai_key)
        pc_index   = get_pinecone_index(pinecone_key, pinecone_idx)

        if MISSING:
            answer = f"⚠️ Missing packages: `{', '.join(MISSING)}`. Run: `pip install {' '.join(MISSING)}`"
            sources = []
        elif not oai_client:
            answer = "⚠️ Please enter your OpenAI API key in the sidebar."
            sources = []
        elif not pc_index:
            answer = "⚠️ Could not connect to Pinecone. Check your API key and index name in the sidebar."
            sources = []
        else:
            with st.spinner("Retrieving relevant chunks..."):
                try:
                    chunks  = retrieve_chunks(pc_index, oai_client, user_input, top_k)
                    if not chunks:
                        answer  = "I couldn't find relevant content in the indexed documents. Try indexing more PDFs."
                        sources = []
                    else:
                        messages = build_prompt(chunks, user_input)
                        resp = oai_client.chat.completions.create(
                            model=model_choice,
                            messages=messages,
                            temperature=0.2,
                            max_tokens=1500,
                        )
                        answer  = resp.choices[0].message.content
                        sources = chunks
                except Exception as e:
                    answer  = f"Error: {e}"
                    sources = []

        st.session_state.messages.append({
            "role": "assistant",
            "content": answer,
            "sources": sources,
        })
        st.rerun()
