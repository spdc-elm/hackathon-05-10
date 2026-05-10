# AGENTS.md

## Prime Directive: Contest Rubric First

The primary project compass is `docs/contest/第一届AI全栈黑客松赛题.md`,
especially Section 5 scoring criteria. Before planning or implementing work,
map the change to the contest rubric and acceptance path.

Prioritize, in order:

1. P0 feature completeness and demo reliability.
2. Scored differentiators: graph interaction/frequency, cross-textbook merge
   decisions, 30% compression evidence, architecture reasoning, reproducibility.
3. Engineering polish only when it protects the demo or earns rubric points.

Do not spend effort on elegant but unscored abstractions while a scored
requirement is missing or fragile.

RAG exception: the RAG module may use our own design ideas instead of blindly
following the suggested baseline pipeline. Even then, it must preserve the
contest-critical contract: grounded answers, explicit citations, inspectable
sources, and a documented rationale/evaluation story.

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

## SSOT: Concept Vault Schema

This section is the canonical schema for concept markdown pages. If code, API docs,
or architecture docs disagree with this section, this section wins.

### Identity

- Concept identity is the normalized concept name.
- Same normalized `name` means the same concept.
- Concept path: `data/vault/concepts/{safe_name}.md`.
- Stable node id: `concept_{safe_name}`. It is independent of textbook, chapter, and extraction order.
- `safe_name` currently preserves Unicode and replaces `/` and `\` with `_`.

### Frontmatter

```yaml
---
id: concept_细胞膜
category: 核心概念
aliases:
  - 质膜
  - cell membrane
sources:
  - textbook_id: doc_abc123
    chapter_id: ch_001
    page_start: 12
    page_end: 18
    definition: 细胞膜是细胞与环境的界面。
    evidence: 细胞膜是细胞与环境的界面...
  - textbook_id: doc_xyz789
    chapter_id: ch_003
    page_start: 44
    page_end: 49
    definition: 质膜由磷脂双分子层构成。
    evidence: 质膜由磷脂双分子层构成...
---
```

Required fields:

- `id`: stable id, always `concept_{safe_name}`.
- `category`: current representative category.
- `aliases`: deduplicated aliases across all sources.
- `sources`: all chapter-level source records for this concept.

Optional source fields:

- `page_start`, `page_end`: preserve citation coordinates when parser provides them.
- `definition`: raw extracted definition from that source.
- `evidence`: direct source quote or short continuous excerpt.

### Parse-Time Merge Rules

When extraction emits a concept whose path already exists, do not overwrite the
page. Merge it.

- Preserve existing `id`.
- Append a new `sources[]` entry for a new `(textbook_id, chapter_id)` source.
- If the same `(textbook_id, chapter_id)` is extracted again, replace that source entry instead of duplicating it. This keeps re-runs idempotent.
- Merge `aliases` by ordered set union.
- Preserve existing `category`; if missing, use the incoming category.
- Merge relation lines by `(relation_type, target)` and keep one graph edge per pair.
- Preserve raw definitions/evidence per source. Do not synthesize or rewrite the canonical content during parse-time merge.

### Content Merge Worker

Parse-time merge is deliberately lossless and shallow. A later content-merge
worker may read `sources[]` and the body, then write a synthesized definition,
deduplicate explanations, and emit integration decisions.

The worker must not delete source records. It may add derived fields such as
`merge_status`, `merge_decision_id`, or a synthesized `## 综合定义` section, but
`sources[]` remains the audit trail.

### Frequency Statistics

Frequency must be derived from `sources[]`, not guessed from filenames.

- `occurrence_count`: `len(sources)`, chapter-level occurrences.
- `document_frequency`: count of distinct `textbook_id` values in `sources`.
- `chapter_frequency`: count of distinct `(textbook_id, chapter_id)` pairs.
- Existing `GraphViewNode.source_count` should map to `occurrence_count` for compatibility.
- `GraphViewNode.source_documents` should list distinct textbook ids.
- `GraphViewNode.color_key` must be source-based, not category-based:
  - single source document: `color_key = textbook_id`
  - multiple source documents: `color_key = merged`
- Node size or color depth should primarily reflect `document_frequency`, because the contest requirement concerns repeated appearance across multiple textbooks. `occurrence_count` may be shown in detail panels.

This distinction matters: one concept repeated in five chapters of one book is
not the same signal as one concept appearing in five different books.
