"""Merge decision audit objects and merge execution for vault concepts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.services.vault import VaultPage, VaultService, WIKILINK_RE


VALID_DECISION_STATUSES = {"candidate", "applied", "failed"}
VALID_TRIGGERS = {"same_name", "manual_scan", "external_scan"}
VALID_METHODS = {"deterministic_same_name", "codex_gpt_scan", "manual"}


class MergeValidationError(ValueError):
    """Raised when a merge request is structurally invalid."""


class MergeConflictError(RuntimeError):
    """Raised when a merge result path would overwrite an unrelated node."""


class MergeNotFoundError(FileNotFoundError):
    """Raised when a requested merge decision does not exist."""


@dataclass(frozen=True)
class DecisionSummary:
    decision_id: str
    status: str
    trigger: str
    method: str
    affected_nodes: list[str]
    result_name: str
    result_node: str
    reason_summary: str
    created_at: str
    updated_at: str
    path: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "status": self.status,
            "trigger": self.trigger,
            "method": self.method,
            "affected_nodes": self.affected_nodes,
            "result_name": self.result_name,
            "result_node": self.result_node,
            "reason_summary": self.reason_summary,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "path": self.path,
        }


class MergeService:
    """Manage merge decision files and apply approved concept merges."""

    def __init__(self, vault: VaultService) -> None:
        self.vault = vault
        self.vault.ensure_structure()

    def scan_same_name_candidates(self) -> list[DecisionSummary]:
        """Create or update deterministic candidates for active same-name concepts."""
        groups: dict[str, list[VaultPage]] = {}
        for page in self.active_concept_pages():
            canonical_name = self.canonical_name(page)
            groups.setdefault(canonical_name, []).append(page)

        decisions: list[DecisionSummary] = []
        for canonical_name, pages in sorted(groups.items()):
            if len(pages) < 2:
                continue
            affected_nodes = [page.path for page in pages]
            decisions.append(
                self.create_or_update_candidate(
                    affected_nodes=affected_nodes,
                    result_name=canonical_name,
                    reason_summary=f"Same canonical_name: {canonical_name}",
                    trigger="same_name",
                    method="deterministic_same_name",
                    decision_id=self.same_name_decision_id(canonical_name),
                    reasoning_md=(
                        f"Deterministic same-name scan found {len(pages)} active nodes "
                        f"with canonical_name `{canonical_name}`."
                    ),
                )
            )
        return decisions

    def create_or_update_candidate(
        self,
        *,
        affected_nodes: list[str],
        result_name: str,
        reason_summary: str,
        trigger: str = "external_scan",
        method: str = "manual",
        decision_id: str | None = None,
        reasoning_md: str = "",
    ) -> DecisionSummary:
        result_name = str(result_name or "").strip()
        reason_summary = str(reason_summary or "").strip()
        if not result_name:
            raise MergeValidationError("result_name is required.")
        if not reason_summary:
            raise MergeValidationError("reason_summary is required.")
        if trigger not in VALID_TRIGGERS:
            raise MergeValidationError("trigger is invalid.")
        if method not in VALID_METHODS:
            raise MergeValidationError("method is invalid.")

        normalized_nodes = self._validate_affected_nodes(affected_nodes)
        if len(normalized_nodes) < 2:
            raise MergeValidationError("affected_nodes must contain at least two concept paths.")

        if decision_id is None:
            decision_id = f"merge_manual_{safe_name(result_name)}"
        decision_id = self._validate_decision_id(decision_id)
        decision_path = self._decision_path(decision_id)
        existing = self._read_decision_or_none(decision_id)
        now = now_iso()
        created_at = existing.frontmatter.get("created_at", now) if existing else now
        result_node = f"concepts/{safe_name(result_name)}.md"

        frontmatter = {
            "decision_id": decision_id,
            "status": "candidate",
            "trigger": trigger,
            "method": method,
            "affected_nodes": normalized_nodes,
            "result_name": result_name,
            "result_node": result_node,
            "reason_summary": reason_summary,
            "created_at": created_at,
            "updated_at": now,
        }
        body = self._render_candidate_body(
            decision_id=decision_id,
            affected_nodes=normalized_nodes,
            result_name=result_name,
            reason_summary=reason_summary,
            reasoning_md=reasoning_md,
        )
        self.vault.write_page(decision_path, frontmatter, body)
        self._attach_decision_to_concepts(decision_id, normalized_nodes)
        return self._summary_from_frontmatter(decision_path, frontmatter)

    def list_decisions(self, status: str | None = None) -> list[DecisionSummary]:
        if status is not None and status not in VALID_DECISION_STATUSES:
            raise MergeValidationError("status is invalid.")

        decisions_dir = self.vault.root / "decisions" / "merge"
        if not decisions_dir.exists():
            return []

        decisions: list[DecisionSummary] = []
        for md_file in sorted(decisions_dir.glob("*.md")):
            page = self.vault.read_page(str(md_file.relative_to(self.vault.root)))
            if status is not None and page.frontmatter.get("status") != status:
                continue
            decisions.append(self._summary_from_page(page))

        return sorted(decisions, key=lambda item: item.updated_at, reverse=True)

    def read_decision(self, decision_id: str) -> VaultPage:
        decision_id = self._validate_decision_id(decision_id)
        try:
            return self.vault.read_page(self._decision_path(decision_id))
        except FileNotFoundError as exc:
            raise MergeNotFoundError(f"Merge decision not found: {decision_id}") from exc

    def execute_merge(
        self,
        *,
        decision_id: str,
        affected_nodes: list[str],
        result_name: str,
        frontmatter: dict[str, Any],
        body: str,
    ) -> DecisionSummary:
        decision = self.read_decision(decision_id)
        if decision.frontmatter.get("status") == "applied":
            raise MergeValidationError("decision is already applied.")

        result_name = str(result_name or "").strip()
        if not result_name:
            raise MergeValidationError("result_name is required.")
        if not isinstance(frontmatter, dict):
            raise MergeValidationError("frontmatter must be an object.")
        if not isinstance(body, str) or not body.strip():
            raise MergeValidationError("body is required.")

        normalized_nodes = self._validate_affected_nodes(affected_nodes)
        result_path = f"concepts/{safe_name(result_name)}.md"
        result_full_path = self.vault.root / result_path
        if result_full_path.exists() and result_path not in normalized_nodes:
            raise MergeConflictError(
                "result path already exists and is not included in affected_nodes."
            )

        old_pages = [self.vault.read_page(path) for path in normalized_nodes]

        for page in old_pages:
            archive_path = f"archive/concepts/{decision_id}/{Path(page.path).name}"
            archived_frontmatter = {
                **page.frontmatter,
                "status": "archived",
                "archived_from": page.path,
                "merged_into": result_path,
                "merge_decision": decision_id,
            }
            self.vault.write_page(archive_path, archived_frontmatter, page.body)
            (self.vault.root / page.path).unlink(missing_ok=True)

        merged_frontmatter = self._build_merged_frontmatter(
            provided=frontmatter,
            result_name=result_name,
            result_path=result_path,
            decision_id=decision_id,
            affected_nodes=normalized_nodes,
            old_pages=old_pages,
        )
        self.vault.write_page(result_path, merged_frontmatter, body)

        old_to_new = {
            Path(path).stem: Path(result_path).stem
            for path in normalized_nodes
            if Path(path).stem != Path(result_path).stem
        }
        if old_to_new:
            self._rewrite_active_wikilinks(old_to_new)

        now = now_iso()
        applied_frontmatter = {
            **decision.frontmatter,
            "status": "applied",
            "affected_nodes": normalized_nodes,
            "result_name": result_name,
            "result_node": result_path,
            "updated_at": now,
        }
        applied_body = self._append_execute_record(
            decision.body,
            affected_nodes=normalized_nodes,
            result_node=result_path,
            archived_nodes=[
                f"archive/concepts/{decision_id}/{Path(path).name}"
                for path in normalized_nodes
            ],
        )
        self.vault.write_page(self._decision_path(decision_id), applied_frontmatter, applied_body)
        return self._summary_from_frontmatter(self._decision_path(decision_id), applied_frontmatter)

    def active_concept_pages(self) -> list[VaultPage]:
        concepts_dir = self.vault.root / "concepts"
        if not concepts_dir.exists():
            return []

        pages: list[VaultPage] = []
        for md_file in sorted(concepts_dir.rglob("*.md")):
            relative = str(md_file.relative_to(self.vault.root))
            page = self.vault.read_page(relative)
            if page.frontmatter.get("status") == "archived":
                continue
            pages.append(page)
        return pages

    def canonical_name(self, page: VaultPage) -> str:
        value = str(page.frontmatter.get("canonical_name") or "").strip()
        if value:
            return value
        return Path(page.path).stem.split("__", 1)[0]

    def same_name_decision_id(self, canonical_name: str) -> str:
        return f"merge_same_name_{safe_name(canonical_name)}"

    def _validate_affected_nodes(self, affected_nodes: list[str]) -> list[str]:
        if not isinstance(affected_nodes, list):
            raise MergeValidationError("affected_nodes must be a list.")

        normalized: list[str] = []
        seen: set[str] = set()
        for raw_path in affected_nodes:
            path = str(raw_path or "").strip()
            if not path.startswith("concepts/") or not path.endswith(".md"):
                raise MergeValidationError("affected_nodes must contain concept .md paths.")
            if ".." in Path(path).parts:
                raise MergeValidationError("affected_nodes cannot contain parent traversal.")
            if path in seen:
                continue
            page = self.vault.read_page(path)
            if page.frontmatter.get("status") == "archived":
                raise MergeValidationError("affected_nodes cannot include archived concepts.")
            normalized.append(path)
            seen.add(path)

        return normalized

    def _attach_decision_to_concepts(self, decision_id: str, affected_nodes: list[str]) -> None:
        for path in affected_nodes:
            page = self.vault.read_page(path)
            decisions = [
                str(item)
                for item in page.frontmatter.get("merge_decisions", [])
                if str(item).strip()
            ]
            if decision_id not in decisions:
                decisions.append(decision_id)
            self.vault.write_page(path, {**page.frontmatter, "merge_decisions": decisions}, page.body)

    def _build_merged_frontmatter(
        self,
        *,
        provided: dict[str, Any],
        result_name: str,
        result_path: str,
        decision_id: str,
        affected_nodes: list[str],
        old_pages: list[VaultPage],
    ) -> dict[str, Any]:
        merged = dict(provided)
        if "category" not in merged:
            merged["category"] = next(
                (
                    page.frontmatter.get("category")
                    for page in old_pages
                    if page.frontmatter.get("category")
                ),
                "核心概念",
            )
        if "aliases" not in merged:
            merged["aliases"] = self._ordered_union(
                alias
                for page in old_pages
                for alias in page.frontmatter.get("aliases", [])
            )
        if "sources" not in merged:
            merged["sources"] = self._aggregate_sources(old_pages)

        merge_decisions = [
            str(item)
            for item in merged.get("merge_decisions", [])
            if str(item).strip()
        ]
        if decision_id not in merge_decisions:
            merge_decisions.append(decision_id)

        merged.update({
            "id": f"concept_{Path(result_path).stem}",
            "canonical_name": result_name,
            "status": "active",
            "merged_from": affected_nodes,
            "merge_decision": decision_id,
            "merge_decisions": merge_decisions,
        })
        return merged

    def _aggregate_sources(self, pages: list[VaultPage]) -> list[dict[str, Any]]:
        sources: list[dict[str, Any]] = []
        seen: set[tuple[str, str, str]] = set()
        for page in pages:
            raw_sources = page.frontmatter.get("sources")
            if isinstance(raw_sources, list):
                page_sources = [item for item in raw_sources if isinstance(item, dict)]
            else:
                page_sources = [{
                    "textbook_id": page.frontmatter.get("textbook_id", ""),
                    "chapter_id": page.frontmatter.get("chapter_id", ""),
                }]
            for source in page_sources:
                key = (
                    str(source.get("textbook_id") or ""),
                    str(source.get("chapter_id") or ""),
                    str(source.get("evidence") or ""),
                )
                if key in seen:
                    continue
                sources.append(dict(source))
                seen.add(key)
        return sources

    def _rewrite_active_wikilinks(self, old_to_new: dict[str, str]) -> None:
        for subdir in ("concepts", "textbooks"):
            base = self.vault.root / subdir
            if not base.exists():
                continue
            for md_file in base.rglob("*.md"):
                content = md_file.read_text(encoding="utf-8")
                rewritten = WIKILINK_RE.sub(
                    lambda match: rewrite_wikilink_match(match.group(1), old_to_new),
                    content,
                )
                if rewritten != content:
                    md_file.write_text(rewritten, encoding="utf-8")

    def _render_candidate_body(
        self,
        *,
        decision_id: str,
        affected_nodes: list[str],
        result_name: str,
        reason_summary: str,
        reasoning_md: str,
    ) -> str:
        node_links = "\n".join(
            f"- [[{Path(path).stem}]] (`{path}`)" for path in affected_nodes
        )
        return (
            f"# Merge decision: {result_name}\n\n"
            "## Affected Nodes\n\n"
            f"{node_links}\n\n"
            "## Reason\n\n"
            f"{reason_summary}\n\n"
            "## Scan Record\n\n"
            f"Decision `{decision_id}` is currently a merge candidate.\n\n"
            f"{reasoning_md.strip()}\n\n"
            "## Execute Record\n\n"
            "Not executed yet.\n"
        )

    def _append_execute_record(
        self,
        body: str,
        *,
        affected_nodes: list[str],
        result_node: str,
        archived_nodes: list[str],
    ) -> str:
        affected_lines = "\n".join(f"- `{path}`" for path in affected_nodes)
        archive_lines = "\n".join(f"- `{path}`" for path in archived_nodes)
        return (
            f"{body.rstrip()}\n\n"
            "## Execute Applied\n\n"
            f"- Applied at: {now_iso()}\n"
            f"- Result node: `{result_node}`\n\n"
            "Affected nodes:\n"
            f"{affected_lines}\n\n"
            "Archived nodes:\n"
            f"{archive_lines}\n"
        )

    def _summary_from_page(self, page: VaultPage) -> DecisionSummary:
        return self._summary_from_frontmatter(page.path, page.frontmatter)

    def _summary_from_frontmatter(self, path: str, frontmatter: dict[str, Any]) -> DecisionSummary:
        return DecisionSummary(
            decision_id=str(frontmatter.get("decision_id") or Path(path).stem),
            status=str(frontmatter.get("status") or ""),
            trigger=str(frontmatter.get("trigger") or ""),
            method=str(frontmatter.get("method") or ""),
            affected_nodes=[
                str(item)
                for item in frontmatter.get("affected_nodes", [])
                if str(item).strip()
            ],
            result_name=str(frontmatter.get("result_name") or ""),
            result_node=str(frontmatter.get("result_node") or ""),
            reason_summary=str(frontmatter.get("reason_summary") or ""),
            created_at=str(frontmatter.get("created_at") or ""),
            updated_at=str(frontmatter.get("updated_at") or ""),
            path=path,
        )

    def _read_decision_or_none(self, decision_id: str) -> VaultPage | None:
        try:
            return self.read_decision(decision_id)
        except MergeNotFoundError:
            return None

    def _decision_path(self, decision_id: str) -> str:
        return f"decisions/merge/{decision_id}.md"

    def _validate_decision_id(self, decision_id: str) -> str:
        decision_id = str(decision_id or "").strip()
        if not decision_id:
            raise MergeValidationError("decision_id is required.")
        if "/" in decision_id or "\\" in decision_id or ".." in decision_id:
            raise MergeValidationError("decision_id cannot contain path separators.")
        return decision_id

    def _ordered_union(self, values: Any) -> list[str]:
        result: list[str] = []
        seen: set[str] = set()
        for value in values:
            item = str(value or "").strip()
            if not item or item in seen:
                continue
            result.append(item)
            seen.add(item)
        return result


def safe_name(value: str) -> str:
    return str(value).strip().replace("/", "_").replace("\\", "_")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def rewrite_wikilink_match(inner: str, old_to_new: dict[str, str]) -> str:
    if "|" in inner:
        target, label = inner.split("|", 1)
        target_key = target.strip()
        new_target = old_to_new.get(target_key)
        if new_target is None:
            return f"[[{inner}]]"
        return f"[[{new_target}|{label.strip()}]]"

    target_key = inner.strip()
    new_target = old_to_new.get(target_key)
    if new_target is None:
        return f"[[{inner}]]"
    return f"[[{new_target}]]"
