# Flag definition schema

Every flag is one `FlagDefinition` (`src/ai_feature_flags/schema.py`):

| Field | Type | Notes |
|---|---|---|
| `schema_version` | int | bumped when the shape of `FlagDefinition` changes |
| `key` | str | unique identifier, dot-namespaced (e.g. `rag.enabled`), no whitespace |
| `type` | `boolean` \| `string` \| `number` \| `object` | picks which Python type `default_value` must be |
| `default_value` | matches `type` | validated against `type` at construction time |
| `description` | str | human-readable purpose |
| `owner` | str | team or individual responsible |
| `created_at` / `updated_at` | datetime | `updated_at >= created_at` is enforced |

Flags are a registry keyed by `key` — new flags are added as new
`FlagDefinition` values (data), never as new schema fields (code).

## One example per type

- **boolean** — `rag.enabled`: toggles retrieval-augmented generation for a request.
- **string** — `llm.provider`: which LLM provider backs chat completions (also
  covers prompt-version flags, e.g. `prompt.summarize_version`).
- **number** — `voice_agent.max_turns`: max conversation turns before handoff.
- **object** — `voice_agent.routing_rules`: intent-to-queue routing table.

See `src/ai_feature_flags/examples.py` for the full definitions and
`examples/flags/rag_enabled.json` for one serialized on disk.

## Validating a flag file

```bash
python -m ai_feature_flags.cli validate examples/flags/rag_enabled.json
```
