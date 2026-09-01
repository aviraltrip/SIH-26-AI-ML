# 🚀 SIH 26 — AI/ML Microservice & Integration Guide

Stateless AI/ML service powered by **FastAPI** and **Google Gemini 2.5 Flash**.  
This microservice provides **speech-to-intent parsing**, **multilingual multimodal certificate OCR**, **vernacular jargon simplification**, **scheme recommendation narratives**, and a **grounded scheme advisory chatbot (RAG)**.

---

## 📌 Quick Integration Cheatsheet for Fullstack Developers

| Base URL | Local: `http://localhost:8000` &nbsp;\|&nbsp; Production: `https://<your-render-service>.onrender.com` |
| :--- | :--- |
| **Interactive Docs (Swagger UI)** | `GET /docs` (Test all endpoints directly from your browser) |
| **OpenAPI JSON Schema** | `GET /openapi.json` |
| **Health Check (Keep-Alive)** | `GET /health` |

---

## 🧭 Endpoint Integration Guide

### 1. 🎤 Voice/Text Intent Extraction (`/extract-applicant-intent`)
> **Use Case in App**: When an applicant speaks (or types) into the search/onboarding bar in Hindi/English/regional languages. Automatically extracts structured profile details to pre-fill their form.

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

#### Fullstack Code Snippet (Axios / Fetch)
```typescript
// Call from Express or Next.js API Route
const res = await axios.post(`${AI_SERVICE_URL}/extract-applicant-intent`, {
  transcript: userSpeechTranscript,
  language: selectedLanguageCode // 'hi', 'en', 'mr', 'ta', etc.
});

const { project_category, requested_amount, annual_income, trade, gender } = res.data;
```

---

### 2. 📄 Certificate OCR & Verification (`/ocr-certificate`)
> **Use Case in App**: When an applicant uploads a Caste or Income Certificate (PDF, JPEG, or PNG). Extracts printed details (name, category, annual income) and checks whether income meets eligibility criteria ($\le$ ₹5,00,000).

* **Endpoint**: `POST /ocr-certificate`
* **Content-Type**: `multipart/form-data`
* **Form Fields**:
  - `file`: The binary file (`.pdf`, `.jpg`, `.jpeg`, `.png`, `.webp`)
  - `doc_type`: Either `"income"` or `"caste"`

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

#### Fullstack Code Snippet (Node.js / FormData)
```typescript
import FormData from 'form-data';
import fs from 'fs';

const formData = new FormData();
formData.append('file', fileBufferOrStream, { filename: 'certificate.pdf' });
formData.append('doc_type', 'income'); // or 'caste'

const res = await axios.post(`${AI_SERVICE_URL}/ocr-certificate`, formData, {
  headers: formData.getHeaders(),
});

console.log('Verified?', res.data.income_verified);
console.log('Extracted Fields:', res.data.extracted_fields);
```

---

### 3. 💡 Financial Jargon Simplifier (`/simplify-term`)
> **Use Case in App**: When a user hovers over or clicks an info icon on complex banking terms like *"Moratorium"*, *"Promoter Margin"*, *"Collateral"*, etc. Returns a 2–3 sentence conversational explanation with real-life analogies in their chosen language.

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

#### Fullstack Code Snippet
```typescript
const res = await axios.post(`${AI_SERVICE_URL}/simplify-term`, {
  term: 'Promoter Margin',
  language: 'mr' // Marathi, Hindi ('hi'), English ('en'), etc.
});

alert(res.data.explanation);
```

---

### 4. 🏆 Scheme Recommendation Explainer (`/recommend-scheme-explainer`)
> **Use Case in App**: On the Scheme Results / Comparison page. Takes the applicant's profile and the candidate schemes shortlisted by your database query, and generates a personalized narrative explaining *why* the top scheme was chosen and how other schemes compare.

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
  "explanation": "Mahila Samriddhi Yojana is the best match for you because it offers 90% project coverage with a highly subsidized interest rate of 4.0% per annum, specifically tailored for women entrepreneurs in tailoring.",
  "runner_up_note": "Micro Credit Scheme is also an option, but it covers only 80% and has a higher interest rate of 6.0%."
}
```

---

### 5. 🤖 Grounded Scheme Advisory Chatbot (`/scheme-chat`)
> **Use Case in App**: An interactive chatbot widget where users can ask any questions about government schemes (eligibility, documents required, loan limits, interest rates). The AI answers strictly from official policy guidelines (`schemes_knowledge.txt`) and dynamically returns 2–3 contextual follow-up questions for the frontend to render as quick-reply chips/pills.

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
  "response": "Under the Mahila Samriddhi Yojana, eligible female beneficiaries can receive loans up to ₹1,40,000 with a subsidized interest rate of 4% per annum. The scheme covers up to 90% of the total project cost.",
  "suggested_questions": [
    "What documents are required to apply for Mahila Samriddhi Yojana?",
    "What is the annual income eligibility criteria?",
    "How can I apply for this loan through a channel partner?"
  ]
}
```

---

## ⚠️ Standard Error Handling

All error responses return a standardized JSON structure:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Schema validation failed or request payload is invalid.",
    "details": "body -> transcript: Field required"
  }
}
```

### HTTP Status Codes
- `200 OK`: Successful operation.
- `400 BAD_REQUEST`: Missing required parameters or empty payload.
- `422 VALIDATION_ERROR`: Incorrect data types or failed field validations.
- `500 INTERNAL_SERVER_ERROR`: Upstream AI provider error (e.g. invalid API key or rate limit).

---

## 🛠️ Local Setup & Running Locally

```bash
# 1. Clone repo
git clone https://github.com/aviraltrip/SIH-26-AI-ML.git
cd SIH-26-AI-ML

# 2. Set up virtual environment
python -m venv venv
# Windows:
.\venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create .env file
echo "GEMINI_API_KEY=your_gemini_api_key_here" > .env

# 5. Run the server
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```
Open [http://localhost:8000/docs](http://localhost:8000/docs) in your browser to test endpoints interactively.

---

## 🌐 Production Deployment (Render)

1. **Environment Variables**: Add `GEMINI_API_KEY` in the Render Dashboard (**Environment** tab).
2. **Preventing Free-Tier Sleep**: Render puts free containers to sleep after 15 minutes of inactivity. Set up a free monitor (e.g. on [UptimeRobot](https://uptimerobot.com)) to ping `GET /health` every 10–12 minutes.
