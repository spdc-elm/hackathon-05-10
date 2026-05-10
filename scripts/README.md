# Scripts

放置可重复运行的开发脚本。不要把一次性实验脚本放在这里，实验脚本应放入 `experiments/`。

## dev.sh — 一键启动开发环境

同时启动 FastAPI 后端和 Vite 前端，Ctrl+C 一并停止。

### 前置条件

```bash
# Python 依赖（项目根目录）
pip install -r requirements.txt

# 前端依赖
cd src/frontend && npm install
```

### 使用方式

```bash
./scripts/dev.sh
```

启动后访问：
- 前端：http://localhost:5173
- 后端 API：http://localhost:8000/api/health

前端已配置代理，`/api` 请求自动转发到后端，无需关心跨域。

### 自定义端口

```bash
BACKEND_PORT=9000 FRONTEND_PORT=3000 ./scripts/dev.sh
```
