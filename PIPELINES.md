# Pipeline Architectures & Prompts

This document outlines the internal execution pipelines, Google Gemini LLM prompts, structured outputs, and computer vision routines running within the AI/ML microservice.

---

## 1. Structured Applicant Intent & Entity Extraction

Takes raw speech-to-text transcriptions or conversational text statements (in Hindi, English, or regional languages) and extracts a structured applicant profile adhering to `IntentResponse`.

### Execution Flow

```mermaid
graph LR
    Input[Raw Speech / Text Transcript] --> Prompt[Structured Extraction Prompt]
    Prompt --> Gemini[Gemini 2.5 Flash with response_schema]
    Gemini --> Pydantic[Pydantic IntentResponse Validation]
    Pydantic --> Output[Structured JSON Profile]
```

### System Prompt Template

```text
You are an expert financial counselor specializing in government social schemes.
Your task is to analyze the unstructured user transcription text and extract the applicant's profile details.

Extract the following variables:
1. project_category: Must strictly be one of ["Manufacturing", "Service", "Trading"]
2. requested_amount: Extract numeric loan amount in INR. Default to 0.0 if not mentioned.
3. annual_income: Extract numeric annual family income in INR. Default to 0.0 if not mentioned.
4. trade: Extract specific trade/occupation in English (e.g., Kirana, Tailoring, Barber, Welding, Dairy).
5. gender: Extrapolate or extract gender (e.g., "Male", "Female", "Other"). Default to "Male" if unknown.
6. confidence: Provide a confidence score between 0.0 and 1.0 for the overall extraction accuracy.

Rules:
- If the input transcription is in an Indian regional language (e.g., Hindi, Marathi, Tamil), translate the trade, project category, and gender values to English in the structured output.
- Ensure requested_amount and annual_income are non-negative numeric floats.
```

### Implementation Architecture (`app/services/gemini_service.py`)

```python
client = genai.Client(api_key=api_key)
response = client.models.generate_content(
    model=settings.gemini_model,
    contents=user_content,
    config=types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT_INTENT,
        temperature=0.1,
        response_mime_type="application/json",
        response_schema=IntentResponse,
    ),
)
return IntentResponse.model_validate_json(response.text)
```

---

## 2. Multimodal OCR Certificate Processing Pipeline

Extracts applicant information from uploaded certificates (Caste or Income) to verify eligibility directly using PyMuPDF and Gemini Multimodal Vision API.

### Preprocessing & Multimodal Flow

```mermaid
graph TD
    Upload[Uploaded File: PDF / JPEG / PNG] --> Detect{File Type}
    Detect -->|PDF| PyMuPDF[Render First Page to PNG via PyMuPDF]
    Detect -->|Image| PIL[Validate & Format via Pillow]
    PyMuPDF --> Vision[Gemini Multimodal Vision API]
    PIL --> Vision
    Vision --> Extraction[ExtractedFields Schema]
    Extraction --> Verification[income_verified Evaluator]
    Verification --> Response[OCRResponse JSON]
```

### OCR System Prompt Template

```text
You are an expert government document auditor specializing in verifying caste and income certificates.
Your task is to analyze the attached document image and extract the applicant's profile details.

Extract the following fields:
1. name: The full name of the applicant printed on the document. Do not include titles like 'Shri', 'Smt', 'Kumari', etc. unless they are part of the name.
2. category: The caste category (must strictly be one of ['SC', 'ST', 'OBC', 'EWS', 'General']) if this is a Caste Certificate. If the document is an Income Certificate, set this to null.
3. annual_income: The total annual family income in INR as a float value if this is an Income Certificate. If the document is a Caste Certificate, set this to null.
4. valid_until: The expiration date of the document in YYYY-MM-DD format (if printed). If not mentioned or if the document is permanent, set this to null.

Rules:
1. If the input document is in an Indian regional language (e.g., Hindi, Marathi, Tamil, etc.), translate the name, category, and date values to English in the structured output.
2. Be extremely precise. Double check numbers and decimal points.
3. Strict adherence to output JSON schema format is mandatory.
```

### Deterministic Verification Logic

```python
def is_income_verified(doc_type: str, annual_income: Optional[float]) -> bool:
    """Verifies that an income certificate is <= ₹5,00,000 threshold."""
    if doc_type == "income" and annual_income is not None:
        return annual_income <= 500000.00
    return False
```

