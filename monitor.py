"""
创想云(Creality Cloud) 耗材库存监控脚本
监控目标: CR-PLA 和 TPU 耗材的库存状态
当库存从0变为>0时，通过 Server酱 推送微信通知

使用方法:
  python monitor.py

环境变量:
  CXY_TOKEN      - 创想云认证Token (必填)
  CXY_UID        - 创想云用户ID (必填)
  CXY_DUID       - 创想云设备ID (必填)
  SERVERCHAN_KEY - Server酱SendKey (必填，用于微信推送)
  CHECK_INTERVAL - 检查间隔秒数 (可选，默认1800=30分钟，本地运行时使用)
"""

import json
import os
import sys
import time
import urllib.request
from datetime import datetime

API_URL = "https://www.crealitycloud.cn/api/rest/lottery/eshop/goods/list"
SERVERCHAN_URL = "https://sctapi.ftqq.com/"

# 监控目标商品ID
TARGET_GOODS = {
    "6476f814ab8e06aa735af9e1": "CR-PLA_1.75_1KG_颜色随机",
    "6476fa51ab8e06aa735afb1a": "CR-PLA彩虹色_1.75_1KG",
    "65f7a5ad42a8f2c3d45c3a39": "TPU耗材-1.0Kg-1.75mm-颜色随机",
}

# 状态文件路径
STATE_FILE = "stock_state.json"


def build_headers():
    """构建API请求头"""
    token = os.environ.get("CXY_TOKEN", "")
    uid = os.environ.get("CXY_UID", "")
    duid = os.environ.get("CXY_DUID", "")

    cookies = (
        f"model_os_version=Windows%2010; "
        f"model_platform_type=2; "
        f"model_device_id={duid}; "
        f"model_token={token}; "
        f"model_user_id={uid}; "
        f"sensorsObjType=1; "
        f"model_lang=1; "
        f"__CXY_OS_LANG_=1; "
        f"cre-theme=dark"
    )

    return {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Cookie": cookies,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
        "Origin": "https://www.crealitycloud.cn",
        "Referer": "https://www.crealitycloud.cn/",
        "__cxy_app_id_": "cxy-gen2",
        "__cxy_brand_": "creality",
        "__cxy_duid_": duid,
        "__cxy_os_lang_": "1",
        "__cxy_os_ver_": "Windows 10",
        "__cxy_platform_": "2",
        "__cxy_timezone_": "28800",
        "__cxy_token_": token,
        "__cxy_uid_": uid,
    }


def fetch_all_goods():
    """获取所有商品列表（分页获取）"""
    headers = build_headers()
    all_items = []

    # 第一页
    payload = json.dumps({
        "page": 1,
        "pageSize": 20,
        "exchangeType": 1,
        "isOnlyVip": False,
        "classId": ""
    }).encode("utf-8")

    req = urllib.request.Request(API_URL, data=payload, headers=headers, method="POST")

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"[错误] API请求失败: {e}")
        return None, "request_failed"

    if data.get("code") != 0:
        msg = data.get("msg", "unknown")
        print(f"[错误] API返回: code={data.get('code')}, msg={msg}")
        return None, msg

    total_count = data["result"]["totalCount"]
    all_items = data["result"]["list"]

    # 获取剩余页面
    if total_count > 20:
        pages = (total_count - 20) // 20 + 1
        for p in range(2, pages + 2):
            payload = json.dumps({
                "page": p,
                "pageSize": 20,
                "exchangeType": 1,
                "isOnlyVip": False,
                "classId": ""
            }).encode("utf-8")
            req = urllib.request.Request(API_URL, data=payload, headers=headers, method="POST")
            try:
                with urllib.request.urlopen(req, timeout=15) as resp:
                    page_data = json.loads(resp.read().decode("utf-8"))
                if page_data.get("code") == 0:
                    all_items.extend(page_data["result"]["list"])
            except Exception:
                pass  # 继续获取其他页面

    return all_items, "success"


def get_target_stock(items):
    """提取目标商品的库存信息"""
    result = {}
    for item in items:
        item_id = item.get("id", "")
        if item_id in TARGET_GOODS:
            result[item_id] = {
                "name": item.get("name", TARGET_GOODS[item_id]),
                "quantity": item.get("quantity", 0),
                "currentQuanity": item.get("currentQuanity", 0),
                "stockStatus": item.get("stockStatus", 0),
                "kwBeans": item.get("kwBeans", 0),
            }
    return result


