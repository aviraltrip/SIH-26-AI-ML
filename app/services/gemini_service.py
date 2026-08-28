import logging
import os
import re

from google import genai
from google.genai import types

from app.config import get_settings
from app.models.schemas import (
    ApplicantProfile,
    CandidateScheme,
    ChatMessage,
    ExplainerResponse,
    IntentResponse,
)

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



_cached_knowledge = None

def _load_knowledge_base() -> str:
    global _cached_knowledge
    if _cached_knowledge is not None:
        return _cached_knowledge

    current_dir = os.path.dirname(os.path.abspath(__file__))
    kb_path = os.path.join(os.path.dirname(current_dir), "resources", "schemes_knowledge.txt")
    
    try:
        with open(kb_path, "r", encoding="utf-8") as f:
            _cached_knowledge = f.read()
        return _cached_knowledge
    except Exception as exc:
        logger.error("Failed to load schemes_knowledge.txt from %s: %s", kb_path, exc)
        raise RuntimeError("Failed to load local scheme knowledge base resource.")


def retrieve_scheme_guidelines(query: str) -> str:
    """Retrieves relevant official government scheme policy guidelines and FAQs based on a search query.

    Args:
        query: The search terms (e.g., 'PM Vishwakarma eligibility', 'Mudra loan limits').

    Returns:
        Matching sections from the official guidelines knowledge base.
    """
    try:
        content = _load_knowledge_base()
    except Exception as exc:
        logger.error("Failed to load knowledge base for tool: %s", exc)
        return "Error: Could not load the official schemes knowledge base."

    sections = re.split(r'\n(?=\d+\.\s+)', content)
    matched_sections = []
    query_lower = (query or "").lower()

    for section in sections:
        lines = section.strip().split('\n')
        if not lines:
            continue
        title = lines[0].lower()
        score = 0
        keywords = []
        if "mahila" in title or "msy" in title:
            keywords.extend(["mahila", "msy", "samriddhi", "women", "nbcfdc"])
        if "micro credit" in title or "mcs" in title or "mcf" in title:
            keywords.extend(["micro credit", "mcs", "mcf", "micro-credit", "nbcfdc", "nsfdc"])
        if "vishwakarma" in title:
            keywords.extend(["vishwakarma", "artisan", "toolkit", "stipend", "traditional", "darzi", "tailor"])
        if "pmegp" in title or "employment generation" in title:
            keywords.extend(["pmegp", "subsidy", "kvic", "manufacturing", "service", "trading"])
        if "mudra" in title or "pmmy" in title:
            keywords.extend(["mudra", "pmmy", "shishu", "kishor", "tarun"])
        if "stand-up" in title or "standup" in title:
            keywords.extend(["stand-up", "standup", "sc", "st", "greenfield"])
        if "svanidhi" in title or "street vendor" in title:
            keywords.extend(["svanidhi", "street vendor", "working capital", "tranche"])
        if "nhfdc" in title or "divyangjan" in title or "disability" in title:
            keywords.extend(["nhfdc", "divyangjan", "handicapped", "disability", "disabled", "assistive"])
        if "udyogini" in title:
            keywords.extend(["udyogini", "kswdc", "women subsidy", "widow"])
        if "nmdfc" in title or "minority" in title:
            keywords.extend(["nmdfc", "minority", "muslim", "christian", "sikh", "buddhist", "parsi", "jain", "virasat"])
        if "education" in title or "elas" in title:
            keywords.extend(["education", "elas", "study", "student", "college", "higher education", "abroad"])
        if "general term loan" in title or "term loan" in title:
            keywords.extend(["term loan", "general term loan", "50 lakh", "project loan"])
        if "adivasi" in title or "amsy" in title or "nstfdc" in title:
            keywords.extend(["adivasi", "amsy", "nstfdc", "tribal", "st women", "scheduled tribe"])
        if "swachhta" in title or "suy" in title or "nskfdc" in title or "safai" in title:
            keywords.extend(["swachhta", "suy", "nskfdc", "safai", "karamchari", "sanitation", "toilet", "manual scavenger"])

        for kw in keywords:
            if kw in query_lower:
                score += 5
        words = [w for w in re.split(r'\W+', query_lower) if len(w) > 3]
        for word in words:
            if word in section.lower():
                score += 1

        if score > 0:
            matched_sections.append((score, section))

    if not matched_sections:
        return "No specific guidelines matching this query were found in the knowledge base."

    matched_sections.sort(key=lambda x: x[0], reverse=True)
    return "\n\n=========================================\n".join(sec[1] for sec in matched_sections[:3])


