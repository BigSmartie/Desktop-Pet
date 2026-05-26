import os
import re
import tempfile
import base64

from typing import List

from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from config.app_settings import load_app_settings, save_app_settings
from core import get_logger, check_liveness, check_readiness, get_vectorstore
from core.log_viewer import read_recent_logs
from agent import build_agent_executor, get_agent_executor_for_route, run_agent
from knowledge import (
    get_retriever,
    list_documents,
    delete_document_from_vectorstore,
    ingest_file_to_vectorstore,
)
from memory import (
    get_session_messages,
    get_session_summary,
    append_user_message,
    append_assistant_message,
    clear_chat_session,
    get_chat_history_for_agent,
    summarize_messages_if_needed,
    set_session_summary,
    reflect_on_interaction,
    load_user_profile,
)
from memory.tasks import load_tasks, update_task, delete_task
from action_queue import (
    approve_action,
    execute_action_async,
    get_action_queue_summary,
    queue_mcp_action,
    reject_action,
)
from pet import (
    get_companion_summary,
    get_pet_state,
    get_state_machine,
    handle_pet_event,
    record_companion_event,
    record_daily_check_in,
)
from pet.daily_report import read_daily_report, recent_daily_reports, reminder_status, save_daily_report
from mcp_bridge import (
    call_mcp_tool_async,
    get_mcp_status,
    get_mcp_tool_metadata,
    list_mcp_tools,
    mcp_tool_requires_approval,
    reload_mcp_config,
)
from api_models import (
    ChatRequest, ChatResponse, ClearRequest, HealthResponse,
    DocumentItem, DocumentUploadResponse, ProfileResponse, TaskItem, TaskUpdateRequest,
    PetStateResponse, PetEventRequest, McpToolCallRequest,
    CompanionCheckInRequest, CompanionSummaryResponse,
    ActionCreateRequest, ActionDecisionRequest, ActionQueueResponse, ActionItem,
    AppSettingsRequest, DailyReportResponse, LogsResponse
)


logger = get_logger(__name__)
UPLOAD_CHUNK_SIZE = 1024 * 1024

# 全局存储组件
_app_state = {}

app = FastAPI(
    title=settings.APP_TITLE,
    description="Backend API for AI Agent",
)

@app.on_event("startup")
async def startup_event():
    # 初始化向量库和智能体
    try:
        logger.info("初始化后端组件...")
        load_app_settings()
        vectorstore = get_vectorstore()
        retriever = get_retriever(vectorstore)
        agent_executor = build_agent_executor(retriever)
        
        _app_state["vectorstore"] = vectorstore
        _app_state["agent_executor"] = agent_executor
        if getattr(settings, "PET_DAILY_REPORT_AUTO", True):
            save_daily_report(force=False)
        handle_pet_event("startup_ready")
        record_companion_event("startup", "Backend services are ready.")
        logger.info("后端组件初始化成功。")
    except Exception as e:
        logger.exception("后端初始化失败")
        _app_state["startup_error"] = str(e)
        handle_pet_event("startup_error")
        record_companion_event("startup_error", str(e)[:220])

# 允许跨域
cors_allow_origins = list(settings.CORS_ALLOW_ORIGINS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_allow_origins,
    allow_credentials="*" not in cors_allow_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse)
async def health_check():
    try:
        health = check_readiness()
        return HealthResponse(**health)
    except Exception as e:
        return HealthResponse(status="error", details={"error": str(e)})


@app.get("/health/live", response_model=HealthResponse)
async def health_live():
    return HealthResponse(**check_liveness())


@app.get("/health/ready", response_model=HealthResponse)
async def health_ready():
    health = check_readiness()
    if health["status"] != "ok":
        raise HTTPException(status_code=503, detail=health["details"])
    return HealthResponse(**health)


@app.get("/api/settings")
async def get_app_settings():
    return load_app_settings()


@app.put("/api/settings")
async def update_app_settings(request: AppSettingsRequest):
    if hasattr(request, "model_dump"):
        payload = request.model_dump(exclude_none=True)
    else:
        payload = request.dict(exclude_none=True)
    return save_app_settings(payload)


