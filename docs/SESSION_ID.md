# 会话 ID (Session ID) 说明

## 什么是会话 ID？

会话 ID 是一个唯一标识符（UUID），用于标识每个浏览器自动化任务实例。

## 会话 ID 的用途

### 1. **任务追踪**
- 每个任务都有唯一的会话 ID
- 可以通过会话 ID 查询任务状态
- 用于日志记录和调试

### 2. **WebSocket 连接**
- 前端通过会话 ID 连接到对应的 WebSocket 端点
- 格式：`ws://localhost:8000/ws/{session_id}`
- 确保每个任务有独立的实时通信通道

### 3. **多任务管理**
- 支持同时运行多个任务
- 每个任务有独立的会话，互不干扰
- 可以同时监控多个任务的执行状态

### 4. **错误追踪**
- 当任务出错时，可以通过会话 ID 查找相关日志
- 便于问题排查和调试

### 5. **资源管理**
- 服务器端通过会话 ID 管理任务资源
- 任务完成后自动清理会话资源

## 会话 ID 的生命周期

1. **创建**：调用 `/v1/tasks` API 时生成
2. **使用**：通过 WebSocket 连接使用
3. **执行**：任务执行期间保持活跃
4. **清理**：任务完成或出错后自动清理

## 示例

```bash
# 1. 创建任务，获得会话 ID
curl -X POST "http://localhost:8000/v1/tasks" \
  -H "Content-Type: application/json" \
  -d '{"task": "找到 browser-use 專案", "model": "gpt-4o"}'

# 返回：
{
  "status": "ok",
  "session_id": "36861c59-1537-435b-b230-ada82802d0d4",
  "message": "Task created. Connect via WebSocket to start execution."
}

# 2. 使用会话 ID 连接 WebSocket
# ws://localhost:8000/ws/36861c59-1537-435b-b230-ada82802d0d4
```

## 注意事项

- 会话 ID 是一次性的，任务完成后不能重复使用
- 如果任务失败，需要创建新的会话 ID
- 会话 ID 在服务器重启后会失效

