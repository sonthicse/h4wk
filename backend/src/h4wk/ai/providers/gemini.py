import httpx2
from google import genai
from google.genai import errors, types

from h4wk.ai.base import REQUEST_TIMEOUT_S, ProviderError, ProviderReply, ProviderRequest
from h4wk.ai.providers.content import split_messages


class GeminiProvider:
    def __init__(self, key: str):
        self.key = key

    def complete(self, request: ProviderRequest) -> ProviderReply:
        system, turns = split_messages(request)
        contents = []
        for message, image in turns:
            parts = [types.Part.from_text(text=message["content"])]
            if image:
                parts.append(types.Part.from_bytes(data=image.data, mime_type=image.mime))
            role = "model" if message["role"] == "assistant" else message["role"]
            contents.append(types.Content(role=role, parts=parts))
        config = types.GenerateContentConfig(
            system_instruction=system or None,
            response_mime_type="application/json",
            response_json_schema=request.schema if request.structured else None,
        )
        options = types.HttpOptions(
            timeout=REQUEST_TIMEOUT_S * 1000, retry_options=types.HttpRetryOptions(attempts=1)
        )
        try:
            with genai.Client(api_key=self.key, http_options=options) as client:
                reply = client.models.generate_content(
                    model=request.model, contents=contents, config=config
                )
        except (errors.APIError, httpx2.RequestError) as error:
            raise ProviderError("Gemini API error") from error
        usage = reply.usage_metadata
        return ProviderReply(
            reply.text or "",
            usage.prompt_token_count if usage else None,
            usage.candidates_token_count if usage else None,
        )
