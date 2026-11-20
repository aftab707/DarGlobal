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

## Phase 2: Data cleaning aur rights review

- Status: Complete
- Tareekh: 2026-11-20

### Kyun

Wasalt data ko RAG index aur public chatbot mein use karne se pehle source ki access aur usage policies check karna zaroori hai.

### Kaise

- Existing JSONL schemas aur public robots policies check kiye; existing data aur scraper scripts mein koi change nahi kiya, na naya scrape chalaya.
- Wasalt ki [LLM policy](https://wasalt.sa/llms.txt) public listing summaries ki ijazat batati hai, lekin cached/stored content par reliance se rokti hai aur redistribution/commercial republishing restrict karti hai.
- Wasalt ki [terms of use](https://wasalt.sa/en/s/terms-of-use) copying, extraction aur republication par bhi restrictions batati hain. Auction site ki [terms](https://auction.wasalt.sa/en/terms-of-use) bhi relevant hain.
- DarGlobal ki assignment email mein Wasalt se cached RAG, third-party model API aur public deployment ki permission explicitly nahi mili thi. Is liye pehle review ke waqt Wasalt text ka naya cleaned/indexed copy ya public use start nahi kiya gaya.
- User ne baad mein bataya ke data use karne ki permission hai. Permission ki details ya alag terms verify nahi ki gayin; external model API aur public deployment ke liye applicable scope ki tasdeeq zaroori rahegi.
- Robots rules aur content-use permission alag cheezein hain; robots access ko copyright ya deployment authorization nahi samjha.

### Kahan

- `process.md`: policy findings aur blocker record kiya.
- `../dar_global/`, `../wasalt_data/`, `../wasalt_company_data/`: existing source files sirf inspect huay; modify nahi huay.

### Verification

- 20 November 2026 ko Wasalt, auction aur DarGlobal ke public robots pages, Wasalt LLM policy aur terms check kiye.
- Initial policy review ke waqt cleaning code aur output generate nahi huay thay; user ki data-cleaning permission ke baad neeche diya gaya kaam kiya gaya.

### Cleaning ka amal aur nateeja

- User ne data clean karne ki ijazat di. Saat existing JSONL inputs par local pipeline chalai; original files modify nahi ki aur naya scrape nahi kiya.
- URL, title aur main content ke conservative matching ke baad property cards aur detail pages merge kiye. Category/search links ko individual listings nahi banaya. Auction/category records ko generic company duplicate par priority di.
- Jahan city, area ya explicit-currency price card aur detail se verify nahi hue, wahan `null` rakha. Details ke description aur recommended-property sections filhaal exclude kiye; is se kuch useful content bhi omit ho sakta hai.
- Emails aur phone-like numbers remove karne ki best-effort cleaning lagai. Yeh names aur doosri personal information ki complete removal ki guarantee nahi hai; external API ya public demo se pehle review zaroori rahega.
- Output: 667 narrative documents — 286 DarGlobal aur 381 Wasalt — aur 302 matching candidate listings. Wasalt ke 20 auction records document types mein preserve huay. Yeh verified live inventory ya poore market ka count nahi.
- 14 DarGlobal records empty thay; 18 property candidates ki identity heuristic se confirm nahi hui aur 2 ki detail missing thi. Woh output listings se exclude huay. 302 listings mein structured price unknown hai; 19 mein area aur 7 mein property type unknown hai. Is wajah se abhi reliable price filtering possible nahi.

### Kahan: implementation

- `backend/app/services/data_cleaning.py`: source reading, URL validation, cleaning, listing matching aur audit.
- `backend/scripts/clean_data.py`: configurable command-line pipeline.
- `backend/tests/test_data_cleaning.py`: invalid JSON, empty pages, duplicate records, search URLs, mismatch, missing prices aur unsafe output path ke focused tests.
- `data/cleaned/documents.jsonl`, `data/cleaned/listings.jsonl`, `data/cleaned/audit_report.json`: local generated outputs; `data/` Git se ignored hai.
- `README.md`: commands, output format aur data limitations.

### Verification: completion

- `backend/.venv/Scripts/python.exe -m pytest -q`: 16 tests pass, including existing health test.
- Cleaning command do martaba chalane par teeno output files ke SHA-256 hashes same thay.
- Cleaning se pehle aur baad saat original input files ke hashes match huay.
- Pylance syntax checks teeno naye Python files ke liye pass huay. Git ignore verify kiya; generated data GitHub par automatically push nahi hoga.

### Blockers aur agla phase

- Phase 2 complete; actual model API aur public demo se pehle permission scope aur privacy review zaroori hai.
- Agla: **Phase 3** — embeddings aur Chroma index. User ke `next` ka intezar.

## Phase 3: LangChain embeddings aur local index

- Status: In progress — multilingual retrieval ka ek exit test fail hai.

### Kyun

Cleaned documents ko searchable banane, Arabic aur English queries support karne aur structured listings ko safe filters ke liye alag rakhne ke liye local persistent index chahiye. User ki choice ke mutabiq LangChain, recursive chunking aur Chroma use kiye.

### Kaise

- LangChain ke `RecursiveCharacterTextSplitter` se model tokenizer ke hisaab se chunks banaye. Title aur special tokens mila kar har embedding input 120 tokens se zyada nahi; overlap ka target 20 tokens hai. Lamba title embedding ke liye chhota hota hai, lekin original metadata mein rehta hai.
- `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` ka fixed revision CPU par use kiya: documents aur queries ke liye same 384-dimensional model hai. Pehli model download ke baad embedding locally hoti hai; index build ke liye OpenRouter key nahi chahiye.
- Chroma mein chunks aur source metadata rakhe aur 302 candidate listings SQLite mein save ki. Build alag version folder mein banta hai; verification ke baad pointer replace hota hai. Failed rebuild previous active index ko preserve karta hai aur lock concurrent builds rokta hai.
- LangSmith tracing aur Chroma telemetry build/check ke dauran disable ki. Data cleaning best-effort thi, is liye external API ya public deployment se pehle permission scope aur privacy review ab bhi zaroori hai.

### Kahan

- `backend/app/services/indexing.py`: chunking, embeddings aur versioned index build.
- `backend/app/services/index_store.py`: index location, model identity aur consistency checks.
- `backend/app/services/health.py`: actual index readiness.
- `backend/scripts/build_index.py`, `backend/scripts/check_index.py`: offline build aur sample retrieval checks.
- `backend/tests/test_indexing.py`, `backend/tests/test_health.py`: focused tests.
- `backend/requirements.txt`, `README.md`: tested dependencies aur commands.
- `data/index/`: local generated Chroma, SQLite aur manifest; Git se ignored hai.

### Verification

- Actual build: 667 documents se 7,176 chunks aur 302 listings; 705.58 seconds, peak process working set 1,521.5 MiB aur index size 44.52 MiB. Yeh offline build metrics hain, chatbot response time nahi.
- Alag process se persisted index open aur verify hua; 7,176 unique chunk IDs, 667 unique source URLs aur 302 distinct listing URLs mile. Source URLs ki scheme aur host valid hain; har link ki live availability check nahi ki.
- `/api/health` actual index ke saath HTTP 200 aur `index_ready: true` deta hai. Yeh storage readiness hai, retrieval quality ya chatbot readiness ki guarantee nahi.
- Backend tests: 20 pass; `pip check` pass. Index ke naye Python files ka Pylance syntax check pass hua.
- Real sample retrieval: DarGlobal AIDA 360, Wasalt company aur Arabic listing pass. English query `south facing 450 sqm villa for sale on 18m road in Al Rimal Riyadh` par expected listing `5971799` top 10 mein nahi aayi; `check_index.py` is wajah se fail aur nonzero exit deta hai.
- Ek alag diagnostic mein city Riyadh, purpose sale aur area 450 manually SQLite se filter kiye: four candidates mein expected listing semantic ranking par first thi. Yeh experiment automatic query parsing ya production retrieval nahi hai aur failed unfiltered test ko pass nahi banata.
- Unrelated bicycle query par bhi nearest result aaya. No-evidence threshold ya abstention abhi implemented nahi; Phase 4 mein labeled examples ke saath banana aur test karna hoga.
- Docker start/build/run nahi kiya. Chat API, LLM integration aur deployment abhi implement nahi huay.

### Blocker aur agla kaam

Phase 3 ko complete mark nahi kiya: roadmap ke mutabiq retrieval tests pass hone chahiye aur English-to-Arabic sample abhi fail hai. Agla kaam structured filtering ya doosri retrieval improvements ko proper query handling aur tests ke saath implement karke isi failing case ko dobara verify karna hai; manually supplied filter ko finished chatbot behavior na samjhein.

## Backend chat API: user ki Groq request

- Status: Initial backend implemented; real Groq response aur full Phase 4/5 validation abhi baqi.

### Kyun

User ne waqt ki kami ki wajah se pehle FastAPI backend aur Groq API mangi; React chatbot baad mein banana hai. User ne English-to-Arabic failed case abhi chhorne ko kaha, is liye usay solved claim nahi kiya.

### Kaise

- `POST /api/chat` current message se local Chroma mein relevant chunks retrieve karta hai. Existing fixed multilingual embedding model first request par load hota hai aur process mein reuse hota hai. Valid source links aur limited duplicate chunks context mein jate hain.
- Groq ki API key server-side `backend/.env` ya OS environment se li jati hai. Default model `llama-3.1-8b-instant` hai aur `GROQ_MODEL` se badla ja sakta hai. Key frontend ya source code mein nahi rakhi.
- JSON request aur history bounded hain. API `sources`, `delta` aur `done` SSE events deti hai; provider error ya incomplete stream par `error` deti hai. Index/key missing aur invalid input par explicit HTTP errors milte hain.
- Prompt model ko sirf evidence use karne, source IDs dene, missing information batane aur scraped instructions ignore karne ko kehta hai. Citations aur grounding ki correctness automatically guaranteed nahi.
- Groq ko user message, history aur retrieved snippets jate hain. Public use se pehle data-use permissions aur privacy confirm karna zaroori hai. Assignment mein OpenRouter specifically tha; Groq accept hone ki hiring team se tasdeeq zaroori hai.

### Kahan

- `backend/app/api/chat.py`, `backend/app/schemas/chat.py`: endpoint, SSE aur request validation.
- `backend/app/services/chat.py`: Chroma retrieval, source validation aur Groq streaming.
- `backend/app/core/config.py`, `backend/app/main.py`: environment loading aur route registration.
- `backend/tests/test_chat.py`, `backend/requirements.txt`, `.env.example`, `README.md`: tests, dependency aur setup instructions.

### Verification aur limitations

- 33 backend tests aur `pip check` pass. Local actual index aur real embedding model ke saath chat endpoint test hua; Groq response network ke bajaye mocked tha. AIDA source mila aur health HTTP 200 tha.
- Real Groq key ya live provider call test nahi ki; model availability, quota, latency aur actual answers user ki key se verify honge.
- Source filtering aur model instructions low-relevance detection ki guarantee nahi hain. Calibrated no-evidence decision, SQLite structured filters, reliable follow-up retrieval, auth aur rate limiting abhi nahi bane. Phase 3 ka English-to-Arabic failure bhi unresolved hai; full Phase 4/5 complete nahi.
- Frontend chat UI aur Docker run/build is step mein nahi kiye.

## React chat interface

- Status: Implemented; live Groq response user ki key ke saath abhi verify nahi hui.

### Kyun

User ko DarGlobal assessment ke liye ek responsive aur interactive interface chahiye tha jahan woh existing backend chatbot se baat kar sake.

### Kaise

- Existing React/Vite app ko replace karke DarGlobal-inspired chat interface banaya: suggested questions, message input, streamed answers, sources, stop aur new conversation controls.
- `POST /api/chat` ki SSE stream ko chunk boundaries ke across parse kiya. Backend/provider error, interrupted stream aur user stop ko visible rakha; incomplete answers history mein nahi bheje jate.
- Source links ka protocol aur domain check hota hai; React text ko plain text render karta hai. Arabic/RTL text `dir=auto` se show hota hai. Source information snapshot hai, live availability nahi.
- Previous complete conversation ka bounded history backend ko bhejte hain; refresh par history clear hoti hai. Index health status Groq ki availability guarantee nahi karta.

### Kahan

- `frontend/src/App.jsx`, `frontend/src/App.css`, `frontend/src/index.css`: chat behavior, responsive layout aur styling.
- `frontend/src/chatStream.js`, `frontend/src/chatStream.test.js`: SSE parsing, safe source links aur focused tests.
- `frontend/index.html`, `frontend/package.json`, `README.md`: page details, test command aur local usage.

### Verification aur limitations

- Frontend ke 4 stream tests, ESLint aur production build pass huay. Browser mein desktop aur 375px mobile layout, mock streaming reply, source link, follow-up history, error, stop aur new conversation check kiye.
- Browser test mein provider mocked tha; user ki key, live Groq response aur deployed URL test nahi kiye. Backend ke existing retrieval limitations aur data-use/privacy review ab bhi apply hote hain.
- Docker start/build/run nahi kiya.

## Docker deployment ki tayyari

- Status: Configuration tayyar; Docker build/run aur Hostinger deployment abhi verify nahi huay.

### Kyun

User ne Git par push se pehle container setup manga aur bataya ke Hostinger par pehle se doosri app hai. Is app ko alag project aur port par chalana zaroori hai.

### Kaise

- Multi-stage image mein React build hota hai aur non-root FastAPI process frontend aur API same origin se serve karta hai. SPA fallback unknown `/api` routes ko mask nahi karta.
- Compose project `darglobal-chatbot` ka default port host ke sirf `127.0.0.1:8085` par hai; doosri app ki configuration change nahi ki. Reverse proxy ke liye alag hostname aur SSE buffering off rakhne ki guidance di.
- Index aur SQLite image/Git mein nahi: poora index host bind mount se aata hai. Model cache alag named volume mein rehta hai; pehli startup par model download hota hai. `.env` build context se exclude hai.
- User ki pichhli language request ke mutabiq simple greetings bina retrieval ke handle hoti hain aur model ko English question par English answer ki instruction di gayi, source Arabic ho tab bhi. Arabic question ke liye Arabic instruction aur no-evidence message add hua; LLM language behavior guaranteed nahi.

### Kahan

- `Dockerfile`, `compose.yaml`, `.dockerignore`: image, separate service/port, index mount aur secret exclusions.
- `backend/app/frontend.py`, `backend/app/main.py`, `backend/tests/test_frontend.py`: frontend serving aur API route separation.
- `backend/app/api/chat.py`, `backend/app/services/chat.py`, `backend/tests/test_chat.py`: language aur greetings; pichhle Groq/startup changes bhi isi working tree mein hain.
- `README.md`: Docker commands, index transfer, permissions, model cache aur VPS/proxy limitations.

### Verification aur limitations

- `docker compose config --quiet` pass hua; Docker engine start nahi kiya aur image build/run nahi ki.
- Frontend serving ka focused test pass: static assets, SPA fallback, existing API aur unknown API 404 check huay. Language/greeting changes ke automated tests is step mein run nahi kiye; pehle backend test commands ki permission decline hui thi. User ne bataya tha ke bot chal raha hai, lekin in naye language changes ka live Groq test nahi hua.
- Windows se Linux Chroma portability, actual Docker image, available disk/memory, container health, HTTPS aur existing proxy integration user ko verify karni hai. Public use se pehle data permission/privacy aur API protection review zaroori hai.
