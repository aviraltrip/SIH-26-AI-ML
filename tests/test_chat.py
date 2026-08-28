from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


@patch("app.services.gemini_service.genai.Client")
def test_scheme_chat_english_basic(mock_genai_client):
    """Test scheme-chat with basic question in English and empty history."""
    mock_instance = MagicMock()
    mock_genai_client.return_value = mock_instance
    mock_response = MagicMock()
    mock_response.text = (
        "Under the PM Vishwakarma scheme, traditional artisans can receive collateral-free credit support "
        "up to ₹3,00,000. It is split into two tranches of ₹1,00,000 and ₹2,00,000."
    )
    mock_instance.models.generate_content.return_value = mock_response

    payload = {
        "message": "What is the loan limit for PM Vishwakarma?",
        "history": [],
        "language": "en",
    }
    response = client.post("/scheme-chat", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    assert "₹3,00,000" in data["response"] or "₹3 lakhs" in data["response"].lower() or "vishwakarma" in data["response"].lower()


@patch("app.services.gemini_service.genai.Client")
def test_scheme_chat_hindi_with_history(mock_genai_client):
    """Test scheme-chat in Hindi with existing conversation history."""
    mock_instance = MagicMock()
    mock_genai_client.return_value = mock_instance
    mock_response = MagicMock()
    mock_response.text = (
        "हाँ, इस योजना में टूलकिट खरीदने के लिए ₹15,000 की वित्तीय सहायता (ई-रुपी वाउचर के रूप में) दी जाती है।"
    )
    mock_instance.models.generate_content.return_value = mock_response

    payload = {
        "message": "क्या मुझे टूलकिट के लिए भी पैसे मिलेंगे?",
        "history": [
            {"role": "user", "parts": "पीएम विश्वकर्मा योजना क्या है?"},
            {"role": "model", "parts": "यह कारीगरों के लिए एक सरकारी योजना है जिसमें ₹3 लाख तक का ऋण मिलता है।"}
        ],
        "language": "hi",
    }
    response = client.post("/scheme-chat", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    assert "₹15,000" in data["response"] or "टूलकिट" in data["response"]


def test_scheme_chat_empty_message_bad_request():
    """Test that empty query message returns 400 Bad Request."""
    payload = {
        "message": "   ",
        "history": [],
        "language": "en"
    }
    response = client.post("/scheme-chat", json=payload)
    assert response.status_code == 400
    err = response.json().get("error", {})
    assert err.get("code") == "BAD_REQUEST"
    assert "empty" in err.get("message", "").lower()


def test_scheme_chat_missing_message_unprocessable_entity():
    """Test that missing required 'message' field returns 422 Unprocessable Entity."""
    payload = {
        "history": [],
        "language": "en"
    }
    response = client.post("/scheme-chat", json=payload)
    assert response.status_code == 422
    err = response.json().get("error", {})
    assert err.get("code") == "VALIDATION_ERROR"
    assert "required" in err.get("details", "").lower()


@patch("app.services.gemini_service.genai.Client")
def test_scheme_chat_provider_failure_returns_500(mock_genai_client):
    """Test that downstream LLM provider failure returns 500."""
    mock_instance = MagicMock()
    mock_genai_client.return_value = mock_instance
    mock_instance.models.generate_content.side_effect = Exception("Service Unavailable")

    payload = {
        "message": "What is PMEGP?",
        "history": [],
        "language": "en"
    }
    response = client.post("/scheme-chat", json=payload)
    assert response.status_code == 500
    err = response.json().get("error", {})
    assert err.get("code") == "INTERNAL_SERVER_ERROR"
    assert "failed" in err.get("message", "").lower()


def test_tool_retrieve_scheme_guidelines():
    """Test retrieve_scheme_guidelines tool directly with queries."""
    from app.services.gemini_service import retrieve_scheme_guidelines
    res = retrieve_scheme_guidelines("tell me about vishwakarma scheme")
    assert "VISHWAKARMA" in res
    assert "collateral-free" in res
    res = retrieve_scheme_guidelines("what is MSY or mahila samriddhi?")
    assert "MAHILA SAMRIDDHI" in res
    assert "NBCFDC" in res
    res = retrieve_scheme_guidelines("random gibberish search terms")
    assert "No specific guidelines" in res


@patch("app.services.gemini_service.simplify_term")
def test_tool_simplify_jargon(mock_simplify):
    """Test simplify_financial_jargon tool wraps simplify_term."""
    from app.services.gemini_service import simplify_financial_jargon

    mock_simplify.return_value = "Easy moratorium explanation"
    res = simplify_financial_jargon("moratorium", "en")
    assert res == "Easy moratorium explanation"
    mock_simplify.assert_called_once_with(term="moratorium", language="en")


@patch("app.services.gemini_service.recommend_scheme_explainer")
def test_tool_explain_recommendations(mock_explainer):
    """Test explain_scheme_recommendations tool correctly validates and calls recommend_scheme_explainer."""
    from app.services.gemini_service import explain_scheme_recommendations
    from app.models.schemas import ExplainerResponse

    mock_explainer.return_value = ExplainerResponse(
        top_scheme="PMEGP",
        explanation="fits profile perfectly",
        runner_up_note="others are ok"
    )

    res = explain_scheme_recommendations(
        project_category="Manufacturing",
        trade="Tailoring",
        requested_amount=100000.0,
        annual_income=200000.0,
        gender="Female",
        candidate_schemes=[
            {
                "scheme_name": "PMEGP",
                "max_coverage_pct": 35.0,
                "interest_rate": 8.5,
                "eligibility_score": 0.9
            }
        ],
        language="en"
    )

    assert res["top_scheme"] == "PMEGP"
    assert res["explanation"] == "fits profile perfectly"
    assert res["runner_up_note"] == "others are ok"
    mock_explainer.assert_called_once()


@patch("app.services.gemini_service.genai.Client")
def test_scheme_chat_passes_tools_and_config(mock_genai_client):
    """Test that chat_with_knowledge sets up the tools, system instructions, and target language correctly."""
    mock_instance = MagicMock()
    mock_genai_client.return_value = mock_instance
    mock_response = MagicMock()
    mock_response.text = "Hello! Sure, let me answer that."
    mock_instance.models.generate_content.return_value = mock_response

    payload = {
        "message": "Is there a scheme for women?",
        "history": [],
        "language": "mr",
    }
    response = client.post("/scheme-chat", json=payload)
    assert response.status_code == 200

    mock_instance.models.generate_content.assert_called_once()
    call_args = mock_instance.models.generate_content.call_args
    config = call_args.kwargs.get("config")
    
    assert config is not None
    assert len(config.tools) == 3
    tool_names = [tool.__name__ for tool in config.tools]
    assert "retrieve_scheme_guidelines" in tool_names
    assert "simplify_financial_jargon" in tool_names
    assert "explain_scheme_recommendations" in tool_names
    assert "Qualifying Conversation Memory" in config.system_instruction
    assert "Grounding & Citations" in config.system_instruction
    assert "Confidence / Strict Abstention" in config.system_instruction

