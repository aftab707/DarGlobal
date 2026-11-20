# DarGlobal and Wasalt Chatbot

Phase 1 ka React aur FastAPI skeleton. Chatbot aur search index abhi implement nahi huay.

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

`GET http://127.0.0.1:8000/api/health` abhi HTTP 503 aur `{"status":"not_ready","index_ready":false}` deta hai. Backend chal raha hai, lekin Phase 3 tak index nahi bana; readiness ko galti se healthy na dikhane ke liye yeh expected hai.

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

`.env.example` mein sirf future OpenRouter key ka placeholder hai; Phase 1 usay read nahi karta. Real keys commit ya frontend mein expose na karein. Source data `Chatbot` ke parent folder mein hai; ingestion aur database later phases mein banenge. Docker setup aur testing user baad mein khud karega.
