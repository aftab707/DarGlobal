# Development Process

## Phase 0: Existing data aur development setup ka audit

- Status: Complete
- Tareekh: 2026-11-20

### Kyun

Development shuru karne se pehle existing React app, backend folder, scraped data aur available tools samajhna zaroori tha. Is se user ka banaya hua frontend replace nahi hoga aur missing data ko valid property information nahi samjha jayega.

### Kaise

- Existing folders, React configuration, scraper scripts aur JSONL records ko sirf read karke check kiya; data ya scraper scripts ko run ya modify nahi kiya.
- User ki instruction ke mutabiq application aur future Git repo ka root `Chatbot/` rakha. Scraped data aur roadmap uske parent folder mein rahenge; future ingestion ke source paths configurable honge.
- Phase 1 ke backend ke liye Python 3.11 select kiya: machine par Conda environment mein Python 3.11.14 available hai. Is existing shared environment ko change karne ke bajaye Phase 1 mein project-specific environment banana hoga.
- Existing frontend React, Vite aur JavaScript par hai; isi setup ko reuse karenge.
- JSONL ko file ki physical lines se parse kiya. General-purpose `splitlines()` kuch Unicode line separators ko bhi split kar deta hai, is liye us se pehla audit galat nikla; dobara physical-line iteration se sahi counts verify kiye.

**Data ki important findings:**

| Source | Records | Masla ya limitation |
|---|---:|---|
| `../dar_global/all_pages.jsonl` | 300 | 14 empty text; 8 URLs mein unencoded whitespace. |
| `../wasalt_company_data/company_pages.jsonl` | 58 | Company pages; content ki quality aur overlap further verify karna hoga. |
| `../wasalt_data/listings.jsonl` | 406 | 401 records mein price missing; 84 URLs `/property/` path se start nahi hote aur unhein actual listings samajhne se pehle verify karna hoga. Ek URL mein unencoded whitespace hai. |
| `../wasalt_data/listing_details.jsonl` | 403 | 4 duplicate URL rows; 3 URLs mein unencoded whitespace. |
| `../wasalt_data/categories.jsonl` | 18 | 5 duplicate URL rows. |
| `../wasalt_data/auctions.jsonl` | 20 | Ye scraped snapshot hai, live auction status nahi. |
| `../wasalt_data/company.jsonl` | 5 | Company dataset ke saath overlap verify karna hoga. |

Upar diye gaye files mein physical-line JSON parsing se koi invalid JSON record nahi mila aur sab records mein HTTP/HTTPS scheme aur host mile. URLs mein whitespace ka matlab ye nahi ke URL unreachable hai: Phase 2 mein safe encoding aur actual identity check karni hogi. Duplicate counts exact URL strings par based hain; canonical URLs aur content-level duplicates alag check honge. Wasalt listings ki scope aur prices complete ya current hone ka claim nahi karna.

**Phase 2 ka reproducible audit plan:** Ek script har input ko UTF-8 physical lines se padhe aur per-file total, invalid JSON, missing fields, exact aur canonical URL duplicates, invalid URL scheme/host, whitespace, empty text, non-property paths aur price/area missing counts report kare. Invalid records aur merge decisions ka reason de; raw personal contact details output na kare. Fixture tests empty pages, malformed URL, search-page-as-listing, duplicate aur missing price cover karein.

### Kahan

- `process.md`: yeh phase log aur audit results.
- `../PROJECT_ROADMAP.md`: existing `Chatbot/` project root, JavaScript frontend aur external source-data paths clear kiye.
- `frontend/`: existing React app sirf inspect ki; koi file change nahi ki.
- `backend/`: existing empty backend folder sirf inspect kiya.
- `../dar_global/`, `../wasalt_data/`, `../wasalt_company_data/`: existing source data sirf inspect kiya.

### Verification

