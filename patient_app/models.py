"""
AI-CARE Lung 病人端 - 資料模型 v2.0
=====================================
更新內容：
1. 分離病人輸入 vs AI 回應
2. 支援開放式問題收集
3. 整合專家回應範本
4. 為未來 NLP 標註準備

三軍總醫院 數位醫療中心
"""

from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Optional, Dict, List, Any
from enum import Enum
import uuid

# ============================================
# 列舉類型
# ============================================

class SymptomType(Enum):
    """症狀類型"""
    PAIN = "pain"
    FATIGUE = "fatigue"
    DYSPNEA = "dyspnea"
    COUGH = "cough"
    SLEEP = "sleep"
    APPETITE = "appetite"
    MOOD = "mood"

class ScoreLevel(Enum):
    """分數等級"""
    NONE = "none"           # 0
    MILD = "mild"           # 1-3
    MODERATE = "moderate"   # 4-6
    SEVERE = "severe"       # 7-10

class ReportMethod(Enum):
    """回報方式"""
    AI_CHAT = "ai_chat"
    QUESTIONNAIRE = "questionnaire"
    VOICE = "voice"

class ReminderLevel(Enum):
    """提醒等級"""
    APP_PUSH = "app_push"       # 0 天未完成
    LINE_MESSAGE = "line_msg"   # 1 天未完成
    PHONE_CALL = "phone_call"   # 2 天未完成
    HOME_VISIT = "home_visit"   # 3+ 天未完成

class AchievementType(Enum):
    """成就類型"""
    STREAK = "streak"           # 連續天數
    COMPLETION = "completion"   # 完成次數
    SPECIAL = "special"         # 特殊成就


# ============================================
# 新增：對話相關列舉
# ============================================

class MessageRole(Enum):
    """訊息角色"""
    PATIENT = "patient"         # 病人輸入
    AI_ASSISTANT = "ai_assistant"  # AI 回應
    SYSTEM = "system"           # 系統訊息

class MessageSource(Enum):
    """訊息來源"""
    PATIENT_RAW_INPUT = "patient_raw_input"     # 病人原始輸入
    PATIENT_BUTTON_CLICK = "patient_button"     # 病人點擊按鈕
    AI_GENERATED = "ai_generated"               # AI 生成
    EXPERT_TEMPLATE = "expert_template"         # 專家範本
    SYSTEM_AUTO = "system_auto"                 # 系統自動生成

class IntentCategory(Enum):
    """意圖分類（預設，待標註確認）"""
    SYMPTOM_REPORT = "symptom_report"           # 症狀回報
    SYMPTOM_INQUIRY = "symptom_inquiry"         # 症狀諮詢
    MEDICATION_QUESTION = "medication_question" # 藥物問題
    LIFESTYLE_ADVICE = "lifestyle_advice"       # 生活建議
    EMOTIONAL_EXPRESSION = "emotional_expression" # 情緒表達
    APPOINTMENT_RELATED = "appointment_related" # 預約相關
    EMERGENCY = "emergency"                     # 緊急求助
    GRATITUDE = "gratitude"                     # 感謝
    GREETING = "greeting"                       # 打招呼
    OTHER = "other"                             # 其他
    UNKNOWN = "unknown"                         # 未分類

class EmotionCategory(Enum):
    """情緒分類（預設，待標註確認）"""
    ANXIOUS = "anxious"         # 焦慮/擔心
    DEPRESSED = "depressed"     # 低落/沮喪
    NEUTRAL = "neutral"         # 平靜/中性
    POSITIVE = "positive"       # 正向/感謝
    ANGRY = "angry"             # 憤怒/不滿
    UNKNOWN = "unknown"         # 未分類

class UrgencyLevel(Enum):
    """緊急程度"""
    EMERGENCY = 1       # 緊急：需立即處理
    IMPORTANT = 2       # 重要：24小時內處理
    NORMAL = 3          # 一般：常規追蹤
    INFORMATIONAL = 4   # 資訊：僅供參考


# ============================================
# 新增：對話訊息類別
# ============================================

