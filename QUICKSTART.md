# 快速開始指南

## 1. 準備環境

```bash
# 確保 Docker 和 Docker Compose 已安裝
docker --version
docker compose version
```

## 2. 設定環境變數

```bash
# 複製環境變數範本
cp .env.example .env

# 編輯 .env 檔案，填入你的 OpenAI API Key
# OPENAI_API_KEY=sk-...
```

## 3. 啟動服務

```bash
# 使用 Makefile（推薦）
make docker-stop && make docker-run-bg

# 或使用快速啟動腳本
./scripts/start.sh
```

## 4. 訪問 Web 介面

開啟瀏覽器訪問：http://localhost:8000

## 5. 使用服務

1. 在左側輸入任務描述
2. 選擇 AI 模型
3. 點擊「開始執行任務」
4. 在右側查看實時操作日誌

## 6. 測試 API

```bash
# 健康檢查
curl http://localhost:8000/health | jq .

# 創建任務
curl -X POST "http://localhost:8000/v1/tasks" \
  -H "Content-Type: application/json" \
  -d '{"task": "找到 browser-use 專案的 GitHub stars 數量", "model": "gpt-4o"}' | jq .
```

## 7. 查看日誌

```bash
make docker-logs
```

## 8. 停止服務

```bash
make docker-stop
```

## 故障排除

### 服務無法啟動

1. 檢查 Docker 狀態：`docker ps`
2. 查看日誌：`make docker-logs`
3. 確認 `.env` 檔案中的 `OPENAI_API_KEY` 已設定

### WebSocket 連接失敗

1. 確認服務運行：`curl http://localhost:8000/health`
2. 檢查瀏覽器控制台是否有錯誤

### OpenAI API 錯誤

1. 確認 API Key 正確
2. 檢查帳戶額度
3. 查看服務日誌

