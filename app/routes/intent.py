from fastapi import APIRouter, HTTPException, status

from app.models.schemas import IntentRequest, IntentResponse
from app.services.gemini_service import extract_applicant_intent

router = APIRouter(tags=["Intent Extraction"])


@router.post(
    "/extract-applicant-intent",
    response_model=IntentResponse,
    status_code=status.HTTP_200_OK,
    summary="Extract Applicant Profile Details from Transcript",
    description=(
        "Analyzes raw speech transcriptions or text statements to extract "
        "structured applicant parameters like project category, requested amount, annual income, trade, gender, "
        "and overall confidence score."
    ),
    responses={
        200: {
            "description": "Successful extraction of structured applicant profile details.",
            "content": {
                "application/json": {
                    "example": {
                        "project_category": "Manufacturing",
                        "requested_amount": 80000.0,
                        "annual_income": 120000.0,
                        "trade": "Tailoring",
                        "gender": "Female",
                        "confidence": 0.94,
                    }
                }
            },
        },
        400: {"description": "Bad Request - Invalid or empty transcript."},
        422: {"description": "Validation Error - Missing required fields or incorrect data types."},
        500: {"description": "Internal Server Error - LLM service failure."},
    },
)
def extract_intent_endpoint(request: IntentRequest) -> IntentResponse:
    """Endpoint to parse unstructured speech/text and extract profile details."""
    try:
        return extract_applicant_intent(transcript=request.transcript, language=request.language)
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
            detail="An unexpected error occurred while processing the request.",
        ) from exc
