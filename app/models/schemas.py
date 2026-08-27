from pydantic import BaseModel, Field


class JargonRequest(BaseModel):
    term: str = Field(
        ...,
        description="The financial or policy jargon term (e.g., 'Moratorium', 'Promoter Margin')",
    )
    language: str = Field(
        "en",
        description="Target ISO language code (e.g., 'en', 'hi', 'mr')",
    )


class JargonResponse(BaseModel):
    explanation: str = Field(
        ...,
        description="Simplified explanation of the term in the target language",
    )
