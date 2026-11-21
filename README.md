# DarGlobal and Wasalt Chatbot

React chat UI, local data-cleaning aur index-building pipeline, aur Groq ke saath FastAPI streaming chat backend.

## Requirements

- Python 3.11 ya 3.12
- Node.js aur npm, existing frontend ke liye

## Backend: Windows PowerShell

Python 3.11 se virtual environment banayein. Neeche `py -3.11` tab chalega jab Python launcher ko 3.11 milta ho; warna apne Python 3.11 executable ka path use karein.

```powershell
cd D:\DarGlobal\Chatbot\backend
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Is machine par Python 3.11 Conda environment mein hai; virtual environment banane ke liye yeh alternative use ho sakta hai:

```powershell
& 'C:\Users\aftab\miniconda3\envs\myenv\python.exe' -m venv .venv
```

Doosre terminal se backend tests:

```powershell
cd D:\DarGlobal\Chatbot\backend
.\.venv\Scripts\python.exe -m pytest -q
```

`GET http://127.0.0.1:8000/api/health` valid index na mile to HTTP 503 aur `{"status":"not_ready","index_ready":false}` deta hai. Valid persistent index aur matching listings database milne par HTTP 200 aur `{"status":"ok","index_ready":true}` milta hai. Yeh index readiness hai, complete chatbot functionality ka claim nahi.

## Frontend: Windows PowerShell

Doosre terminal mein:

```powershell
cd D:\DarGlobal\Chatbot\frontend
npm install
npm run dev
```

Vite ke terminal mein dikhaya gaya local URL kholein. Chat mein suggested questions ya apna message bhej sakte hain; Enter send karta hai aur Shift+Enter se nayi line banti hai. Stream ke dauran Stop, New conversation aur source links available hain. Assistant ke Markdown answers mein headings, bold, lists aur tables format hote hain; generated links sirf trusted source domains ke liye active hain. Arabic aur doosra RTL text automatic direction ke saath dikhta hai. Conversation sirf current page session mein rehti hai, refresh par clear hoti hai.

Page index health dikhata hai; green status Groq key ya model availability ki guarantee nahi. Backend startup par embedding model aur index load karta hai, is liye server ready hone mein waqt lag sakta hai. Development proxy `/api` requests ko `127.0.0.1:8000` par bhejta hai.

Production build aur lint:

```powershell
npm run build
npm run lint
npm run test
```

## Secrets aur data

`.env.example` mein Groq key ka empty placeholder hai. Real keys commit ya frontend mein expose na karein. Docker setup neeche hai; Docker build aur run user khud karega.

## Groq chat API

`backend/.env` file banayein aur apni key locally set karein; key chat ya GitHub par share na karein:

```dotenv
GROQ_API_KEY=your-key-here
GROQ_MODEL=openai/gpt-oss-20b
```

`GROQ_MODEL` optional hai. OS environment variables `.env` se priority rakhte hain. File edit karne ke baad backend restart karein. `python-dotenv` aur baqi dependencies install karne ke liye `backend` folder mein `.\.venv\Scripts\python.exe -m pip install -r requirements.txt` chalayein, phir upar wali Uvicorn command se backend start karein.

`POST /api/chat` JSON leta hai: `{"message":"What is AIDA 360?","history":[]}`. History optional hai, maximum 10 `user`/`assistant` messages; message aur har history item maximum 2,000 characters, combined maximum 12,000 characters hain. Response `text/event-stream` hai: `sources`, ek ya zyada `delta`, phir `done`. Streaming ke dauran provider fail ho to `error` event aata hai, `done` nahi. Missing key ya unavailable index par HTTP 503; invalid input par HTTP 422 milta hai.

Simple English aur Arabic greetings bina search ke handle hote hain. Doosre sawalon ke liye model ko English by default aur Arabic sawal ka jawab Arabic mein dene ki instruction hai, chahe evidence kisi aur language mein ho. LLM ka instruction follow karna guaranteed nahi; Arabic script ki pehchan no-evidence message ke liye heuristic hai aur Urdu jaisi languages bhi Arabic script use karti hain.

Local test, backend run hone ke baad:

```powershell
$body = @{ message = "What is AIDA 360?"; history = @() } | ConvertTo-Json -Depth 4
$response = Invoke-WebRequest -Uri http://127.0.0.1:8000/api/chat -Method Post -ContentType "application/json" -Body $body
$response.Content
```

PowerShell yahan poora response buffer kar sakta hai; React UI SSE events stream karti hai. API ko `/docs` par bhi dekha ja sakta hai. Backend startup par local embedding model load hota hai aur waqt lag sakta hai; restart ke baad index/model phir load honge.

Chat request mein user message, history aur retrieved snippets **Groq ko bheje jate hain**. Public use se pehle unka data-use authorization aur privacy review confirm karein. Assignment email ne specifically OpenRouter free model manga tha; direct Groq use accept hone ki tasdeeq hiring team se karein.