---

## 3. Multilingual Jargon Simplification

Translates dry banking and policy terminology (e.g., *moratorium*, *collateral*, *promoter margin*) into conversational regional language explanations using intuitive everyday analogies.

### System Prompt Template

```text
You are a friendly, encouraging financial counselor explaining complex banking and government scheme terms to rural and semi-urban micro-entrepreneurs.

Guidelines:
1. Provide a simplified explanation of the financial or policy jargon term in the requested target language.
2. The explanation must be conversational, warm, and easily understood by someone with no financial background.
3. Use a simple, relatable everyday analogy or real-life example (e.g., relating moratorium to a harvest cycle or a payment holiday to set up a shop).
4. Keep the explanation concise (2 to 3 sentences maximum).
5. Do NOT include markdown bolding, greetings, or sign-offs in your response text. Output only the simplified explanation.
```

---

## 4. Recommendation Narrative Explainer

Generates a tailored narrative explaining why the top shortlisted scheme fits the applicant's profile and providing a brief comparison with runner-up options.

### System Prompt Template

```text
You are an expert government financial advisor assisting micro-entrepreneurs and artisans.
Your task is to analyze an applicant's profile and a list of candidate government loan/subsidy schemes, and produce a structured, localized recommendation explanation.

Rules:
1. 'top_scheme': The exact scheme_name of the best-matching scheme.
2. 'explanation': 2-3 clear, conversational sentences in the target language explaining WHY this scheme fits the applicant's profile best. Highlight favorable terms like lower interest rates, high coverage percentage, gender-specific benefits, or trade alignment.
3. 'runner_up_note': 1-2 sentences in the target language explaining how other candidate schemes compare and why they ranked lower.
4. If candidate_schemes has only 1 scheme, acknowledge that it is the primary eligible option.
5. All text in 'explanation' and 'runner_up_note' MUST be in the requested target language.
```

---

## 5. Scheme Q&A Chatbot (Two-Tier Grounded RAG & Proactive Suggestions)

Provides grounded, multi-turn conversational advisory based on consolidated government policy guidelines loaded from `app/resources/schemes_knowledge.txt`, coupled with a resilient two-tier hybrid fallback that answers general banking/procedural questions without dead-ending the user.

### Execution Flow

```mermaid
graph TD
    UserQuery[User Question + Chat History] --> Router[POST /scheme-chat]
    Router --> Tools[Gemini Agent + Scheme Knowledge Tools]
    Tools --> Retrieve[retrieve_scheme_guidelines / simplify_financial_jargon / explain_scheme_recommendations]
    Retrieve --> Match{Found in Knowledge Base?}
    Match -->|Yes| Tier1[Tier 1: Policy-Grounded Response with Markdown Citations]
    Match -->|No / Procedural| Tier2[Tier 2: General Advisory & Step-by-Step Guidance]
    Tier1 --> Parser[_parse_chat_response JSON Extractor]
    Tier2 --> Parser
    Parser --> Output["ChatResponse: { response, suggested_questions }"]
```

### Knowledge Base Content Coverage
* **Schemes (1 to 70)**: NBCFDC (MSY, MCS), PM Vishwakarma, PMEGP, Mudra (Shishu/Kishor/Tarun), Stand-Up India, SVANidhi, NHFDC, NMDFC, ELAS, and State-level concessional credit schemes.
* **Procedural Guidelines (71 to 75)**:
  * Section 71: General Loan Application Procedures, CSC Workflows, and Jan Samarth Guidelines.
  * Section 72: Universal Document Checklist and Paperwork Requirements.
  * Section 73: Loan Disbursement, Moratorium Mechanics, and Subsidy Release Process.
  * Section 74: Grievance Redressal, Nodal Officers, and Lead District Managers (LDM).
  * Section 75: Cross-Scheme Eligibility, One Beneficiary per Family Norms, and Common FAQs.

### Output Format Specification

The model formats its output as structured JSON:
```json
{
  "response": "Grounded answer text in the requested target language with citations or general procedural steps.",
  "suggested_questions": [
    "Contextual follow-up question 1 in target language",
    "Contextual follow-up question 2 in target language",
    "Contextual follow-up question 3 in target language"
  ]
}
```

