# 🚀 SIH 26 — AI/ML Microservice & Integration Guide

Stateless, production-ready AI/ML microservice built with **FastAPI**, **Google Gemini 2.5 Flash** (via `google-genai` SDK and **OpenRouter** fallback), and **Pydantic v2**.

This service powers the intelligence layer for the Smart India Hackathon (SIH) Scheme Matching Platform, providing:
- 🎤 **Multilingual Voice & Text Intent Extraction** (Speech transcription to structured profile)
- 📄 **Multimodal Certificate OCR & Verification** (Income & Caste certificates in PDF/Image formats via PyMuPDF + Gemini Vision)
- 💡 **Vernacular Financial Jargon Simplification** (Explaining complex terms in 12+ Indian regional languages with real-life analogies)
- 🏆 **Personalized Scheme Recommendation Narratives** (Localized justification comparing candidate schemes)
- 🤖 **Grounded Scheme Advisory Chatbot (RAG)** (Two-tier hybrid RAG answering from official policy guidelines with proactive follow-up quick-replies)

---

## 📌 Quick Integration Cheatsheet for Fullstack Developers

| Property | Value |
| :--- | :--- |
| **Base URL (Local)** | `http://localhost:8000` |
| **Base URL (Production)** | `https://<your-service-name>.onrender.com` |
| **Interactive Docs (Swagger UI)** | [`GET /docs`](http://localhost:8000/docs) (Test and inspect all endpoints directly in your browser) |
| **Alternative Docs (ReDoc)** | [`GET /redoc`](http://localhost:8000/redoc) |
| **OpenAPI Schema** | `GET /openapi.json` |
| **Health Check & Keep-Alive** | `GET /health` |
| **Root Welcome Endpoint** | `GET /` |

---

## 🧭 Endpoint Integration Guide

### 1. 🎤 Voice/Text Intent Extraction (`POST /extract-applicant-intent`)

> **Use Case**: When an applicant speaks or types into the search or onboarding interface in Hindi, English, Marathi, Tamil, etc. Automatically extracts structured profile parameters to pre-fill their application form.

* **Endpoint**: `POST /extract-applicant-intent`
* **Content-Type**: `application/json`

#### Request Payload
```json
{
  "transcript": "नमस्ते, मैं एक सिलाई की दुकान शुरू करने के लिए 80,000 रुपये का ऋण चाहती हूँ। मेरी वार्षिक पारिवारिक आय 1,20,000 रुपये है।",
  "language": "hi"
}
```

#### Response (200 OK)
```json
{
  "project_category": "Manufacturing",
  "requested_amount": 80000.0,
  "annual_income": 120000.0,
  "trade": "Tailoring",
  "gender": "Female",
  "confidence": 0.95
}
```

#### Frontend / Fullstack Integration (TypeScript / Axios)
```typescript
import axios from "axios";

interface IntentResponse {
  project_category: "Manufacturing" | "Service" | "Trading";
  requested_amount: number;
  annual_income: number;
  trade: string;
  gender: string;
  confidence: number;
}

export async function extractApplicantIntent(transcript: string, language: string = "hi"): Promise<IntentResponse> {
  const { data } = await axios.post<IntentResponse>(`${process.env.AI_SERVICE_URL}/extract-applicant-intent`, {
    transcript,
    language,
  });
  return data;
}
```

---

### 2. 📄 Multimodal Certificate OCR & Verification (`POST /ocr-certificate`)

> **Use Case**: When an applicant uploads a Caste or Income Certificate (`.pdf`, `.jpg`, `.jpeg`, `.png`, `.webp`). Extracts printed name, category, income, and validity date, and automatically verifies income eligibility ($\le$ ₹5,00,000).

* **Endpoint**: `POST /ocr-certificate`
* **Content-Type**: `multipart/form-data`
* **Form Fields**:
  - `file`: Binary file stream (`.pdf`, `.png`, `.jpg`, `.jpeg`, `.webp`)
  - `doc_type`: String — `"income"` or `"caste"`

#### Response (200 OK — Income Certificate)
```json
{
  "doc_type": "income",
  "extracted_fields": {
    "name": "Amit Ramesh Kumar",
    "category": null,
    "annual_income": 180000.0,
    "valid_until": "2027-03-31"
  },
  "income_verified": true,
  "raw_confidence": 0.92
}
```

#### Response (200 OK — Caste Certificate)
```json
{
  "doc_type": "caste",
  "extracted_fields": {
    "name": "Sunita Devi",
    "category": "OBC",
    "annual_income": null,
    "valid_until": null
  },
  "income_verified": false,
  "raw_confidence": 0.95
}
```

#### Frontend / Fullstack Integration (Node.js FormData / Web API)
```typescript
import FormData from "form-data";
import axios from "axios";

export async function verifyCertificate(fileBuffer: Buffer, filename: string, docType: "income" | "caste") {
  const formData = new FormData();
  formData.append("file", fileBuffer, { filename });
  formData.append("doc_type", docType);

  const { data } = await axios.post(`${process.env.AI_SERVICE_URL}/ocr-certificate`, formData, {
    headers: formData.getHeaders(),
  });

  return data;
}
```

---

### 3. 💡 Financial Jargon Simplifier (`POST /simplify-term`)

> **Use Case**: When a user clicks or hovers over complex banking terms (e.g. *"Moratorium"*, *"Promoter Margin"*, *"Collateral"*, *"Working Capital"*, *"Debt-Equity Ratio"*). Returns a 2–3 sentence conversational explanation with real-life analogies in their chosen language without technical jargon.

* **Endpoint**: `POST /simplify-term`
* **Content-Type**: `application/json`

#### Request Payload
```json
{
  "term": "Moratorium Period",
  "language": "hi"
}
```

#### Response (200 OK)
```json
{
  "explanation": "मोरेटोरियम अवधि एक प्रकार की भुगतान छूट की अवधि है जिसमें आपको ऋण लेने के तुरंत बाद मासिक किस्त (EMI) चुकाने की जरूरत नहीं होती। यह आपको अपना व्यवसाय शुरू करने और स्थिर होने के लिए आवश्यक समय देती है।"
}
```

#### Frontend / Fullstack Integration (TypeScript / Fetch)
```typescript
export async function simplifyJargon(term: string, language: string = "hi"): Promise<string> {
  const res = await fetch(`${process.env.AI_SERVICE_URL}/simplify-term`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ term, language }),
  });
  const data = await res.json();
  return data.explanation;
}
```

---

### 4. 🏆 Scheme Recommendation Explainer (`POST /recommend-scheme-explainer`)

> **Use Case**: On the scheme comparison or recommendation page. Takes the applicant's profile and database-shortlisted candidate schemes, and generates a personalized narrative explaining *why* the top scheme was recommended and how other alternatives compare.

* **Endpoint**: `POST /recommend-scheme-explainer`
* **Content-Type**: `application/json`

#### Request Payload
```json
{
  "applicant": {
    "project_category": "Manufacturing",
    "requested_amount": 80000.0,
    "annual_income": 120000.0,
    "trade": "Tailoring",
    "gender": "Female"
  },
  "candidate_schemes": [
    {
      "scheme_name": "Mahila Samriddhi Yojana",
      "max_coverage_pct": 90.0,
      "interest_rate": 4.0,
      "eligibility_score": 0.95
    },
    {
      "scheme_name": "Micro Credit Scheme",
      "max_coverage_pct": 80.0,
      "interest_rate": 6.0,
      "eligibility_score": 0.82
    }
  ],
  "language": "en"
}
```

#### Response (200 OK)
```json
{
  "top_scheme": "Mahila Samriddhi Yojana",
  "explanation": "Mahila Samriddhi Yojana is the most suitable scheme for you because it offers the highest financial coverage (90%) and a low subsidized interest rate of 4.0% specifically designed for female entrepreneurs in tailoring.",
  "runner_up_note": "Micro Credit Scheme is also an option, but it covers only 80% with a higher interest rate of 6.0%."
}
```

---

### 5. 🤖 Grounded Scheme Advisory Chatbot (`POST /scheme-chat`)

> **Use Case**: Interactive conversational assistant widget. Users can ask questions regarding schemes, eligibility, documents, interest rates, and loan procedures in any language. The AI answers strictly from official scheme knowledge (`schemes_knowledge.txt`), provides general procedural guidance when needed, and returns 2–3 contextual follow-up question suggestions for clickable quick-reply chips.

* **Endpoint**: `POST /scheme-chat`
* **Content-Type**: `application/json`

#### Request Payload
```json
{
  "message": "What is the maximum loan limit and interest rate for Mahila Samriddhi Yojana?",
  "history": [
    {
      "role": "user",
      "parts": "Hello"
    },
    {
      "role": "model",
      "parts": "Namaste! I am your scheme advisor. How can I help you today?"
    }
  ],
  "language": "en"
}
```

#### Response (200 OK)
```json
{
  "response": "Under the Mahila Samriddhi Yojana (MSY), female beneficiaries from backward classes can avail loans up to ₹1,40,000 with a subsidized interest rate of 4% per annum. The scheme covers up to 90% of the project cost.",
  "suggested_questions": [
    "What documents are required to apply for Mahila Samriddhi Yojana?",
    "What is the annual income eligibility limit?",
    "How can I apply for this loan through a State Channelising Agency?"
  ]
}
```

---

## ⚠️ Standardized Error Response

All error responses across all routes follow a unified JSON envelope:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Schema validation failed or request payload is invalid.",
    "details": "body -> transcript: Field required"
  }
}
```

### HTTP Status Code Mapping

| Status Code | Error Code | Trigger Condition |
| :--- | :--- | :--- |
| `200 OK` | — | Successful processing. |
| `400 BAD_REQUEST` | `BAD_REQUEST` | Empty input text, unsupported document extension, corrupted upload. |
| `401 UNAUTHORIZED` | `UNAUTHORIZED` | Invalid or expired API credentials with upstream LLM provider. |
| `403 FORBIDDEN` | `FORBIDDEN` | Upstream provider permission denied. |
| `404 NOT_FOUND` | `NOT_FOUND` | Route not found. |
| `422 UNPROCESSABLE` | `VALIDATION_ERROR` | Missing required payload fields or invalid data types. |
| `500 INTERNAL ERROR` | `INTERNAL_SERVER_ERROR` | Upstream API downtime or runtime processing failure. |

---

## ⚙️ Configuration & Environment Variables

Create a `.env` file in the root directory (see [`.env.example`](file:///c:/Users/avira/SIH-26-AI-ML/.env.example)):

```env
# Option 1: Direct Google Gemini API Key (Recommended)
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash

