import io
import json
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient
from PIL import Image
from main import app

client = TestClient(app)


def _get_dummy_png_bytes() -> bytes:
    buf = io.BytesIO()
    img = Image.new("RGB", (10, 10), color="white")
    img.save(buf, format="PNG")
    return buf.getvalue()


DUMMY_PNG_BYTES = _get_dummy_png_bytes()



@patch("app.services.ocr_service.genai.Client")
def test_ocr_caste_certificate_success(mock_genai_client):
    """Test successful OCR processing for a Caste Certificate."""
    mock_instance = MagicMock()
    mock_genai_client.return_value = mock_instance
    mock_response = MagicMock()
    mock_response.text = json.dumps({
        "name": "Amit Ramesh Kumar",
        "category": "OBC",
        "annual_income": None,
        "valid_until": None,
    })
    mock_instance.models.generate_content.return_value = mock_response

    files = {"file": ("caste_cert.png", DUMMY_PNG_BYTES, "image/png")}
    data = {"doc_type": "caste"}
    
    response = client.post("/ocr-certificate", files=files, data=data)
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["doc_type"] == "caste"
    assert res_data["extracted_fields"]["name"] == "Amit Ramesh Kumar"
    assert res_data["extracted_fields"]["category"] == "OBC"
    assert res_data["extracted_fields"]["annual_income"] is None
    assert res_data["income_verified"] is False
    assert res_data["raw_confidence"] == 0.95


@patch("app.services.ocr_service.genai.Client")
def test_ocr_income_certificate_verified_success(mock_genai_client):
    """Test successful OCR processing for an Income Certificate within limit (verified)."""
    mock_instance = MagicMock()
    mock_genai_client.return_value = mock_instance
    mock_response = MagicMock()
    mock_response.text = json.dumps({
        "name": "Rahul Sharma",
        "category": None,
        "annual_income": 180000.0,
        "valid_until": "2027-03-31",
    })
    mock_instance.models.generate_content.return_value = mock_response

    files = {"file": ("income_cert.jpg", DUMMY_PNG_BYTES, "image/jpeg")}
    data = {"doc_type": "income"}
    
    response = client.post("/ocr-certificate", files=files, data=data)
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["doc_type"] == "income"
    assert res_data["extracted_fields"]["name"] == "Rahul Sharma"
    assert res_data["extracted_fields"]["annual_income"] == 180000.0
    assert res_data["extracted_fields"]["valid_until"] == "2027-03-31"
    assert res_data["income_verified"] is True


@patch("app.services.ocr_service.genai.Client")
def test_ocr_income_certificate_unverified_exceeds_limit(mock_genai_client):
    """Test Income Certificate where income exceeds 5 Lakhs limit (unverified)."""
    mock_instance = MagicMock()
    mock_genai_client.return_value = mock_instance
    mock_response = MagicMock()
    mock_response.text = json.dumps({
        "name": "Sunita Devi",
        "category": None,
        "annual_income": 650000.0,
        "valid_until": None,
    })
    mock_instance.models.generate_content.return_value = mock_response

    files = {"file": ("income_large.png", DUMMY_PNG_BYTES, "image/png")}
    data = {"doc_type": "income"}
    
    response = client.post("/ocr-certificate", files=files, data=data)
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["income_verified"] is False
    assert res_data["extracted_fields"]["annual_income"] == 650000.0


def test_ocr_certificate_invalid_doc_type_returns_400():
    """Test that invalid document type (not caste/income) returns 400 Bad Request."""
    files = {"file": ("doc.png", DUMMY_PNG_BYTES, "image/png")}
    data = {"doc_type": "invalid_type"}
    
    response = client.post("/ocr-certificate", files=files, data=data)
    assert response.status_code == 400
    err = response.json().get("error", {})
    assert err.get("code") == "BAD_REQUEST"
    assert "doc_type" in err.get("message", "").lower()


def test_ocr_certificate_invalid_file_format_returns_400():
    """Test that unsupported file format (e.g. text file) returns 400 Bad Request."""
    files = {"file": ("notes.txt", b"some text content", "text/plain")}
    data = {"doc_type": "caste"}
    
    response = client.post("/ocr-certificate", files=files, data=data)
    assert response.status_code == 400
    err = response.json().get("error", {})
    assert err.get("code") == "BAD_REQUEST"
    assert "format" in err.get("message", "").lower() or "allowed" in err.get("message", "").lower()


def test_ocr_certificate_missing_fields_unprocessable_entity():
    """Test that missing required parameters returns 422 Unprocessable Entity."""
    files = {"file": ("caste.png", DUMMY_PNG_BYTES, "image/png")}
    
    response = client.post("/ocr-certificate", files=files)
    assert response.status_code == 422
    err = response.json().get("error", {})
    assert err.get("code") == "VALIDATION_ERROR"
