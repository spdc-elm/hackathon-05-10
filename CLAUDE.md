# CLAUDE.md

## Project Philosophy: 万物皆MD (Everything-is-Markdown)

This is an alternative approach to the AI hackathon knowledge integration project. Instead of storing knowledge graphs as JSON schemas, we store everything as Obsidian-flavored Markdown files with `[[wikilinks]]`. The knowledge graph is derived automatically from link topology.

Core principle: **The vault IS the knowledge base.** It's human-readable, Obsidian-compatible, and git-friendly.

## Architecture

```
PDF upload → PyMuPDF parse → ParsedDocument (JSON)
                                    ↓
                          LLM extraction per chapter
                                    ↓
                    Concepts as MD files in data/vault/concepts/
                    (YAML frontmatter + [[wikilinks]])
                                    ↓
                    Graph = scan all [[links]] across vault
                                    ↓
                    Frontend: Cytoscape graph + MD page viewer
```

## Module Layout

```
src/backend/
├── main.py                    FastAPI server
└── app/
    ├── core/config.py         Settings from .env
    ├── parsers/               PDF/MD/TXT → ParsedDocument
    ├── services/
    │   ├── llm.py             OpenAI-compatible LLM adapter
    │   ├── vault.py           Vault CRUD + wikilink scanning
    │   ├── concept_writer.py  LLM output → concept MD files
    │   └── graph_builder.py   Derive GraphView from vault links
    └── storage/repository.py  Document metadata persistence

src/frontend/                  React + Vite + TypeScript + Cytoscape
```

## Development Commands

```bash
# Backend
cd src/backend && uvicorn main:app --reload --port 8000

# Frontend
cd src/frontend && npm run dev

# Both (convenience)
./scripts/dev.sh

# Tests
pytest tests/ -v
```

## Conventions

- Backend: Python 3.11+, type hints everywhere, async FastAPI endpoints
- Frontend: React 19, TypeScript strict, Vite 7
- Tests: pytest, no network calls, FakeLLMClient for LLM tests
- Storage: filesystem MD/JSON under `data/` (gitignored)
- API: JSON envelope with `content_md` field for markdown content
- Vault: YAML frontmatter + Obsidian `[[wikilinks]]` in markdown body

## Key Design Decisions

1. Graph is ephemeral: derived on-demand from vault scan, never stored separately
2. Each concept = one MD file in `data/vault/concepts/`
3. Relation types encoded as structured lines in `## 关系` section
4. Frontend receives same `GraphView` schema as before — Cytoscape code reused
5. Clicking a node shows the raw concept MD rendered with react-markdown
