from fastapi import APIRouter, HTTPException, status

from app.models.schemas import ExplainerRequest, ExplainerResponse
from app.services.gemini_service import recommend_scheme_explainer

router = APIRouter(tags=["Scheme Explainer"])


@router.post(
    "/recommend-scheme-explainer",
    response_model=ExplainerResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate Narrative Explanation for Recommended Schemes",
    description=(
        "Generates a tailored natural-language narrative describing why the shortlisted "
        "schemes fit the applicant's profile and explaining any alternative candidate options."
    ),
    responses={
        200: {
            "description": "Successful generation of scheme recommendation narrative.",
            "content": {
                "application/json": {
                    "example": {
                        "top_scheme": "Mahila Samriddhi Yojana",
                        "explanation": (
                            "यह योजना आपकी आवश्यकताओं के लिए सबसे उपयुक्त है क्योंकि यह विशेष रूप से महिला उद्यमियों "
                            "(दर्जी व्यवसाय के लिए) को लक्षित करती है। आपको आवश्यक ₹80,000 की राशि का 90% कवरेज मिलेगा "
                            "और ब्याज दर केवल 4% वार्षिक है, जो सबसे कम है।"
                        ),
                        "runner_up_note": (
                            "माइक्रो क्रेडिट योजना भी एक विकल्प है, लेकिन इसकी ब्याज दर 6% है, "
                            "जो महिला समृद्धि योजना की तुलना में 2% अधिक है।"
                        ),
                    }
                }
            },
        },
        400: {"description": "Bad Request - Invalid or empty candidate schemes list."},
        422: {"description": "Validation Error - Missing required fields or incorrect data types."},
        500: {"description": "Internal Server Error - LLM service failure."},
    },
)
def recommend_scheme_explainer_endpoint(request: ExplainerRequest) -> ExplainerResponse:
    """Endpoint to generate tailored narrative explanation for shortlisted schemes."""
    try:
        return recommend_scheme_explainer(
            applicant=request.applicant,
            candidate_schemes=request.candidate_schemes,
            language=request.language,
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
            detail="An unexpected error occurred while processing the request.",
        ) from exc
