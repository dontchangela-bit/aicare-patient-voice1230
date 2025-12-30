"""
AI-CARE Lung 病人端 - 對話儲存與分析模組
==========================================
功能：
1. 分離儲存病人輸入 vs AI 回應
2. 對話會話管理
3. 簡易 NLP 前處理（為未來標註準備）
4. 資料匯出（供標註團隊使用）

三軍總醫院 數位醫療中心
"""

import json
import re
from datetime import datetime, date
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
import uuid

from models import (
    ConversationMessage, ConversationSession, OpenEndedResponse,
    MessageRole, MessageSource, IntentCategory, EmotionCategory, UrgencyLevel,
    generate_message_id, generate_session_id, generate_response_id,
    SYMPTOM_DEFINITIONS, SymptomType
)


class ConversationStore:
    """
    對話儲存管理器
    
    負責：
    - 建立和管理對話會話
    - 分離儲存病人輸入和 AI 回應
    - 匯出標註資料
    """
    
    def __init__(self):
        # 記憶體儲存（實際部署時改為資料庫）
        self.sessions: Dict[str, ConversationSession] = {}
        self.messages: Dict[str, ConversationMessage] = {}
        self.open_ended_responses: Dict[str, OpenEndedResponse] = {}
        
        # 當前活躍會話
        self.active_session_id: Optional[str] = None
    
    # ============================================
    # 會話管理
    # ============================================
    
    def start_session(self, patient_id: str, session_type: str = "daily_report") -> ConversationSession:
        """開始新的對話會話"""
        session = ConversationSession(
            session_id=generate_session_id(),
            patient_id=patient_id,
            start_time=datetime.now(),
            session_type=session_type
        )
        
        self.sessions[session.session_id] = session
        self.active_session_id = session.session_id
        
        return session
    
    def end_session(self, session_id: str, completion_type: str = "completed"):
        """結束對話會話"""
        if session_id in self.sessions:
            session = self.sessions[session_id]
            session.end_time = datetime.now()
            session.is_completed = True
            session.completion_type = completion_type
            
            if self.active_session_id == session_id:
                self.active_session_id = None
    
    def get_current_session(self) -> Optional[ConversationSession]:
        """取得當前活躍會話"""
        if self.active_session_id:
            return self.sessions.get(self.active_session_id)
        return None
    
    # ============================================
    # 訊息管理
    # ============================================
    
    def add_patient_message(
        self,
        patient_id: str,
        content: str,
        input_method: str = "text",
        raw_input: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> ConversationMessage:
        """
        新增病人訊息
        
        這是最有價值的資料，完整保存原始輸入
        """
        if session_id is None:
            session_id = self.active_session_id
        
        # 自動偵測意圖和情緒
        detected_intent = self._detect_intent(content)
        detected_emotion = self._detect_emotion(content)
        detected_urgency = self._detect_urgency(content)
        
        message = ConversationMessage(
            message_id=generate_message_id(),
            session_id=session_id or "",
            patient_id=patient_id,
            role=MessageRole.PATIENT,
            content=content,
            source=MessageSource.PATIENT_RAW_INPUT if raw_input else MessageSource.PATIENT_BUTTON_CLICK,
            input_method=input_method,
            raw_input=raw_input or content,
            detected_intent=detected_intent,
            detected_emotion=detected_emotion,
            detected_urgency=detected_urgency,
            needs_human_review=detected_urgency == UrgencyLevel.EMERGENCY
        )
        
        self.messages[message.message_id] = message
        
        # 加入會話
        if session_id and session_id in self.sessions:
            self.sessions[session_id].add_message(message)
        
        return message
    
    def add_ai_message(
        self,
        patient_id: str,
        content: str,
        source: MessageSource = MessageSource.AI_GENERATED,
        template_id: Optional[str] = None,
        ai_model: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> ConversationMessage:
        """
        新增 AI/系統訊息
        
        記錄回應來源，區分 AI 生成 vs 專家範本
        """
        if session_id is None:
            session_id = self.active_session_id
        
        message = ConversationMessage(
            message_id=generate_message_id(),
            session_id=session_id or "",
            patient_id=patient_id,
            role=MessageRole.AI_ASSISTANT,
            content=content,
            source=source,
            template_id=template_id,
            ai_model=ai_model
        )
        
        self.messages[message.message_id] = message
        
        # 加入會話
        if session_id and session_id in self.sessions:
            self.sessions[session_id].add_message(message)
        
        return message
    
    # ============================================
    # 開放式問題回應
    # ============================================
    
    def add_open_ended_response(
        self,
        patient_id: str,
        report_id: str,
        question_id: str,
        question_text: str,
        question_category: str,
        response_text: str,
        input_method: str = "text"
    ) -> OpenEndedResponse:
        """新增開放式問題回應"""
        
        # 自動偵測症狀關鍵字
        detected_symptoms = self._extract_symptoms(response_text)
        detected_emotion = self._detect_emotion(response_text).value
        
        response = OpenEndedResponse(
            response_id=generate_response_id(),
            patient_id=patient_id,
            report_id=report_id,
            question_id=question_id,
            question_text=question_text,
            question_category=question_category,
            response_text=response_text,
            input_method=input_method,
            detected_symptoms=detected_symptoms,
            detected_emotion=detected_emotion
        )
        
        self.open_ended_responses[response.response_id] = response
        
        return response
    
    # ============================================
    # 簡易 NLP 偵測（為未來標註準備）
    # ============================================
    
    def _detect_intent(self, text: str) -> IntentCategory:
        """
        簡易意圖偵測
        
        注意：這是規則式偵測，僅作為預設值
        最終需要人工標註確認
        """
        text_lower = text.lower()
        
        # 緊急關鍵字
        emergency_keywords = ["很痛", "非常痛", "受不了", "喘不過氣", "發燒", "出血", "緊急", "救命"]
        if any(kw in text for kw in emergency_keywords):
            return IntentCategory.EMERGENCY
        
        # 症狀回報
        symptom_keywords = ["分", "今天", "昨天", "這幾天"]
        if any(kw in text for kw in symptom_keywords):
            return IntentCategory.SYMPTOM_REPORT
        
        # 症狀諮詢
        inquiry_keywords = ["正常嗎", "會不會", "是不是", "怎麼辦", "該怎麼"]
        if any(kw in text for kw in inquiry_keywords):
            return IntentCategory.SYMPTOM_INQUIRY
        
        # 藥物問題
        medication_keywords = ["藥", "吃藥", "止痛", "副作用"]
        if any(kw in text for kw in medication_keywords):
            return IntentCategory.MEDICATION_QUESTION
        
        # 生活建議
        lifestyle_keywords = ["可以", "能不能", "運動", "洗澡", "工作", "開車"]
        if any(kw in text for kw in lifestyle_keywords):
            return IntentCategory.LIFESTYLE_ADVICE
        
        # 情緒表達
        emotion_keywords = ["擔心", "害怕", "焦慮", "難過", "開心", "謝謝"]
        if any(kw in text for kw in emotion_keywords):
            return IntentCategory.EMOTIONAL_EXPRESSION
        
        # 感謝
        if "謝" in text or "感謝" in text:
            return IntentCategory.GRATITUDE
        
        # 打招呼
        greeting_keywords = ["你好", "早安", "午安", "晚安", "嗨"]
        if any(kw in text for kw in greeting_keywords):
            return IntentCategory.GREETING
        
        return IntentCategory.OTHER
    
    def _detect_emotion(self, text: str) -> EmotionCategory:
        """
        簡易情緒偵測
        
        注意：這是規則式偵測，僅作為預設值
        """
        # 焦慮/擔心
        anxious_keywords = ["擔心", "害怕", "焦慮", "緊張", "不安", "恐懼"]
        if any(kw in text for kw in anxious_keywords):
            return EmotionCategory.ANXIOUS
        
        # 低落/沮喪
        depressed_keywords = ["難過", "沮喪", "低落", "憂鬱", "不想", "沒意思"]
        if any(kw in text for kw in depressed_keywords):
            return EmotionCategory.DEPRESSED
        
        # 正向
        positive_keywords = ["謝謝", "感謝", "開心", "高興", "好多了", "進步"]
        if any(kw in text for kw in positive_keywords):
            return EmotionCategory.POSITIVE
        
        # 憤怒
        angry_keywords = ["生氣", "憤怒", "不滿", "抱怨", "受不了"]
        if any(kw in text for kw in angry_keywords):
            return EmotionCategory.ANGRY
        
        return EmotionCategory.NEUTRAL
    
    def _detect_urgency(self, text: str) -> UrgencyLevel:
        """簡易緊急程度偵測"""
        # 緊急
        emergency_keywords = ["非常痛", "劇痛", "喘不過氣", "發高燒", "大量出血", "昏倒", "意識"]
        if any(kw in text for kw in emergency_keywords):
            return UrgencyLevel.EMERGENCY
        
        # 重要
        important_keywords = ["很痛", "發燒", "出血", "嚴重", "惡化", "加重"]
        if any(kw in text for kw in important_keywords):
            return UrgencyLevel.IMPORTANT
        
        # 一般
        return UrgencyLevel.NORMAL
    
    def _extract_symptoms(self, text: str) -> List[str]:
        """提取症狀關鍵字"""
        detected = []
        
        for symptom_type, definition in SYMPTOM_DEFINITIONS.items():
            keywords = definition.get("keywords", [])
            for keyword in keywords:
                if keyword in text:
                    detected.append(symptom_type.value)
                    break
        
        return detected
    
    # ============================================
    # 資料匯出（供標註團隊使用）
    # ============================================
    
    def export_for_annotation(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        include_ai_responses: bool = False
    ) -> List[Dict[str, Any]]:
        """
        匯出標註資料
        
        預設只匯出病人輸入，供標註團隊使用
        """
        export_data = []
        
        for message in self.messages.values():
            # 只匯出病人訊息
            if not include_ai_responses and message.role != MessageRole.PATIENT:
                continue
            
            # 日期過濾
            msg_date = message.timestamp.date()
            if start_date and msg_date < start_date:
                continue
            if end_date and msg_date > end_date:
                continue
            
            export_item = {
                "message_id": message.message_id,
                "patient_id": message.patient_id,
                "timestamp": message.timestamp.isoformat(),
                "content": message.content,
                "raw_input": message.raw_input,
                "input_method": message.input_method,
                
                # 預設標註（供參考）
                "auto_detected_intent": message.detected_intent.value,
                "auto_detected_emotion": message.detected_emotion.value,
                "auto_detected_urgency": message.detected_urgency.value,
                
                # 人工標註欄位（待填寫）
                "annotated_intent": message.annotated_intent,
                "annotated_emotion": message.annotated_emotion,
                "annotated_urgency": message.annotated_urgency,
                "annotated_entities": message.annotated_entities,
                "annotator_id": None,
                "annotation_time": None
            }
            
            export_data.append(export_item)
        
        return export_data
    
    def export_open_ended_for_annotation(self) -> List[Dict[str, Any]]:
        """匯出開放式回應供標註"""
        return [resp.to_dict() for resp in self.open_ended_responses.values()]
    
    def export_sessions_summary(self) -> List[Dict[str, Any]]:
        """匯出會話摘要"""
        summaries = []
        
        for session in self.sessions.values():
            summary = {
                "session_id": session.session_id,
                "patient_id": session.patient_id,
                "start_time": session.start_time.isoformat(),
                "end_time": session.end_time.isoformat() if session.end_time else None,
                "session_type": session.session_type,
                "is_completed": session.is_completed,
                "total_patient_messages": session.total_patient_messages,
                "total_ai_messages": session.total_ai_messages,
                "total_words_patient": session.total_words_patient,
                "avg_words_per_message": (
                    session.total_words_patient / session.total_patient_messages
                    if session.total_patient_messages > 0 else 0
                )
            }
            summaries.append(summary)
        
        return summaries
    
    # ============================================
    # 統計分析
    # ============================================
    
    def get_patient_stats(self, patient_id: str) -> Dict[str, Any]:
        """取得病人對話統計"""
        patient_messages = [
            m for m in self.messages.values()
            if m.patient_id == patient_id and m.role == MessageRole.PATIENT
        ]
        
        patient_sessions = [
            s for s in self.sessions.values()
            if s.patient_id == patient_id
        ]
        
        # 計算統計
        total_messages = len(patient_messages)
        total_words = sum(len(m.content.split()) for m in patient_messages)
        
        # 意圖分布
        intent_distribution = {}
        for m in patient_messages:
            intent = m.detected_intent.value
            intent_distribution[intent] = intent_distribution.get(intent, 0) + 1
        
        # 情緒分布
        emotion_distribution = {}
        for m in patient_messages:
            emotion = m.detected_emotion.value
            emotion_distribution[emotion] = emotion_distribution.get(emotion, 0) + 1
        
        return {
            "patient_id": patient_id,
            "total_sessions": len(patient_sessions),
            "total_messages": total_messages,
            "total_words": total_words,
            "avg_words_per_message": total_words / total_messages if total_messages > 0 else 0,
            "intent_distribution": intent_distribution,
            "emotion_distribution": emotion_distribution,
            "open_ended_responses": len([
                r for r in self.open_ended_responses.values()
                if r.patient_id == patient_id
            ])
        }


# ============================================
# 全域實例
# ============================================

# 建立全域對話儲存器
conversation_store = ConversationStore()


# ============================================
# 便利函數
# ============================================

def log_patient_input(
    patient_id: str,
    content: str,
    input_method: str = "text",
    raw_input: Optional[str] = None
) -> ConversationMessage:
    """記錄病人輸入的便利函數"""
    return conversation_store.add_patient_message(
        patient_id=patient_id,
        content=content,
        input_method=input_method,
        raw_input=raw_input
    )


def log_ai_response(
    patient_id: str,
    content: str,
    source: MessageSource = MessageSource.AI_GENERATED,
    template_id: Optional[str] = None
) -> ConversationMessage:
    """記錄 AI 回應的便利函數"""
    return conversation_store.add_ai_message(
        patient_id=patient_id,
        content=content,
        source=source,
        template_id=template_id
    )


def log_open_ended_response(
    patient_id: str,
    report_id: str,
    question_id: str,
    question_text: str,
    question_category: str,
    response_text: str
) -> OpenEndedResponse:
    """記錄開放式回應的便利函數"""
    return conversation_store.add_open_ended_response(
        patient_id=patient_id,
        report_id=report_id,
        question_id=question_id,
        question_text=question_text,
        question_category=question_category,
        response_text=response_text
    )
