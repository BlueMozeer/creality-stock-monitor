# 创想云耗材库存监控

自动监控创想云(Creality Cloud)平台 CR-PLA 和 TPU 耗材的库存状态，当库存恢复时通过微信推送通知。

## 监控目标

| 商品 | 说明 |
|------|------|
| CR-PLA_1.75_1KG_颜色随机 | 1KG PLA耗材，颜色随机 |
| CR-PLA彩虹色_1.75_1KG | 1KG PLA彩虹色耗材 |
| TPU耗材-1.0Kg-1.75mm-颜色随机 | 1KG TPU耗材，颜色随机 |

## 通知方式

当库存从缺货变为有货时，通过 **Server酱** 推送微信通知。

## 快速部署（5分钟上手）

### 第1步：注册 Server酱

1. 访问 [https://sct.ftqq.com/](https://sct.ftqq.com/)
2. 用微信扫码登录
3. 关注「Server酱」服务号
4. 在后台获取 **SendKey**（形如 `SCTxxxxx`）

### 第2步：创建 GitHub 仓库

1. 在 GitHub 上创建一个**公开仓库**（如 `creality-stock-monitor`）
2. 将本项目所有文件推送到仓库

### 第3步：配置 GitHub Secrets

在仓库 Settings → Secrets and variables → Actions 中添加：

| Secret名称 | 值 | 获取方法 |
|------------|------|---------|
| `CXY_TOKEN` | `6e4953c8d0e39f131db1d094ce1185e0acf11ba3d7fe3a998aa610896e840e03` | 浏览器F12 → Network → 请求头中的 `model_token` 或 `__cxy_token_` |
| `CXY_UID` | `1563066814` | 请求头中的 `model_user_id` 或 `__cxy_uid_` |
| `CXY_DUID` | `uuid-dde63c9c-4066-453a-91eb-95ac0e2804b8` | 请求头中的 `model_device_id` 或 `__cxy_duid_` |
| `SERVERCHAN_KEY` | 你的SendKey | Server酱后台获取 |

### 第4步：测试运行

1. 进入仓库 → Actions → 创想云耗材库存监控
2. 点击 **Run workflow** 手动触发一次
3. 检查运行日志，确认脚本正常工作
4. 如果收到微信通知 "Token过期"，说明需要更新Token

## Token过期处理

创想云的认证Token会定期过期（通常7-30天）。脚本会自动检测Token过期并通过微信提醒你更新。

更新方法：
1. 在浏览器中重新登录创想云网站
2. F12打开开发者工具 → Network → 找到任意API请求
3. 复制请求头中新的 `model_token` 值
4. 更新 GitHub Secrets 中的 `CXY_TOKEN`

## 检查频率

- GitHub Actions 每 **30分钟** 自动检查一次
- 也可手动触发检查（Actions → Run workflow）
- GitHub Actions cron有延迟，实际间隔可能为35-40分钟

## 监控逻辑

脚本判断"有货"的条件：
- `currentQuanity` 从 0 变为 >0（可兑换数量恢复）
- `stockStatus` 从 2 变为 1（商品状态变为可购买）

首次运行时所有商品都标记为"缺货"状态，后续每次运行与上次状态对比。

## 添加更多监控商品

编辑 `monitor.py` 中的 `TARGET_GOODS` 字典：

```python
TARGET_GOODS = {
    "商品ID": "商品名称",
    # ...
}
```

商品ID可通过浏览器F12抓包获取，或运行 `fetch_goods.py` 查看完整商品列表。

## 本地运行（不使用GitHub Actions）

```bash
# 设置环境变量
export CXY_TOKEN="你的token"
export CXY_UID="你的uid"
export CXY_DUID="你的duid"
export SERVERCHAN_KEY="你的sendkey"

# 单次检查
python monitor.py

# 持续监控（每30分钟）
while true; do
  python monitor.py
  sleep 1800
done
```

## 文件说明

| 文件 | 用途 |
|------|------|
| `monitor.py` | 主监控脚本 |
| `stock_state.json` | 上次库存状态（自动生成，用于对比变化） |
| `fetch_goods.py` | 商品列表查询工具（调试用） |
| `.github/workflows/stock-monitor.yml` | GitHub Actions 定时任务配置 |