@app.get("/api/daily-report/today", response_model=DailyReportResponse)
async def get_today_daily_report():
    return DailyReportResponse(**read_daily_report(auto_create=True))


@app.post("/api/daily-report/generate", response_model=DailyReportResponse)
async def generate_daily_report():
    report = save_daily_report(force=True)
    handle_pet_event(
        "reminder",
        mood="warm",
        message="Daily report is ready with tomorrow's suggestions.",
        duration_seconds=14,
    )
    record_companion_event("daily_report", "Generated today's daily report.")
    return DailyReportResponse(**report)


@app.get("/api/daily-report/recent")
async def list_recent_daily_reports(limit: int = 7):
    return {"reports": recent_daily_reports(limit)}


@app.get("/api/reminders/status")
async def get_reminder_status():
    return reminder_status()


@app.get("/api/logs/recent", response_model=LogsResponse)
async def recent_logs(max_lines: int = 160):
    return LogsResponse(**read_recent_logs(max_lines=max_lines))


@app.get("/api/pet/state", response_model=PetStateResponse)
async def pet_state():
    return PetStateResponse(**get_pet_state())


@app.get("/api/pet/machine")
async def pet_machine():
    return get_state_machine()


@app.post("/api/pet/event", response_model=PetStateResponse)
async def pet_event(request: PetEventRequest):
    state = handle_pet_event(
        event=request.event,
        activity=request.activity,
        mood=request.mood,
        message=request.message,
        position=request.position,
        payload=request.payload,
        duration_seconds=request.duration_seconds,
    )
    record_companion_event(
        event_type=f"pet_{request.event}",
        detail=request.message or request.event,
        metadata={"activity": state.get("activity"), "mood": state.get("mood")},
    )
    return PetStateResponse(**state)


@app.get("/api/companion/summary", response_model=CompanionSummaryResponse)
async def companion_summary():
    return CompanionSummaryResponse(**get_companion_summary())


@app.post("/api/companion/check-in", response_model=CompanionSummaryResponse)
async def companion_check_in(request: CompanionCheckInRequest):
    record_daily_check_in(mood=request.mood or "", note=request.note or "")
    handle_pet_event(
        "reminder",
        mood="warm",
        message="Daily check-in saved. I will keep this in mind.",
        duration_seconds=12,
    )
    return CompanionSummaryResponse(**get_companion_summary())


@app.get("/api/mcp/status")
async def mcp_status():
    return get_mcp_status()


@app.get("/api/mcp/tools")
async def mcp_tools():
    return {"tools": list_mcp_tools(include_disabled=True)}


@app.post("/api/mcp/reload")
async def mcp_reload():
    return reload_mcp_config()


@app.post("/api/mcp/call")
async def mcp_call(request: McpToolCallRequest):
    if mcp_tool_requires_approval(request.tool_name):
        metadata = get_mcp_tool_metadata(request.tool_name)
        action = queue_mcp_action(
            tool_name=request.tool_name,
            arguments=request.arguments,
            title=f"Approve MCP action: {metadata.get('tool') or request.tool_name}",
            reason=metadata.get("description", ""),
            risk=metadata.get("risk", "medium"),
            source="api",
            requires_approval=True,
        )
        handle_pet_event(
            "action_queued",
            message=f"Action waiting for approval: {metadata.get('tool') or request.tool_name}",
            payload={"context": {"action_id": action["id"], "risk": action["risk"]}},
        )
        record_companion_event(
            "action_queued",
            action["title"],
            {"action_id": action["id"], "tool_name": request.tool_name},
        )
        return {"queued": True, "action": action}

    result = await call_mcp_tool_async(request.tool_name, request.arguments)
    return {"tool_name": request.tool_name, "result": result}


@app.get("/api/actions", response_model=ActionQueueResponse)
async def action_queue():
    return ActionQueueResponse(**get_action_queue_summary())