@dataclass
class ConversationMessage:
    """
    對話訊息 - 分離儲存病人輸入和 AI 回應
    
    這是為了未來 NLP 訓練準備的核心資料結構
    """
    message_id: str
    session_id: str
    patient_id: str
    
    # 訊息內容
    role: MessageRole
    content: str                        # 訊息內容
    source: MessageSource               # 訊息來源
    
    # 時間戳記
    timestamp: datetime = field(default_factory=datetime.now)
    
    # 如果是病人輸入，記錄額外資訊
    input_method: Optional[str] = None  # text, button, voice
    raw_input: Optional[str] = None     # 原始輸入（未處理）
    
    # 如果是 AI/專家回應，記錄來源
    template_id: Optional[str] = None   # 使用的範本 ID
    ai_model: Optional[str] = None      # 使用的 AI 模型
    
    # 預設標註（待人工確認）
    detected_intent: IntentCategory = IntentCategory.UNKNOWN
    detected_emotion: EmotionCategory = EmotionCategory.UNKNOWN
    detected_urgency: UrgencyLevel = UrgencyLevel.NORMAL
    
    # 人工標註欄位（供標註團隊使用）
    annotated_intent: Optional[str] = None
    annotated_emotion: Optional[str] = None
    annotated_urgency: Optional[int] = None
    annotated_entities: Optional[List[Dict]] = None  # NER 標註
    annotator_id: Optional[str] = None
    annotation_time: Optional[datetime] = None
    
    # 品質評分（供標註團隊使用）
    response_quality_score: Optional[int] = None  # 1-5 分
    needs_human_review: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典（用於儲存）"""
        return {
            "message_id": self.message_id,
            "session_id": self.session_id,
            "patient_id": self.patient_id,
            "role": self.role.value,
            "content": self.content,
            "source": self.source.value,
            "timestamp": self.timestamp.isoformat(),
            "input_method": self.input_method,
            "raw_input": self.raw_input,
            "template_id": self.template_id,
            "ai_model": self.ai_model,
            "detected_intent": self.detected_intent.value,
            "detected_emotion": self.detected_emotion.value,
            "detected_urgency": self.detected_urgency.value,
            "annotated_intent": self.annotated_intent,
            "annotated_emotion": self.annotated_emotion,
            "annotated_urgency": self.annotated_urgency,
            "annotated_entities": self.annotated_entities,
            "annotator_id": self.annotator_id,
            "annotation_time": self.annotation_time.isoformat() if self.annotation_time else None,
            "response_quality_score": self.response_quality_score,
            "needs_human_review": self.needs_human_review
        }


@dataclass
class ConversationSession:
    """
    對話會話 - 記錄一次完整的對話過程
    """
    session_id: str
    patient_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    
    # 會話類型
    session_type: str = "daily_report"  # daily_report, inquiry, follow_up
    
    # 訊息列表
    messages: List[ConversationMessage] = field(default_factory=list)
    
    # 會話狀態
    is_completed: bool = False
    completion_type: Optional[str] = None  # completed, abandoned, transferred
    
    # 統計資訊
    total_patient_messages: int = 0
    total_ai_messages: int = 0
    total_words_patient: int = 0
    
    # 關聯的回報
    linked_report_id: Optional[str] = None
    
    def add_message(self, message: ConversationMessage):
        """新增訊息並更新統計"""
        self.messages.append(message)
        
        if message.role == MessageRole.PATIENT:
            self.total_patient_messages += 1
            self.total_words_patient += len(message.content)
        elif message.role == MessageRole.AI_ASSISTANT:
            self.total_ai_messages += 1
    
    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典"""
        return {
            "session_id": self.session_id,
            "patient_id": self.patient_id,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "session_type": self.session_type,
            "messages": [m.to_dict() for m in self.messages],
            "is_completed": self.is_completed,
            "completion_type": self.completion_type,
            "total_patient_messages": self.total_patient_messages,
            "total_ai_messages": self.total_ai_messages,
            "total_words_patient": self.total_words_patient,
            "linked_report_id": self.linked_report_id
        }


