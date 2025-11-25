from browser_use import Agent, Browser
from browser_use.browser.profile import BrowserProfile
from browser_use.llm.openai.chat import ChatOpenAI
from dotenv import load_dotenv
import asyncio
from pathlib import Path

# 加载 .env 文件（会自动将 OPENAI_API_KEY 加载到环境变量）
load_dotenv()

async def example():
    # 创建视频录制目录
    video_dir = Path("./recordings")
    video_dir.mkdir(exist_ok=True)
    
    # 创建 BrowserProfile 配置
    browser_profile = BrowserProfile(
        headless=False,  # 设置为 False 让浏览器可见
        demo_mode=True,  # 启用 demo mode，在浏览器中显示实时日志面板
        record_video_dir=str(video_dir),  # 录制视频到指定目录
        record_video_framerate=10,  # 视频帧率
        window_size={"width": 1280, "height": 720},  # 设置浏览器窗口大小
    )
    
    browser = Browser(
        browser_profile=browser_profile,
        # use_cloud=True,  # Uncomment to use a stealth browser on Browser Use Cloud
    )

    # 使用 browser-use 的 ChatOpenAI（会自动从环境变量读取 OPENAI_API_KEY）
    llm = ChatOpenAI(
        model="gpt-4o",  # 或使用 "gpt-4", "gpt-3.5-turbo" 等
    )

    agent = Agent(
        task="Find the number of stars of the browser-use repo",
        llm=llm,
        browser=browser,
    )

    print("🚀 开始执行任务...")
    print("📹 浏览器操作将被录制到 ./recordings/ 目录")
    print("👀 浏览器窗口将显示操作步骤（demo_mode 已启用）")
    print("-" * 50)
    
    history = await agent.run()
    
    print("-" * 50)
    print("✅ 任务完成！")
    print(f"📹 视频文件保存在: {video_dir.absolute()}")
    
    return history

if __name__ == "__main__":
    history = asyncio.run(example())