"""One example FlagDefinition per flag type, covering the project's use cases."""

from __future__ import annotations

from datetime import datetime, timezone

from ai_feature_flags.schema import FlagDefinition, FlagType

_TS = datetime(2025, 1, 1, tzinfo=timezone.utc)


def example_flags() -> list[FlagDefinition]:
    return [
        FlagDefinition(
            key="rag.enabled",
            type=FlagType.BOOLEAN,
            default_value=False,
            description="Toggle retrieval-augmented generation on for a request.",
            owner="platform-ai",
            created_at=_TS,
            updated_at=_TS,
        ),
        FlagDefinition(
            key="llm.provider",
            type=FlagType.STRING,
            default_value="anthropic",
            description="Which LLM provider backs chat completions.",
            owner="platform-ai",
            created_at=_TS,
            updated_at=_TS,
        ),
        FlagDefinition(
            key="prompt.summarize_version",
            type=FlagType.STRING,
            default_value="v3",
            description="Which prompt template version the summarization endpoint uses.",
            owner="prompt-eng",
            created_at=_TS,
            updated_at=_TS,
        ),
        FlagDefinition(
            key="voice_agent.max_turns",
            type=FlagType.NUMBER,
            default_value=12,
            description="Maximum conversation turns before the voice agent hands off to a human.",
            owner="voice-team",
            created_at=_TS,
            updated_at=_TS,
        ),
        FlagDefinition(
            key="voice_agent.routing_rules",
            type=FlagType.OBJECT,
            default_value={"default": "general_queue", "billing": "billing_queue"},
            description="Intent-to-queue routing table for the voice agent.",
            owner="voice-team",
            created_at=_TS,
            updated_at=_TS,
        ),
    ]
