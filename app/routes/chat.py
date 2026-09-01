from fastapi import APIRouter, HTTPException, status

from app.models.schemas import ChatRequest, ChatResponse
from app.services.gemini_service import chat_with_knowledge

router = APIRouter(tags=["Scheme Chatbot"])


@router.post(
    "/scheme-chat",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
    summary="Chat Grounded on Scheme Guidelines",
    description=(
        "An interactive chatbot grounded on official government scheme policies and guidelines. "
        "Answers multi-turn conversational queries truthfully without hallucinating."
    ),
    responses={
        200: {
            "description": "Successful chat response with grounded advice and follow-up suggestions.",
            "content": {
                "application/json": {
                    "example": {
                        "response": "महिला समृद्धि योजना के लिए ब्याज दर केवल 4% वार्षिक है, जो महिला लाभार्थियों के लिए बेहद अनुकूल है।",
                        "suggested_questions": [
                            "इस योजना के तहत अधिकतम ऋण राशि कितनी है?",
                            "आवेदन करने के लिए कौन-से दस्तावेज़ आवश्यक हैं?",
                            "क्या इस योजना के लिए पारिवारिक आय की कोई सीमा है?"
                        ]
                    }
                }
            },
        },
        400: {"description": "Bad Request - Invalid or empty question."},
        422: {"description": "Validation Error - Missing required fields or incorrect data types."},
        500: {"description": "Internal Server Error - LLM service failure."},
    },
)
def scheme_chat_endpoint(request: ChatRequest) -> ChatResponse:
    """Endpoint to interact with the scheme chatbot."""
    try:
        response_text, suggested_questions = chat_with_knowledge(
            message=request.message,
            history=request.history,
            language=request.language,
        )
        return ChatResponse(response=response_text, suggested_questions=suggested_questions)
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
