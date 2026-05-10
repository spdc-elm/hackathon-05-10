# Frontend Merge Handoff

v1 后端已提供 merge decision API；前端暂不实现 UI。本文件定义后续前端应接入的最小体验，便于演示赛题“整合决策列表”和“可审计合并”。

## 入口

在 graph 视图 toolbar 增加一个手动入口：

- `Scan merges`：调用 `POST /api/merge/scan`
- 扫描后打开 decision 列表，默认筛选 `candidate`

## Decision 列表

数据源：`GET /api/merge/decisions?status=candidate`

列表字段：

- `decision_id`
- `status`
- `method`
- `result_name`
- `affected_nodes.length`
- `reason_summary`
- `updated_at`

候选按 `updated_at` 降序，`failed` 可单独筛选以便修复。

## Decision 详情

数据源：`GET /api/merge/decisions/{decision_id}`

详情区展示：

- frontmatter 摘要
- `content_md` 渲染结果
- `affected_nodes` 中每个概念的跳转入口
- `result_node` 或 `result_name`

decision body 中的 wikilink 仍保持审计原貌，点击时应走现有 node detail 逻辑；若旧节点已归档，可提示“archived”而非静默失败。

## Merged 节点跳转

`GET /api/graph/nodes/{name}` 的 node detail 会暴露：

- `merge_decision`
- `merged_from`

当存在 `merge_decision` 时，详情面板显示一个轻量入口，跳转到对应 decision 详情。

## Execute Handoff

v1 不要求前端生成合并正文。若后续接入，可将 execute 表单设计为人工/外部 agent 提供：

- `decision_id`
- `affected_nodes`
- `result_name`
- merged concept `frontmatter`
- merged concept `body`

提交 `POST /api/merge/execute`。若返回 `409`，前端提示调用方把冲突节点纳入本次 merge；若返回 `422`，展示后端 detail 并保留 candidate。
