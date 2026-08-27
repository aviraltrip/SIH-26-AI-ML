from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_root_endpoint():
    """Verify existing root endpoint is intact."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "online"


def test_health_endpoint():
    """Verify existing health check endpoint is intact."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


@patch("app.services.gemini_service.genai.Client")
def test_simplify_term_english_moratorium(mock_genai_client):
    """Test simplify-term with Moratorium Period in English."""
    mock_instance = MagicMock()
    mock_genai_client.return_value = mock_instance
    mock_response = MagicMock()
    mock_response.text = (
        "A moratorium period is a payment holiday where you don't have to pay loan installments immediately. "
        "Think of it like the time crops take to grow before harvest when you have no income to pay."
    )
    mock_instance.models.generate_content.return_value = mock_response

    payload = {
        "term": "Moratorium Period",
        "language": "en",
    }
    response = client.post("/simplify-term", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "explanation" in data
    assert "moratorium" in data["explanation"].lower() or "payment holiday" in data["explanation"].lower()


@patch("app.services.gemini_service.genai.Client")
def test_simplify_term_hindi_moratorium(mock_genai_client):
    """Test simplify-term with Moratorium Period in Hindi."""
    mock_instance = MagicMock()
    mock_genai_client.return_value = mock_instance
    mock_response = MagicMock()
    mock_response.text = (
        "मोरेटोरियम अवधि एक ऐसी छूट अवधि है जिसमें आपको तुरंत लोन की किस्त नहीं चुकानी पड़ती। "
        "यह फसल बोने से कटाई के बीच के समय की तरह है जब आमदनी शुरू होने तक राहत मिलती है।"
    )
    mock_instance.models.generate_content.return_value = mock_response

    payload = {
        "term": "Moratorium Period",
        "language": "hi",
    }
    response = client.post("/simplify-term", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "explanation" in data
    assert len(data["explanation"]) > 10


@patch("app.services.gemini_service.genai.Client")
def test_simplify_term_marathi_collateral(mock_genai_client):
    """Test simplify-term with Collateral in Marathi."""
    mock_instance = MagicMock()
    mock_genai_client.return_value = mock_instance
    mock_response = MagicMock()
    mock_response.text = (
        "तारण (Collateral) म्हणजे कर्ज घेण्यासाठी बँकेकडे हमी म्हणून ठेवलेली तुमची मौल्यवान वस्तू किंवा मालमत्ता. "
        "जर वेळेवर कर्ज परत करता आले नाही, तर बँक त्या मालमत्तेतून आपली रक्कम वसूल करू शकते."
    )
    mock_instance.models.generate_content.return_value = mock_response

    payload = {
        "term": "Collateral",
        "language": "mr",
    }
    response = client.post("/simplify-term", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "explanation" in data
    assert len(data["explanation"]) > 10


@patch("app.services.gemini_service.genai.Client")
def test_simplify_term_promoter_margin_default_language(mock_genai_client):
    """Test simplify-term with default language (omitted language parameter defaults to 'en')."""
    mock_instance = MagicMock()
    mock_genai_client.return_value = mock_instance
    mock_response = MagicMock()
    mock_response.text = (
        "Promoter margin is your own share of money that you must invest before the bank funds your project. "
        "It is like putting your own small seed money into your shop before borrowing the rest from a lender."
    )
    mock_instance.models.generate_content.return_value = mock_response

    payload = {
        "term": "Promoter Margin",
    }
    response = client.post("/simplify-term", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "explanation" in data
    assert len(data["explanation"]) > 10


def test_simplify_term_empty_term_bad_request():
    """Test that empty term returns 400 Bad Request."""
    payload = {
        "term": "",
        "language": "hi",
    }
    response = client.post("/simplify-term", json=payload)
    assert response.status_code == 400
    err = response.json().get("error", {})
    assert err.get("code") == "BAD_REQUEST"
    assert "empty" in err.get("message", "").lower()


def test_simplify_term_whitespace_term_bad_request():
    """Test that whitespace-only term returns 400 Bad Request."""
    payload = {
        "term": "    ",
        "language": "hi",
    }
    response = client.post("/simplify-term", json=payload)
    assert response.status_code == 400
    err = response.json().get("error", {})
    assert err.get("code") == "BAD_REQUEST"
    assert "empty" in err.get("message", "").lower()


def test_simplify_term_missing_term_unprocessable_entity():
    """Test that missing required 'term' field returns 422 Unprocessable Entity."""
    payload = {
        "language": "hi",
    }
    response = client.post("/simplify-term", json=payload)
    assert response.status_code == 422
    err = response.json().get("error", {})
    assert err.get("code") == "VALIDATION_ERROR"
    assert "required" in err.get("details", "").lower()


def test_simplify_term_invalid_type_unprocessable_entity():
    """Test that invalid types for 'term' return 422 Unprocessable Entity."""
    payload = {
        "term": ["Not", "A", "String"],
        "language": "en",
    }
    response = client.post("/simplify-term", json=payload)
    assert response.status_code == 422
    err = response.json().get("error", {})
    assert err.get("code") == "VALIDATION_ERROR"
    assert "string" in err.get("details", "").lower()


@patch("app.services.gemini_service.genai.Client")
def test_simplify_term_provider_failure_returns_500(mock_genai_client):
    """Test that downstream LLM provider failure returns 500 without leaking secrets."""
    mock_instance = MagicMock()
    mock_genai_client.return_value = mock_instance
    mock_instance.models.generate_content.side_effect = Exception("API connection timed out")

    payload = {
        "term": "Working Capital",
        "language": "en",
    }
    response = client.post("/simplify-term", json=payload)
    assert response.status_code == 500
    err = response.json().get("error", {})
    assert err.get("code") == "INTERNAL_SERVER_ERROR"
    assert "API_KEY" not in err.get("message", "")
    assert "API_KEY" not in (err.get("details") or "")
    assert "failed" in err.get("message", "").lower()