Yeh initial backend hai, production-ready retrieval nahi: SQLite listing filters aur calibrated low-relevance threshold abhi nahi bane, irrelevant nearest results aa sakte hain aur LLM citations/grounding guaranteed nahi. Purana English-to-Arabic sample bhi unresolved hai. History evidence nahi; follow-up retrieval sirf current message se hoti hai. Auth aur rate limiting abhi nahi, is liye public exposure se pehle protection zaroor add karein.

## Data cleaning aur audit

Original source folders `Chatbot` ke parent mein hone chahiye: `dar_global`, `wasalt_data` aur `wasalt_company_data`. Existing files ko edit ya re-scrape nahi kiya jata. Backend folder se:

```powershell
cd D:\DarGlobal\Chatbot\backend
.\.venv\Scripts\python.exe scripts\clean_data.py
```

Different location ke liye `--input-root` aur `--output-dir` specify kar sakte hain:

```powershell
.\.venv\Scripts\python.exe scripts\clean_data.py --input-root "D:\DarGlobal" --output-dir "D:\DarGlobal\Chatbot\data\cleaned"
```

Output:

- `data/cleaned/documents.jsonl`: source, URL, title, type, scrape timestamp aur cleaned narrative text. DarGlobal ki per-page scrape date source mein nahi hai to `null` rehti hai.
- `data/cleaned/listings.jsonl`: matched Wasalt properties aur verified city, purpose, property type, area, price/currency jaisi fields. Unknown values `null` hain.
- `data/cleaned/audit_report.json`: input counts, duplicates, exclusions, missing fields aur limitations.

Same data par repeated runs same output dete hain. Script missing input ya invalid JSON par error deti hai aur source files overwrite nahi karti. Failure ke baad pehle se maujood output purana ho sakta hai; usay new successful run samajh kar use na karein.

Property card aur detail ko matching URL, title aur main content ke conservative rules se check kiya jata hai; yeh heuristic hai, manual verification ka substitute nahi. Search/category URLs ko individual listing nahi banaya jata. Category aur auction records apni category ke taur par alag rahte hain. Card ki city, area aur explicitly-currency-labelled price bhi detail se match na hon to unknown rehte hain. Duplicate URL par specific auction/category record generic company record se pehle aata hai; same priority par latest source timestamp, text length aur content hash se deterministic choice hoti hai.

Listing ke description aur recommended listings filhaal intentionally exclude hain, taake property details mix na hon. Emails aur phone-like numbers remove karne ki best-effort koshish hoti hai, lekin names ya baqi personal information ki complete removal **guaranteed nahi**; external API, public demo ya upload se pehle privacy aur data-use permission review zaroori hai. Prices aur availability historical snapshot hain, live data nahi. Current output ki 302 verified-candidate listings mein structured price `null` hai, is liye price-based filtering se abhi reliable results nahi milenge.

`data/` Git se ignored hai; GitHub par output automatically upload nahi hoga. Doosri machine par script dubara chalane ke liye source files aur zaroori authorization alag se chahiye.

## LangChain aur local index

Cleaning ke baad backend folder se index banayein:

```powershell
cd D:\DarGlobal\Chatbot\backend
.\.venv\Scripts\python.exe scripts\build_index.py
```

Is process mein LangChain recursive splitter embedding model ke tokenizer se chunks measure karta hai. Title aur special tokens mila kar har embedding input maximum 120 tokens hai; 20-token overlap target hai. Agar title 20 tokens se lamba ho to embedding mein uska short version use hota hai, lekin complete title source metadata mein rehta hai. Source URL, type aur timestamp bhi metadata mein hain.

Embedding model `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` CPU par local chalta hai aur model revision fixed hai. Pehli baar model files Hugging Face se download hoti hain; data embedding ke liye bahar nahi bheja jata. Chroma telemetry aur build ke dauran LangSmith tracing disable hain.

Index `data/index/versions/<build-id>/chroma` mein aur listing fields usi build ki `listings.sqlite3` mein rehte hain. `data/index/current.json` sirf successfully verified build ko point karta hai. Build ke liye app stop rakhein: ek time par ek writer allowed hai. Agar process crash ki wajah se `build.lock` reh jaye, pehle confirm karein ke koi build process nahi chal raha; phir sirf us lock file ko manually remove karein. Failed build ka incomplete version agar cleanup na ho sake to error log mein path milta hai. Successful rebuild par purana version automatic delete nahi hota.

Existing index ko verify aur sample retrieval check karne ke liye:

```powershell
.\.venv\Scripts\python.exe scripts\check_index.py
```

Yeh sample checks actual full chatbot evaluation ka substitute nahi. Current index par English se Arabic listing ka sample unfiltered top 10 mein fail hota hai, is liye command nonzero exit code deti hai aur Phase 3 ka retrieval exit criterion abhi poora nahi hua. Ek local experiment mein city, purpose aur area manually filter karne ke baad expected listing four candidates mein first aayi; natural-language filter extraction aur automatic search abhi implement nahi huay. Unrelated query par semantic search hamesha nearest results de sakti hai; no-evidence decision aur threshold Phase 4 mein implement aur test karne hain. Listing prices abhi unknown hain.