@app.post("/api/actions", response_model=ActionItem)
async def create_action(request: ActionCreateRequest):
    action = queue_mcp_action(
        tool_name=request.tool_name,
        arguments=request.arguments,
        title=request.title or "",
        reason=request.reason or "",
        risk=request.risk or "medium",
        source="api",
        requires_approval=request.requires_approval,
    )
    handle_pet_event(
        "action_queued",
        message=f"Action waiting for approval: {action['title']}",
        payload={"context": {"action_id": action["id"], "risk": action["risk"]}},
    )
    record_companion_event(
        "action_queued",
        action["title"],
        {"action_id": action["id"], "tool_name": action["tool_name"]},
    )
    return ActionItem(**action)


@app.post("/api/actions/{action_id}/approve", response_model=ActionItem)
async def approve_queued_action(action_id: str, request: ActionDecisionRequest):
    try:
        action = approve_action(action_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Action not found: {action_id}")
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))

    handle_pet_event(
        "action_approved",
        message=f"Approved: {action['title']}",
        payload={"context": {"action_id": action["id"]}},
    )

    if request.execute:
        return await run_queued_action(action_id)

    record_companion_event("action_approved", action["title"], {"action_id": action["id"]})
    return ActionItem(**action)


@app.post("/api/actions/{action_id}/reject", response_model=ActionItem)
async def reject_queued_action(action_id: str, request: ActionDecisionRequest):
    try:
        action = reject_action(action_id, request.reason or "")
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Action not found: {action_id}")
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))

    handle_pet_event(
        "action_rejected",
        message=f"Skipped: {action['title']}",
        payload={"context": {"action_id": action["id"]}},
        duration_seconds=10,
    )
    record_companion_event("action_rejected", action["title"], {"action_id": action["id"]})
    return ActionItem(**action)


@app.post("/api/actions/{action_id}/run", response_model=ActionItem)
async def run_queued_action(action_id: str):
    handle_pet_event(
        "action_started",
        message="Executing approved action...",
        payload={"context": {"action_id": action_id}},
    )
    try:
        action = await execute_action_async(action_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Action not found: {action_id}")
    except PermissionError as exc:
        handle_pet_event(
            "action_queued",
            message="This action still needs approval.",
            payload={"context": {"action_id": action_id}},
        )
        raise HTTPException(status_code=403, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))

    if action.get("status") == "succeeded":
        handle_pet_event(
            "action_succeeded",
            message=f"Done: {action['title']}",
            payload={"context": {"action_id": action["id"]}},
            duration_seconds=14,
        )
        record_companion_event("action_succeeded", action["title"], {"action_id": action["id"]})
    else:
        handle_pet_event(
            "action_failed",
            message=action.get("error") or f"Action failed: {action['title']}",
            payload={"context": {"action_id": action["id"]}},
        )
        record_companion_event(
            "action_failed",
            action.get("error") or action["title"],
            {"action_id": action["id"]},
        )

    return ActionItem(**action)


@app.get("/api/profile", response_model=ProfileResponse)
async def get_profile():
    profile = load_user_profile()
    return ProfileResponse(
        name=profile.get("name", ""),
        preferred_style=profile.get("preferred_style", ""),
        interests=profile.get("interests", []),
        current_projects=profile.get("current_projects", []),
        current_goals=profile.get("current_goals", []),
        workflow_preferences=profile.get("workflow_preferences", []),
        persona_notes=profile.get("persona_notes", ""),
    )


@app.get("/api/tasks", response_model=List[TaskItem])
async def get_tasks():
    tasks = load_tasks()
    return [TaskItem(id=t["id"], content=t["content"], status=t["status"]) for t in tasks]


@app.post("/api/tasks/{task_id}/status")
async def modify_task_status(task_id: int, request: TaskUpdateRequest):
    updated = update_task(task_id, {"status": request.status})
    if not updated:
        raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")
    return {"message": "Task updated"}


