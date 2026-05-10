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
                    Concepts as active MD files in data/vault/concepts/
                    (YAML frontmatter + [[wikilinks]])
                                    ↓
                    Merge candidates/decisions in data/vault/decisions/merge/
                                    ↓
                    Graph = scan active concept [[links]] only
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

1. Graph is ephemeral: derived on-demand from active concept pages, never stored separately
2. Extraction is lossless: same-name concepts remain separate active files until a merge decision is executed
3. Merge decisions are first-class Markdown audit objects under `data/vault/decisions/merge/`
4. Relation types are encoded as structured lines in `## 关系` section
5. Frontend receives the same `GraphView` schema as before — Cytoscape code reused
6. Clicking a node shows the raw concept MD rendered with react-markdown

## SSOT: Concept Vault Schema

This section is the canonical schema for concept markdown pages. If code, API docs,
or architecture docs disagree with this section, this section wins.

### Identity

- Concept identity is the concept file path, not only the normalized concept name.
- `canonical_name` stores the normalized/original concept name emitted by extraction.
- Same `canonical_name` means "merge candidate", not "safe to merge automatically".
- First concept path: `data/vault/concepts/{safe_name}.md`.
- Same-name follow-up path: `data/vault/concepts/{safe_name}__{textbook_id}__{chapter_id}__{n}.md`.
- Stable node id: `concept_{path_stem}`. It is independent of extraction order.
- `safe_name` currently preserves Unicode and replaces `/` and `\` with `_`.

### Frontmatter

```yaml
---
id: concept_细胞膜
canonical_name: 细胞膜
status: active
category: 核心概念
aliases:
  - 质膜
  - cell membrane
merge_decisions:
  - merge_same_name_细胞膜
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

- `id`: stable id, always `concept_{path_stem}`.
- `canonical_name`: concept name used for same-name grouping and display.
- `status`: `active` for graph/search-visible concepts; `archived` after merge execution.
- `category`: current representative category.
- `aliases`: aliases for this concept page.
- `sources`: chapter-level source records for this concept page.
- `merge_decisions`: decision ids that mention this concept.

Optional source fields:

- `page_start`, `page_end`: preserve citation coordinates when parser provides them.
- `definition`: raw extracted definition from that source.
- `evidence`: direct source quote or short continuous excerpt.

### Parse-Time Concept Rules

When extraction emits a concept, do not overwrite an existing active concept and
do not merge definitions at parse time.

- If `concepts/{safe_name}.md` does not exist as an active concept, create it.
- If an active concept with the same `canonical_name` exists, write the new page
  as `concepts/{safe_name}__{textbook_id}__{chapter_id}__{n}.md`.
- The new page keeps its own `sources[]`, relations, evidence, and aliases.
- Same-name collisions create or update a merge decision candidate.
- Reruns may produce additional suffixed pages; v1 prioritizes auditability over
  aggressive idempotent collapse.

### Merge Decisions

Merge decisions live at `data/vault/decisions/merge/{decision_id}.md`. A single
decision file moves through `candidate -> applied | failed`.

Required decision frontmatter:

- `decision_id`
- `status`: `candidate`, `applied`, or `failed`
- `trigger`: `same_name`, `manual_scan`, or `external_scan`
- `method`: `deterministic_same_name`, `codex_gpt_scan`, or `manual`
- `affected_nodes`: active concept paths before execution
- `result_name`
- `result_node`
- `reason_summary`
- `created_at`, `updated_at`

Decision body must keep merge-before wikilinks, scan notes, execute notes, and
failure reason when applicable. Execute updates the same decision file; it does
not create a second audit object.

### Merge Execution

The merge API is an executor, not a judge. It only runs after a candidate has
already decided that nodes should merge.

- Successful execution writes `concepts/{safe_result_name}.md`.
- The merged node frontmatter includes `canonical_name`, `status: active`,
  `merged_from`, and `merge_decision`.
- Old nodes move to `archive/concepts/{decision_id}/{old_filename}.md`.
- Archived nodes are marked with `status: archived`, `archived_from`,
  `merged_into`, and `merge_decision`.
- Active vault content such as `concepts/` and `textbooks/` has wikilinks
  rewritten from old node names to the merged node name.
- `archive/` and `decisions/` are not rewritten; they preserve audit history.
- `[[old]]` becomes `[[new]]`; `[[old|label]]` becomes `[[new|label]]`.

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

Archived concepts, decision files, and archive files must not appear in graph or
search results.
