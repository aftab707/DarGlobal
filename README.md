# DarGlobal and Wasalt AI Assistant

An assessment project that answers real-estate questions using an existing snapshot of DarGlobal and Wasalt website content. It combines a React chat interface, a FastAPI backend, LangChain, a local Chroma vector index, and a Groq language model.

> **Before you start:** This repository does **not** contain the source dataset, cleaned dataset, vector index, or API key. They are kept private and excluded from Git. A new installation must receive an authorized index separately or rebuild it from authorized source files. A clone alone is not enough to start the backend.

The application is an assessment demo, not an official DarGlobal or Wasalt service. Its answers may be incorrect, incomplete, or out of date. Verify property prices, availability, and other important details with the original source.

## Contents

- [How it works](#how-it-works)
- [Data sources and coverage](#data-sources-and-coverage)
- [Requirements](#requirements)
- [Setup on Windows](#setup-on-windows)
- [Docker setup](#docker-setup)
- [Deploy on a Linux VPS](#deploy-on-a-linux-vps)
- [API](#api)
- [Tests and evaluation](#tests-and-evaluation)
- [Troubleshooting](#troubleshooting)
- [Privacy and limitations](#privacy-and-limitations)

## How it works

```text
DarGlobal and Wasalt JSONL snapshots
              |
       Cleaning and audit
              |
      Recursive token-aware chunking
              |
  Local multilingual embeddings (CPU)
              |
   Persistent Chroma index + SQLite listings
              |
React chat -> FastAPI -> Chroma retrieval -> Groq -> streamed answer
                             |
                        source links
```

1. The offline cleaning pipeline reads the existing source files and produces cleaned documents, structured candidate listings, and an audit report.
2. The offline index pipeline uses LangChain's `RecursiveCharacterTextSplitter` and the embedding model's tokenizer. The full embedding input, including title and special tokens, is limited to 120 tokens; the overlap target is 20 tokens.
3. The embedding model is `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`, pinned to revision `e8f8c211226b894fcb81acc59f3b34ba3efd5f42`. The 384-dimensional embeddings run locally on the CPU.
4. Chroma stores the document chunks and source metadata. A separate SQLite database stores structured listing fields. **The chat endpoint currently retrieves from Chroma; it does not yet apply SQLite listing filters.**
5. FastAPI loads the index and embedding model at startup. For a chat request, it sends the question, bounded history, and retrieved snippets to Groq and streams the response to React. Simple greetings are handled locally.

The UI supports English and Arabic questions, source links, streamed answers, stop/new conversation controls, and Markdown formatting. Conversation history remains in the current page session and is cleared on refresh. English is the default response language; Arabic responses are requested for Arabic questions, but model behavior is not guaranteed.

## Data sources and coverage

The project uses **previously collected snapshots**, not live website data. The following counts are from the existing local audit; another dataset or rebuild may produce different results.

### Input files

The input root is the directory containing the following three folders. These folders are outside the cloned repository by default:

| Relative path from input root | Contents | Input records |
|---|---|---:|
| `dar_global/all_pages.jsonl` | DarGlobal pages, including project and general company content | 300 |
| `wasalt_company_data/company_pages.jsonl` | Wasalt company pages | 58 |
| `wasalt_data/company.jsonl` | Additional Wasalt company pages | 5 |
| `wasalt_data/categories.jsonl` | Sale and rental category pages | 18 |
| `wasalt_data/auctions.jsonl` | Auction pages | 20 |
| `wasalt_data/listings.jsonl` | Listing cards and search results | 406 |
| `wasalt_data/listing_details.jsonl` | Listing detail pages | 403 |

These are input row counts, not counts of unique properties. Records may overlap, be duplicates, or be excluded by cleaning. The repository's cleaning scripts do not scrape the websites; the source files must already exist and their use must be authorized.

### Cleaned snapshot

| Category | Documents |
|---|---:|
| DarGlobal general pages | 204 |
| DarGlobal project details | 77 |
| DarGlobal investment information | 4 |
| DarGlobal investor relations | 1 |
| Wasalt company pages | 46 |
| Wasalt sale and rental category pages | 13 |
| Wasalt auction home and detail pages | 20 |
| Wasalt property details | 302 |
| **Total narrative documents** | **667** |

There are **286 DarGlobal** and **381 Wasalt** documents, plus **302 candidate listings** in the structured output. The corresponding index contains **7,176 chunks**. The audited candidate listings all have a `null` structured price; 19 lack an area and 7 lack a property type. Do not treat generated prices as verified just because they appear in an answer.

Cleaning performs conservative URL normalization, duplicate handling, and property-card/detail matching. It excludes listing descriptions and recommended-property sections to reduce misattribution. Empty pages, non-property URLs, unmatched details, and uncertain identities can be excluded. These heuristics are not a substitute for manual review.

The cleaning pipeline outputs:

- `data/cleaned/documents.jsonl`: cleaned narrative text, title, source, type, URL, and available scrape timestamp.
- `data/cleaned/listings.jsonl`: matched candidate listings with fields such as city, purpose, property type, area, price, and currency. Unknown values are `null`.
- `data/cleaned/audit_report.json`: counts, exclusions, missing fields, and limitations.

Emails and phone-like numbers are removed on a best-effort basis, but the data is **not guaranteed to be anonymized**. Source and cleaned files, the index, and private backups require appropriate access controls.

## Requirements

- Git.
- Python 3.11 for local backend development; Python 3.11 was used for the existing environment and Docker image.
- Node.js compatible with Vite: `^20.19.0` or `>=22.12.0`; Node.js 24 is used in the Docker frontend build.
- A Groq API key and access to the configured model. The default is `llama-3.1-8b-instant`; `openai/gpt-oss-20b` can be configured.
- An authorized, compatible index **or** all seven authorized JSONL input files listed above.
- Internet access for package installation, the initial Hugging Face model download, and Groq API requests.
- Docker and the Docker Compose plugin if using the container setup. The VPS instructions below assume a Linux VPS with Docker access; shared hosting is not sufficient unless it explicitly supports Docker.

The existing offline index build took approximately 706 seconds and used a peak process working set of approximately 1.5 GiB on the original machine. These are **not** response-time or VPS sizing guarantees. Allow adequate memory, disk space, and time for installation and model downloads.

## Setup on Windows

The commands below use PowerShell. Replace `REPOSITORY_URL` with the repository URL.

### 1. Clone the project

```powershell
git clone https://github.com/aftab707/DarGlobal.git DarGlobalChatbot
cd DarGlobalChatbot
```

The project directory contains `backend`, `frontend`, `Dockerfile`, and `compose.yaml`. The examples below assume commands start from this project directory.

### 2. Create the backend environment

```powershell
cd backend
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
cd ..
```

If the Python launcher does not know Python 3.11, use the full path to a Python 3.11 executable in place of `py -3.11`.

### 3. Configure the Groq key

```powershell
Copy-Item .env.example backend\.env
notepad backend\.env
```

In the editor, set the key locally:

```dotenv
GROQ_API_KEY=your-key-here
GROQ_MODEL=openai/gpt-oss-20b
```

Never commit or share the real key. `GROQ_MODEL` is optional. Operating-system environment variables take precedence over `backend/.env`; restart the backend after changes.

### 4. Prepare the index

Choose **one** option:

**Option A — use an existing authorized index.** Copy the complete `data/index` directory from a trusted private backup into the project. It must include `current.json` and the referenced version's `manifest.json`, `chroma` directory, and `listings.sqlite3`. Stop the source app and any index build before making the copy, so the snapshot is consistent. A copied index must match the configured model and index format.

**Option B — rebuild from source files.** Obtain all seven source files listed above. Arrange the three source folders under a single input root, then run:

```powershell
cd backend
.\.venv\Scripts\python.exe scripts\clean_data.py --input-root "C:\path\to\input-root"
.\.venv\Scripts\python.exe scripts\build_index.py
cd ..
```

The default input root, if `--input-root` is omitted, is the **parent of the project directory**. Cleaning writes to `data/cleaned` and does not modify the source files. The index build writes to `data/index`; it downloads the embedding model on first use and can take several minutes. Both commands must succeed before starting the backend. A failed cleaning run can leave old output in place; do not mistake it for a successful new run.

Index builds use a single-writer lock and publish a new version only after verification, preserving the previous active build on failure. Stop the app before rebuilding, and do not run concurrent builders. If a crashed build leaves `data/index/build.lock`, confirm that no build process is running before manually removing **only** that lock file. Previous versions are not automatically deleted.

### 5. Start the backend

From the project directory:

```powershell
cd backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

The model and index load at startup, before the server is ready. Missing or incompatible index files can prevent startup. Once ready, open `http://127.0.0.1:8000/api/health`; a healthy index returns `{"status":"ok","index_ready":true}`. This does not verify Groq access or answer quality.

### 6. Start the frontend

Open a second PowerShell terminal and replace the example path with the actual clone location:

```powershell
cd C:\path\to\DarGlobalChatbot\frontend
npm ci
npm run dev
```

Open the URL printed by Vite. Its development proxy forwards `/api` requests to `127.0.0.1:8000`. In the chat, Enter sends a message and Shift+Enter inserts a newline.

## Docker setup

The multi-stage [Dockerfile](Dockerfile) builds the React frontend and serves it from the FastAPI image. Compose starts one non-root app worker and keeps the model cache in a named volume. It binds the app to `127.0.0.1:8085` by default, rather than exposing it directly to the internet.

### 1. Prepare private inputs

From the project root:

1. Create `backend/.env` from `.env.example` and set your Groq key as described above.
2. Copy an authorized, complete index to `data/index`, or create one using the local rebuild steps. This bind-mount directory must already exist; Compose will not create it automatically.
3. Ensure the container's user, UID `10001`, can read and write the index. On a Linux host, after confirming the path is the project's own index, run `sudo chown -R 10001:10001 ./data/index`. Do not change ownership of unrelated directories. Docker Desktop host-mount permissions can differ by platform.

The key, index, and other generated data are excluded from both Git and the Docker build context. The image does not contain a prebuilt index. Chroma's on-disk compatibility and mount permissions must be tested when moving an index between operating systems.

### 2. Build and run

From the project directory:

```powershell
docker compose config --quiet
docker compose up -d --build
docker compose ps
docker compose logs --tail 100 app
```

The first startup downloads the pinned embedding model from Hugging Face; subsequent container recreations reuse the named `model-cache` volume. Do not remove the volume with `docker compose down -v` unless you intentionally want to remove the cache.

After startup, open `http://127.0.0.1:8085/` on the **host machine**, and check `http://127.0.0.1:8085/api/health`. Test an actual question as well: health does not validate the Groq key or model.

To select a different host port, create a separate project-root `.env` file containing, for example, `CHATBOT_PORT=8086`, then recreate the container. This file configures Compose and is distinct from the secret `backend/.env`. Check that the selected port is free. For an alternative index location, set `INDEX_PATH` in the Compose environment or project-root `.env`.

## Deploy on a Linux VPS

The existing deployment uses a separate Compose project and a loopback port to avoid replacing another application's containers or ports. Adapt the steps to your server, domain, and proxy. Back up existing proxy configuration and check for domain/port conflicts before making changes.

### 1. Clone and prepare the server

Connect using SSH, then on the VPS:

```bash
git clone https://github.com/aftab707/DarGlobal.git ~/darglobal-chatbot
cd ~/darglobal-chatbot
mkdir -p data
cp .env.example backend/.env
chmod 600 backend/.env
```

Edit `backend/.env` on the server and set the Groq key and model. Keep the key out of Git and logs. Confirm Docker and Compose are available with `docker --version` and `docker compose version`.

### 2. Transfer the index

Stop the source app/build and transfer an authorized complete index privately. For example, from Windows PowerShell, while in the local project directory:

```powershell
scp -r .\data\index VPS_USER@VPS_HOST:~/darglobal-chatbot/data/
```

On the VPS, check that `data/index/current.json` and the referenced version exist, then set the ownership of **that directory only**:

```bash
cd ~/darglobal-chatbot
sudo chown -R 10001:10001 data/index
docker compose config --quiet
docker compose up -d --build
docker compose ps
docker compose logs --tail 100 app
curl http://127.0.0.1:8085/api/health
```

Wait for the model download and startup. A `200` health response confirms index readiness, not answer correctness. If the copied Windows index is incompatible or incomplete on Linux, rebuild from authorized input files in a suitable Linux Python environment and test the resulting index before deployment.

### 3. Connect a domain and HTTPS

Create a DNS A record for your chosen hostname pointing to the VPS IPv4 address. Configure a **separate** reverse-proxy server block for that hostname, forwarding to `http://127.0.0.1:8085`. For Nginx, disable response buffering for the proxied location (`proxy_buffering off`) and set an appropriate read timeout for SSE. Enable HTTPS using your server's certificate management process, then test the domain and `/api/health`.

Do not replace an existing site's Nginx configuration or reuse its hostname. A proxy running inside a different container cannot access the host through its own `127.0.0.1`; it needs appropriate host/container networking. The user reported successful deployment and HTTPS setup on the original Hostinger VPS, but a new server requires its own validation.

### 4. Updating and maintenance

After pushing changes to GitHub, on the VPS:

```bash
cd ~/darglobal-chatbot
git pull --ff-only
docker compose up -d --build app
docker compose ps
curl http://127.0.0.1:8085/api/health
```

Keep a private backup of the complete index, including its active pointer. To update the index, stop the app, prepare and verify a complete replacement, then start the app again. Do not run multiple workers or concurrent index builds against the same directory. Check an actual chat response and source link after an update or restart.

## API

### `GET /api/health`

Returns `{"status":"ok","index_ready":true}` when the index checks pass, or HTTP 503 with a not-ready response when a running app detects an invalid index. Startup itself can fail if the index or model cannot be loaded.

### `POST /api/chat`

Request:

```json
{
  "message": "What is AIDA 360?",
  "history": [
    {"role": "user", "content": "Tell me about DarGlobal"}
  ]
}
```

`message` is required. History is optional and limited to 10 user/assistant messages. Each message is limited to 2,000 characters, with a combined limit of 12,000 characters. Invalid input returns HTTP 422; a missing Groq key or unavailable index returns HTTP 503 for normal retrieval requests.

The response is `text/event-stream` with `sources`, one or more `delta` events, and `done`. If the upstream stream fails, an `error` event is sent instead of `done`. Simple greetings bypass retrieval and the model. The interactive API documentation is available at `/docs`.

Example from Windows PowerShell, with the backend running:

```powershell
$body = @{ message = "What is AIDA 360?"; history = @() } | ConvertTo-Json -Depth 4
$response = Invoke-WebRequest -Uri http://127.0.0.1:8000/api/chat -Method Post -ContentType "application/json" -Body $body
$response.Content
```

PowerShell may buffer the response; the React UI displays stream chunks as they arrive. Source URLs are restricted to the configured DarGlobal and Wasalt domains, but source relevance and citation correctness are not guaranteed.

## Tests and evaluation

From the backend directory:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe scripts\check_index.py
```

`check_index.py` checks the persistent index and sample retrievals. On the existing snapshot, the English-to-Arabic listing query did **not** retrieve its expected listing in the top 10, so this command can exit nonzero. This is a known retrieval issue, not a successful evaluation. No calibrated relevance threshold is implemented; an unrelated question can still retrieve a nearest chunk.

From the frontend directory:

```powershell
npm run test
npm run lint
npm run build
```

Suggested manual checks: ask about DarGlobal, AIDA 360, Wasalt, and an Arabic question; check that each source link is relevant; try an unrelated question; and confirm that a property price is not presented as verified without supporting evidence. Test actual Groq access, SSE streaming, startup, and container restart in the target environment.

## Troubleshooting

| Symptom | What to check |
|---|---|
| Backend fails during startup | Confirm the complete index exists, permissions allow access, the model can download, and the index manifest matches the configured model. Inspect application logs. |
| Groq authentication or model error | Check `GROQ_API_KEY`, `GROQ_MODEL`, account access, and any overriding OS environment variables. Restart after changing `backend/.env`. Do not publish the key. |
| Groq rate limit or timeout | Check provider quota, model access, network connectivity, and retry later. |
| Docker bind mount fails | Ensure the configured index directory already exists and is accessible to container UID `10001`. Check `INDEX_PATH` and host mount permissions. |
| Port already in use | Choose a free `CHATBOT_PORT`; update the reverse proxy to use the same host port. |
| Frontend works locally but not through the domain | Check DNS, TLS, Nginx hostname and upstream port, and proxy networking. Keep SSE buffering disabled. |
| Answers are irrelevant or missing facts | Inspect source links and original content. The dataset is incomplete and semantic search can return unrelated results. |

## Privacy and limitations

- Source data is local/private by choice and is not included in the repository. Confirm applicable permissions before transferring, publishing, or redistributing it. Review the [Wasalt LLM policy](https://wasalt.sa/llms.txt) and [terms of use](https://wasalt.sa/en/s/terms-of-use), as well as any applicable source and auction terms.
- The user's question, conversation history, and retrieved snippets are sent to **Groq**. Review privacy and data-use authorization before sending sensitive content to the provider or exposing the application publicly.
- The assignment originally requested a free model through OpenRouter; this implementation uses Groq directly. Confirm with the hiring team whether this is acceptable.
- Data is a historical snapshot, not verified live inventory. Structured price filtering, calibrated no-evidence handling, authentication, and rate limiting are not implemented. Source links and prompt instructions do not guarantee factual grounding.
- HTTPS protects transport but does not add authentication or rate limiting. Add suitable protection before public use, and never place secrets in the frontend, Git history, or Docker image.