@app.delete("/api/tasks/{task_id}")
async def remove_task(task_id: int):
    deleted = delete_task(task_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")
    return {"message": "Task deleted"}


@app.get("/api/chat/history")
async def chat_history(session_id: str = "default"):
    normalized_session_id = _normalize_session_id(session_id)
    messages = get_session_messages(normalized_session_id)
    return {"session_id": normalized_session_id, "messages": messages}


@app.post("/api/chat/clear")
async def clear_chat(request: ClearRequest):
    session_id = _normalize_session_id(request.session_id)
    clear_chat_session(session_id)
    return {"message": "Chat session cleared", "session_id": session_id}


def _normalize_session_id(session_id: str) -> str:
    normalized = (session_id or "").strip()
    return normalized or "default"


def _validate_upload_filename(filename: str) -> str:
    suffix = os.path.splitext(filename or "")[-1].lower()
    if not suffix:
        raise HTTPException(status_code=400, detail="Uploaded file must include an extension.")

    allowed_suffixes = {f".{ext.lower().lstrip('.')}" for ext in settings.ALLOWED_FILE_TYPES}
    if suffix not in allowed_suffixes:
        allowed_text = ", ".join(sorted(allowed_suffixes))
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {suffix}. Allowed types: {allowed_text}",
        )

    return suffix


async def _save_upload_to_temp_file(file: UploadFile, suffix: str) -> str:
    settings.ensure_dirs()
    max_bytes = settings.MAX_FILE_SIZE_MB * 1024 * 1024
    total_size = 0
    temp_path = None

    try:
        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=suffix,
            dir=settings.TEMP_DIR,
        ) as tmp_file:
            temp_path = tmp_file.name

            while True:
                chunk = await file.read(UPLOAD_CHUNK_SIZE)
                if not chunk:
                    break

                total_size += len(chunk)
                if total_size > max_bytes:
                    raise HTTPException(
                        status_code=413,
                        detail=f"File too large. Maximum size is {settings.MAX_FILE_SIZE_MB} MB.",
                    )

                tmp_file.write(chunk)

        if total_size == 0:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")

        return temp_path

    except Exception:
        if temp_path and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except OSError:
                logger.warning("清理超限临时文件失败 | path=%s", temp_path)
        raise
    finally:
        await file.close()


def _update_memory_after_chat(session_id: str, user_input: str, output: str):
    # 更新对话摘要
    messages = get_session_messages(session_id)
    current_summary = get_session_summary(session_id)
    try:
        new_summary = summarize_messages_if_needed(messages, current_summary)
        if new_summary != current_summary:
            set_session_summary(new_summary, session_id)
    except Exception:
        logger.exception("更新会话摘要失败")

    # 触发事实提取反思
    reflect_on_interaction(user_input, output)


    reflect_on_interaction(user_input, output)


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, background_tasks: BackgroundTasks):
    session_id = _normalize_session_id(request.session_id)
    user_input = request.message

    if not user_input.strip() and not request.image_base64:
        raise HTTPException(status_code=400, detail="Empty message")

    handle_pet_event("chat_started")

    if request.image_base64:
        from knowledge.vision import describe_image_with_ollama
        handle_pet_event("vision_received")

        # Strip standard web base64 prefix if present
        b64_data = re.sub(r'^data:image/.+;base64,', '', request.image_base64)
        try:
            image_bytes = base64.b64decode(b64_data, validate=True)
            description = describe_image_with_ollama(image_bytes)
            if description:
                user_input += f"\n\n[用户提供了一张图片，本地 Ollama (qwen3-vl:8b) 的视觉分析结果如下：\n{description}\n请根据上述图片内容回答用户的问题。]"
        except Exception:
            logger.exception("解析图片 Base64 参数失败")
            raise HTTPException(status_code=400, detail="Invalid image payload.")

    append_user_message(user_input, session_id)
    
    messages = get_session_messages(session_id)
    summary = get_session_summary(session_id)
    history = get_chat_history_for_agent(
        messages=messages,
        summary=summary,
        exclude_last_user=True,
    )

    agent_executor = _app_state.get("agent_executor")
    if not agent_executor:
        logger.warning("Agent Core 未在启动阶段完成初始化，尝试按 general 路由懒加载")
        agent_executor = get_agent_executor_for_route("general")
        _app_state["agent_executor"] = agent_executor

    try:
        result = run_agent(
            agent_executor=agent_executor,
            user_input=user_input,
            chat_history=history,
        )
        
        raw_output = result["output"]
        image_paths = result.get("image_paths", [])

        # Strip any <thought_plan>...</thought_plan> tags silently before saving
        answer_text = re.sub(r"<thought_plan>.*?</thought_plan>", "", raw_output, flags=re.DOTALL).strip()
        if not answer_text:
            answer_text = raw_output.strip()

        append_assistant_message(answer_text, session_id)
        record_companion_event(
            "chat",
            user_input[:180],
            {"answer_preview": answer_text[:180], "session_id": session_id},
        )
        handle_pet_event(
            "chat_completed",
            message=answer_text[:180],
            duration_seconds=18,
        )

        # 添加后台任务更新记忆和摘要
        background_tasks.add_task(_update_memory_after_chat, session_id, user_input, answer_text)

        background_tasks.add_task(_update_memory_after_chat, session_id, user_input, answer_text)

        return ChatResponse(
            session_id=session_id,
            answer=answer_text,
            thought_plan=None,
            image_paths=image_paths
        )

    except Exception as e:
        handle_pet_event(
            "error",
            message=str(e)[:180],
        )
        logger.exception("执行智能体失败")
        record_companion_event("chat_error", str(e)[:220], {"session_id": session_id})
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/knowledge", response_model=List[DocumentItem])
async def get_documents():
    try:
        records = list_documents()
        return [DocumentItem(**item) for item in records]
    except Exception as e:
        logger.exception("读取文档列表失败")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/knowledge/{doc_id}")
