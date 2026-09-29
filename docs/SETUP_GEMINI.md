# Setup Guide: Google Gemini Flash Primary Reasoning Engine

This guide walks you through setting up Google Gemini Flash (Free Tier) as the primary cognitive brain for Orvix Sphere.

---

## 1. Overview & Benefits
- **Lightning-Fast Reasoning**: Replaces the constrained 1B CPU model with Google Gemini 2.0 Flash for multi-step reasoning, coding, and tool chaining.
- **100% Free**: Google AI Studio provides a free tier with:
  - **15 requests per minute (RPM)** (Orvix includes a built-in safety rate limiter at 14 RPM).
  - **1,000,000 tokens per minute (TPM)**.
  - **1,500 requests per day**.
  - **$0.00 cost**.
- **Offline Fallback**: If you lose internet connection, hit rate limits, or don't set an API key, Orvix automatically and silently falls back to your local 1B model / native reasoning engine.

---

## 2. Getting Your Free API Key

1. Open your browser and navigate to:
   👉 **[https://aistudio.google.com/apikey](https://aistudio.google.com/apikey)**
2. Sign in with your Google account.
3. Click the blue button: **"Create API Key"**.
4. Select or create a Google Cloud project (no billing required for the free tier).
5. Copy your newly generated API key.

---

## 3. Configuring Orvix Sphere

You can configure your key using any of the following methods:

### Option A: Environment Variable (Recommended)

#### PowerShell (Current Session):
```powershell
$env:GEMINI_API_KEY = "AIzaSy..."
```

#### PowerShell (Permanent User Environment):
```powershell
[System.Environment]::SetEnvironmentVariable('GEMINI_API_KEY', 'AIzaSy...', 'User')
```

#### Linux / macOS (Bash / Zsh):
```bash
export GEMINI_API_KEY="AIzaSy..."
```

### Option B: `.env` File in Project Root

Create or update `.env` in `C:\Users\ph50\.gemini\antigravity\scratch\orvix_sphere\.env`:
```env
GEMINI_API_KEY=AIzaSy...
MODEL_MODE=cloud_first
```

---

## 4. Standalone Verification

Verify that Gemini Flash is functioning standalone using Python:

```powershell
.\.venv\Scripts\python.exe -c "
from tools.gemini_engine import GeminiEngine
g = GeminiEngine()
print('Available:', g.is_available())
if g.is_available():
    print('Response:', g.generate('Who are you? Answer in one sentence.'))
else:
    print('Key not detected. Please set GEMINI_API_KEY.')
"
```

---

## 5. Using Gemini Flash Inside Orvix Sphere

Start the interactive chat interface:
```powershell
.\.venv\Scripts\python.exe run_model_chat.py
```

### Slash Commands:
- `/router`: Inspect the current routing mode, active engines, and rate limit headroom.
- `/router cloud_first`: Prefer Gemini Flash, fallback to local model on network loss (Default).
- `/router cloud_only`: Always require Gemini Flash.
- `/router local_only`: Run 100% locally on CPU without making cloud calls.
- `/router auto`: Smart route by task complexity (simple greetings run locally; complex tasks route to Gemini).
- `/api-usage`: Inspect token consumption, request counts, and cost today ($0.00).
- `/test-brain`: Runs a 5-question cognitive diagnostic test and displays which engine answered.

---

## 6. Architecture & Failsafe Design

```
                     User Request
                          │
                   ▼ ModelRouter
            ┌─────────────┴─────────────┐
     Cloud Available?               Offline?
            │                           │
     ▼ Rate Limiter (14 RPM)            │
            │                           │
     ▼ GeminiEngine                     │
    (gemini-2.0-flash)                  │
            │ (On failure)              │
            └───────────► LocalEngine ◄─┘
                          (1B / Native)
```
