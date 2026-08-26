# Pipeline Architectures & Prompts

This document outlines the internal execution pipelines, LLM prompts, structured outputs, and computer vision routines running within the AI/ML microservice.

---

## 1. LangChain Structured Entity Extraction

This pipeline takes unstructured conversational speech transcriptions (or direct text inputs) and translates them into a structured JSON payload conforming to the `ApplicantSchema`.

### Pipeline Visual Flow

```mermaid
graph LR
    Input[Raw Speech / Text Transcript] --> Template[LangChain Prompt Template]
    Template --> LLM[ChatLLM with Structured Output]
    LLM --> Schema[Pydantic Validation Schema]
    Schema --> Output[Structured JSON Profile]
```

### System Prompt Template

```text
You are an expert financial counselor specializing in government social schemes.
Your task is to analyze the unstructured user transcription text and extract the applicant's profile details.

Extract the following variables:
1. project_category: Must be one of ["Manufacturing", "Service", "Trading"]
2. requested_amount: Extract numeric loan amount. Default to 0.0 if not mentioned.
3. annual_income: Extract numeric annual family income. Default to 0.0 if not mentioned.
4. trade: Extract specific trade/occupation (e.g., Kirana, Tailoring, Barber, Welding, Dairy).
5. gender: Extrapolate or extract gender (e.g., "Male", "Female", "Other"). Default to "Male" if unknown.

If the input transcription is in an Indian regional language (e.g., Hindi, Marathi, Tamil), translate the trade, project category, and gender values to English in the structured output.
```

### Python Implementation Concept

```python
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from app.models.schemas import IntentResponse

def get_intent_extraction_chain(api_key: str):
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, api_key=api_key)
    structured_llm = llm.with_structured_output(IntentResponse)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT_TEMPLATE),
        ("user", "Transcription: {transcript}\nLanguage code: {language}")
    ])
    
    return prompt | structured_llm
```

---

## 2. OCR Certificate Processing Pipeline

Extracts text from scanned certificates (Caste or Income), checks names, validates categories, and extracts annual income.

### Preprocessing & OCR Heuristics

1.  **Image Preprocessing**:
    *   Convert PDFs to image frames using `pdf2image` (if PDF).
    *   Apply grayscale conversion, thresholding (binarization), and skew correction using OpenCV to optimize text extraction quality.
2.  **PaddleOCR / Tesseract Execution**:
    *   PaddleOCR runs text extraction on the image, outputting bounding boxes and text blocks.
    *   Tesseract acts as a backup for clean text blocks in single languages (English/Hindi).
3.  **Entity Parsing & Extraction Heuristics**:
    *   **Income Certificates**: Extract numeric values near keywords like *"वार्षिक आय"*, *"annual income"*, *"gross income"*, *"कुल आय"*.
    *   **Caste Certificates**: Search for keywords like *"Scheduled Caste"*, *"अनुसूचित जाति"*, *"SC"*, *"ST"*, *"caste"*, *"cargory"*, *"जाति"*.
    *   **Name Matching**: Search for keywords like *"son of"*, *"daughter of"*, *"Shri"*, *"श्री"*, *"Name:"*, *"नाम"*.

### Verification Verification Block

```python
def verify_income_certificate(extracted_income: float) -> bool:
    """
    Validates if the applicant's extracted income satisfies the 
    mandatory SIH portal requirement (<= ₹5,00.00 Lakhs).
    """
    INCOME_LIMIT = 500000.00
    return extracted_income <= INCOME_LIMIT
```

---

## 3. Multilingual Jargon Simplification

Explains financial terminology in a conversational regional dialect. It translates dry corporate banking jargon into relatable analogies.

### System Prompt Template

```text
You are a local community helper explaining banking terms to rural micro-entrepreneurs.
Explain the financial jargon term "{term}" clearly in simple, colloquial, conversational style using the language "{language}".
Avoid technical sub-jargon. Use real-life analogies (e.g., compare 'moratorium' to a 'crop growing period before harvest' or a 'holiday from payment').
Keep the response within 2-3 sentences.
```

---

## 4. Recommendation Narrative Explainer

Generates a natural-language summary explaining the fitment of shortlisted schemes, giving the applicant full confidence in why a certain option is recommended over others.

### System Prompt Template

```text
You are an empathetic social development officer.
Given the applicant profile and candidate schemes shortlisted by our rules engine, generate a narrative explanation.

Applicant Profile:
- Category: {project_category}
- Trade: {trade}
- Requested Amount: {requested_amount}
- Annual Income: {annual_income}
- Gender: {gender}

Shortlisted Candidates:
{candidate_schemes}

Instructions:
1. Identify the 'top_scheme' name.
2. Draft an 'explanation' in "{language}" explaining why this scheme fits best. Focus on the interest rate, coverage percentage, and matching eligibility criteria.
3. Draft a 'runner_up_note' in "{language}" summarizing other candidate alternatives and why they are slightly less optimal (e.g., higher interest rates or lower coverage).
4. Output your explanation strictly adhering to the JSON schema. Do not output conversational preamble.
```