async def delete_document(doc_id: str):
    vectorstore = _app_state.get("vectorstore")
    if not vectorstore:
        logger.warning("Vectorstore 未在启动阶段完成初始化，尝试懒加载")
        vectorstore = get_vectorstore()
        _app_state["vectorstore"] = vectorstore
    
    try:
        result = delete_document_from_vectorstore(vectorstore, doc_id)
        if result.get("status") == "not_found":
            raise HTTPException(status_code=404, detail="Document not found")
        return {"message": "Document deleted", "result": result}
    except Exception as e:
        logger.exception("删除文档失败")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/knowledge/upload", response_model=DocumentUploadResponse)
async def upload_document(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file selected")

    vectorstore = _app_state.get("vectorstore")
    if not vectorstore:
        logger.warning("Vectorstore 未在启动阶段完成初始化，尝试懒加载")
        vectorstore = get_vectorstore()
        _app_state["vectorstore"] = vectorstore

    temp_path = None
    
    try:
        suffix = _validate_upload_filename(file.filename)
        temp_path = await _save_upload_to_temp_file(file, suffix)

        result = ingest_file_to_vectorstore(temp_path, vectorstore, original_filename=file.filename)
        
        # 兼容原来的返回结构
        status = result.get("status", "unknown")
        if status == "success":
            return DocumentUploadResponse(
                status=status,
                doc_id=result.get("doc_id"),
                document_count=result.get("document_count"),
                chunk_count=result.get("chunk_count"),
                message=f"Successfully ingested {file.filename}"
            )
        elif status == "skipped_duplicate":
            return DocumentUploadResponse(
                status=status,
                doc_id=result.get("doc_id"),
                message=f"Skipped duplicate document: {file.filename}"
            )
        else:
            return DocumentUploadResponse(
                status=status,
                message=f"File processing returned state: {status}"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("文档上传和处理失败")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except Exception:
                pass


@app.post("/api/wisdom/consolidate")
async def consolidate_wisdom():
    from memory.wisdom import consolidate_wisdom as consolidate_func
    try:
        result = consolidate_func()
        return {"message": "Wisdom consolidation complete", "details": result}
    except Exception as e:
        logger.exception("提炼智慧失败")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    # run programmatically primarily for testing, standard execution via: uvicorn main:app --reload
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