def simplify_financial_jargon(term: str, language: str = "en") -> str:
    """Simplifies a financial, banking, or government-scheme jargon term into conversational language.

    Args:
        term: The financial jargon term to simplify (e.g., 'moratorium', 'collateral').
        language: Target ISO language code or name (e.g., 'en', 'hi', 'mr').

    Returns:
        A simplified explanation with analogies in the target language.
    """
    try:
        return simplify_term(term=term, language=language)
    except Exception as exc:
        logger.error("Failed to simplify jargon in tool: %s", exc)
        return f"Error: Could not simplify term '{term}'."


def explain_scheme_recommendations(
    project_category: str,
    trade: str,
    requested_amount: float,
    annual_income: float,
    gender: str,
    candidate_schemes: list[dict],
    language: str = "en",
) -> dict:
    """Generates a tailored explanation describing why shortlisted schemes fit an applicant's profile.

    Args:
        project_category: Categorized project type ('Manufacturing', 'Service', or 'Trading').
        trade: Specific trade name (e.g., Tailoring, Dairy, Kirana).
        requested_amount: Requested loan amount in INR.
        annual_income: Household annual income in INR.
        gender: Gender (e.g., Male, Female, Other).
        candidate_schemes: List of candidates containing 'scheme_name', 'max_coverage_pct', 'interest_rate', and 'eligibility_score'.
        language: Target ISO language code (e.g., 'en', 'hi', 'mr').

    Returns:
        A dictionary with 'top_scheme', 'explanation', and 'runner_up_note'.
    """
    try:
        applicant_obj = ApplicantProfile(
            project_category=project_category,
            trade=trade,
            requested_amount=requested_amount,
            annual_income=annual_income,
            gender=gender,
        )
        candidates_list = []
        for s in candidate_schemes:
            candidates_list.append(
                CandidateScheme(
                    scheme_name=s.get("scheme_name", ""),
                    max_coverage_pct=float(s.get("max_coverage_pct", 0.0)),
                    interest_rate=float(s.get("interest_rate", 0.0)),
                    eligibility_score=float(s.get("eligibility_score", 0.0)),
                )
            )
        res = recommend_scheme_explainer(
            applicant=applicant_obj,
            candidate_schemes=candidates_list,
            language=language,
        )
        return {
            "top_scheme": res.top_scheme,
            "explanation": res.explanation,
            "runner_up_note": res.runner_up_note,
        }
    except Exception as exc:
        logger.error("Failed to generate scheme explanation in tool: %s", exc)
        return {
            "top_scheme": "",
            "explanation": "Error: Could not generate fitment explanation.",
            "runner_up_note": "",
        }


CHAT_SYSTEM_PROMPT_TEMPLATE = (
    "You are an expert government policy advisor helping rural micro-entrepreneurs and applicants understand banking and social welfare schemes.\n"
    "Your goal is to answer the user's questions truthfully and help them qualify for the correct government schemes.\n\n"
    "You have access to the following tools to fulfill your role:\n"
    "1. `retrieve_scheme_guidelines`: Searches the official knowledge base. You MUST call this tool when answering questions about a scheme's eligibility, rules, interest rates, or features.\n"
    "2. `simplify_financial_jargon`: Explains complex terminology using simple words and real-life analogies. Call this whenever the user asks about jargon like 'moratorium', 'collateral', 'subsidy', etc.\n"
    "3. `explain_scheme_recommendations`: Explains scheme recommendations and fitment. Call this when users want to know why a scheme matches their profile or which schemes they fit.\n\n"
    "CRITICAL RULES:\n"
    "1. Grounding & Citations: When you answer using scheme guidelines, you MUST append inline citations in markdown format referring to the scheme name and section (e.g., '[Source: PM Vishwakarma Scheme - Credit Support]'). Do not cite general knowledge.\n"
    "2. Confidence / Strict Abstention: If the tools do not return relevant information, or if you cannot find the answer in the retrieved facts, you MUST state exactly: "
    "\"I apologize, but I do not have official guidelines for that specific detail. Please consult the nearest branch or nodal officer.\"\n"
    "Do not invent facts, numbers, or rules.\n"
    "3. Qualifying Conversation Memory: Keep track of applicant details mentioned in the conversation history (e.g., gender, income, trade). If the user asks if they are eligible for a scheme but you are missing key details to qualify them, do not answer with a generic yes/no; instead, ask friendly follow-up questions to obtain the missing details (e.g., trade, annual income) to qualify them.\n"
    "4. Target Language: Respond in the requested target language."
)


