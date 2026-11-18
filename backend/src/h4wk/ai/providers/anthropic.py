from anthropic import Anthropic, APIError, transform_schema

from h4wk.ai.base import ProviderError, ProviderReply, ProviderRequest
from h4wk.ai.providers.content import split_messages


class AnthropicProvider:
    def __init__(self, key: str):
        self.key = key

    def complete(self, request: ProviderRequest) -> ProviderReply:
        system, turns = split_messages(request)
        messages = []
        for message, image in turns:
            content = [{"type": "text", "text": message["content"]}]
            if image:
                content.append(
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": image.mime,
                            "data": image.base64(),
                        },
                    }
                )
            messages.append({"role": message["role"], "content": content})
        options = {}
        if system:
            options["system"] = system
        if request.structured:
            try:
                schema = transform_schema(request.schema)
            except ValueError as error:
                raise ProviderError("Anthropic không hỗ trợ schema này") from error
            options["output_config"] = {"format": {"type": "json_schema", "schema": schema}}
        try:
            with Anthropic(api_key=self.key, max_retries=0) as client:
                reply = client.messages.create(
                    model=request.model, max_tokens=4096, messages=messages, **options
                )
        except APIError as error:
            raise ProviderError("Lỗi API Anthropic") from error
        text = "".join(b.text for b in reply.content if b.type == "text")
        return ProviderReply(text, reply.usage.input_tokens, reply.usage.output_tokens)
