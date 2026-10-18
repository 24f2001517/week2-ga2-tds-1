# FastAPI Middleware Service

Implements `GET /ping` with request IDs, exact-origin CORS, and a per-client rate limit.

## Run locally

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate
pip install -r requirements.txt
```

Set your email before starting the server:

**Windows PowerShell**
```powershell
$env:EMAIL="your-real-logged-in-email@example.com"
$env:EXAM_ORIGIN="https://your-exam-page-origin.example"
uvicorn main:app --host 0.0.0.0 --port 8000
```

**macOS/Linux**
```bash
export EMAIL="your-real-logged-in-email@example.com"
export EXAM_ORIGIN="https://your-exam-page-origin.example"
uvicorn main:app --host 0.0.0.0 --port 8000
```

Visit `http://localhost:8000/ping`.

## Deploy to Render

1. Upload this project to a GitHub repository.
2. In Render, create **New + → Web Service** and connect the repository.
3. Use:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
4. Add environment variable `EMAIL` with the email address used for the assessment.
5. Add `EXAM_ORIGIN` with the exact origin of the exam page (scheme + hostname, no path). The assigned origin `https://app-s2twjt.example.com` is already allowed in code.
6. Deploy, then submit the deployed base URL, for example `https://your-service-name.onrender.com`.

## Behavior

- `X-Request-ID` is reused when supplied; otherwise a UUID4 is generated. It is returned in JSON and the `X-Request-ID` response header.
- Only the assigned CORS origin and the explicitly configured `EXAM_ORIGIN` receive `Access-Control-Allow-Origin`. No wildcard is used.
- Each `X-Client-Id` is limited to 10 requests per rolling 10-second window. A missing client ID uses the `anonymous` bucket.
- The limiter is in-memory and intended for a single service instance, as expected for this assessment.

## Quick checks

```bash
curl -i http://localhost:8000/ping -H "X-Request-ID: demo-123"
curl -i http://localhost:8000/ping -H "X-Client-Id: client-a"
curl -i -X OPTIONS http://localhost:8000/ping \
  -H "Origin: https://app-s2twjt.example.com" \
  -H "Access-Control-Request-Method: GET" \
  -H "Access-Control-Request-Headers: x-request-id,x-client-id"
```
