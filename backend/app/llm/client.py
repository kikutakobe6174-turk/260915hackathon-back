import json
from typing import Any

from google import genai

from app.config import Settings


class LlmCallError(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


def image_part(image_base64: str, media_type: str) -> dict:
    return {"type": "image", "mime_type": media_type, "data": image_base64}


def text_part(text: str) -> dict:
    return {"type": "text", "text": text}


def call_structured(
    settings: Settings,
    input_parts: list[dict] | str,
    json_schema: dict,
    system_instruction: str | None = None,
) -> Any:
    """Call Gemini via the Interactions API and return the parsed JSON body.

    Raises LlmCallError on any configuration, network, API, or parsing failure.
    Never persists image bytes anywhere; store=False keeps Google from retaining
    the request/response for later retrieval.
    """
    if not settings.gemini_api_key or not settings.gemini_model:
        raise LlmCallError("GEMINI_API_KEY または GEMINI_MODEL が設定されていません")

    client = genai.Client(api_key=settings.gemini_api_key)

    try:
        interaction = client.interactions.create(
            model=settings.gemini_model,
            input=input_parts,
            system_instruction=system_instruction,
            response_format={
                "type": "text",
                "mime_type": "application/json",
                "schema": json_schema,
            },
            store=False,
            timeout=settings.gemini_timeout_ms / 1000,
        )
    except Exception as exc:  # network / auth / API errors
        raise LlmCallError(f"Gemini呼び出しに失敗しました: {exc}") from exc

    if interaction.status != "completed":
        detail = "; ".join(f"{e.code}: {e.message}" for e in (interaction.errors or []))
        raise LlmCallError(f"Geminiの応答が完了しませんでした (status={interaction.status}) {detail}")

    output_text = interaction.output_text
    if not output_text:
        raise LlmCallError("Geminiから空の応答が返されました")

    try:
        return json.loads(output_text)
    except json.JSONDecodeError as exc:
        raise LlmCallError(f"Geminiの応答をJSONとして解析できませんでした: {exc}") from exc
