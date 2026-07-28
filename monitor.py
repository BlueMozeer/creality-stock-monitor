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

    # 测试通知模式
    if os.environ.get("TEST_NOTIFY", "false") == "true":
        print("\n[测试] 发送模拟有货通知...")
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        send_serverchan(
            "🎉 测试通知：创想云耗材有货了！",
            f"## 这是一条测试通知\n\n"
            f"如果你收到了这条消息，说明 **Server酱微信推送** 配置成功！\n\n"
            f"- CR-PLA_1.75_1KG_颜色随机（模拟）\n"
            f"- TPU耗材-1.0Kg-1.75mm（模拟）\n\n"
            f"检测时间: {now}\n\n"
            f"---\n\n"
            f"👉 [立即前往创想云兑换](https://www.crealitycloud.cn)\n"
        )
        print("[测试] 通知发送完毕")
        return

    # 单次检查模式（GitHub Actions使用）
    run_check()
