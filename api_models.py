from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class ChatRequest(BaseModel):
    session_id: str = Field(default="default", description="会话标识")
    message: str = Field(..., description="用户的输入消息")
    image_base64: Optional[str] = Field(None, description="可选的Base64编码的图片")

class ChatResponse(BaseModel):
    session_id: str
    answer: str = Field(..., description="助理回复的最终内容")
    thought_plan: Optional[str] = Field(None, description="助理的内部思考或计划内容")
    image_paths: List[str] = Field(default_factory=list, description="产生的相关图片")

class ClearRequest(BaseModel):
    session_id: str = Field(default="default", description="会话标识")

class HealthResponse(BaseModel):
    status: str
    details: Dict[str, Any]

class DocumentItem(BaseModel):
    doc_id: str
    source_file: str
    doc_type: str
    document_count: int
    chunk_count: int
    ingest_time: str

class DocumentUploadResponse(BaseModel):
    status: str
    doc_id: Optional[str] = None
    document_count: Optional[int] = None
    chunk_count: Optional[int] = None
    message: Optional[str] = None

class ProfileResponse(BaseModel):
    name: str = ""
    preferred_style: str = ""
    interests: List[str] = []
    current_projects: List[str] = []
    current_goals: List[str] = []
    workflow_preferences: List[str] = []
    persona_notes: str = ""

class TaskItem(BaseModel):
    id: int
    content: str
    status: str

class TaskUpdateRequest(BaseModel):
    status: str

class PetStateResponse(BaseModel):
    activity: str = "idle"
    mood: str = "calm"
    message: str = ""
    last_event: str = "boot"
    updated_at: str = ""
    expires_at: str = ""
    position: Dict[str, int] = Field(default_factory=lambda: {"x": 80, "y": 80})
    context: Dict[str, Any] = Field(default_factory=dict)
    display: Dict[str, Any] = Field(default_factory=dict)
    allowed_events: List[str] = Field(default_factory=list)

class PetEventRequest(BaseModel):
    event: str
    activity: Optional[str] = None
    mood: Optional[str] = None
    message: Optional[str] = None
    position: Optional[Dict[str, int]] = None
    payload: Optional[Dict[str, Any]] = None
    duration_seconds: Optional[int] = None

class McpToolCallRequest(BaseModel):
    tool_name: str
    arguments: Dict[str, Any] = Field(default_factory=dict)

class CompanionCheckInRequest(BaseModel):
    mood: Optional[str] = ""
    note: Optional[str] = ""

class CompanionSummaryResponse(BaseModel):
    pet_name: str = "Maple"
    pet_persona: str = ""
    pet_tone: str = "warm"
    pet_theme: str = "mint"
    started_at: str = ""
    last_seen_at: str = ""
    days_together: int = 1
    interaction_count: int = 0
    chat_count: int = 0
    pet_event_count: int = 0
    checkin_streak: int = 0
    checked_in_today: bool = False
    recent_checkin: Optional[Dict[str, Any]] = None
    recent_moments: List[Dict[str, Any]] = Field(default_factory=list)
    active_task_count: int = 0
    next_task: Optional[Dict[str, Any]] = None
    document_count: int = 0
    level: int = 1
    affinity: int = 0
    greeting: str = ""
    nudges: List[str] = Field(default_factory=list)

class ActionCreateRequest(BaseModel):
    tool_name: str
    arguments: Dict[str, Any] = Field(default_factory=dict)
    title: Optional[str] = None
    reason: Optional[str] = None
    risk: Optional[str] = "medium"
    requires_approval: bool = True

class ActionDecisionRequest(BaseModel):
    reason: Optional[str] = ""
    execute: bool = True

class ActionItem(BaseModel):
    id: str
    kind: str = "mcp_tool"
    title: str
    tool_name: str
    arguments: Dict[str, Any] = Field(default_factory=dict)
    risk: str = "medium"
    reason: str = ""
    source: str = "agent"
    requires_approval: bool = True
    status: str = "pending_approval"
    created_at: str = ""
    updated_at: str = ""
    approved_at: str = ""
    completed_at: str = ""
    result: str = ""
    error: str = ""

class ActionQueueResponse(BaseModel):
    actions: List[ActionItem] = Field(default_factory=list)
    counts: Dict[str, int] = Field(default_factory=dict)
    pending_count: int = 0
    running_count: int = 0
    recent_count: int = 0

class AppSettingsRequest(BaseModel):
    model: Optional[Dict[str, Any]] = None
    knowledge: Optional[Dict[str, Any]] = None
    pet: Optional[Dict[str, Any]] = None
    mcp: Optional[Dict[str, Any]] = None

class DailyReportResponse(BaseModel):
    date: str
    content: str
    path: str = ""
    exists: bool = False
    created: bool = False
    updated: bool = False
    summary: Dict[str, Any] = Field(default_factory=dict)

class LogsResponse(BaseModel):
    app: List[str] = Field(default_factory=list)
    electron_backend: List[str] = Field(default_factory=list)