`INDEX_ROOT` environment variable se index folder change kiya ja sakta hai. Index aur SQLite artifacts `data/` ki tarah Git se ignored hain. LLM API ya public deployment se pehle data-use permissions aur privacy review zaroor karein.

## Docker aur Hostinger VPS preparation

Dockerfile React ko build karta hai aur FastAPI usi image se frontend aur `/api` serve karti hai. Compose project ka naam `darglobal-chatbot` hai. Default par sirf host ke `127.0.0.1:8085` par bind hota hai; existing app ke containers, ports aur proxy config modify nahi karta. Port 8085 agar busy ho to project root ki ignored `.env` mein `CHATBOT_PORT=8086` likhein ya shell environment mein set karein. Yeh backend ki secret `backend/.env` se alag file hai.

**Zaroori:** Yeh Docker-capable Linux VPS ke liye hai; shared hosting ya managed plan par Docker access ki guarantee nahi. Container memory aur disk requirements verify karein: local indexing ke dauran peak working set lagbhag 1.5 GiB tha, lekin container production requirements abhi measure nahi hui. Ek hi worker aur index ka ek hi owner rakhein.

### Git aur server par kya transfer karna hai

- Source Git se clone hoga, lekin `backend/.env` aur `data/index` Git aur Docker build context dono se excluded hain. Secrets aur index image mein bake nahi hote.
- Server par `backend/.env` khud banayein: `.env.example` copy karke `GROQ_API_KEY` aur `GROQ_MODEL` set karein. Key ko private rakhein aur restrictive file permissions dein. `GROQ_MODEL=openai/gpt-oss-20b` bhi use kar sakte hain. Chat mein expose hui purani key revoke karke nayi key use karein.
- Local complete `data/index` folder securely server ke project ke `data/index` mein transfer karein: `current.json` **aur** us ke referenced `versions/<build-id>` folder mein `manifest.json`, poora `chroma` aur `listings.sqlite3` required hain. Sirf `chroma` copy na karein. Copy se pehle index build aur app band rakhein taake consistent snapshot ho. User authorization/privacy review ke baghair scraped data ya index public jagah upload na karein.
- Bind mount ke liye directory pehle se honi chahiye. Container non-root UID `10001` se chalta hai aur Chroma ko index directory mein read/write permissions chahiye. Linux server par apne project directory se zarurat par `sudo chown -R 10001:10001 ./data/index` karein; doosri app ki files na badlein. Windows-built Chroma index ka Linux par compatibility aur permissions actual container test se verify karna zaroori hai; agar open na ho to authorized source data se Linux par index rebuild karein.
- Embedding model pehle startup par Hugging Face se download hota hai. Named Docker volume us model cache ko restart/recreate ke baad preserve karta hai; pehli startup par internet aur extra time/disk chahiye. Is volume ko `docker compose down -v` se delete na karein jab tak cache deliberately remove na karna ho. Index alag host bind mount mein hai; us ka private backup rakhein. Rebuild/update ke waqt app stop rakhein, complete verified index replace karein, phir app restart karein.

Misal ke taur par, agar repository VPS par `~/darglobal-chatbot` mein clone ki hai, pehle VPS terminal mein `mkdir -p ~/darglobal-chatbot/data` chalayein. Phir Windows PowerShell mein project root se neeche command mein `VPS_USER` aur `VPS_HOST` apni details se replace karke snapshot bhejein:

```powershell
scp -r .\data\index VPS_USER@VPS_HOST:~/darglobal-chatbot/data/
```

Server par project root se `cp .env.example backend/.env` karke file private editor mein configure karein aur `chmod 600 backend/.env` chalayein. GitHub ya chat mein key na likhein.

### Run aur verify — user ke liye

Project root par Docker aur Compose plugin installed hon, `backend/.env` aur `data/index` ready hon:

```powershell
cd D:\DarGlobal\Chatbot
docker compose config --quiet
docker compose up -d --build
docker compose ps
docker compose logs --tail 100 app
```

Server par bhi yahi `docker compose` commands project root mein chalengi. Pehle model download/startup complete hone dein. Us machine par `http://127.0.0.1:8085/` aur `http://127.0.0.1:8085/api/health` check karein; localhost binding ki wajah se remote browser se yeh directly open nahi hoga. Local testing ke liye SSH port forwarding ya public deployment ke liye apne existing reverse proxy par **alag hostname** configure karein. User ke `/api/chat` test mein streaming answer aur source links, phir `docker compose restart app` ke baad health/chat dobara verify karein. Health sirf index readiness hai, Groq availability nahi.

Reverse proxy ko alag hostname se `http://127.0.0.1:8085` tak forward karein, TLS enable karein, aur chat streaming ke liye response buffering off aur suitable read timeout rakhein. Existing site ka server block ya ports replace na karein. Agar proxy bhi Docker container mein hai, us ka `127.0.0.1` host nahi hota: usay host tak pahunch dene ke liye environment-specific networking configure karein. DNS, TLS aur proxy actual server par separately verify karne honge. Is app mein abhi authentication/rate limiting nahi; internet par expose karne se pehle suitable protections lagayein.

Docker image build/run, Linux index portability, Hostinger network/proxy aur live deployment abhi verify nahi huay.
