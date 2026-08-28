# API Contract Specifications

This document defines the strict API contracts, Pydantic schemas, validation constraints, and error response formats for the FastAPI AI/ML microservice.

---

## Global Error Response Format

All standard HTTP exceptions, validation errors, and runtime failures return a consistent JSON schema:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Schema validation failed or request payload is invalid.",
    "details": "body -> transcript: Field required"
  }
}
```

### Standard Error Codes
* `BAD_REQUEST` (400): Missing required parameters or empty payload.
* `VALIDATION_ERROR` (422): JSON schema validation failed or type constraints violated.
* `UNAUTHORIZED` / `FORBIDDEN` (401 / 403): Auth failure with upstream providers.
* `NOT_FOUND` (404): Route or resource not found.
* `INTERNAL_SERVER_ERROR` (500): Downstream LLM provider timeout or processing error.

---

## 1. Extract Applicant Intent

Parses conversational speech transcriptions or text statements into structured applicant profiles.

* **URL**: `/extract-applicant-intent`
* **Method**: `POST`
* **Content-Type**: `application/json`

### Pydantic Models

```python
from typing import Literal
from pydantic import BaseModel, Field

class IntentRequest(BaseModel):
    transcript: str = Field(..., description="Raw text or transcription from speech-to-text")
    language: str = Field("en", description="ISO language code of transcription (e.g., 'en', 'hi', 'mr')")

class IntentResponse(BaseModel):
    project_category: Literal["Manufacturing", "Service", "Trading"] = Field(
        ..., description="Categorized project type (Manufacturing, Service, or Trading)"
    )
    requested_amount: float = Field(
        ..., ge=0.0, description="Requested loan amount in INR. Defaults to 0.0 if not detected."
    )
    annual_income: float = Field(
        ..., ge=0.0, description="Applicant's household annual income in INR. Defaults to 0.0 if not detected."
    )
    trade: str = Field(..., description="Specific trade name in English (e.g. Tailoring, Dairy, Barber)")
    gender: str = Field(..., description="Gender (e.g. Male, Female, Other). Defaults to Male if unknown.")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score of extraction between 0.0 and 1.0")
```

### Example Request
```json
{
  "transcript": "नमस्ते, मैं एक सिलाई की दुकान शुरू करने के लिए 80,000 रुपये का ऋण चाहती हूँ। मेरी वार्षिक पारिवारिक आय 1,20,000 रुपये है।",
  "language": "hi"
}
```

### Example Response (200 OK)
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

---

## 2. OCR Certificate

Extracts applicant information from uploaded certificates (Caste or Income) to verify eligibility.

* **URL**: `/ocr-certificate`
* **Method**: `POST`
* **Content-Type**: `multipart/form-data`

### Request Parameters (Form Data)

| Field | Type | Required | Description |
|---|---|---|---|
| `file` | `UploadFile` (Binary) | Yes | Uploaded file (`application/pdf`, `image/jpeg`, `image/png`, `image/webp`). |
| `doc_type` | `str` | Yes | Type of certificate: `"caste"` or `"income"`. |

### Pydantic Models

```python
from typing import Optional
from pydantic import BaseModel, Field

class ExtractedFields(BaseModel):
    name: str = Field(..., description="Name of the applicant printed on the document")
    category: Optional[str] = Field(None, description="Caste category (SC, ST, OBC, General) extracted from Caste Certificate")
    annual_income: Optional[float] = Field(None, description="Annual income in INR extracted from Income Certificate")
    valid_until: Optional[str] = Field(None, description="Expiration date of document in YYYY-MM-DD format (if applicable)")

class OCRResponse(BaseModel):
    doc_type: str = Field(..., description="Type of certificate processed ('caste' or 'income')")
    extracted_fields: ExtractedFields = Field(..., description="Structured fields extracted from certificate")
    income_verified: bool = Field(..., description="True if document type is income and annual income is extracted and <= 500000.00")
    raw_confidence: float = Field(..., description="Average OCR engine extraction confidence (0.0 to 1.0)")