# ============================================
# 新增：開放式問題回應
# ============================================

@dataclass
class OpenEndedResponse:
    """
    開放式問題回應 - 收集病人自然語言描述
    
    這是最有價值的 NLP 訓練資料來源
    """
    response_id: str
    patient_id: str
    report_id: str
    
    # 問題資訊
    question_id: str
    question_text: str
    question_category: str  # symptom_description, daily_impact, additional_concerns
    
    # 病人回應
    response_text: str
    response_time: datetime = field(default_factory=datetime.now)
    
    # 輸入方式
    input_method: str = "text"  # text, voice
    
    # 字數統計
    word_count: int = 0
    char_count: int = 0
    
    # 預設分析（自動偵測）
    detected_symptoms: List[str] = field(default_factory=list)
    detected_severity: Optional[str] = None
    detected_emotion: Optional[str] = None
    
    # 人工標註欄位
    annotated_entities: Optional[List[Dict]] = None
    annotation_notes: Optional[str] = None
    
    def __post_init__(self):
        """計算字數"""
        self.word_count = len(self.response_text.split())
        self.char_count = len(self.response_text)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "response_id": self.response_id,
            "patient_id": self.patient_id,
            "report_id": self.report_id,
            "question_id": self.question_id,
            "question_text": self.question_text,
            "question_category": self.question_category,
            "response_text": self.response_text,
            "response_time": self.response_time.isoformat(),
            "input_method": self.input_method,
            "word_count": self.word_count,
            "char_count": self.char_count,
            "detected_symptoms": self.detected_symptoms,
            "detected_severity": self.detected_severity,
            "detected_emotion": self.detected_emotion,
            "annotated_entities": self.annotated_entities,
            "annotation_notes": self.annotation_notes
        }


# ============================================
# 新增：專家回應範本
# ============================================

@dataclass
class ExpertResponseTemplate:
    """
    專家回應範本 - 由護理師/醫師撰寫
    
    用於取代 AI 生成的回應，或作為 RAG 知識庫
    """
    template_id: str
    
    # 範本內容
    category: str               # 分類：symptom_response, medication, lifestyle, emotional
    scenario_name: str          # 情境名稱
    trigger_conditions: Dict[str, Any]  # 觸發條件
    
    # 回應內容
    response_template: str      # 主要回應範本
    response_variations: List[str] = field(default_factory=list)  # 變體
    
    # 觸發關鍵字
    trigger_keywords: List[str] = field(default_factory=list)
    
    # 後續動作
    follow_up_actions: List[str] = field(default_factory=list)  # alert_nurse, suggest_meds, etc.
    
    # 作者資訊
    author_id: str = ""
    author_name: str = ""
    author_role: str = ""       # nurse, physician, pharmacist
    
    # 審核資訊
    reviewed_by: Optional[str] = None
    review_date: Optional[date] = None
    is_approved: bool = False
    
    # 使用統計
    use_count: int = 0
    last_used: Optional[datetime] = None
    
    # 元資料
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    version: int = 1
    is_active: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "template_id": self.template_id,
            "category": self.category,
            "scenario_name": self.scenario_name,
            "trigger_conditions": self.trigger_conditions,
            "response_template": self.response_template,
            "response_variations": self.response_variations,
            "trigger_keywords": self.trigger_keywords,
            "follow_up_actions": self.follow_up_actions,
            "author_id": self.author_id,
            "author_name": self.author_name,
            "author_role": self.author_role,
            "reviewed_by": self.reviewed_by,
            "review_date": self.review_date.isoformat() if self.review_date else None,
            "is_approved": self.is_approved,
            "use_count": self.use_count,
            "last_used": self.last_used.isoformat() if self.last_used else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "version": self.version,
            "is_active": self.is_active
        }


# ============================================
# 原有資料類別（保留並更新）
# ============================================

