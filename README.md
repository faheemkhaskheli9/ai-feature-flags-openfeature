# Feature Flag System for AI Applications

> LLM, RAG & Agentic AI portfolio project — independent open-source implementation.
> This is an original, from-scratch build. It is not affiliated with, and does not
> contain any code, prompts, data, or business logic from, any employer or client.

![status](https://img.shields.io/badge/status-in%20progress-yellow)
![python](https://img.shields.io/badge/python-3.10%2B-blue)
![license](https://img.shields.io/badge/license-MIT-green)

## 1. Problem

AI product teams need to toggle prompt versions, providers, models, and experimental features per user segment without redeploying code.

## 2. Architecture

```text
Flag Config Store -> OpenFeature Provider -> Application Code (evaluates flag per request/user segment)
```

## 3. Technology Stack

- Python
- OpenFeature SDK
- FastAPI
- Redis / config store

## 4. Feature List

- OpenFeature-based flag evaluation
- Prompt version flags
- LLM provider/model flags
- RAG toggle flags
- Voice agent feature flags
- Experimental feature rollout by group
- Per-segment targeting rules

## 5. Implementation Plan

1. Phase 1: Flag schema and config store
2. Phase 2: OpenFeature provider implementation
3. Phase 3: Segment targeting rules
4. Phase 4: Admin UI for flag management

## Task Tracking

Work is broken into phase-tagged user stories tracked as GitHub Issues, not in this file. To see what's open:

    gh issue list --repo faheemkhaskheli9/ai-feature-flags-openfeature --state open --label type:user-story

Implement Phase 1 issues first (later phases depend on it). When you start one, add label `status:in-progress`. When you finish, close it referencing the commit (e.g. `git commit -m "... Closes #4"`) and push.

## 6. Repository Structure

```text
ai-feature-flags-openfeature/
├── README.md
├── LICENSE
├── .gitignore
├── pyproject.toml
├── .env.example
├── docker/
├── docs/
│   ├── architecture.md
│   └── evaluation.md
├── src/
├── tests/
├── configs/
├── scripts/
├── notebooks/
├── examples/
├── assets/
└── .github/
    └── workflows/
```

## 7. Setup

```bash
git clone <this-repo-url>
cd ai-feature-flags-openfeature
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt   # or: pip install -e .
cp .env.example .env              # fill in API keys / config
```

## 8. Dataset

Document which public dataset(s) or synthetic data generators are used here.
No proprietary, employer-owned, or client-identifiable data is used in this project.

## 9. Training / Execution

Phase 1 defines the versioned flag schema (`docs/flag_schema.md`) — a
pydantic `FlagDefinition` covering boolean/string/number/object flags, with
`default_value` validated against `type`:

```bash
pip install -r requirements.txt
python -m ai_feature_flags.cli show-examples
python -m ai_feature_flags.cli validate examples/flags/rag_enabled.json
```

## 10. Evaluation

Document evaluation metrics and how to reproduce them here (see `docs/evaluation.md`).

## 11. Results

_To be filled in as the implementation progresses — screenshots, metrics tables, and
sample outputs go here._

## 12. API

_If this project exposes an API, document the main endpoints here (or link to
auto-generated OpenAPI docs, e.g. `/docs` for FastAPI)._

## 13. Docker

```bash
docker build -t ai-feature-flags-openfeature .
docker run -p 8000:8000 ai-feature-flags-openfeature
```

## 14. Tests

```bash
pytest tests/
```

## 15. Limitations

- This is a from-scratch, independent recreation built for portfolio purposes.
- Performance numbers, once added, are based on public datasets and are not
  representative of any production system's real-world results.

## 16. Future Work

- Expand evaluation coverage and add CI-based regression checks.
- Add more configuration presets and deployment targets.
- Track open items as GitHub Issues.

## 17. Disclosure

This repository is an **independent open-source recreation inspired by the kind of
production systems I have worked on professionally**. It contains no employer or
client source code, prompts, datasets, credentials, architecture diagrams, or
business logic. All code, data, and documentation here are original or built on
publicly available datasets and open-source tools.

---
_Last updated: 2026-08-18_