```

### Example Response (200 OK - Income Certificate)
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

---

## 3. Simplify Term (Jargon Simplifier)

Rephrases financial, structural, and regulatory jargon (e.g., *moratorium*, *collateral*, *promoter margin*) into plain, conversational regional language.

* **URL**: `/simplify-term`
* **Method**: `POST`
* **Content-Type**: `application/json`

### Pydantic Models

```python
class JargonRequest(BaseModel):
    term: str = Field(..., description="The financial or policy jargon term (e.g., 'Moratorium', 'Promoter Margin')")
    language: str = Field("en", description="Target ISO language code (e.g., 'en', 'hi', 'mr')")

class JargonResponse(BaseModel):
    explanation: str = Field(..., description="Simplified explanation of the term in the target language")
```

### Example Request
```json
{
  "term": "Moratorium Period",
  "language": "hi"
}
```

### Example Response (200 OK)
```json
{
  "explanation": "मोरेटोरियम अवधि एक प्रकार की भुगतान छूट की अवधि है जिसमें आपको ऋण लेने के तुरंत बाद मासिक किस्त (EMI) चुकाने की जरूरत नहीं होती। यह आपको अपना व्यवसाय शुरू करके कमाई करने के लिए आवश्यक समय देती है।"
}
```

---

## 4. Recommend Scheme Explainer

Generates a localized natural-language narrative describing why the shortlisted schemes fit the applicant's profile and explaining any alternatives.

* **URL**: `/recommend-scheme-explainer`
* **Method**: `POST`
* **Content-Type**: `application/json`

### Pydantic Models

```python
class ApplicantProfile(BaseModel):
    project_category: str
    requested_amount: float
    annual_income: float
    trade: str
    gender: str

class CandidateScheme(BaseModel):
    scheme_name: str
    max_coverage_pct: float
    interest_rate: float
    eligibility_score: float

class ExplainerRequest(BaseModel):
    applicant: ApplicantProfile
    candidate_schemes: list[CandidateScheme]
    language: str = Field("en", description="Target language of the narrative")

class ExplainerResponse(BaseModel):
    top_scheme: str = Field(..., description="Name of the best-matching scheme")
    explanation: str = Field(..., description="A localized justification explaining why this scheme fits the applicant's profile")
    runner_up_note: str = Field(..., description="Brief note on other candidate options or why they ranked lower")
```

### Example Request
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

### Example Response (200 OK)
```json
{
  "top_scheme": "Mahila Samriddhi Yojana",
  "explanation": "Mahila Samriddhi Yojana is the most suitable scheme for you because it offers the highest financial coverage (90%) and the lowest interest rate (4.0%) specifically tailored for female entrepreneurs in tailoring.",
  "runner_up_note": "Micro Credit Scheme is also a viable option but offers slightly lower project coverage (80%) with a higher interest rate (6.0%)."
}
```

---

## 5. Scheme Q&A Chatbot

Conversational, multi-turn questions and answers grounded in official scheme policy guidelines.

* **URL**: `/scheme-chat`
* **Method**: `POST`
* **Content-Type**: `application/json`

### Pydantic Models

```python
class ChatMessage(BaseModel):
    role: str = Field(..., description="The role of the message author (e.g. 'user' or 'model')")
    parts: str = Field(..., description="The text content of the message")

class ChatRequest(BaseModel):
    message: str = Field(..., description="The current user question or message")
    history: list[ChatMessage] = Field(default_factory=list, description="Previous conversation history")
    language: str = Field("en", description="Target ISO language code (e.g., 'en', 'hi', 'mr')")

class ChatResponse(BaseModel):
    response: str = Field(..., description="The grounded, localized response generated by the AI advisor")
```

### Example Request
```json
{
  "message": "What is the maximum loan limit and interest rate for Mahila Samriddhi Yojana?",
  "history": [],
  "language": "en"
}
```

### Example Response (200 OK)
```json
{
  "response": "Under the Mahila Samriddhi Yojana, female beneficiaries can avail loans up to ₹1,40,000 with a subsidized interest rate of 4% per annum. The scheme covers up to 90% of the project cost."
}
```
