import base64
import io
import logging
import re
from PIL import Image
import fitz
from google import genai
from google.genai import types
from openai import OpenAI

from app.config import get_settings
from app.models.schemas import ExtractedFields

logger = logging.getLogger(__name__)

OCR_SYSTEM_PROMPT = (
    "You are an expert government document auditor specializing in verifying caste and income certificates.\n"
    "Your task is to analyze the attached document image and extract the applicant's profile details.\n\n"
    "Extract the following fields:\n"
    "1. name: The full name of the applicant printed on the document. Do not include titles like 'Shri', 'Smt', 'Kumari', etc. unless they are part of the name.\n"
    "2. category: The caste category (must strictly be one of ['SC', 'ST', 'OBC', 'EWS', 'General']) if this is a Caste Certificate. If the document is an Income Certificate, set this to null.\n"
    "3. annual_income: The total annual family income in INR as a float value if this is an Income Certificate. If the document is a Caste Certificate, set this to null.\n"
    "4. valid_until: The expiration date of the document in YYYY-MM-DD format (if printed). If not mentioned or if the document is permanent, set this to null.\n\n"
    "Rules:\n"
    "1. If the input document is in an Indian regional language (e.g., Hindi, Marathi, Tamil, etc.), translate the name, category, and date values to English in the structured output.\n"
    "2. Be extremely precise. Double check numbers and decimal points.\n"
    "3. Strict adherence to output JSON schema format is mandatory."
)


def _redact_secrets(text: str, api_key: str) -> str:
    """Redact API key and common secret patterns from a string before logging."""
    safe = text
    if api_key:
        safe = safe.replace(api_key, "[REDACTED]")
    safe = re.sub(r"(AIza[0-9A-Za-z\-_]{30,}|AQ\.[0-9A-Za-z\-_]{30,}|sk-or-[0-9A-Za-z\-_]{20,})", "[REDACTED]", safe)
    safe = re.sub(r"(Bearer\s+)[^\s,'\"<>]+", r"\1[REDACTED]", safe)
    return safe


def process_certificate(file_bytes: bytes, filename: str, doc_type: str) -> ExtractedFields:
    """Processes Caste or Income Certificate files using Gemini Multimodal Vision.

    Args:
        file_bytes: Raw bytes of the uploaded file.
        filename: Name of the uploaded file (used to detect format).
        doc_type: Type of document: 'caste' or 'income'.

    Returns:
        ExtractedFields parsed via Gemini.

    Raises:
        ValueError: If file is invalid, unsupported, or corrupted.
        RuntimeError: If Gemini/OpenRouter API fails.
    """
    settings = get_settings()
    api_key = settings.gemini_api_key
    if not api_key:
        logger.error("GEMINI_API_KEY is not configured in environment.")
        raise RuntimeError("LLM service is not configured. Please set GEMINI_API_KEY.")

    fn_lower = filename.lower()

    image = None
    try:
        if fn_lower.endswith(".pdf"):
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            if len(doc) == 0:
                raise ValueError("The uploaded PDF contains no pages.")
            page = doc[0]
            zoom = 300 / 72
            matrix = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=matrix)
            png_bytes = pix.tobytes("png")
            image = Image.open(io.BytesIO(png_bytes))
        else:
            image = Image.open(io.BytesIO(file_bytes))
            image.verify()
            image = Image.open(io.BytesIO(file_bytes))
    except Exception as exc:
        logger.error("Failed to parse file format for filename '%s': %s", filename, exc)
        if isinstance(exc, ValueError):
            raise exc
        raise ValueError("Invalid, unsupported, or corrupted document file format.") from exc

    try:
        user_prompt = f"Please extract fields from this {doc_type} certificate."

        if settings.is_openrouter:
            buf = io.BytesIO()
            image.save(buf, format="PNG")
            b64_img = base64.b64encode(buf.getvalue()).decode("utf-8")

            client = OpenAI(base_url=settings.openrouter_base_url, api_key=api_key)
            response = client.chat.completions.create(
                model=settings.gemini_model,
                messages=[
                    {"role": "system", "content": OCR_SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": user_prompt},
                            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64_img}"}},
                        ],
                    },
                ],
                response_format={"type": "json_object"},
                temperature=0.0,
                max_tokens=500,
            )
            raw_text = response.choices[0].message.content or ""
            if not raw_text.strip():
                raise RuntimeError("Empty response received from LLM provider.")
            return ExtractedFields.model_validate_json(raw_text)
        else:
            client = genai.Client(api_key=api_key)
            response = client.models.generate_content(
                model=settings.gemini_model,
                contents=[image, user_prompt],
                config=types.GenerateContentConfig(
                    system_instruction=OCR_SYSTEM_PROMPT,
                    response_mime_type="application/json",
                    response_schema=ExtractedFields,
                    temperature=0.0,
                ),
            )

            if not response.text:
                raise RuntimeError("Empty response received from Gemini Vision model.")
            return ExtractedFields.model_validate_json(response.text)

    except Exception as exc:
        raw_msg = str(exc)
        safe_msg = _redact_secrets(raw_msg, api_key)
        logger.error("Vision call failed for certificate [%s]: %s", type(exc).__name__, safe_msg)

        if (
            "API_KEY" in raw_msg
            or "api key" in raw_msg.lower()
            or "auth" in raw_msg.lower()
            or "suspended" in raw_msg.lower()
            or "PERMISSION_DENIED" in raw_msg
            or "401" in raw_msg
            or "403" in raw_msg
        ):
            raise RuntimeError("Authentication failed with LLM provider.") from None

        if "validation" in raw_msg.lower() or "validate" in raw_msg.lower():
            raise RuntimeError("Vision parsed output did not conform to the expected schemas.") from None

        raise RuntimeError("Failed to extract structured data from document via Vision LLM.") from None