def chat_with_knowledge(message: str, history: list[ChatMessage], language: str = "en") -> str:
    """Answers a user question grounded on official scheme policy guidelines using tools.

    Args:
        message: Current user message/question.
        history: List of past ChatMessage elements.
        language: ISO target language code or name.

    Returns:
        Grounded response text from Gemini.
    """
    msg_clean = (message or "").strip()
    if not msg_clean:
        raise ValueError("Message must not be empty or whitespace only.")

    settings = get_settings()
    api_key = settings.gemini_api_key
    if not api_key:
        logger.error("GEMINI_API_KEY is not configured in environment.")
        raise RuntimeError("LLM service is not configured. Please set GEMINI_API_KEY.")

    target_lang = _get_language_label(language)
    system_instruction = CHAT_SYSTEM_PROMPT_TEMPLATE

    contents = []
    for turn in history:
        role = turn.role.strip().lower()
        if role not in ("user", "model"):
            role = "user"
        contents.append(
            types.Content(
                role=role,
                parts=[types.Part.from_text(text=turn.parts)]
            )
        )

    user_prompt = f"User Question: {msg_clean}\nPlease respond in the language: {target_lang}."
    contents.append(
        types.Content(
            role="user",
            parts=[types.Part.from_text(text=user_prompt)]
        )
    )

    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=settings.gemini_model,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.2,
                tools=[
                    retrieve_scheme_guidelines,
                    simplify_financial_jargon,
                    explain_scheme_recommendations,
                ],
            ),
        )

        if not response.text:
            raise RuntimeError("Empty response received from LLM provider.")

        return _clean_explanation(response.text)

    except Exception as exc:
        raw_msg = str(exc)
        safe_msg = _redact_secrets(raw_msg, api_key)
        logger.error("Gemini Chat LLM call failed [%s]: %s", type(exc).__name__, safe_msg)

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
        raise RuntimeError("Failed to generate chat response from LLM provider.") from None



INTENT_SYSTEM_PROMPT = (
    "You are an expert financial counselor specializing in government social schemes.\n"
    "Your task is to analyze the unstructured user transcription text and extract the applicant's profile details.\n\n"
    "Extract the following fields:\n"
    "1. project_category: Must strictly be one of [\"Manufacturing\", \"Service\", \"Trading\"]\n"
    "2. requested_amount: Extract the numeric loan amount requested in INR. Default to 0.0 if not mentioned.\n"
    "3. annual_income: Extract the numeric annual family income of the applicant in INR. Default to 0.0 if not mentioned.\n"
    "4. trade: Extract the specific trade or occupation (e.g., Kirana, Tailoring, Barber, Welding, Dairy).\n"
    "5. gender: Extrapolate or extract gender (e.g., \"Male\", \"Female\", \"Other\"). Default to \"Male\" if unknown.\n"
    "6. confidence: Assess your overall extraction confidence as a float value between 0.0 and 1.0.\n\n"
    "Rules:\n"
    "1. If the input transcription is in an Indian regional language (e.g., Hindi, Marathi, Tamil, etc.), "
    "translate the trade, project_category, and gender values to English in the structured output.\n"
    "2. If requested_amount or annual_income are missing or not detected, set them to 0.0.\n"
    "3. Strict adherence to output JSON schema format is mandatory."
)


def extract_applicant_intent(transcript: str, language: str = "en") -> IntentResponse:
    """Extracts structured applicant parameters from conversational speech transcriptions.

    Args:
        transcript: Raw text or transcription.
        language: ISO language code (e.g. 'en', 'hi', 'mr').

    Returns:
        Structured IntentResponse containing profile details and confidence score.

    Raises:
        ValueError: If transcript is empty.
        RuntimeError: If Gemini API fails.
    """
    transcript_clean = (transcript or "").strip()
    if not transcript_clean:
        raise ValueError("Transcript must not be empty or whitespace only.")

    settings = get_settings()
    api_key = settings.gemini_api_key
    if not api_key:
        logger.error("GEMINI_API_KEY is not configured in environment.")
        raise RuntimeError("LLM service is not configured. Please set GEMINI_API_KEY.")

    target_lang = _get_language_label(language)
    user_content = (
        f"Transcription: {transcript_clean}\n"
        f"Input Language: {target_lang}"
    )

    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=settings.gemini_model,
            contents=user_content,
            config=types.GenerateContentConfig(
                system_instruction=INTENT_SYSTEM_PROMPT,
                response_mime_type="application/json",
                response_schema=IntentResponse,
                temperature=0.0,
            ),
        )

        if not response.text:
            raise RuntimeError("Empty response received from LLM provider.")

        return IntentResponse.model_validate_json(response.text)

    except Exception as exc:
        raw_msg = str(exc)
        safe_msg = _redact_secrets(raw_msg, api_key)
        logger.error("Gemini Intent LLM call failed [%s]: %s", type(exc).__name__, safe_msg)

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

        if "validation" in raw_msg.lower() or "validate" in raw_msg.lower():
            raise RuntimeError("Extracted data did not match the required response schema constraints.") from None

        raise RuntimeError("Failed to extract applicant intent from LLM provider.") from None


