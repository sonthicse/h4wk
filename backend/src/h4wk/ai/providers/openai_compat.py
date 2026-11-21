from openai import APIError, OpenAI

from h4wk.ai.base import REQUEST_TIMEOUT_S, ProviderError, ProviderReply, ProviderRequest
from h4wk.ai.providers.content import split_messages


class OpenAICompatProvider:
    def __init__(self, key: str, base_url: str, *, ollama: bool = False):
        self.key = key
        self.base_url = base_url
        self.ollama = ollama

    def complete(self, request: ProviderRequest) -> ProviderReply:
        system, turns = split_messages(request)
        messages = [{"role": "system", "content": system}] if system else []
        for message, image in turns:
            if image:
                url = f"data:{image.mime};base64,{image.base64()}"
                messages.append(
                    {
                        "role": message["role"],
                        "content": [
                            {"type": "text", "text": message["content"]},
                            {"type": "image_url", "image_url": {"url": url}},
                        ],
                    }
                )
            else:
                messages.append(message)
        if request.structured:
            function = {"name": "result", "parameters": request.schema}
            options = {
                "tools": [{"type": "function", "function": function}],
                "tool_choice": {"type": "function", "function": {"name": "result"}},
            }
        else:
            options = {"response_format": {"type": "json_object"}}
        if self.ollama:
            options["max_tokens"] = 4096
        try:
            with OpenAI(
                api_key=self.key,
                base_url=self.base_url,
                max_retries=0,
                timeout=300 if self.ollama else REQUEST_TIMEOUT_S,
            ) as client:
                reply = client.chat.completions.create(
                    model=request.model, messages=messages, **options
                )
        except APIError as error:
            raise ProviderError("chat completions API error") from error
        if not reply.choices:
            raise ProviderError("API returned no choices")
        message = reply.choices[0].message
        text = message.content or ""
        if request.structured:
            text = next(
                (
                    call.function.arguments
                    for call in message.tool_calls or []
                    if call.type == "function" and call.function.name == "result"
                ),
                "",
            )
        usage = reply.usage
        return ProviderReply(
            text, usage.prompt_tokens if usage else None, usage.completion_tokens if usage else None
        )
