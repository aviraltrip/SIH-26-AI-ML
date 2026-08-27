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
