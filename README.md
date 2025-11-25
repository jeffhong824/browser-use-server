# Browser Use SaaS

> AI 驅動的瀏覽器自動化服務 - 透過 Web 介面執行任務並實時查看操作步驟

## 📋 專案說明

Browser Use SaaS 是一個基於 [browser-use](https://github.com/browser-use/browser-use) 的 Web 服務，提供：

- 🌐 **Web 前端介面**：輸入任務描述，實時查看操作步驟
- 🔄 **實時更新**：透過 WebSocket 即時顯示瀏覽器操作過程
- 🤖 **AI 驅動**：使用 OpenAI GPT 模型自動執行瀏覽器任務
- 🐳 **Docker 部署**：一鍵啟動，環境隔離

## 🚀 快速開始

### 前置需求

- Docker & Docker Compose
- OpenAI API Key

### 安裝步驟

1. **複製環境變數檔案**

   ```bash
   cp .env.example .env
   ```

2. **設定環境變數**

   編輯 `.env` 檔案，填入你的 OpenAI API Key：

   ```env
   OPENAI_API_KEY=your_openai_api_key_here
   ```

3. **啟動服務**

   ```bash
   make docker-stop && make docker-run-bg
   ```

4. **訪問 Web 介面**

   開啟瀏覽器訪問：http://localhost:8000

## 📖 使用說明

### Web 介面使用

1. 在左側面板輸入任務描述（例如：「找到 browser-use 專案的 GitHub stars 數量」）
2. 選擇 AI 模型（預設：GPT-4o）
3. 點擊「開始執行任務」
4. 在右側面板實時查看操作步驟和日誌

### API 使用

#### 健康檢查

```bash
curl -sS http://localhost:8000/health | jq .
```

#### 創建任務

```bash
curl -X POST "http://localhost:8000/v1/tasks" \
  -H "Content-Type: application/json" \
  -d '{
    "task": "找到 browser-use 專案的 GitHub stars 數量",
    "model": "gpt-4o"
  }' | jq .
```

#### WebSocket 連接（實時更新）

使用 WebSocket 客戶端連接到：`ws://localhost:8000/ws/{session_id}`

發送訊息格式：

```json
{
  "action": "start",
  "task": "你的任務描述"
}
```

接收訊息格式：

```json
{
  "type": "status|complete|error",
  "message": "訊息內容",
  "data": {...}
}
```

## 🛠️ 開發

### 本地開發（不使用 Docker）

1. **安裝依賴**

   ```bash
   make install
   ```

2. **設定環境變數**

   ```bash
   export OPENAI_API_KEY=your_key_here
   export API_PORT=8000
   ```

3. **啟動服務**

   ```bash
   python -m uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
   ```

### 測試

```bash
# 健康檢查
curl -sS http://localhost:8000/health | jq .

# 創建任務
curl -sS -X POST "http://localhost:8000/v1/tasks" \
  -H "Content-Type: application/json" \
  -d '{"task": "hello", "model": "gpt-4o"}' | jq .
```

### 查看日誌

```bash
make docker-logs
```

### 進入容器

```bash
make docker-shell
```

## 📁 專案結構

```
.
├── src/
│   ├── ai/              # AI 服務模組
│   │   └── browser_agent.py
│   ├── api/             # FastAPI 後端
│   │   └── main.py
│   ├── configs/          # 配置檔案
│   │   └── app.yaml
│   ├── static/           # 靜態檔案
│   └── templates/       # HTML 模板
│       └── index.html
├── tests/               # 測試檔案
├── scripts/             # 工具腳本
├── docs/                # 文件
├── Dockerfile
├── docker-compose.yml
├── Makefile
├── requirements.txt
├── .env.example
└── README.md
```

## ⚙️ 環境變數

| 變數 | 說明 | 預設值 |
|------|------|--------|
| `API_PORT` | API 服務埠號 | `8000` |
| `LOG_LEVEL` | 日誌級別 | `INFO` |
| `OPENAI_API_KEY` | OpenAI API Key（必填） | - |
| `LLM_MODEL` | AI 模型名稱 | `gpt-4o` |
| `BROWSER_HEADLESS` | 瀏覽器無頭模式 | `true` |
| `BROWSER_DEMO_MODE` | 啟用 demo mode | `false` |
| `BROWSER_WINDOW_WIDTH` | 瀏覽器視窗寬度 | `1280` |
| `BROWSER_WINDOW_HEIGHT` | 瀏覽器視窗高度 | `720` |
| `RECORD_VIDEO` | 錄製視頻 | `false` |
| `VIDEO_DIR` | 視頻儲存目錄 | `./recordings` |

## 🔧 Makefile 命令

```bash
make install          # 安裝 Python 依賴
make docker-build     # 建置 Docker 映像
make docker-run-bg    # 背景執行服務
make docker-stop      # 停止服務
make docker-logs      # 查看日誌
make docker-shell     # 進入容器
make test             # 執行測試
make lint             # 執行 linter
make clean            # 清理暫存檔案
```

## 🐛 故障排除

### 服務無法啟動

1. 檢查 Docker 是否運行：`docker ps`
2. 查看日誌：`make docker-logs`
3. 確認環境變數：檢查 `.env` 檔案

### WebSocket 連接失敗

1. 確認服務已啟動：`curl http://localhost:8000/health`
2. 檢查防火牆設定
3. 查看瀏覽器控制台錯誤訊息

### OpenAI API 錯誤

1. 確認 `OPENAI_API_KEY` 已正確設定
2. 檢查 API Key 是否有效
3. 確認帳戶有足夠額度

## 📝 已知限制

- 目前僅支援 OpenAI 模型
- 瀏覽器操作需要較長時間，請耐心等待
- 無頭模式在 Docker 中預設啟用（如需 GUI，需額外配置）

## 🔮 待辦事項

- [ ] 支援更多 LLM 提供商（Anthropic, Google 等）
- [ ] 任務佇列系統
- [ ] 用戶認證與授權
- [ ] 任務歷史記錄
- [ ] 視頻回放功能
- [ ] 多語言支援

## 📄 授權

MIT License

## 🙏 致謝

- [browser-use](https://github.com/browser-use/browser-use) - 核心瀏覽器自動化框架
- [FastAPI](https://fastapi.tiangolo.com/) - 現代化 Web 框架