def recommend_scheme_explainer(
    applicant: ApplicantProfile,
    candidate_schemes: list[CandidateScheme],
    language: str = "en",
) -> ExplainerResponse:
    """Generates a tailored natural-language narrative explaining why shortlisted schemes fit an applicant.

    Args:
        applicant: Applicant profile parameters.
        candidate_schemes: List of shortlisted candidate schemes with scores.
        language: Target ISO language code (e.g., 'en', 'hi', 'mr').

    Returns:
        Structured ExplainerResponse containing top_scheme, explanation, and runner_up_note.

    Raises:
        ValueError: If candidate_schemes is empty or language is unsupported.
        RuntimeError: If LLM service fails or returns invalid structured output.
    """
    if not candidate_schemes:
        raise ValueError("Candidate schemes list must not be empty.")

    lang_code = (language or "en").strip().lower()
    if lang_code not in LANGUAGE_MAP:
        raise ValueError(
            f"Unsupported language: '{language}'. Supported languages: {', '.join(sorted(LANGUAGE_MAP.keys()))}"
        )

    settings = get_settings()
    api_key = settings.gemini_api_key
    if not api_key:
        logger.error("GEMINI_API_KEY is not configured in environment.")
        raise RuntimeError("LLM service is not configured. Please set GEMINI_API_KEY.")

    target_lang = LANGUAGE_MAP[lang_code]

    candidate_schemes_text = "\n".join([
        f"- Scheme: {s.scheme_name}, Max Coverage: {s.max_coverage_pct}%, Interest Rate: {s.interest_rate}%, Eligibility Score: {s.eligibility_score}"
        for s in candidate_schemes
    ])

    user_content = (
        f"Applicant Profile:\n"
        f"- Category: {applicant.project_category}\n"
        f"- Trade: {applicant.trade}\n"
        f"- Requested Amount: {applicant.requested_amount}\n"
        f"- Annual Income: {applicant.annual_income}\n"
        f"- Gender: {applicant.gender}\n\n"
        f"Shortlisted Candidates:\n"
        f"{candidate_schemes_text}\n\n"
        f"Target Language: {target_lang}"
    )

    system_instruction = (
        "You are an empathetic social development officer helping an applicant understand their scheme recommendations.\n\n"
        "Instructions:\n"
        "1. Evaluate ALL shortlisted candidate schemes provided in the request.\n"
        "2. Compare them against the supplied applicant profile.\n"
        "3. Consider all supplied candidate attributes, including eligibility_score, interest_rate, max_coverage_pct, and scheme_name.\n"
        "4. Select ONE scheme that you determine to be the best overall fit for the applicant.\n"
        "5. Return the exact supplied scheme_name of that selected scheme as 'top_scheme'.\n"
        f"6. Generate an 'explanation' in \"{target_lang}\" describing why the selected scheme is the best fit using ONLY the information provided in the request.\n"
        f"7. Generate a 'runner_up_note' in \"{target_lang}\" explaining the other candidate scheme(s) and why they are slightly less optimal, or explaining that there are no alternative candidates if only one candidate is provided.\n"
        "8. Do NOT invent eligibility rules, income limits, interest rates, coverage percentages, subsidies, benefits, government policies, approval guarantees, application requirements, or financial/legal advice.\n"
        "9. Do NOT infer specific eligibility criteria that are not supplied in the request.\n"
        "10. Do NOT use external knowledge to introduce facts about a scheme that were not supplied in the request.\n"
        "11. Output your explanation strictly adhering to the JSON schema with fields 'top_scheme', 'explanation', and 'runner_up_note'. Do not output conversational preamble or markdown formatting."
    )

    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=settings.gemini_model,
            contents=user_content,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json",
                response_schema=ExplainerResponse,
                temperature=0.2,
            ),
        )

        if not response.text:
            raise RuntimeError("Empty response received from LLM provider.")

        return ExplainerResponse.model_validate_json(response.text)

    except Exception as exc:
        raw_msg = str(exc)
        safe_msg = _redact_secrets(raw_msg, api_key)
        logger.error("Gemini Explainer LLM call failed [%s]: %s", type(exc).__name__, safe_msg)

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

        if "validation" in raw_msg.lower() or "validate" in raw_msg.lower():
            raise RuntimeError("Generated explanation did not match the required response schema constraints.") from None

        raise RuntimeError("Failed to generate scheme explanation from LLM provider.") from None

