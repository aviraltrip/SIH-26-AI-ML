from fastapi import APIRouter, HTTPException, status
from app.models.schemas import JargonRequest, JargonResponse
from app.services.langchain_service import simplify_term

router = APIRouter(tags=["Jargon Simplification"])


@router.post(
    "/simplify-term",
    response_model=JargonResponse,
    status_code=status.HTTP_200_OK,
    summary="Simplify Financial & Policy Terminology",
    description=(
        "Explains financial, banking, policy, and government-scheme terminology "
        "in simple, conversational, relatable language for ordinary users and rural micro-entrepreneurs."
    ),
    responses={
        200: {
            "description": "Successful simplification of the term in the target language.",
            "content": {
                "application/json": {
                    "example": {
                        "explanation": "मोरेटोरियम अवधि (ऋण स्थगन अवधि) वह समय है जिसके दौरान आपको बैंक को कोई भी ईएमआई (EMI) या किस्त चुकाने की आवश्यकता नहीं होती है। यह एक भुगतान छुट्टी की तरह है जो आपको अपना व्यवसाय शुरू करने और स्थिर होने के लिए दी जाती है।"
                    }
                }
            },
        },
        400: {"description": "Bad Request - Invalid or empty term."},
        422: {"description": "Validation Error - Missing required fields or incorrect data types."},
        500: {"description": "Internal Server Error - LLM service failure."},
    },
)
def simplify_term_endpoint(request: JargonRequest) -> JargonResponse:
    """Endpoint to simplify financial, banking, and government-scheme terminology."""
    if not request.term or not request.term.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Term cannot be empty or whitespace only.",
        )

    try:
        explanation = simplify_term(term=request.term, language=request.language)
        return JargonResponse(explanation=explanation)
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
