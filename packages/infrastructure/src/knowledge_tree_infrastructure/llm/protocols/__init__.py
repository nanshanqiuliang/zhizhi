"""Protocol adapters for the LLM port (WORK-2026-008)."""

from .openai_chat import build_chat_request, parse_chat_response, sse_stream_events

__all__ = ["build_chat_request", "parse_chat_response", "sse_stream_events"]
