# API Contract Specifications

This document defines the strict API contracts, data schemas, validation constraints, and error formats for the FastAPI AI/ML microservice. All responses are returned in JSON format.

---

## Endpoint 1: Extract Applicant Intent

Parses conversational transcriptions or text statements to extract structured applicant parameters.

*   **URL**: `/extract-applicant-intent`
*   **Method**: `POST`
*   **Content-Type**: `application/json`

### Pydantic Models

```python
from pydantic import BaseModel, Field

class IntentRequest(BaseModel):
    transcript: str = Field(..., description="Raw text or transcription from speech-to-text")
    language: str = Field("en", description="ISO language code of transcription (e.g., 'en', 'hi', 'mr')")

class IntentResponse(BaseModel):
    project_category: str = Field(..., description="Categorized project type (e.g., Manufacturing, Service, Trading)")
    requested_amount: float = Field(..., description="Requested loan amount in INR")
    annual_income: float = Field(..., description="Applicant's household annual income in INR")
    trade: str = Field(..., description="Specific trade name (e.g., Tailoring, Dairy, Kirana, Barber)")
    gender: str = Field(..., description="Gender (e.g., Male, Female, Other)")
    confidence: float = Field(..., description="Confidence score of extraction between 0.0 and 1.0")
```

### JSON Request Payload
```json
{
  "transcript": "नमस्ते, मैं एक सिलाई की दुकान शुरू करने के लिए 80,000 रुपये का ऋण चाहता हूँ। मेरी वार्षिक पारिवारिक आय 1,20,000 रुपये है।",
  "language": "hi"
}
```

### JSON Response Payload (200 OK)
```json
{
  "project_category": "Manufacturing",
  "requested_amount": 80000.0,
  "annual_income": 120000.0,
  "trade": "Tailoring",
  "gender": "Female",
  "confidence": 0.94
}
```

### Validation Constraints
*   `confidence` must be a float constraint `0.0 <= confidence <= 1.0`.
*   `requested_amount` and `annual_income` must be non-negative values. If undetected in the text, they should default to `0.0`.

---

## Endpoint 2: OCR Certificate

Extracts applicant information from uploaded certificates (Caste or Income) to verify eligibility.

*   **URL**: `/ocr-certificate`
*   **Method**: `POST`
*   **Content-Type**: `multipart/form-data`

### Request Parameters

| Parameter Name | Data Type | Requirement | Description / Allowed Values |
| :--- | :--- | :--- | :--- |
| **file** | Binary (File) | Required | Uploaded document in `image/jpeg`, `image/png`, or `application/pdf` format. |
| **doc_type** | String | Required | Type of certificate: `"caste"` or `"income"`. |

### Pydantic Models

```python
from pydantic import BaseModel, Field
from typing import Optional

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

### JSON Response Payload (200 OK - Income Certificate)
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
  "raw_confidence": 0.89
}
```

### Verification Logic
*   **Caste Categories**: SC, ST, OBC, EWS, Gen.
*   **income_verified Criteria**: Evaluated as `True` if `doc_type == "income"` and `extracted_fields.annual_income <= 500000.00`. If `doc_type == "caste"`, `income_verified` defaults to `false`.

---

## Endpoint 3: Simplify Term

Rephrases financial, structural, and regulatory jargon (e.g., *moratorium*, *collateral*) into plain language localized to regional dialects.

*   **URL**: `/simplify-term`
*   **Method**: `POST`
*   **Content-Type**: `application/json`

### Pydantic Models

```python
class JargonRequest(BaseModel):
    term: str = Field(..., description="The financial or policy jargon term (e.g., 'Moratorium', 'Promoter Margin')")
    language: str = Field("en", description="Target ISO language code (e.g., 'en', 'hi', 'mr')")

class JargonResponse(BaseModel):
    explanation: str = Field(..., description="Simplified explanation of the term in the target language")
```

### JSON Request Payload
```json
{
  "term": "Moratorium Period",
  "language": "hi"
}
```

### JSON Response Payload (200 OK)
```json
{
  "explanation": "मोरेटोरियम अवधि (ऋण स्थगन अवधि) वह समय है जिसके दौरान आपको बैंक को कोई भी ईएमआई (EMI) या किस्त चुकाने की आवश्यकता नहीं होती है। यह एक भुगतान छुट्टी की तरह है जो आपको अपना व्यवसाय शुरू करने और स्थिर होने के लिए दी जाती है।"
}
```

---

## Endpoint 4: Recommend Scheme Explainer

Generates a tailored natural-language narrative describing why the shortlisted schemes fit the applicant's profile and explaining any alternatives.

*   **URL**: `/recommend-scheme-explainer`
*   **Method**: `POST`
*   **Content-Type**: `application/json`

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

### JSON Request Payload
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
      "max_coverage_pct": 90.0,
      "interest_rate": 6.0,
      "eligibility_score": 0.85
    }
  ],
  "language": "hi"
}
```

### JSON Response Payload (200 OK)
```json
{
  "top_scheme": "Mahila Samriddhi Yojana",
  "explanation": "यह योजना आपकी आवश्यकताओं के लिए सबसे उपयुक्त है क्योंकि यह विशेष रूप से महिला उद्यमियों (दर्जी व्यवसाय के लिए) को लक्षित करती है। आपको आवश्यक ₹80,000 की राशि का 90% कवरेज मिलेगा और ब्याज दर केवल 4% वार्षिक है, जो सबसे कम है।",
  "runner_up_note": "माइक्रो क्रेडिट योजना भी एक विकल्प है, लेकिन इसकी ब्याज दर 6% है, जो महिला समृद्धि योजना की तुलना में 2% अधिक है।"
}
```

---

## Endpoint 5: Scheme Q&A Chatbot

Provides conversational, multi-turn questions and answers grounded on official scheme policy guidelines.

*   **URL**: `/scheme-chat`
*   **Method**: `POST`
*   **Content-Type**: `application/json`

### Pydantic Models

```python
from pydantic import BaseModel, Field

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

### JSON Request Payload
```json
{
  "message": "What is the interest rate for the Mahila Samriddhi scheme?",
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
  "language": "hi"
}
```

### JSON Response Payload (200 OK)
```json
{
  "response": "महिला समृद्धि योजना के लिए ब्याज दर केवल 4% वार्षिक है, जो महिला लाभार्थियों के लिए बेहद अनुकूल है।"
}
```

---


## Standardized HTTP Error States

To ensure stability in Repo 1 integration, Repo 2 returns standard HTTP response status codes:

*   **400 Bad Request**: Invalid format, missing required files, or unsupported languages.
*   **422 Unprocessable Entity**: JSON schema validation fails or types do not match expectations.
*   **500 Internal Server Error**: Downstream LLM api calls timed out or PaddleOCR failed to initialize.

### Error Response Schema
```json
{
  "error": {
    "code": "ENTITY_EXTRACTION_FAILURE",
    "message": "Failed to parse text: transcription is blank or noisy.",
    "details": "Language 'xyz' is not supported."
  }
}
```
