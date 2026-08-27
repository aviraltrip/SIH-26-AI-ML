import logging
import re

from google import genai
from google.genai import types

from app.config import get_settings

logger = logging.getLogger(__name__)

LANGUAGE_MAP = {
    "en": "English",
    "hi": "Hindi",
    "mr": "Marathi",
    "ta": "Tamil",
    "te": "Telugu",
    "bn": "Bengali",
    "gu": "Gujarati",
    "kn": "Kannada",
    "pa": "Punjabi",
    "ml": "Malayalam",
    "or": "Odia",
    "ur": "Urdu",
}

SYSTEM_PROMPT_TEMPLATE = (
    "You are a local community helper explaining banking and government-scheme terms to rural micro-entrepreneurs.\n"
    "Explain the financial jargon term clearly in simple, colloquial, conversational style using the requested target language.\n"
    "Avoid technical sub-jargon. Use real-life analogies (for example, compare 'moratorium' to a 'crop growing period before harvest' or a 'holiday from payment', "
    "or 'collateral' to a 'security item or guarantee pledged for a loan').\n"
    "Keep the response within 2-3 sentences.\n"
    "Rules:\n"
    "1. Preserve the correct meaning of the financial term.\n"
    "2. Do not invent policy rules, eligibility conditions, interest rates, or benefits.\n"
    "3. Do not provide financial or legal advice.\n"
    "4. Do not use complex vocabulary or dictionary-style definitions.\n"
    "5. Prefer natural, conversational tone in the requested language.\n"
    "6. Do NOT include preambles (such as 'Here is the explanation:'), headings, markdown bolding/formatting, or bullet points.\n"
    "7. Return ONLY the plain explanation text."
)

def _get_language_label(language_code: str) -> str:
    code_clean = (language_code or "en").strip().lower()
    return LANGUAGE_MAP.get(code_clean, code_clean)


def _clean_explanation(text: str) -> str:
    if not text:
        return ""
    cleaned = text.strip()
    cleaned = re.sub(r"^```[a-zA-Z]*\n?", "", cleaned)
    cleaned = re.sub(r"\n?```$", "", cleaned)
    cleaned = re.sub(r"^(Explanation|सरल व्याख्या|स्पष्टीकरण)\s*:\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = cleaned.strip('"\'  \n\r\t')  
    return cleaned


def _redact_secrets(text: str, api_key: str) -> str:
    """Redact API key and common secret patterns from a string before logging."""
    safe = text
    if api_key:
        safe = safe.replace(api_key, "[REDACTED]")
    safe = re.sub(r"(AIza[0-9A-Za-z\-_]{30,}|AQ\.[0-9A-Za-z\-_]{30,})", "[REDACTED]", safe)
    safe = re.sub(r"(Bearer\s+)[^\s,'\"<>]+", r"\1[REDACTED]", safe)
    return safe


def simplify_term(term: str, language: str = "en") -> str:
    """Simplifies a financial or policy jargon term into conversational language.

    Args:
        term: The financial jargon term to simplify.
        language: Target ISO language code or name (e.g. 'en', 'hi', 'mr').

    Returns:
        A simplified 2-3 sentence conversational explanation in the target language.

    Raises:
        ValueError: If term is empty.
        RuntimeError: If Gemini API fails or is not configured.
    """
    term_clean = (term or "").strip()
    if not term_clean:
        raise ValueError("Term must not be empty or whitespace only.")

    settings = get_settings()
    api_key = settings.gemini_api_key
    if not api_key:
        logger.error("GEMINI_API_KEY is not configured in environment.")
        raise RuntimeError("LLM service is not configured. Please set GEMINI_API_KEY.")

    target_lang = _get_language_label(language)

    user_content = (
        f"Financial jargon term: {term_clean}\n"
        f"Target language: {target_lang}"
    )

    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=settings.gemini_model,
            contents=user_content,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT_TEMPLATE,
                temperature=0.3,
            ),
        )

        if not response.text:
            raise RuntimeError("Empty response received from LLM provider.")

        return _clean_explanation(response.text)

    except Exception as exc:  
        raw_msg = str(exc)
        safe_msg = _redact_secrets(raw_msg, api_key)
        logger.error("Gemini LLM call failed [%s]: %s", type(exc).__name__, safe_msg)

        if (
            "API_KEY" in raw_msg
            or "api key" in raw_msg.lower()
            or "auth" in raw_msg.lower()
            or "suspended" in raw_msg.lower()
            or "PERMISSION_DENIED" in raw_msg
            or "400" in raw_msg
            or "403" in raw_msg
        ):
            raise RuntimeError("Authentication failed with LLM provider.") from None
        raise RuntimeError("Failed to generate simplified explanation from LLM provider.") from None
