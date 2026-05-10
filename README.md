# LLM Wiki Knowledge Integrator

一个面向“学科知识整合智能体”赛题的全栈原型。核心思路是 **万物皆 Markdown**：教材章节、概念节点、关系与 merge decision 都落在 Obsidian-compatible vault 中，知识图谱从 `[[wikilinks]]` 实时派生。

## 当前实现范围

- PDF / Markdown / TXT 上传与解析
- LLM 章节级知识点抽取
- Concept Markdown vault 写入
- Cytoscape 知识图谱可视化、缩放拖拽、节点详情、搜索
- 同名 concept 保留多节点并生成 merge candidate
- Merge decision 列表、详情、审计文件与执行 API
- 报告与架构文档

未实现：RAG 问答、教师多轮对话、完整 7 本教材整合执行。

## 环境依赖

- Python 3.11+
- Node.js 20+
- npm

## 安装

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cd src/frontend
npm install
cd ../..
```

## 配置

复制环境变量模板：

```bash
cp .env.example .env
```

需要配置 OpenAI-compatible LLM：

```env
LLM_BASE_URL=https://your-compatible-endpoint/v1
LLM_API_KEY=your-key
LLM_MODEL=your-model
```

运行数据默认写入：

- `data/runtime`
- `data/vault`

这些目录已被 `.gitignore` 排除，不会提交教材或运行缓存。

## 启动

一键启动前后端：

```bash
./scripts/dev.sh
```

默认地址：

- Backend: `http://localhost:8000`
- Frontend: `http://localhost:5173`

也可分别启动：

```bash
cd src/backend
uvicorn main:app --reload --port 8000
```

```bash
cd src/frontend
npm run dev
```

## Docker / ModelScope 创空间

仓库根目录提供 `Dockerfile`，会先构建 Vite 前端，再由 FastAPI 托管静态页面与 `/api/*` 接口。容器默认监听 `7860`：

```bash
docker build -t hackathon-05-10 .
docker run --rm -p 7860:7860 \
  -e LLM_PROVIDER=openai_compatible \
  -e LLM_BASE_URL=https://your-compatible-endpoint/v1 \
  -e LLM_API_KEY=your-key \
  -e LLM_MODEL=your-model \
  hackathon-05-10
```

ModelScope 创空间环境变量建议配置：

```env
PORT=7860
LLM_PROVIDER=openai_compatible
LLM_BASE_URL=https://your-compatible-endpoint/v1
LLM_API_KEY=your-key
LLM_MODEL=your-model
LLM_TEMPERATURE=0.2
LLM_TIMEOUT_SECONDS=180
RUNTIME_DIR=/data/runtime
VAULT_DIR=/data/vault
```

不要把 `LLM_API_KEY` 或 ModelScope Git token 写入代码、README、Dockerfile 或 `.env` 后提交。

## 使用流程

1. 打开前端页面。
2. 上传 PDF/MD/TXT 教材。
3. 后端解析章节并后台触发 LLM 抽取。
4. 在 Graph 视图查看节点、关系、来源与 Markdown 内容。
5. 点击 `Scan merges` 扫描同名概念候选。
6. 在 Merge Decisions 面板查看 candidate、reason、affected nodes。
7. 如需执行合并，调用 `POST /api/merge/execute`，传入人工或外部 agent 生成的 merged concept frontmatter/body。

## 测试

```bash
pytest tests/ -q
```

```bash
cd src/frontend
npm run build
```

## 关键文档

- [需求分析](docs/需求分析.md)
- [系统设计](docs/系统设计.md)
- [Agent 架构说明](docs/Agent架构说明.md)
- [API 接口文档](docs/接口文档.md)
- [Merge 设计](docs/merge_design.md)
- [整合报告](report/整合报告.md)