# Option 2: OpenRouter API Key (Automatic detection for sk-or-... keys)
# OPENROUTER_API_KEY=sk-or-v1-...
# GEMINI_MODEL=google/gemini-2.5-flash
# OPENROUTER_BASE_URL=https://openrouter.ai/api/v1

PORT=8000
```

---

## 🛠️ Local Setup & Testing

### 1. Clone & Setup Environment
```bash
git clone https://github.com/aviraltrip/SIH-26-AI-ML.git
cd SIH-26-AI-ML

# Create and activate virtual environment
python -m venv venv
# On Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# On Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Run the Test Suite (45 Unit & Integration Tests)
```bash
python -m pytest
```

### 3. Launch Development Server
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```
Open [http://localhost:8000/docs](http://localhost:8000/docs) in your browser for interactive testing via Swagger UI.

---

## 🐳 Docker & Containerization

### Build and Run Docker Container Locally
```bash
# Build Docker image
docker build -t sih-ai-ml-service .

# Run container
docker run -p 7860:7860 -e GEMINI_API_KEY="your_api_key" sih-ai-ml-service
```

---

## 🌐 Production Deployment (Render)

1. Connect your repository to **Render** as a **Web Service** (Docker runtime).
2. Set Environment Variables in Render Dashboard:
   - `GEMINI_API_KEY`: Your Google Gemini API Key (or `OPENROUTER_API_KEY`)
   - `GEMINI_MODEL`: `gemini-2.5-flash` (or `google/gemini-2.5-flash`)
3. Render will build the container using [`Dockerfile`](file:///c:/Users/avira/SIH-26-AI-ML/Dockerfile) and expose the required port.
4. **Keep-Alive**: Set up a free uptime monitor (e.g. UptimeRobot or Cron-Job) targeting `GET /health` every 10 minutes to prevent container sleep.

---

## 📚 Technical Documentation Links

- [AI_ML_SPECIFICATION.md](file:///c:/Users/avira/SIH-26-AI-ML/AI_ML_SPECIFICATION.md) — System architecture, boundaries, and separation of concerns.
- [API_CONTRACTS.md](file:///c:/Users/avira/SIH-26-AI-ML/API_CONTRACTS.md) — Detailed Pydantic schemas, validation rules, and status codes.
- [PIPELINES.md](file:///c:/Users/avira/SIH-26-AI-ML/PIPELINES.md) — LLM prompt templates, multimodal OCR heuristics, and two-tier RAG architecture.
