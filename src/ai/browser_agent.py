"""Browser Agent Service for executing browser automation tasks."""
import asyncio
from pathlib import Path
from typing import AsyncGenerator, Optional, Callable
from loguru import logger

from browser_use import Agent, Browser
from browser_use.browser.profile import BrowserProfile
from browser_use.llm.openai.chat import ChatOpenAI


class BrowserAgentService:
    """Service for running browser automation tasks with real-time updates."""

    def __init__(
        self,
        openai_api_key: str,
        model: str = "gpt-4o",
        headless: bool = True,
        demo_mode: bool = False,
        window_size: Optional[dict] = None,
        record_video: bool = True,
        video_dir: str = "./recordings",
        capture_screenshots: bool = True,
        screenshots_dir: str = "./screenshots",
    ):
        """
        Initialize Browser Agent Service.

        Args:
            openai_api_key: OpenAI API key
            model: LLM model name
            headless: Run browser in headless mode
            demo_mode: Enable demo mode panel
            window_size: Browser window size dict with width/height
            record_video: Enable video recording
            video_dir: Directory for video recordings
            capture_screenshots: Enable screenshot capture at each step
            screenshots_dir: Directory for screenshots
        """
        self.openai_api_key = openai_api_key
        self.model = model
        self.headless = headless
        self.demo_mode = demo_mode
        self.window_size = window_size or {"width": 1280, "height": 720}
        self.record_video = record_video
        self.video_dir = Path(video_dir)
        self.video_dir.mkdir(exist_ok=True, parents=True)
        logger.info(f"📹 Video directory: {self.video_dir.absolute()}")
        
        self.capture_screenshots = capture_screenshots
        self.screenshots_dir = Path(screenshots_dir)
        self.screenshots_dir.mkdir(exist_ok=True, parents=True)
        if self.capture_screenshots:
            logger.info(f"📸 Screenshots directory: {self.screenshots_dir.absolute()}")

    async def run_task(
        self, task: str, session_id: str
    ) -> AsyncGenerator[dict, None]:
        """
        Run a browser automation task and yield real-time updates.

        Args:
            task: Task description/prompt
            session_id: Unique session identifier
            step_callback: Optional callback function to receive step updates

        Yields:
            dict: Real-time update with type, message, and data
        """
        video_path = None
        try:
            # Initialize browser profile
            profile_kwargs = {
                "headless": self.headless,
                "demo_mode": self.demo_mode,
                "window_size": self.window_size,
            }
            
            # Disable demo_mode in headless mode (it requires visible browser and causes startup issues)
            if self.headless and self.demo_mode:
                logger.warning("⚠️  Disabling demo_mode because headless=True (demo_mode requires visible browser)")
                profile_kwargs["demo_mode"] = False
                self.demo_mode = False
            
            # Enable video recording if requested
            if self.record_video:
                # Ensure absolute path for video directory
                video_dir_absolute = str(self.video_dir.resolve())
                profile_kwargs["record_video_dir"] = video_dir_absolute
                profile_kwargs["record_video_framerate"] = 10  # Default framerate
                logger.info(f"📹 Video recording enabled: {video_dir_absolute}")
            else:
                logger.info("📹 Video recording disabled")
            
            browser_profile = BrowserProfile(**profile_kwargs)

            # Create browser instance
            # Browser-use will handle browser installation automatically if needed
            try:
                browser = Browser(browser_profile=browser_profile)
            except (FileNotFoundError, OSError) as browser_error:
                error_msg = str(browser_error)
                if "No such file or directory" in error_msg or "chromium" in error_msg.lower():
                    yield {
                        "type": "error",
                        "message": "❌ 瀏覽器未安裝。請在容器中執行: uvx browser-use install",
                        "data": {
                            "session_id": session_id,
                            "error": "Browser not installed. Run 'uvx browser-use install' in container.",
                            "suggestion": "Try: docker compose exec browser-use-api uvx browser-use install",
                        },
                    }
                    return
                else:
                    raise

            # Initialize LLM
            llm = ChatOpenAI(
                model=self.model,
                api_key=self.openai_api_key,
            )

            # Create agent
            agent = Agent(
                task=task,
                llm=llm,
                browser=browser,
            )

            # Send initial status
            yield {
                "type": "status",
                "message": "🚀 开始执行任务...",
                "data": {"session_id": session_id, "task": task},
            }

            # Use a queue to pass step updates from callbacks to the generator
            step_queue = asyncio.Queue()
            
            # Track last sent state to avoid duplicates
            last_sent_model_output_id = None
            last_sent_result_id = None
            
            async def send_model_state_update(agent_instance, step_num):
                """Extract and send detailed model state updates"""
                nonlocal last_sent_model_output_id, last_sent_result_id
                
                if not hasattr(agent_instance, 'state') or not agent_instance.state:
                    return
                
                # Get model output with thinking, evaluation, memory, next_goal, actions
                model_output = agent_instance.state.last_model_output
                if model_output and hasattr(model_output, 'current_state'):
                    current_output_id = id(model_output)
                    
                    # Only send if this is new model output
                    if current_output_id != last_sent_model_output_id:
                        last_sent_model_output_id = current_output_id
                        state = model_output.current_state
                        
                        # Send thinking (if available)
                        if hasattr(state, 'thinking') and state.thinking and state.thinking.strip():
                            await step_queue.put({
                                "type": "thinking",
                                "message": f"💭 思考中...",
                                "data": {
                                    "session_id": session_id,
                                    "step": step_num,
                                    "thinking": state.thinking[:2000],  # Increased limit
                                },
                            })
                        
                        # Send evaluation of previous goal
                        if hasattr(state, 'evaluation_previous_goal') and state.evaluation_previous_goal and state.evaluation_previous_goal.strip():
                            eval_text = state.evaluation_previous_goal
                            await step_queue.put({
                                "type": "evaluation",
                                "message": f"🔍 驗證結果",
                                "data": {
                                    "session_id": session_id,
                                    "step": step_num,
                                    "evaluation": eval_text[:1000],
                                },
                            })
                        
                        # Send memory update
                        if hasattr(state, 'memory') and state.memory and state.memory.strip():
                            await step_queue.put({
                                "type": "memory",
                                "message": f"🧠 記憶更新",
                                "data": {
                                    "session_id": session_id,
                                    "step": step_num,
                                    "memory": state.memory[:1000],
                                },
                            })
                        
                        # Send next goal
                        if hasattr(state, 'next_goal') and state.next_goal and state.next_goal.strip():
                            await step_queue.put({
                                "type": "planning",
                                "message": f"🎯 下一步目標",
                                "data": {
                                    "session_id": session_id,
                                    "step": step_num,
                                    "next_goal": state.next_goal[:1000],
                                },
                            })
                        
                        # Send actions to be executed
                        if hasattr(model_output, 'action') and model_output.action:
                            actions_str = []
                            for action in model_output.action:
                                if hasattr(action, 'model_dump'):
                                    try:
                                        action_dict = action.model_dump(exclude_unset=True)
                                        action_name = action_dict.get('action', 'unknown')
                                        action_str = f"▶️ {action_name}"
                                        # Add key parameters
                                        for key in ['text', 'index', 'query', 'url', 'selector', 'xpath', 'tag']:
                                            if key in action_dict and action_dict[key] is not None:
                                                val = str(action_dict[key])
                                                if len(val) > 60:
                                                    val = val[:57] + "..."
                                                action_str += f"\n   {key}: {val}"
                                        actions_str.append(action_str)
                                    except Exception as e:
                                        logger.debug(f"Error formatting action: {e}")
                                        actions_str.append(f"▶️ {str(action)[:100]}")
                            
                            if actions_str:
                                await step_queue.put({
                                    "type": "action",
                                    "message": f"🎬 執行操作",
                                    "data": {
                                        "session_id": session_id,
                                        "step": step_num,
                                        "actions": actions_str,
                                        "action_count": len(actions_str),
                                    },
                                })
                
                # Send action results (check for new results)
                if hasattr(agent_instance.state, 'last_result') and agent_instance.state.last_result:
                    results = agent_instance.state.last_result
                    if results:
                        current_result_id = id(results)
                        if current_result_id != last_sent_result_id:
                            last_sent_result_id = current_result_id
                            results_str = []
                            for result in results:
                                if hasattr(result, 'error') and result.error:
                                    results_str.append(f"❌ 錯誤: {result.error[:500]}")
                                elif hasattr(result, 'extracted_content') and result.extracted_content:
                                    content = result.extracted_content[:500]
                                    results_str.append(f"📄 提取內容: {content}")
                                elif hasattr(result, 'long_term_memory') and result.long_term_memory:
                                    memory = result.long_term_memory[:500]
                                    results_str.append(f"🧠 記憶: {memory}")
                                elif hasattr(result, 'success') and result.success is not None:
                                    results_str.append(f"{'✅ 成功' if result.success else '⚠️ 失敗'}")
                            
                            if results_str:
                                await step_queue.put({
                                    "type": "result",
                                    "message": f"📊 操作結果",
                                    "data": {
                                        "session_id": session_id,
                                        "step": step_num,
                                        "results": results_str,
                                    },
                                })
            
            # Define step callbacks to capture real-time updates
            async def on_step_start(agent_instance):
                """Callback when a step starts"""
                step_num = agent_instance.state.n_steps
                max_steps = getattr(agent_instance, 'max_steps', 100)
                
                await step_queue.put({
                    "type": "step_start",
                    "message": f"📍 步驟 {step_num}/{max_steps} 開始",
                    "data": {"session_id": session_id, "step": step_num, "max_steps": max_steps},
                })
            
            async def on_step_end(agent_instance):
                """Callback when a step ends"""
                step_num = agent_instance.state.n_steps - 1
                
                # Send final state update for this step
                await send_model_state_update(agent_instance, step_num)
                
                # Capture screenshot if enabled
                screenshot_path = None
                if self.capture_screenshots and hasattr(agent_instance, 'browser_session'):
                    try:
                        browser_session = agent_instance.browser_session
                        
                        # Use browser-use's built-in take_screenshot method
                        if hasattr(browser_session, 'take_screenshot'):
                            # Create screenshot filename with session_id and step number
                            screenshot_filename = f"{session_id}_step_{step_num:03d}.png"
                            screenshot_path = self.screenshots_dir / screenshot_filename
                            
                            # Take screenshot using browser-use's method
                            # take_screenshot returns bytes (even with path parameter)
                            screenshot_result = await browser_session.take_screenshot(
                                path=None,  # We'll save manually
                                full_page=True,
                                format='png'
                            )
                            
                            # Save bytes to file
                            if isinstance(screenshot_result, bytes):
                                screenshot_path.write_bytes(screenshot_result)
                            else:
                                logger.warning(f"Unexpected screenshot result type: {type(screenshot_result)}")
                                return
                            
                            logger.info(f"📸 Screenshot saved: {screenshot_path}")
                            
                            # Send screenshot update
                            await step_queue.put({
                                "type": "screenshot",
                                "message": f"📸 步驟 {step_num} 截圖已保存",
                                "data": {
                                    "session_id": session_id,
                                    "step": step_num,
                                    "screenshot_path": screenshot_filename,
                                    "screenshot_url": f"/api/v1/screenshots/{session_id}/{screenshot_filename}",
                                },
                            })
                        else:
                            logger.warning(f"⚠️  BrowserSession does not have take_screenshot method")
                            # Fallback: Try to get page and use Playwright screenshot
                            page = None
                            # Try get_current_page or get_pages
                            if hasattr(browser_session, 'get_current_page'):
                                try:
                                    page = await browser_session.get_current_page()
                                except:
                                    pass
                            elif hasattr(browser_session, 'get_pages'):
                                try:
                                    pages = await browser_session.get_pages()
                                    if pages and len(pages) > 0:
                                        page = pages[0]
                                except:
                                    pass
                            
                            if page:
                                screenshot_filename = f"{session_id}_step_{step_num:03d}.png"
                                screenshot_path = self.screenshots_dir / screenshot_filename
                                await page.screenshot(path=str(screenshot_path), full_page=True)
                                logger.info(f"📸 Screenshot saved (via page): {screenshot_path}")
                                
                                await step_queue.put({
                                    "type": "screenshot",
                                    "message": f"📸 步驟 {step_num} 截圖已保存",
                                    "data": {
                                        "session_id": session_id,
                                        "step": step_num,
                                        "screenshot_path": screenshot_filename,
                                        "screenshot_url": f"/api/v1/screenshots/{session_id}/{screenshot_filename}",
                                    },
                                })
                            else:
                                logger.debug(f"Could not capture screenshot: no take_screenshot method and no page access")
                    except Exception as e:
                        logger.warning(f"⚠️  Could not capture screenshot: {e}", exc_info=True)
                
                # Get step summary
                step_info = {
                    "step": step_num,
                    "message": f"✅ 步驟 {step_num} 完成",
                }
                
                # Get current URL and page info
                if hasattr(agent_instance, 'browser_session'):
                    try:
                        state = await agent_instance.browser_session.get_state()
                        if state:
                            if hasattr(state, 'url') and state.url:
                                step_info["url"] = state.url
                            if hasattr(state, 'title') and state.title:
                                step_info["title"] = state.title
                    except Exception as e:
                        logger.debug(f"Could not get browser state: {e}")
                
                await step_queue.put({
                    "type": "step_end",
                    "message": step_info["message"],
                    "data": {"session_id": session_id, **step_info},
                })
            
            # Run agent in background with step callbacks
            # Add timeout wrapper to catch browser startup issues
            async def run_agent_with_timeout():
                try:
                    return await asyncio.wait_for(
                        agent.run(
                            max_steps=100,
                            on_step_start=on_step_start,
                            on_step_end=on_step_end,
                        ),
                        timeout=600.0  # 10 minutes total timeout
                    )
                except asyncio.TimeoutError:
                    logger.error("⏰ Agent execution timed out after 10 minutes")
                    raise
                except Exception as e:
                    logger.error(f"❌ Agent execution error: {e}", exc_info=True)
                    raise
            
            agent_task = asyncio.create_task(run_agent_with_timeout())
            
            # Also monitor state during step execution
            async def monitor_step_progress():
                """Monitor agent state during step execution and send updates"""
                while not agent_task.done():
                    await asyncio.sleep(0.3)  # Check every 300ms for faster updates
                    
                    try:
                        if hasattr(agent, 'state') and agent.state:
                            current_step = agent.state.n_steps
                            # Send state update (function handles deduplication)
                            await send_model_state_update(agent, current_step)
                    except Exception as e:
                        logger.debug(f"Error monitoring step progress: {e}")
                        continue
            
            # Start monitoring task
            monitor_task = asyncio.create_task(monitor_step_progress())
            
            # Monitor step queue and yield updates
            while not agent_task.done():
                try:
                    # Wait for step update with timeout
                    update = await asyncio.wait_for(step_queue.get(), timeout=0.5)
                    yield update
                except asyncio.TimeoutError:
                    # Check if agent is done
                    if agent_task.done():
                        break
                    continue
            
            # Get the history result
            history = await agent_task
            
            # Cancel monitoring task
            monitor_task.cancel()
            try:
                await monitor_task
            except asyncio.CancelledError:
                pass
            
            # Close browser to ensure video is saved
            try:
                if hasattr(agent, 'browser_session') and agent.browser_session:
                    # Get browser session ID before closing (might be used in video filename)
                    browser_session_id = None
                    if hasattr(agent.browser_session, 'session_id'):
                        browser_session_id = agent.browser_session.session_id
                    elif hasattr(agent.browser_session, 'cdp_url'):
                        # Extract session ID from CDP URL if available
                        cdp_url = agent.browser_session.cdp_url
                        logger.info(f"📹 Browser CDP URL: {cdp_url}")
                    
                    await agent.browser_session.close()
                    logger.info("📹 Browser closed, waiting for video to be saved...")
                    # Wait longer for video file to be written (browser-use may need time)
                    await asyncio.sleep(3)
            except Exception as e:
                logger.debug(f"Error closing browser: {e}")
            
            # Find the video file associated with this session
            # browser-use saves videos with a UUID-based naming pattern
            video_path = None
            try:
                # Ensure we're using absolute path
                video_dir_abs = self.video_dir.resolve()
                logger.info(f"📹 Searching for videos in: {video_dir_abs}")
                
                # Get list of video files
                video_files = list(video_dir_abs.glob("*.mp4"))
                if video_files:
                    # Get the most recently modified video file (should be the one just created)
                    video_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
                    video_path = video_files[0]
                    video_path_abs = video_path.resolve()
                    logger.info(f"📹 Found video: {video_path_abs} (modified: {video_path.stat().st_mtime})")
                    
                    # Verify the video file is not too old (created within last 5 minutes)
                    import time
                    current_time = time.time()
                    file_mtime = video_path.stat().st_mtime
                    if current_time - file_mtime > 300:  # 5 minutes
                        logger.warning(f"📹 Video file seems old, might not be from this session")
                else:
                    logger.warning(f"📹 No video files found in {video_dir_abs}")
                    # List directory contents for debugging
                    try:
                        dir_contents = list(video_dir_abs.iterdir())
                        logger.info(f"📹 Directory contents: {[str(p.name) for p in dir_contents]}")
                    except Exception as e:
                        logger.debug(f"Could not list directory: {e}")
            except Exception as e:
                logger.error(f"📹 Error finding video file: {e}", exc_info=True)
                video_path = None
            
            # Extract final result from history - look for done action result
            final_message = "✅ 任务完成！"
            result_summary = ""
            result_text = ""
            
            if history:
                # Try to get the final result from history
                # Check for done action in history items
                if hasattr(history, 'history') and history.history:
                    for item in reversed(history.history):
                        # Check if this item has a done action result
                        if hasattr(item, 'result') and item.result:
                            for result in item.result:
                                if hasattr(result, 'is_done') and result.is_done:
                                    # This is the final done result
                                    if hasattr(result, 'extracted_content') and result.extracted_content:
                                        result_text = result.extracted_content
                                    elif hasattr(result, 'long_term_memory') and result.long_term_memory:
                                        result_text = result.long_term_memory
                                    break
                        
                        # Also check model_output for done action
                        if hasattr(item, 'model_output') and item.model_output:
                            if hasattr(item.model_output, 'action') and item.model_output.action:
                                for action in item.model_output.action:
                                    if hasattr(action, 'action') and str(action.action).lower() == 'done':
                                        # Extract text from done action
                                        if hasattr(action, 'text') and action.text:
                                            result_text = action.text
                                        elif hasattr(action, 'model_dump'):
                                            action_dict = action.model_dump()
                                            if 'text' in action_dict:
                                                result_text = action_dict['text']
                                        break
                        
                        if result_text:
                            break
                
                # Fallback: try to get from messages
                if not result_text and hasattr(history, 'messages') and history.messages:
                    for msg in reversed(history.messages):
                        if hasattr(msg, 'content') and msg.content:
                            content = str(msg.content)
                            # Look for done message or final result
                            if 'done' in content.lower() or 'result' in content.lower():
                                result_text = content[:1000]
                                break
                
                # Fallback: try to get from history string
                if not result_text:
                    history_str = str(history)
                    if "Final Result" in history_str or "done" in history_str.lower():
                        # Extract final result section
                        if "Final Result" in history_str:
                            parts = history_str.split("Final Result")
                            if len(parts) > 1:
                                result_text = parts[1][:1000]
                        else:
                            # Try to find done action text
                            lines = history_str.split('\n')
                            for i, line in enumerate(reversed(lines)):
                                if 'done' in line.lower() and i < 5:
                                    # Get surrounding context
                                    start = max(0, len(lines) - i - 3)
                                    result_text = '\n'.join(lines[start:])[:1000]
                                    break
            
            if result_text:
                result_summary = result_text.strip()
                final_message = f"✅ 任务完成！"
            else:
                result_summary = "任务已执行完成，但未获取到详细结果。"
            
            # Prepare completion data with video path and result
            completion_data = {
                "session_id": session_id,
                "history": str(history) if history else None,
                "result": result_summary,  # Add LLM result
            }
            
            # Add video path if available
            if video_path:
                # Get absolute path and then just the filename for API access
                video_path_abs = Path(video_path).resolve()
                video_filename = video_path_abs.name
                completion_data["video_path"] = video_filename
                completion_data["video_url"] = f"/api/v1/videos/{session_id}/{video_filename}"
                logger.info(f"📹 Video file: {video_path_abs}")
                logger.info(f"📹 Video filename: {video_filename}")
                logger.info(f"📹 Video URL: {completion_data['video_url']}")
            else:
                logger.warning(f"📹 No video file found for session {session_id}")
                logger.warning(f"📹 Video directory was: {self.video_dir.resolve()}")
            
            yield {
                "type": "complete",
                "message": final_message,
                "data": completion_data,
            }

        except asyncio.TimeoutError as e:
            logger.error(f"⏰ Browser agent timeout: {e}", exc_info=True)
            error_msg = "浏览器启动或执行超时。这可能是由于：\n1. 浏览器启动时间过长\n2. 网络连接问题\n3. Docker 容器资源不足\n\n建议：\n- 检查 Docker 容器资源（CPU/内存）\n- 确认网络连接正常\n- 尝试重启服务"
            yield {
                "type": "error",
                "message": f"❌ 执行超时: {str(e)}",
                "data": {
                    "session_id": session_id,
                    "error": str(e),
                    "error_type": "timeout",
                    "suggestion": error_msg,
                },
            }
        except Exception as e:
            logger.error(f"❌ Error in browser agent: {e}", exc_info=True)
            error_type = type(e).__name__
            error_msg = str(e)
            
            # Provide more helpful error messages
            if "CDP" in error_msg or "client not initialized" in error_msg:
                error_msg = f"浏览器连接失败: {error_msg}\n\n可能原因：\n1. 浏览器启动失败\n2. CDP 连接超时\n3. Docker 容器配置问题\n\n建议检查：\n- Docker compose 配置（shm_size, security_opt）\n- 浏览器是否正确安装\n- 容器日志中的详细错误信息"
            elif "timeout" in error_msg.lower():
                error_msg = f"操作超时: {error_msg}\n\n建议：\n- 增加超时时间\n- 检查网络连接\n- 确认目标网站可访问"
            
            yield {
                "type": "error",
                "message": f"❌ 执行出错: {error_msg}",
                "data": {
                    "session_id": session_id,
                    "error": str(e),
                    "error_type": error_type,
                },
            }

    async def get_task_status(self, session_id: str) -> dict:
        """
        Get status of a running task.

        Args:
            session_id: Session identifier

        Returns:
            dict: Task status information
        """
        # TODO: Implement task status tracking
        return {"session_id": session_id, "status": "unknown"}

