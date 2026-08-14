"""Generated from docs/contracts/llm.v1.schema.json.

Do not hand-edit. Re-run: pnpm --filter @knowledge-tree/contracts-ts generate
"""

LLM_V1_SCHEMA_JSON = r"""{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://knowledge-tree.local/contracts/llm.v1.schema.json",
  "title": "Knowledge Tree LLM canonical contracts v1",
  "description": "Canonical LLM port contract for WORK-2026-007 per LLM-COMPAT-BASELINE-001. This is the only hand-edited contract source: Provider/Protocol IDs, capability names, finish reasons and stable error codes are all defined here and consumed by generated artifacts. Runtime code must never hand-maintain a second enum with the same meaning.",
  "oneOf": [
    {
      "$ref": "#/$defs/GenerationRequest"
    },
    {
      "$ref": "#/$defs/GenerationResult"
    },
    {
      "$ref": "#/$defs/CapabilitySet"
    },
    {
      "$ref": "#/$defs/ContentPart"
    },
    {
      "$ref": "#/$defs/CanonicalMessage"
    },
    {
      "$ref": "#/$defs/ToolDefinition"
    },
    {
      "$ref": "#/$defs/CanonicalToolCall"
    },
    {
      "$ref": "#/$defs/CanonicalUsage"
    },
    {
      "$ref": "#/$defs/Budget"
    },
    {
      "$ref": "#/$defs/TraceContext"
    }
  ],
  "$defs": {
    "ProviderId": {
      "enum": [
        "mock",
        "deepseek",
        "openai",
        "kimi",
        "anthropic"
      ]
    },
    "ProtocolId": {
      "enum": [
        "mock",
        "openai_chat_completions",
        "openai_responses",
        "anthropic_messages"
      ]
    },
    "MessageRole": {
      "enum": [
        "system",
        "user",
        "assistant",
        "tool"
      ]
    },
    "ContentPartKind": {
      "enum": [
        "text",
        "image_ref",
        "tool_call",
        "tool_result"
      ]
    },
    "FinishReason": {
      "enum": [
        "stop",
        "length",
        "tool_calls",
        "content_filter",
        "abort"
      ]
    },
    "LlmErrorCode": {
      "enum": [
        "provider_invalid_request",
        "provider_config_invalid",
        "provider_continuation_lost",
        "provider_secret_missing",
        "provider_auth_failed",
        "provider_balance_exhausted",
        "provider_rate_limited",
        "provider_unavailable",
        "provider_connection_failed",
        "provider_timeout",
        "provider_schema_failed",
        "provider_protocol_mismatch",
        "provider_capability_missing",
        "provider_stream_incomplete",
        "budget_exceeded",
        "model_run_cancelled",
        "provider_unknown_error"
      ]
    },
    "CapabilityName": {
      "enum": [
        "text_input",
        "text_output",
        "image_input",
        "streaming",
        "tool_calls",
        "parallel_tool_calls",
        "json_object",
        "json_schema",
        "strict_tool_schema",
        "thinking",
        "reasoning_effort",
        "reasoning_replay",
        "system_message",
        "developer_message",
        "usage_tokens",
        "prompt_cache_usage",
        "provider_request_id",
        "web_search",
        "file_search",
        "embeddings"
      ]
    },
    "ContentPart": {
      "type": "object",
      "required": [
        "kind",
        "value"
      ],
      "properties": {
        "kind": {
          "$ref": "#/$defs/ContentPartKind"
        },
        "value": {},
        "media_type": {
          "type": [
            "string",
            "null"
          ]
        }
      },
      "additionalProperties": false
    },
    "CanonicalMessage": {
      "type": "object",
      "required": [
        "role",
        "parts"
      ],
      "properties": {
        "role": {
          "$ref": "#/$defs/MessageRole"
        },
        "parts": {
          "type": "array",
          "items": {
            "$ref": "#/$defs/ContentPart"
          }
        },
        "tool_call_id": {
          "type": [
            "string",
            "null"
          ]
        }
      },
      "additionalProperties": false
    },
    "ToolDefinition": {
      "type": "object",
      "required": [
        "name",
        "description",
        "parameters"
      ],
      "properties": {
        "name": {
          "type": "string",
          "minLength": 1
        },
        "description": {
          "type": "string"
        },
        "parameters": {
          "type": "object"
        }
      },
      "additionalProperties": false
    },
    "CanonicalToolCall": {
      "type": "object",
      "required": [
        "id",
        "name",
        "arguments"
      ],
      "properties": {
        "id": {
          "type": "string",
          "minLength": 1
        },
        "name": {
          "type": "string",
          "minLength": 1
        },
        "arguments": {
          "type": "object"
        }
      },
      "additionalProperties": false
    },
    "CanonicalUsage": {
      "type": "object",
      "required": [
        "input_tokens",
        "output_tokens"
      ],
      "properties": {
        "input_tokens": {
          "type": "integer",
          "minimum": 0
        },
        "output_tokens": {
          "type": "integer",
          "minimum": 0
        },
        "cache_read_tokens": {
          "type": [
            "integer",
            "null"
          ],
          "minimum": 0
        }
      },
      "additionalProperties": false
    },
    "Budget": {
      "type": "object",
      "required": [
        "max_attempts",
        "max_output_tokens"
      ],
      "properties": {
        "max_attempts": {
          "type": "integer",
          "minimum": 1
        },
        "max_fallbacks": {
          "type": "integer",
          "minimum": 0
        },
        "max_input_tokens": {
          "type": [
            "integer",
            "null"
          ],
          "minimum": 1
        },
        "max_output_tokens": {
          "type": "integer",
          "minimum": 1
        },
        "max_latency_ms": {
          "type": [
            "integer",
            "null"
          ],
          "minimum": 1
        },
        "max_cost_usd": {
          "type": [
            "number",
            "null"
          ],
          "exclusiveMinimum": 0
        }
      },
      "additionalProperties": false
    },
    "TraceContext": {
      "type": "object",
      "required": [
        "correlation_id"
      ],
      "properties": {
        "correlation_id": {
          "type": "string",
          "format": "uuidv7"
        },
        "job_id": {
          "anyOf": [
            {
              "type": "string",
              "format": "uuidv7"
            },
            {
              "type": "null"
            }
          ]
        },
        "stage_run_id": {
          "anyOf": [
            {
              "type": "string",
              "format": "uuidv7"
            },
            {
              "type": "null"
            }
          ]
        }
      },
      "additionalProperties": false
    },
    "GenerationRequest": {
      "type": "object",
      "required": [
        "schema_version",
        "model_run_id",
        "task",
        "messages",
        "model_policy",
        "idempotency_key",
        "budget",
        "trace_context"
      ],
      "properties": {
        "schema_version": {
          "const": 1
        },
        "model_run_id": {
          "type": "string",
          "format": "uuidv7"
        },
        "task": {
          "type": "string",
          "minLength": 1
        },
        "messages": {
          "type": "array",
          "minItems": 1,
          "items": {
            "$ref": "#/$defs/CanonicalMessage"
          }
        },
        "output_schema": {
          "type": [
            "object",
            "null"
          ]
        },
        "tools": {
          "type": "array",
          "items": {
            "$ref": "#/$defs/ToolDefinition"
          }
        },
        "model_policy": {
          "type": "string",
          "minLength": 1
        },
        "idempotency_key": {
          "type": "string",
          "minLength": 1
        },
        "budget": {
          "$ref": "#/$defs/Budget"
        },
        "trace_context": {
          "$ref": "#/$defs/TraceContext"
        }
      },
      "additionalProperties": false
    },
    "GenerationResult": {
      "type": "object",
      "required": [
        "schema_version",
        "model_run_id",
        "provider",
        "protocol",
        "model_id",
        "usage",
        "finish_reason"
      ],
      "properties": {
        "schema_version": {
          "const": 1
        },
        "model_run_id": {
          "type": "string",
          "format": "uuidv7"
        },
        "text": {
          "type": [
            "string",
            "null"
          ]
        },
        "typed_output": {},
        "tool_calls": {
          "type": "array",
          "items": {
            "$ref": "#/$defs/CanonicalToolCall"
          }
        },
        "usage": {
          "$ref": "#/$defs/CanonicalUsage"
        },
        "finish_reason": {
          "$ref": "#/$defs/FinishReason"
        },
        "provider_response_id": {
          "type": [
            "string",
            "null"
          ]
        },
        "provider": {
          "$ref": "#/$defs/ProviderId"
        },
        "protocol": {
          "$ref": "#/$defs/ProtocolId"
        },
        "model_id": {
          "type": "string",
          "minLength": 1
        },
        "model_revision": {
          "type": [
            "string",
            "null"
          ]
        },
        "capability_snapshot": {
          "type": [
            "string",
            "null"
          ]
        }
      },
      "additionalProperties": false
    },
    "CapabilitySet": {
      "type": "object",
      "required": [
        "text_input",
        "text_output",
        "image_input",
        "streaming",
        "tool_calls",
        "parallel_tool_calls",
        "json_object",
        "json_schema",
        "strict_tool_schema",
        "thinking",
        "reasoning_effort",
        "reasoning_replay",
        "system_message",
        "developer_message",
        "usage_tokens",
        "prompt_cache_usage",
        "provider_request_id",
        "web_search",
        "file_search",
        "embeddings"
      ],
      "properties": {
        "text_input": {
          "type": "boolean"
        },
        "text_output": {
          "type": "boolean"
        },
        "image_input": {
          "type": "boolean"
        },
        "streaming": {
          "type": "boolean"
        },
        "tool_calls": {
          "type": "boolean"
        },
        "parallel_tool_calls": {
          "type": "boolean"
        },
        "json_object": {
          "type": "boolean"
        },
        "json_schema": {
          "type": "boolean"
        },
        "strict_tool_schema": {
          "type": "boolean"
        },
        "thinking": {
          "type": "boolean"
        },
        "reasoning_effort": {
          "type": "boolean"
        },
        "reasoning_replay": {
          "type": "boolean"
        },
        "system_message": {
          "type": "boolean"
        },
        "developer_message": {
          "type": "boolean"
        },
        "usage_tokens": {
          "type": "boolean"
        },
        "prompt_cache_usage": {
          "type": "boolean"
        },
        "provider_request_id": {
          "type": "boolean"
        },
        "web_search": {
          "type": "boolean"
        },
        "file_search": {
          "type": "boolean"
        },
        "embeddings": {
          "type": "boolean"
        }
      },
      "additionalProperties": false
    }
  }
}"""