@dataclass
class Patient:
    """病人資料"""
    patient_id: str
    name: str
    gender: str
    birth_date: date
    phone: str
    surgery_date: date
    surgery_type: str
    cancer_stage: str
    
    @property
    def post_op_day(self) -> int:
        return (datetime.now().date() - self.surgery_date).days
    
    @property
    def age(self) -> int:
        today = datetime.now().date()
        return today.year - self.birth_date.year - (
            (today.month, today.day) < (self.birth_date.month, self.birth_date.day)
        )


@dataclass
class SymptomScore:
    """症狀分數"""
    symptom_type: SymptomType
    score: int
    timestamp: datetime = field(default_factory=datetime.now)
    
    # 新增：病人描述
    patient_description: Optional[str] = None  # 病人對此症狀的文字描述
    
    @property
    def level(self) -> ScoreLevel:
        if self.score == 0:
            return ScoreLevel.NONE
        elif self.score <= 3:
            return ScoreLevel.MILD
        elif self.score <= 6:
            return ScoreLevel.MODERATE
        else:
            return ScoreLevel.SEVERE
    
    @property
    def level_label(self) -> str:
        labels = {
            ScoreLevel.NONE: "無症狀",
            ScoreLevel.MILD: "輕度",
            ScoreLevel.MODERATE: "中度",
            ScoreLevel.SEVERE: "重度"
        }
        return labels.get(self.level, "未知")
    
    @property
    def level_color(self) -> str:
        colors = {
            ScoreLevel.NONE: "#10b981",
            ScoreLevel.MILD: "#22c55e",
            ScoreLevel.MODERATE: "#f59e0b",
            ScoreLevel.SEVERE: "#ef4444"
        }
        return colors.get(self.level, "#9ca3af")


@dataclass
class DailyReport:
    """
    每日回報 - 更新版
    
    新增：
    - 對話會話 ID
    - 開放式問題回應
    - 病人原始輸入記錄
    """
    report_id: str
    patient_id: str
    report_date: date
    report_time: datetime
    method: ReportMethod
    scores: Dict[SymptomType, int]
    
    # 新增欄位
    conversation_session_id: Optional[str] = None   # 關聯的對話會話
    open_ended_responses: List[str] = field(default_factory=list)  # 開放式回應 ID 列表
    
    # 症狀描述（結構化）
    symptom_descriptions: Dict[str, str] = field(default_factory=dict)  # {symptom_id: description}
    
    # AI 摘要
    ai_summary: Optional[str] = None
    
    # 警示
    alert_triggered: bool = False
    alert_reasons: List[str] = field(default_factory=list)
    
    # 回應來源追蹤
    response_sources: Dict[str, str] = field(default_factory=dict)  # {message_id: source_type}
    
    @property
    def total_score(self) -> int:
        return sum(self.scores.values())
    
    @property
    def avg_score(self) -> float:
        if not self.scores:
            return 0.0
        return sum(self.scores.values()) / len(self.scores)
    
    @property
    def has_severe_symptom(self) -> bool:
        return any(score >= 7 for score in self.scores.values())
    
    @property
    def has_patient_descriptions(self) -> bool:
        """是否有病人文字描述"""
        return len(self.symptom_descriptions) > 0 or len(self.open_ended_responses) > 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id,
            "patient_id": self.patient_id,
            "report_date": self.report_date.isoformat(),
            "report_time": self.report_time.isoformat(),
            "method": self.method.value,
            "scores": {k.value: v for k, v in self.scores.items()},
            "conversation_session_id": self.conversation_session_id,
            "open_ended_responses": self.open_ended_responses,
            "symptom_descriptions": self.symptom_descriptions,
            "ai_summary": self.ai_summary,
            "alert_triggered": self.alert_triggered,
            "alert_reasons": self.alert_reasons,
            "response_sources": self.response_sources
        }


