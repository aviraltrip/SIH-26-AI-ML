from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


@patch("app.services.gemini_service.genai.Client")
def test_extract_intent_english_basic(mock_genai_client):
    """Test intent extraction with basic English transcript."""
    mock_instance = MagicMock()
    mock_genai_client.return_value = mock_instance
    mock_response = MagicMock()
    mock_response.text = (
        '{"project_category": "Manufacturing", "requested_amount": 150000.0, '
        '"annual_income": 300000.0, "trade": "Carpentry", "gender": "Male", "confidence": 0.95}'
    )
    mock_instance.models.generate_content.return_value = mock_response

    payload = {
        "transcript": "I want to start a carpentry workshop and need a loan of 1.5 lakhs. My family income is 3 lakhs.",
        "language": "en",
    }
    response = client.post("/extract-applicant-intent", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["project_category"] == "Manufacturing"
    assert data["requested_amount"] == 150000.0
    assert data["annual_income"] == 300000.0
    assert data["trade"] == "Carpentry"
    assert data["gender"] == "Male"
    assert data["confidence"] == 0.95


@patch("app.services.gemini_service.genai.Client")
def test_extract_intent_hindi_translation(mock_genai_client):
    """Test intent extraction with Hindi transcript (translating values to English)."""
    mock_instance = MagicMock()
    mock_genai_client.return_value = mock_instance
    mock_response = MagicMock()
    mock_response.text = (
        '{"project_category": "Service", "requested_amount": 80000.0, '
        '"annual_income": 120000.0, "trade": "Tailoring", "gender": "Female", "confidence": 0.92}'
    )
    mock_instance.models.generate_content.return_value = mock_response

    payload = {
        "transcript": "नमस्ते, मैं एक सिलाई की दुकान शुरू करने के लिए 80,000 रुपये का ऋण चाहता हूँ। मेरी वार्षिक पारिवारिक आय 1,20,000 रुपये है।",
        "language": "hi",
    }
    response = client.post("/extract-applicant-intent", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["project_category"] == "Service"
    assert data["requested_amount"] == 80000.0
    assert data["annual_income"] == 120000.0
    assert data["trade"] == "Tailoring"  
    assert data["gender"] == "Female"    
    assert data["confidence"] == 0.92


def test_extract_intent_empty_transcript_bad_request():
    """Test that empty transcript returns 400 Bad Request."""
    payload = {
        "transcript": "   ",
        "language": "en"
    }
    response = client.post("/extract-applicant-intent", json=payload)
    assert response.status_code == 400
    err = response.json().get("error", {})
    assert err.get("code") == "BAD_REQUEST"
    assert "empty" in err.get("message", "").lower()


def test_extract_intent_missing_transcript_unprocessable_entity():
    """Test that missing required 'transcript' field returns 422 Unprocessable Entity."""
    payload = {
        "language": "en"
    }
    response = client.post("/extract-applicant-intent", json=payload)
    assert response.status_code == 422
    err = response.json().get("error", {})
    assert err.get("code") == "VALIDATION_ERROR"
    assert "required" in err.get("details", "").lower()


@patch("app.services.gemini_service.genai.Client")
def test_extract_intent_provider_failure_returns_500(mock_genai_client):
    """Test that downstream LLM provider failure returns 500."""
    mock_instance = MagicMock()
    mock_genai_client.return_value = mock_instance
    mock_instance.models.generate_content.side_effect = Exception("Service Unavailable")

    payload = {
        "transcript": "I need a loan for dairy business.",
        "language": "en"
    }
    response = client.post("/extract-applicant-intent", json=payload)
    assert response.status_code == 500
    err = response.json().get("error", {})
    assert err.get("code") == "INTERNAL_SERVER_ERROR"
    assert "failed" in err.get("message", "").lower()
