# DarGlobal and Wasalt Chatbot

React aur FastAPI skeleton ke saath local data-cleaning aur index-building pipeline. Chatbot API abhi implement nahi hui.

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

Vite ke terminal mein dikhaya gaya local URL kholein. Page backend connectivity status dikhata hai. Development proxy `/api` requests ko `127.0.0.1:8000` par bhejta hai.

Production build aur lint:

```powershell
npm run build
npm run lint
```

## Secrets aur data

`.env.example` mein sirf future OpenRouter key ka placeholder hai; app abhi usay read nahi karti. Real keys commit ya frontend mein expose na karein. Docker setup aur testing user baad mein khud karega.

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