@dataclass
class ComplianceStats:
    """順從度統計"""
    patient_id: str
    current_streak: int = 0
    best_streak: int = 0
    total_completed: int = 0
    total_days: int = 0
    total_points: int = 0
    level: int = 1
    
    @property
    def completion_rate(self) -> float:
        if self.total_days == 0:
            return 0.0
        return (self.total_completed / self.total_days) * 100
    
    @property
    def level_progress(self) -> float:
        thresholds = [0, 50, 150, 300, 500, 800, 1200]
        if self.level >= len(thresholds) - 1:
            return 1.0
        
        prev = thresholds[self.level - 1] if self.level > 0 else 0
        next_t = thresholds[self.level]
        
        return min((self.total_points - prev) / (next_t - prev), 1.0)
    
    def add_points(self, points: int):
        self.total_points += points
        
        thresholds = [0, 50, 150, 300, 500, 800, 1200]
        for i, threshold in enumerate(thresholds):
            if self.total_points >= threshold:
                self.level = i + 1


@dataclass
class Achievement:
    """成就"""
    achievement_id: str
    name: str
    description: str
    icon: str
    achievement_type: AchievementType
    requirement: int
    points: int
    unlocked: bool = False
    unlocked_date: Optional[date] = None
    
    def check_unlock(self, stats: ComplianceStats) -> bool:
        if self.unlocked:
            return False
        
        if self.achievement_type == AchievementType.STREAK:
            return stats.current_streak >= self.requirement
        elif self.achievement_type == AchievementType.COMPLETION:
            return stats.total_completed >= self.requirement
        
        return False
    
    def unlock(self):
        self.unlocked = True
        self.unlocked_date = datetime.now().date()


@dataclass
class Reminder:
    """提醒"""
    reminder_id: str
    patient_id: str
    reminder_level: ReminderLevel
    scheduled_time: datetime
    sent: bool = False
    sent_time: Optional[datetime] = None
    response_received: bool = False
    
    @property
    def is_overdue(self) -> bool:
        return datetime.now() > self.scheduled_time and not self.sent


# ============================================
# 開放式問題定義
# ============================================

OPEN_ENDED_QUESTIONS = [
    {
        "question_id": "daily_feeling",
        "question_text": "請用您自己的話描述一下，今天整體感覺如何？",
        "category": "daily_impact",
        "required": False,
        "show_after_scores": True,
        "hint": "例如：今天走路比較喘、傷口還是會痛、睡得不太好..."
    },
    {
        "question_id": "symptom_detail",
        "question_text": "您今天有什麼症狀特別想跟我們說的嗎？",
        "category": "symptom_description",
        "required": False,
        "show_after_scores": True,
        "hint": "可以描述症狀的位置、時間、什麼情況下會加重或減輕..."
    },
    {
        "question_id": "daily_activity",
        "question_text": "今天的日常活動有受到影響嗎？",
        "category": "daily_impact",
        "required": False,
        "show_after_scores": True,
        "hint": "例如：走路、上下樓梯、做家事、工作等..."
    },
    {
        "question_id": "additional_concerns",
        "question_text": "還有其他想問的問題或擔心的事情嗎？",
        "category": "additional_concerns",
        "required": False,
        "show_after_scores": True,
        "hint": "任何關於恢復、用藥、生活的問題都可以提出..."
    }
]


# ============================================
# 預設成就列表
# ============================================