def load_state():
    """加载上次库存状态"""
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_state(state):
    """保存当前库存状态"""
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def check_stock_change(prev_state, current_stock):
    """检查库存变化，返回有货的商品列表"""
    available = []
    for item_id, info in current_stock.items():
        prev = prev_state.get(item_id, {})
        prev_qty = prev.get("currentQuanity", 0)
        prev_status = prev.get("stockStatus", 0)
        cur_qty = info["currentQuanity"]
        cur_status = info["stockStatus"]

        # 库存从0变为>0，或者stockStatus变化（2→1可能代表上架）
        if (prev_qty == 0 and cur_qty > 0) or (prev_status == 2 and cur_status == 1):
            available.append(info)

    return available


def send_serverchan(title, content):
    """通过 Server酱 推送微信通知"""
    key = os.environ.get("SERVERCHAN_KEY", "")
    if not key:
        print("[警告] 未设置 SERVERCHAN_KEY，无法发送微信通知")
        return False

    url = f"{SERVERCHAN_URL}{key}.send"
    payload = json.dumps({"title": title, "desp": content}).encode("utf-8")

    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            if result.get("code") == 0:
                print(f"[通知] Server酱推送成功: {title}")
                return True
            else:
                print(f"[错误] Server酱推送失败: {result}")
                return False
    except Exception as e:
        print(f"[错误] Server酱请求失败: {e}")
        return False


def run_check():
    """执行一次库存检查"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n{'='*60}")
    print(f"[{now}] 开始库存检查...")

    items, status = fetch_all_goods()

    if status == "invalid login":
        send_serverchan(
            "⚠️ 创想云Token已过期",
            f"监控脚本无法访问创想云API，Token已过期。\n\n请更新GitHub Secrets中的 CXY_TOKEN。\n\n检测时间: {now}"
        )
        print("[严重] Token过期，已发送提醒通知")
        return False

    if items is None:
        print("[错误] 无法获取商品数据")
        return False

    current_stock = get_target_stock(items)
    if not current_stock:
        print("[警告] 未找到目标商品")
        return False

    # 打印当前库存状态
    print("\n当前库存状态:")
    for item_id, info in current_stock.items():
        name = info["name"]
        qty = info["quantity"]
        cur = info["currentQuanity"]
        ss = info["stockStatus"]
        beans = info["kwBeans"]
        status_text = "有货!" if cur > 0 or ss == 1 else "缺货"
        print(f"  {name}: 总库存={qty}, 可兑换={cur}, stockStatus={ss}, 创想豆={beans} [{status_text}]")

    # 与上次状态对比
    prev_state = load_state()
    available = check_stock_change(prev_state, current_stock)

    if available:
        # 有商品从缺货变为有货！发送通知
        title_parts = [a["name"] for a in available]
        title = f"🎉 创想云耗材有货了！{', '.join(title_parts)}"

        content_lines = ["## 创想云耗材库存通知\n"]
        content_lines.append(f"**检测时间**: {now}\n\n")
        content_lines.append("以下耗材从**缺货**变为**有货**:\n\n")

        for info in available:
            content_lines.append(f"- **{info['name']}**\n")
            content_lines.append(f"  - 可兑换数量: {info['currentQuanity']}\n")
            content_lines.append(f"  - 总库存: {info['quantity']}\n")
            content_lines.append(f"  - 创想豆价格: {info['kwBeans']}\n")
            content_lines.append(f"  - stockStatus: {info['stockStatus']}\n\n")

        content_lines.append("---\n")
        content_lines.append("👉 [立即前往创想云兑换](https://www.crealitycloud.cn)\n")

        content = "".join(content_lines)
        send_serverchan(title, content)
        print(f"\n[通知] 发现库存变化！已发送微信通知: {title}")
    else:
        print("\n[正常] 库存无变化，所有目标商品仍为缺货状态")

    # 保存当前状态
    save_state(current_stock)
    return True


def main():
    """主函数"""
    # 检查必要环境变量
    required_vars = ["CXY_TOKEN", "CXY_UID", "CXY_DUID"]
    missing = [v for v in required_vars if not os.environ.get(v)]
    if missing:
        print(f"[错误] 缺少必要环境变量: {', '.join(missing)}")
        print("请设置以下环境变量:")
        print("  CXY_TOKEN      - 创想云认证Token")
        print("  CXY_UID        - 创想云用户ID")
        print("  CXY_DUID       - 创想云设备ID")
        print("  SERVERCHAN_KEY - Server酱SendKey (用于微信推送)")
        sys.exit(1)

    # 单次检查模式（GitHub Actions使用）
    run_check()


if __name__ == "__main__":
    main()
