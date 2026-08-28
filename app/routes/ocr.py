from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from app.models.schemas import OCRResponse
from app.services.ocr_service import process_certificate

router = APIRouter(tags=["Document OCR"])


@router.post(
    "/ocr-certificate",
    response_model=OCRResponse,
    status_code=status.HTTP_200_OK,
    summary="OCR Caste & Income Certificates",
    description=(
        "Extracts structured applicant information from uploaded caste or income certificates "
        "and verifies income criteria eligibility."
    ),
    responses={
        200: {
            "description": "Successful OCR extraction.",
            "content": {
                "application/json": {
                    "example": {
                        "doc_type": "income",
                        "extracted_fields": {
                            "name": "Amit Ramesh Kumar",
                            "category": None,
                            "annual_income": 180000.0,
                            "valid_until": "2027-03-31",
                        },
                        "income_verified": True,
                        "raw_confidence": 0.95,
                    }
                }
            },
        },
        400: {"description": "Bad Request - Unsupported file format or invalid document type."},
        422: {"description": "Validation Error - Missing required fields or incorrect data types."},
        500: {"description": "Internal Server Error - OCR service failure."},
    },
)
async def ocr_certificate_endpoint(
    file: UploadFile = File(..., description="Uploaded Caste or Income Certificate file (PDF or Image)"),
    doc_type: str = Form(..., description="Type of certificate: 'caste' or 'income'"),
) -> OCRResponse:
    """Endpoint to process caste/income certificate files via OCR."""
    dt_clean = (doc_type or "").strip().lower()
    if dt_clean not in ("caste", "income"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid doc_type. Must strictly be 'caste' or 'income'.",
        )

    fn = (file.filename or "").lower()
    if not (
        fn.endswith(".pdf")
        or fn.endswith(".jpg")
        or fn.endswith(".jpeg")
        or fn.endswith(".png")
        or fn.endswith(".webp")
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported document file format. Only PDF, PNG, JPEG, WebP are allowed.",
        )

    try:
        file_bytes = await file.read()
        extracted_fields = process_certificate(
            file_bytes=file_bytes,
            filename=file.filename,
            doc_type=dt_clean,
        )
        income_verified = False
        if dt_clean == "income":
            if extracted_fields.annual_income is not None:
                income_verified = extracted_fields.annual_income <= 500000.00

        return OCRResponse(
            doc_type=dt_clean,
            extracted_fields=extracted_fields,
            income_verified=income_verified,
            raw_confidence=0.95,
        )
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(val_err),
        ) from val_err
    except RuntimeError as run_err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(run_err),
        ) from run_err
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while processing the document.",
        ) from exc
