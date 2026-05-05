# 🚀 Complete Setup Guide
### Revenue Dashboard + RAG Chatbot — From Zero to Running

---

## Prerequisites (one-time installs)

| Tool | Why | Install |
|------|-----|---------|
| Python 3.10+ | Runs both apps | [python.org/downloads](https://python.org/downloads) |
| Git | Version control | [git-scm.com](https://git-scm.com) |
| VS Code | Code editor | [code.visualstudio.com](https://code.visualstudio.com) |
| GitHub account | Host the repo | [github.com](https://github.com) |

Verify installs after:
```bash
python --version     # should show 3.10+
git --version        # should show 2.x
```

---

## STEP 1 — Create GitHub Repository

1. Go to **github.com** → click the **+** icon → **New repository**
2. Fill in:
   - **Repository name:** `snowflake-streamlit-apps`
   - **Description:** `Revenue Dashboard + RAG Chatbot powered by Snowflake & OpenAI`
   - **Visibility:** Private (recommended — your API keys live nearby)
   - ✅ Check **Add a README file**
3. Click **Create repository**
4. Copy the repo URL (looks like `https://github.com/YOUR_USERNAME/snowflake-streamlit-apps.git`)

---

## STEP 2 — Clone & Set Up Locally

Open your terminal (PowerShell on Windows, Terminal on Mac):

```bash
# 1. Clone the repo
git clone https://github.com/YOUR_USERNAME/snowflake-streamlit-apps.git
cd snowflake-streamlit-apps

# 2. You'll see a blank repo with just README.md
# That's fine — we'll add the app files next
```

---

## STEP 3 — Copy App Files into the Repo

Download the files from this conversation, then organize them like this:

```
snowflake-streamlit-apps/
│
├── .gitignore                          ← prevents secrets from being committed
├── README.md                           ← project overview (already there from GitHub)
│
├── revenue_dashboard/
│   ├── app.py                          ← main Streamlit dashboard
│   ├── snowflake_conn.py               ← Snowflake connection + demo data
│   ├── seed_snowflake.sql              ← run once in Snowflake to create dummy data
│   ├── requirements.txt
│   └── .streamlit/
│       └── secrets.toml.template       ← copy → secrets.toml, fill credentials
│
└── rag_chatbot/
    ├── rag_chatbot.py                  ← PDF upload + RAG chatbot
    ├── requirements.txt
    └── .streamlit/
        └── secrets.toml.template       ← copy → secrets.toml, fill credentials
```

Copy the `.gitignore` from this package into the repo root. This is critical — it prevents your API keys from ever reaching GitHub.

---

## STEP 4 — Create Python Virtual Environments

Using separate virtual environments for each app keeps dependencies clean.

### Revenue Dashboard
```bash
cd snowflake-streamlit-apps/revenue_dashboard

# Create virtual environment
python -m venv venv

# Activate it
# Mac/Linux:
source venv/bin/activate
# Windows PowerShell:
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Verify
pip list | grep streamlit
```

### RAG Chatbot
Open a **new terminal tab**:
```bash
cd snowflake-streamlit-apps/rag_chatbot

python -m venv venv

# Mac/Linux:
source venv/bin/activate
# Windows:
.\venv\Scripts\Activate.ps1

pip install -r requirements.txt
```

---

## STEP 5 — Set Up Secrets (Credentials)

### Revenue Dashboard

```bash
cd revenue_dashboard/.streamlit
cp secrets.toml.template secrets.toml
```

Open `secrets.toml` in VS Code and fill in your Snowflake credentials:
```toml
[snowflake]
account   = "abc12345.us-east-1"    # Snowflake UI → bottom-left → copy account identifier
user      = "SRIKANTH"
password  = "yourpassword"
warehouse = "COMPUTE_WH"
database  = "REVENUE_DB"
schema    = "ANALYTICS"
```

> **Note:** If you skip this step the app still runs in demo mode with synthetic data — no Snowflake needed to test the UI.

### RAG Chatbot

#### Get OpenAI API Key:
1. Go to [platform.openai.com](https://platform.openai.com)
2. Click your profile → **API keys** → **Create new secret key**
3. Copy it immediately (shown only once)

#### Get Pinecone API Key + Create Index:
1. Go to [app.pinecone.io](https://app.pinecone.io) → sign up free
2. Click **Create Index**:
   - **Name:** `rag-chatbot`
   - **Dimensions:** `1536`
   - **Metric:** `cosine`
   - **Cloud:** AWS · us-east-1 (free tier)
3. Go to **API Keys** → copy your key

```bash
cd rag_chatbot/.streamlit
cp secrets.toml.template secrets.toml
```

Open `secrets.toml`:
```toml
OPENAI_API_KEY   = "sk-proj-..."
PINECONE_API_KEY = "pcsk_..."
PINECONE_INDEX   = "rag-chatbot"
```

---

## STEP 6 — Seed Snowflake with Dummy Data (Optional)

If you want real Snowflake data (not synthetic):

1. Open **Snowsight** (app.snowflake.com)
2. Click **Projects → Worksheets** → **+** new worksheet
3. Open `revenue_dashboard/seed_snowflake.sql` in VS Code
4. Copy the entire contents → paste into the Snowflake worksheet
5. Click **Run All**
6. You should see a results table showing 4 tenants with row counts

This creates `REVENUE_DB.ANALYTICS.DAILY_REVENUE` with 2 years of data for ALPHA, BETA, GAMMA, DELTA.

---

## STEP 7 — Run the Revenue Dashboard

```bash
cd snowflake-streamlit-apps/revenue_dashboard

# Activate venv if not already active
source venv/bin/activate    # Mac/Linux
.\venv\Scripts\Activate.ps1 # Windows

# Run
streamlit run app.py
```

Browser opens at **http://localhost:8501**

You should see:
- Dark command-center UI
- 4 tenant checkboxes in the sidebar (ALPHA, BETA, GAMMA, DELTA)
- Date range picker with quick presets
- KPI cards, main revenue chart, gauge, heatmap, trend lines
- Green "Connected to Snowflake" or yellow "DEMO MODE" badge at bottom of sidebar

---

## STEP 8 — Run the RAG Chatbot

Open a **new terminal tab**:
```bash
cd snowflake-streamlit-apps/rag_chatbot

source venv/bin/activate    # Mac/Linux
.\venv\Scripts\Activate.ps1 # Windows

streamlit run rag_chatbot.py
```

Browser opens at **http://localhost:8502** (Streamlit picks the next available port)

**First time using it:**
1. Sidebar — enter your OpenAI and Pinecone keys (if not in secrets.toml yet)
2. Click **📄 Ingest Documents** tab
3. Upload any PDF (try the SnowPro Core Study Guide PDF you have!)
4. Click **⚡ Index to Pinecone** — watch the progress bar embed each chunk
5. Switch to **💬 Chat** tab
6. Type a question — e.g. *"What is the exam domain weighting for Domain 1?"*
7. See the answer with source citations

---

## STEP 9 — Commit Everything to GitHub

```bash
cd snowflake-streamlit-apps

# Check what git sees
git status

# Stage all files EXCEPT secrets (gitignore handles this)
git add .

# Verify secrets.toml is NOT in the staged files
git status
# You should NOT see any secrets.toml files listed

# Commit
git commit -m "feat: add revenue dashboard and RAG chatbot

- Revenue dashboard: Snowflake DAILY_REVENUE table, 4 tenants,
  daily revenue vs budget vs Win The Day, KPI cards, gauge,
  heatmap, trend lines, date range filters
- RAG chatbot: PDF ingestion, chunking, OpenAI embeddings,
  Pinecone vector search, GPT-4o-mini Q&A with source citations
- Both apps work in demo mode without external credentials"

# Push to GitHub
git push origin main
```

Go to your GitHub repo — you should see all the files there.

---

## STEP 10 — Daily Git Workflow

Whenever you make changes:
```bash
# See what changed
git status
git diff

# Stage changes
git add revenue_dashboard/app.py          # specific file
git add .                                  # everything

# Commit with a descriptive message
git commit -m "feat: add monthly aggregation toggle to dashboard"

# Push
git push origin main
```

Good commit message prefixes:
- `feat:` — new feature
- `fix:` — bug fix
- `refactor:` — code cleanup
- `docs:` — documentation update
- `chore:` — maintenance

---

## Folder Structure (Final)

```
snowflake-streamlit-apps/          ← git root
│
├── .gitignore                     ✅ committed
├── README.md                      ✅ committed
│
├── revenue_dashboard/
│   ├── app.py                     ✅ committed
│   ├── snowflake_conn.py          ✅ committed
│   ├── seed_snowflake.sql         ✅ committed
│   ├── requirements.txt           ✅ committed
│   ├── venv/                      🚫 gitignored (local only)
│   └── .streamlit/
│       ├── secrets.toml           🚫 gitignored (your credentials)
│       └── secrets.toml.template  ✅ committed (safe placeholder)
│
└── rag_chatbot/
    ├── rag_chatbot.py             ✅ committed
    ├── requirements.txt           ✅ committed
    ├── venv/                      🚫 gitignored (local only)
    └── .streamlit/
        ├── secrets.toml           🚫 gitignored (your credentials)
        └── secrets.toml.template  ✅ committed (safe placeholder)
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `ModuleNotFoundError` | Make sure venv is activated: `source venv/bin/activate` |
| Dashboard shows error connecting to Snowflake | Check account identifier format in secrets.toml — it should look like `abc12345.us-east-1` |
| Pinecone `404 Index not found` | Index name in secrets.toml must exactly match what you created in Pinecone console |
| `streamlit: command not found` | Run `pip install streamlit` inside the activated venv |
| Port 8501 already in use | Run `streamlit run app.py --server.port 8503` |
| Git says `secrets.toml` is tracked | Run `git rm --cached revenue_dashboard/.streamlit/secrets.toml` |

---

## What to Put on LinkedIn / GitHub README

Once it's running, add to your GitHub README:
- Screenshots of the dashboard
- A short GIF of the chatbot answering a question
- Tech stack badges: Streamlit · Snowflake · OpenAI · Pinecone · Python

This repo demonstrates: **Streamlit, Snowflake connectivity, vector search RAG pipeline, OpenAI embeddings, Pinecone** — all signals that Snowflake recruiters and partners look for.