- `python --version`: terminal Python 3.13.10; VS Code/Pylance ka selected interpreter bhi parent `.venv` hai. Backend ke liye selected Python 3.11.14 alag available Conda environments mein verify hua.
- `node --version`: v24.11.1; `npm --version`: 11.19.1; `git --version`: 2.52.0.windows.1.
- `docker --version`: Docker CLI 29.8.2 installed. `docker info` fail hua kyunke Docker Desktop Linux engine se connection nahi hua; Docker runtime/build abhi verify nahi hua.
- `git -C Chatbot rev-parse --show-toplevel`: repository nahi mili. Git initialization aur push commands Phase 1 ke baad user ko di jayengi; abhi koi commit ya push nahi hua.
- Frontend build, backend tests, database aur deployment is phase ka hissa nahi thay; abhi run ya setup nahi huay.

### Blockers aur agla phase

- Phase 0 ke liye koi blocker nahi.
- Phase 8 se pehle Docker Desktop/engine start karna hoga. Actual server access aur OpenRouter key baad ke phases mein chahiye hongi; key chat mein share na karein.
- Agla: **Phase 1** — existing React frontend reuse karke structured FastAPI skeleton, health check, safe Git ignore aur local setup. User ke `next` ka intezar.

## Phase 1: React aur FastAPI skeleton

- Status: Complete
- Tareekh: 2026-11-20

### Kyun

Frontend aur backend ka bunyadi connection aur project ki organized structure chahiye thi, taake aglay phases mein data processing, database aur chatbot isi foundation par ban sakein.

### Kaise

- Existing React + Vite + JavaScript app ko replace nahi kiya. Us mein backend connection ka status add kiya aur Vite proxy ko local FastAPI server se connect kiya.
- FastAPI mein API route, service, response schema aur configuration ke alag folders banaye. `/api/health` abhi HTTP 503 ke saath `not_ready` deta hai: backend connected hai lekin search index abhi bana nahi. Phase 3 mein actual index readiness check lagana hoga.
- Python 3.11 ka project-specific `backend/.venv` banaya aur backend dependencies install ki. Existing parent environment ya scraper requirements change nahi kiye.
- Root `.gitignore` se secrets, virtual environments, generated data, caches aur frontend dependencies ko Git se exclude kiya. `.env.example` mein sirf future key ka empty placeholder hai; Phase 1 abhi environment file read nahi karta.
- User ki nayi hidayat ke mutabiq Docker engine start nahi kiya jayega. Phase 8 mein Docker files aur commands tayyar honge; user baad mein khud Docker run/test karega. Is hidayat ko roadmap mein bhi update kiya hai. Phase 0 ka Docker engine start karne wala note is se supersede hota hai.

### Kahan

- `backend/app/main.py`: FastAPI application aur API router.
- `backend/app/api/health.py`, `backend/app/services/health.py`, `backend/app/schemas/health.py`: health endpoint, current readiness aur response shape.
- `backend/app/core/config.py`: app title aur API prefix.
- `backend/tests/test_health.py`: index na hone par expected health response ka test.
- `backend/requirements.txt`, `backend/.venv/`: Python dependencies aur local environment; `.venv` Git mein include nahi hoga.
- `frontend/src/BackendStatus.jsx`, `frontend/src/App.jsx`, `frontend/vite.config.js`: connection status aur development proxy.
- `.gitignore`, `.env.example`, `README.md`: safe Git setup, future secret placeholder aur local run/test instructions.
- `../PROJECT_ROADMAP.md`: Docker ki user-managed verification hidayat.

### Verification

- `backend`: `python -m pytest -q` — 1 test pass; `python -m pip check` — dependencies compatible.
- `frontend`: `npm run build` aur `npm run lint` — dono pass.
- Temporary backend aur Vite servers se `/api/health` directly aur frontend proxy ke through check kiya: dono par expected HTTP 503 aur `{"status":"not_ready","index_ready":false}` mila. Browser mein `Backend connected. The search index is not ready yet.` verify hua. Temporary servers band kar diye.
- Python files ki Pylance syntax validation pass hui. Docker build/run nahi kiya, user ki instruction ke mutabiq.
- Git repository initialize, commit ya push nahi kiya; user apni repository banakar commands khud chalayega.

### Blockers aur agla phase

- Phase 1 ke liye koi blocker nahi. Git remote abhi user banayega.
- Database aur chatbot abhi implement nahi huay; 503 readiness expected hai.
- Agla: **Phase 2** — scraped data ki cleaning aur reproducible audit. User ke `next` ka intezar.
