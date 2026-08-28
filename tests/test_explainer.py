import json
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


@patch("app.services.gemini_service.genai.Client")
def test_recommend_scheme_explainer_english_success(mock_genai_client):
    """Test scheme explainer with valid English payload."""
    mock_instance = MagicMock()
    mock_genai_client.return_value = mock_instance
    mock_response = MagicMock()
    mock_response.text = json.dumps({
        "top_scheme": "Mahila Samriddhi Yojana",
        "explanation": "This scheme is best suited for you as it offers 90% coverage with a low interest rate of 4.0% for female entrepreneurs in tailoring.",
        "runner_up_note": "Micro Credit Scheme is also an option, but has a higher interest rate of 6.0%.",
    })
    mock_instance.models.generate_content.return_value = mock_response

    payload = {
        "applicant": {
            "project_category": "Manufacturing",
            "requested_amount": 80000.0,
            "annual_income": 120000.0,
            "trade": "Tailoring",
            "gender": "Female",
        },
        "candidate_schemes": [
            {
                "scheme_name": "Mahila Samriddhi Yojana",
                "max_coverage_pct": 90.0,
                "interest_rate": 4.0,
                "eligibility_score": 0.95,
            },
            {
                "scheme_name": "Micro Credit Scheme",
                "max_coverage_pct": 90.0,
                "interest_rate": 6.0,
                "eligibility_score": 0.85,
            },
        ],
        "language": "en",
    }
    response = client.post("/recommend-scheme-explainer", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["top_scheme"] == "Mahila Samriddhi Yojana"
    assert "explanation" in data and isinstance(data["explanation"], str)
    assert "runner_up_note" in data and isinstance(data["runner_up_note"], str)
    assert len(data["explanation"]) > 0
    assert len(data["runner_up_note"]) > 0


@patch("app.services.gemini_service.genai.Client")
def test_recommend_scheme_explainer_hindi_success(mock_genai_client):
    """Test scheme explainer with valid Hindi payload."""
    mock_instance = MagicMock()
    mock_genai_client.return_value = mock_instance
    mock_response = MagicMock()
    mock_response.text = json.dumps({
        "top_scheme": "Mahila Samriddhi Yojana",
        "explanation": "यह योजना आपकी आवश्यकताओं के लिए सबसे उपयुक्त है क्योंकि यह विशेष रूप से महिला उद्यमियों को 4% ब्याज पर 90% कवरेज प्रदान करती है।",
        "runner_up_note": "माइक्रो क्रेडिट योजना भी एक विकल्प है, लेकिन इसकी ब्याज दर 6% अधिक है।",
    })
    mock_instance.models.generate_content.return_value = mock_response

    payload = {
        "applicant": {
            "project_category": "Manufacturing",
            "requested_amount": 80000.0,
            "annual_income": 120000.0,
            "trade": "Tailoring",
            "gender": "Female",
        },
        "candidate_schemes": [
            {
                "scheme_name": "Mahila Samriddhi Yojana",
                "max_coverage_pct": 90.0,
                "interest_rate": 4.0,
                "eligibility_score": 0.95,
            },
            {
                "scheme_name": "Micro Credit Scheme",
                "max_coverage_pct": 90.0,
                "interest_rate": 6.0,
                "eligibility_score": 0.85,
            },
        ],
        "language": "hi",
    }
    response = client.post("/recommend-scheme-explainer", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["top_scheme"] == "Mahila Samriddhi Yojana"
    assert "explanation" in data and len(data["explanation"]) > 0
    assert "runner_up_note" in data and len(data["runner_up_note"]) > 0


def test_recommend_scheme_explainer_empty_candidate_schemes_bad_request():
    """Test that empty candidate_schemes list returns 400 Bad Request."""
    payload = {
        "applicant": {
            "project_category": "Manufacturing",
            "requested_amount": 80000.0,
            "annual_income": 120000.0,
            "trade": "Tailoring",
            "gender": "Female",
        },
        "candidate_schemes": [],
        "language": "en",
    }
    response = client.post("/recommend-scheme-explainer", json=payload)
    assert response.status_code == 400
    err = response.json().get("error", {})
    assert err.get("code") == "BAD_REQUEST"
    assert "empty" in err.get("message", "").lower() or "candidate" in err.get("message", "").lower()


def test_recommend_scheme_explainer_missing_applicant_field_unprocessable_entity():
    """Test that missing required applicant field returns 422 Unprocessable Entity."""
    payload = {
        "applicant": {
            "project_category": "Manufacturing",
            "requested_amount": 80000.0,
            "annual_income": 120000.0,
            
        },
        "candidate_schemes": [
            {
                "scheme_name": "Mahila Samriddhi Yojana",
                "max_coverage_pct": 90.0,
                "interest_rate": 4.0,
                "eligibility_score": 0.95,
            }
        ],
        "language": "en",
    }
    response = client.post("/recommend-scheme-explainer", json=payload)
    assert response.status_code == 422
    err = response.json().get("error", {})
    assert err.get("code") == "VALIDATION_ERROR"
    assert "required" in err.get("details", "").lower()


def test_recommend_scheme_explainer_missing_candidate_field_unprocessable_entity():
    """Test that missing required candidate_scheme field returns 422 Unprocessable Entity."""
    payload = {
        "applicant": {
            "project_category": "Manufacturing",
            "requested_amount": 80000.0,
            "annual_income": 120000.0,
            "trade": "Tailoring",
            "gender": "Female",
        },
        "candidate_schemes": [
            {
                "scheme_name": "Mahila Samriddhi Yojana",
                
            }
        ],
        "language": "en",
    }
    response = client.post("/recommend-scheme-explainer", json=payload)
    assert response.status_code == 422
    err = response.json().get("error", {})
    assert err.get("code") == "VALIDATION_ERROR"


def test_recommend_scheme_explainer_invalid_field_type_unprocessable_entity():
    """Test that incorrect data types return 422 Unprocessable Entity."""
    payload = {
        "applicant": {
            "project_category": "Manufacturing",
            "requested_amount": "not-a-number",
            "annual_income": 120000.0,
            "trade": "Tailoring",
            "gender": "Female",
        },
        "candidate_schemes": [
            {
                "scheme_name": "Mahila Samriddhi Yojana",
                "max_coverage_pct": 90.0,
                "interest_rate": 4.0,
                "eligibility_score": 0.95,
            }
        ],
        "language": "en",
    }
    response = client.post("/recommend-scheme-explainer", json=payload)
    assert response.status_code == 422
    err = response.json().get("error", {})
    assert err.get("code") == "VALIDATION_ERROR"


@patch("app.services.gemini_service.genai.Client")
def test_recommend_scheme_explainer_provider_failure_returns_500(mock_genai_client):
    """Test that downstream LLM provider failure returns 500."""
    mock_instance = MagicMock()
    mock_genai_client.return_value = mock_instance
    mock_instance.models.generate_content.side_effect = Exception("LLM Provider Timeout")

    payload = {
        "applicant": {
            "project_category": "Manufacturing",
            "requested_amount": 80000.0,
            "annual_income": 120000.0,
            "trade": "Tailoring",
            "gender": "Female",
        },
        "candidate_schemes": [
            {
                "scheme_name": "Mahila Samriddhi Yojana",
                "max_coverage_pct": 90.0,
                "interest_rate": 4.0,
                "eligibility_score": 0.95,
            }
        ],
        "language": "en",
    }
    response = client.post("/recommend-scheme-explainer", json=payload)
    assert response.status_code == 500
    err = response.json().get("error", {})
    assert err.get("code") == "INTERNAL_SERVER_ERROR"
    assert "failed" in err.get("message", "").lower()


@patch("app.services.gemini_service.genai.Client")
def test_recommend_scheme_explainer_unsupported_language_returns_400(mock_genai_client):
    """Test A: Test that unsupported language code returns 400 before calling Gemini."""
    payload = {
        "applicant": {
            "project_category": "Manufacturing",
            "requested_amount": 80000.0,
            "annual_income": 120000.0,
            "trade": "Tailoring",
            "gender": "Female",
        },
        "candidate_schemes": [
            {
                "scheme_name": "Mahila Samriddhi Yojana",
                "max_coverage_pct": 90.0,
                "interest_rate": 4.0,
                "eligibility_score": 0.95,
            }
        ],
        "language": "xyz",
    }
    response = client.post("/recommend-scheme-explainer", json=payload)
    assert response.status_code == 400
    err = response.json().get("error", {})
    assert err.get("code") == "BAD_REQUEST"
    assert "unsupported" in err.get("message", "").lower() or "xyz" in err.get("message", "").lower()
    mock_genai_client.assert_not_called()


@patch("app.services.gemini_service.genai.Client")
def test_recommend_scheme_explainer_default_language_success(mock_genai_client):
    """Test B: Test that omitting language field defaults to English without making live calls."""
    mock_instance = MagicMock()
    mock_genai_client.return_value = mock_instance
    mock_response = MagicMock()
    mock_response.text = json.dumps({
        "top_scheme": "Scheme A",
        "explanation": "Scheme A provides 90% coverage at a low 4% interest rate.",
        "runner_up_note": "Scheme B has a higher interest rate of 6%.",
    })
    mock_instance.models.generate_content.return_value = mock_response

    payload = {
        "applicant": {
            "project_category": "Manufacturing",
            "requested_amount": 80000.0,
            "annual_income": 120000.0,
            "trade": "Tailoring",
            "gender": "Female",
        },
        "candidate_schemes": [
            {
                "scheme_name": "Scheme A",
                "max_coverage_pct": 90.0,
                "interest_rate": 4.0,
                "eligibility_score": 0.95,
            },
            {
                "scheme_name": "Scheme B",
                "max_coverage_pct": 80.0,
                "interest_rate": 6.0,
                "eligibility_score": 0.85,
            },
        ],
    }
    response = client.post("/recommend-scheme-explainer", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["top_scheme"] == "Scheme A"
    assert data["explanation"] == "Scheme A provides 90% coverage at a low 4% interest rate."
    assert data["runner_up_note"] == "Scheme B has a higher interest rate of 6%."
    call_args = mock_instance.models.generate_content.call_args
    assert "English" in call_args.kwargs.get("contents", "") or "English" in str(call_args)


@patch("app.services.gemini_service.genai.Client")
def test_recommend_scheme_explainer_malformed_structured_output_returns_500(mock_genai_client):
    """Test C: Test that incomplete/malformed structured output from Gemini returns 500."""
    mock_instance = MagicMock()
    mock_genai_client.return_value = mock_instance
    mock_response = MagicMock()
    mock_response.text = json.dumps({
        "top_scheme": "Mahila Samriddhi Yojana"
    })
    mock_instance.models.generate_content.return_value = mock_response

    payload = {
        "applicant": {
            "project_category": "Manufacturing",
            "requested_amount": 80000.0,
            "annual_income": 120000.0,
            "trade": "Tailoring",
            "gender": "Female",
        },
        "candidate_schemes": [
            {
                "scheme_name": "Mahila Samriddhi Yojana",
                "max_coverage_pct": 90.0,
                "interest_rate": 4.0,
                "eligibility_score": 0.95,
            }
        ],
        "language": "en",
    }
    response = client.post("/recommend-scheme-explainer", json=payload)
    assert response.status_code == 500
    err = response.json().get("error", {})
    assert err.get("code") == "INTERNAL_SERVER_ERROR"

