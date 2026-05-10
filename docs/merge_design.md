# Merge / Concept 分流设计

## 目标

本设计服务赛题的“跨教材知识图谱整合”评分点：系统必须能展示重复识别、整合决策、执行结果与可复现审计链。v1 将概念抽取与合并执行拆开，避免抽取阶段静默覆盖或静默合并。

## 目录

```text
data/vault/
├── concepts/                         # active concepts only
│   ├── 细胞膜.md
│   └── 细胞膜__doc_x__ch_y__1.md
├── decisions/merge/                  # merge decision audit objects
│   └── merge_same_name_细胞膜.md
└── archive/concepts/{decision_id}/   # archived pre-merge concepts
    └── 细胞膜__doc_x__ch_y__1.md
```

`GraphBuilder` 只扫描 `concepts/` 下 `status != archived` 的页面。`archive/` 与 `decisions/` 永不进入图谱。

## Concept Schema

抽取流程只保留事实，不判断等价性：

```yaml
---
id: concept_细胞膜__doc_x__ch_y__1
canonical_name: 细胞膜
status: active
category: 核心概念
aliases: []
merge_decisions:
  - merge_same_name_细胞膜
sources:
  - textbook_id: doc_x
    chapter_id: ch_y
    definition: ...
    evidence: ...
---
```

写入规则：

- 首个同名 active concept 写入 `concepts/{safe_name}.md`。
- 后续同名 active concept 写入 `concepts/{safe_name}__{textbook_id}__{chapter_id}__{n}.md`。
- 同名冲突创建或更新 `candidate` decision，不覆盖旧节点。

## Decision Schema

Decision 文件路径：`data/vault/decisions/merge/{decision_id}.md`。

```yaml
---
decision_id: merge_same_name_细胞膜
status: candidate
trigger: same_name
method: deterministic_same_name
affected_nodes:
  - concepts/细胞膜.md
  - concepts/细胞膜__doc_x__ch_y__1.md
result_name: 细胞膜
result_node: concepts/细胞膜.md
reason_summary: Same canonical_name: 细胞膜
created_at: "2026-05-10T00:00:00+00:00"
updated_at: "2026-05-10T00:00:00+00:00"
---
```

状态机：

```text
candidate -> applied
candidate -> failed
failed    -> candidate   # scan 可重新补全候选
```

body 必须包含：

- 合并前节点 wikilink 列表
- 决策原因
- scan 阶段记录
- execute 阶段记录
- 失败原因（若有）

## API

### `POST /api/merge/scan`

v1 内置 deterministic same-name scan。扫描 active concepts，按 `canonical_name` 分组，发现同名多节点则创建或更新 candidate。

返回：

```json
{
  "decisions": [
    {
      "decision_id": "merge_same_name_细胞膜",
      "status": "candidate",
      "affected_nodes": ["concepts/细胞膜.md", "concepts/细胞膜__doc_x__ch_y__1.md"],
      "result_name": "细胞膜"
    }
  ]
}
```

### `POST /api/merge/decisions`

供外部 GPT/Codex scanner 写入 candidate。调用方提供 `affected_nodes`、`result_name`、`reason_summary`，可附加 reasoning markdown。后端只校验路径存在与字段格式。

### `GET /api/merge/decisions`

支持 `?status=candidate|applied|failed`。

### `GET /api/merge/decisions/{decision_id}`

返回 `frontmatter`、`content_md`、`wikilinks`。

### `POST /api/merge/execute`

请求最小结构：

```json
{
  "decision_id": "merge_same_name_细胞膜",
  "affected_nodes": ["concepts/细胞膜.md", "concepts/细胞膜__doc_x__ch_y__1.md"],
  "result_name": "细胞膜",
  "frontmatter": {"category": "核心概念", "aliases": []},
  "body": "# 细胞膜\n\n综合定义...\n\n## 关系\n\n- 包含: [[脂质双层]]\n"
}
```

约束：

- 缺字段或格式不合法：`422`，不移动文件。
- `result_name` 对应路径已存在且不在 `affected_nodes`：`409`。
- 成功：写 merged node，归档旧节点，重写 active vault wikilink，decision 更新为 `applied`。

## 链接重写

只重写 active 内容：

- `concepts/`
- `textbooks/`

不重写：

- `archive/`
- `decisions/`

规则：

- `[[旧节点]]` -> `[[新节点]]`
- `[[旧节点|显示名]]` -> `[[新节点|显示名]]`

这里的“节点”使用概念文件 stem，例如 `细胞膜__doc_x__ch_y__1`。

## v1 边界

- 不内置 LLM synthesis；execute payload 由外部调用方提供。
- 不内置 GPT/Codex semantic scanner；外部 scanner 通过 `POST /api/merge/decisions` 写入候选。
- 不做前端 UI，只提供 API 与前端 handoff 文档。
