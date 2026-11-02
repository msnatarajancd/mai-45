"""Small dependency-free adapter for Nebius' OpenAI-compatible chat endpoint."""
import json
import os
import socket
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, build_opener, HTTPRedirectHandler

DEFAULT_MODEL = 'Qwen/Qwen3-30B-A3B-Instruct-2507'
MAX_RESPONSE_BYTES = 100_000


class PlanningClientError(ValueError):
    """Sanitized provider error with an application-owned display category."""

    def __init__(self, message: str, *, code: str = 'provider_error') -> None:
        self.code = code
        super().__init__(message)


class RecoveryLLMClient(Protocol):
    def complete(self, messages: list[dict[str, str]]) -> str: ...


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class NebiusClient:
    def __init__(self, *, model: str | None = None, timeout: float = 30) -> None:
        self.model = model or os.environ.get('NEBIUS_MODEL') or DEFAULT_MODEL
        if not self.model.strip() or not 0 < timeout <= 120:
            raise PlanningClientError('Invalid AI client configuration.')
        self.timeout = timeout

    def complete(self, messages: list[dict[str, str]]) -> str:
        key = os.environ.get('NEBIUS_API_KEY', '').strip()
        if not key:
            raise PlanningClientError('NEBIUS_API_KEY is not configured.', code='missing_key')
        payload = json.dumps(dict(model=self.model, messages=messages,
            temperature=0, max_tokens=2500, stream=False,
            response_format={'type': 'json_object'})).encode('utf-8')
        try:
            request = Request('https://api.tokenfactory.nebius.com/v1/chat/completions',
                data=payload, headers={'Authorization': f'Bearer {key}',
                                      'Content-Type': 'application/json'}, method='POST')
            with build_opener(_NoRedirect()).open(request, timeout=self.timeout) as response:
                raw = response.read(MAX_RESPONSE_BYTES + 1)
            if len(raw) > MAX_RESPONSE_BYTES:
                raise PlanningClientError('AI provider response exceeded the size limit.')
            data = json.loads(raw)
            choice = data['choices'][0]
            if choice.get('finish_reason') != 'stop' or choice['message'].get('tool_calls'):
                raise PlanningClientError('AI provider returned an incomplete or unsupported response.')
            content = choice['message']['content']
            if not isinstance(content, str) or not content.strip():
                raise PlanningClientError('AI provider returned empty content.')
            return content
        except PlanningClientError:
            raise
        except (TimeoutError, socket.timeout):
            raise PlanningClientError('AI provider request timed out.', code='timeout') from None
        except HTTPError:
            raise PlanningClientError('AI provider rejected the request.') from None
        except URLError as error:
            if isinstance(error.reason, (TimeoutError, socket.timeout)):
                raise PlanningClientError('AI provider request timed out.', code='timeout') from None
            raise PlanningClientError('AI provider request failed.') from None
        except (OSError, ValueError, KeyError, IndexError, TypeError):
            raise PlanningClientError('AI provider request failed or returned invalid content.') from None