DEFAULT_ACHIEVEMENTS = [
    Achievement(
        achievement_id="first_report",
        name="初次回報",
        description="完成第一次症狀回報",
        icon="🌟",
        achievement_type=AchievementType.COMPLETION,
        requirement=1,
        points=10
    ),
    Achievement(
        achievement_id="streak_3",
        name="連續3天",
        description="連續3天完成回報",
        icon="🌱",
        achievement_type=AchievementType.STREAK,
        requirement=3,
        points=10
    ),
    Achievement(
        achievement_id="streak_7",
        name="連續7天",
        description="連續7天完成回報",
        icon="🔥",
        achievement_type=AchievementType.STREAK,
        requirement=7,
        points=30
    ),
    Achievement(
        achievement_id="streak_14",
        name="連續14天",
        description="連續14天完成回報",
        icon="⭐",
        achievement_type=AchievementType.STREAK,
        requirement=14,
        points=50
    ),
    Achievement(
        achievement_id="streak_21",
        name="連續21天",
        description="連續21天完成回報",
        icon="🏅",
        achievement_type=AchievementType.STREAK,
        requirement=21,
        points=80
    ),
    Achievement(
        achievement_id="streak_30",
        name="連續30天",
        description="連續30天完成回報",
        icon="🏆",
        achievement_type=AchievementType.STREAK,
        requirement=30,
        points=150
    ),
    Achievement(
        achievement_id="complete_50",
        name="完成50次",
        description="累積完成50次回報",
        icon="💎",
        achievement_type=AchievementType.COMPLETION,
        requirement=50,
        points=100
    ),
    Achievement(
        achievement_id="complete_90",
        name="完成90次",
        description="累積完成90次回報",
        icon="👑",
        achievement_type=AchievementType.COMPLETION,
        requirement=90,
        points=200
    ),
    # 新增：開放式回報成就
    Achievement(
        achievement_id="first_description",
        name="詳細描述者",
        description="首次填寫開放式問題",
        icon="✍️",
        achievement_type=AchievementType.SPECIAL,
        requirement=1,
        points=15
    ),
]


# ============================================
# 症狀定義
# ============================================

SYMPTOM_DEFINITIONS = {
    SymptomType.PAIN: {
        "name": "疼痛",
        "icon": "🩹",
        "question": "今天傷口或胸部的疼痛程度如何？",
        "keywords": ["痛", "疼", "刺痛", "悶痛", "脹痛", "傷口"],
        "follow_up_prompt": "可以描述一下疼痛的位置和感覺嗎？"
    },
    SymptomType.FATIGUE: {
        "name": "疲勞",
        "icon": "😮‍💨",
        "question": "今天感覺疲勞或虛弱嗎？",
        "keywords": ["累", "疲", "沒力", "虛弱", "倦怠"],
        "follow_up_prompt": "疲勞有影響到您的日常活動嗎？"
    },
    SymptomType.DYSPNEA: {
        "name": "呼吸困難",
        "icon": "💨",
        "question": "今天呼吸順暢嗎？有沒有喘或胸悶？",
        "keywords": ["喘", "呼吸", "氣促", "胸悶", "透不過氣"],
        "follow_up_prompt": "什麼情況下會比較喘？休息時還是活動時？"
    },
    SymptomType.COUGH: {
        "name": "咳嗽",
        "icon": "🤧",
        "question": "今天咳嗽的情況如何？",
        "keywords": ["咳", "痰", "咳嗽", "乾咳"],
        "follow_up_prompt": "咳嗽有痰嗎？痰的顏色是什麼？"
    },
    SymptomType.SLEEP: {
        "name": "睡眠",
        "icon": "😴",
        "question": "昨晚睡得好嗎？",
        "keywords": ["睡", "失眠", "睡眠", "睡不著", "睡不好"],
        "follow_up_prompt": "大約睡了幾個小時？有什麼原因影響睡眠嗎？"
    },
    SymptomType.APPETITE: {
        "name": "食慾",
        "icon": "🍽️",
        "question": "今天胃口怎麼樣？",
        "keywords": ["吃", "食", "胃口", "食慾", "沒胃口"],
        "follow_up_prompt": "今天有正常吃三餐嗎？"
    },
    SymptomType.MOOD: {
        "name": "心情",
        "icon": "💭",
        "question": "今天心情如何？有沒有焦慮或擔心？",
        "keywords": ["心情", "情緒", "焦慮", "擔心", "害怕", "憂鬱"],
        "follow_up_prompt": "有什麼特別讓您擔心或困擾的事嗎？"
    }
}


# ============================================
# 輔助函數
# ============================================

def generate_message_id() -> str:
    """生成訊息 ID"""
    return f"msg_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}"

def generate_session_id() -> str:
    """生成會話 ID"""
    return f"sess_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}"

def generate_response_id() -> str:
    """生成回應 ID"""
    return f"resp_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}"

def generate_report_id() -> str:
    """生成回報 ID"""
    return f"rpt_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}"
