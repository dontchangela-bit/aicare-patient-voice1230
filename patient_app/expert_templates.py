"""
AI-CARE Lung 病人端 - 專家回應範本管理
======================================
功能：
1. 管理護理師/醫師撰寫的回應範本
2. 根據情境選擇合適範本
3. 範本使用追蹤
4. 範本審核管理

三軍總醫院 數位醫療中心
"""

from datetime import datetime, date
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
import json
import re

from models import ExpertResponseTemplate, MessageSource


class ExpertTemplateManager:
    """
    專家回應範本管理器
    
    管理護理師/醫師撰寫的標準回應
    用於取代部分 AI 生成回應，確保醫療安全和品質
    """
    
    def __init__(self):
        # 範本儲存
        self.templates: Dict[str, ExpertResponseTemplate] = {}
        
        # 載入預設範本
        self._load_default_templates()
    
    def _load_default_templates(self):
        """載入預設範本（由護理師提供）"""
        default_templates = self._get_default_templates()
        for template in default_templates:
            self.templates[template.template_id] = template
    
    # ============================================
    # 範本查詢
    # ============================================
    
    def find_matching_template(
        self,
        category: str,
        symptom_type: Optional[str] = None,
        score: Optional[int] = None,
        keywords: Optional[List[str]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[ExpertResponseTemplate]:
        """
        根據條件查找匹配的範本
        
        優先級：
        1. 完全匹配觸發條件
        2. 關鍵字匹配
        3. 類別匹配
        """
        candidates = []
        
        for template in self.templates.values():
            if not template.is_active or not template.is_approved:
                continue
            
            if template.category != category:
                continue
            
            # 檢查觸發條件
            match_score = self._calculate_match_score(
                template, symptom_type, score, keywords, context
            )
            
            if match_score > 0:
                candidates.append((template, match_score))
        
        if not candidates:
            return None
        
        # 返回最佳匹配
        candidates.sort(key=lambda x: x[1], reverse=True)
        best_template = candidates[0][0]
        
        # 更新使用統計
        best_template.use_count += 1
        best_template.last_used = datetime.now()
        
        return best_template
    
    def _calculate_match_score(
        self,
        template: ExpertResponseTemplate,
        symptom_type: Optional[str],
        score: Optional[int],
        keywords: Optional[List[str]],
        context: Optional[Dict[str, Any]]
    ) -> float:
        """計算範本匹配分數"""
        match_score = 0.0
        conditions = template.trigger_conditions
        
        # 檢查症狀類型
        if symptom_type and "symptom_type" in conditions:
            if conditions["symptom_type"] == symptom_type:
                match_score += 2.0
            else:
                return 0.0  # 症狀不匹配，直接排除
        
        # 檢查分數範圍
        if score is not None and "score_range" in conditions:
            min_score, max_score = conditions["score_range"]
            if min_score <= score <= max_score:
                match_score += 1.5
            else:
                return 0.0  # 分數不在範圍，排除
        
        # 檢查關鍵字
        if keywords and template.trigger_keywords:
            keyword_matches = sum(
                1 for kw in keywords
                if any(tkw in kw for tkw in template.trigger_keywords)
            )
            match_score += keyword_matches * 0.5
        
        # 檢查其他上下文條件
        if context and conditions:
            for key, value in conditions.items():
                if key in ["symptom_type", "score_range"]:
                    continue
                if key in context and context[key] == value:
                    match_score += 0.5
        
        return match_score
    
    def get_response(
        self,
        category: str,
        symptom_type: Optional[str] = None,
        score: Optional[int] = None,
        keywords: Optional[List[str]] = None,
        context: Optional[Dict[str, Any]] = None,
        use_variation: bool = True
    ) -> Tuple[Optional[str], Optional[str], MessageSource]:
        """
        取得回應內容
        
        返回：(回應內容, 範本ID, 訊息來源)
        """
        template = self.find_matching_template(
            category, symptom_type, score, keywords, context
        )
        
        if template:
            # 選擇回應（主範本或變體）
            if use_variation and template.response_variations:
                import random
                response = random.choice(
                    [template.response_template] + template.response_variations
                )
            else:
                response = template.response_template
            
            # 替換變數
            response = self._fill_template_variables(response, context)
            
            return response, template.template_id, MessageSource.EXPERT_TEMPLATE
        
        return None, None, MessageSource.AI_GENERATED
    
    def _fill_template_variables(
        self,
        template: str,
        context: Optional[Dict[str, Any]]
    ) -> str:
        """填充範本變數"""
        if not context:
            return template
        
        result = template
        
        # 替換 {variable} 格式的變數
        for key, value in context.items():
            result = result.replace(f"{{{key}}}", str(value))
        
        return result
    
    # ============================================
    # 範本管理
    # ============================================
    
    def add_template(self, template: ExpertResponseTemplate) -> bool:
        """新增範本"""
        if template.template_id in self.templates:
            return False
        
        self.templates[template.template_id] = template
        return True
    
    def update_template(
        self,
        template_id: str,
        updates: Dict[str, Any]
    ) -> bool:
        """更新範本"""
        if template_id not in self.templates:
            return False
        
        template = self.templates[template_id]
        
        for key, value in updates.items():
            if hasattr(template, key):
                setattr(template, key, value)
        
        template.updated_at = datetime.now()
        template.version += 1
        
        return True
    
    def approve_template(
        self,
        template_id: str,
        reviewer_name: str
    ) -> bool:
        """審核通過範本"""
        if template_id not in self.templates:
            return False
        
        template = self.templates[template_id]
        template.is_approved = True
        template.reviewed_by = reviewer_name
        template.review_date = datetime.now().date()
        
        return True
    
    def deactivate_template(self, template_id: str) -> bool:
        """停用範本"""
        if template_id not in self.templates:
            return False
        
        self.templates[template_id].is_active = False
        return True
    
    # ============================================
    # 統計和匯出
    # ============================================
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """取得範本使用統計"""
        stats = {
            "total_templates": len(self.templates),
            "approved_templates": sum(1 for t in self.templates.values() if t.is_approved),
            "active_templates": sum(1 for t in self.templates.values() if t.is_active),
            "total_usage": sum(t.use_count for t in self.templates.values()),
            "by_category": {},
            "top_used": []
        }
        
        # 按類別統計
        for template in self.templates.values():
            cat = template.category
            if cat not in stats["by_category"]:
                stats["by_category"][cat] = {"count": 0, "usage": 0}
            stats["by_category"][cat]["count"] += 1
            stats["by_category"][cat]["usage"] += template.use_count
        
        # 使用最多的範本
        sorted_templates = sorted(
            self.templates.values(),
            key=lambda t: t.use_count,
            reverse=True
        )
        stats["top_used"] = [
            {
                "template_id": t.template_id,
                "scenario_name": t.scenario_name,
                "use_count": t.use_count
            }
            for t in sorted_templates[:10]
        ]
        
        return stats
    
    def export_templates(self) -> List[Dict[str, Any]]:
        """匯出所有範本"""
        return [t.to_dict() for t in self.templates.values()]
    
    # ============================================
    # 預設範本定義
    # ============================================
    
    def _get_default_templates(self) -> List[ExpertResponseTemplate]:
        """
        預設範本列表
        
        這些範本應由護理師/醫師審核後使用
        目前為示範用途，實際部署時需要完整審核
        """
        templates = [
            # ============================================
            # 症狀回應 - 疼痛
            # ============================================
            ExpertResponseTemplate(
                template_id="pain_low_001",
                category="symptom_response",
                scenario_name="輕度疼痛回應",
                trigger_conditions={
                    "symptom_type": "pain",
                    "score_range": [0, 3]
                },
                response_template="收到！疼痛：**{score} 分**（輕度）\n\n很好，您的傷口疼痛控制得不錯！👍\n\n術後傷口輕微不適是正常的恢復過程，如果疼痛維持在可忍受範圍，表示恢復狀況良好。",
                response_variations=[
                    "收到！疼痛：**{score} 分**（輕度）\n\n傷口疼痛控制得很好！這是正常的術後恢復過程。請繼續保持，有任何變化再告訴我們。"
                ],
                trigger_keywords=["痛", "傷口", "疼"],
                follow_up_actions=[],
                author_name="示範護理師",
                author_role="nurse",
                is_approved=True,
                reviewed_by="示範主管",
                review_date=date.today()
            ),
            
            ExpertResponseTemplate(
                template_id="pain_moderate_001",
                category="symptom_response",
                scenario_name="中度疼痛回應",
                trigger_conditions={
                    "symptom_type": "pain",
                    "score_range": [4, 6]
                },
                response_template="收到！疼痛：**{score} 分**（中度）\n\n了解，這個程度的疼痛我們會持續關注。\n\n💊 建議：\n- 可按醫囑服用止痛藥\n- 嘗試變換姿勢減輕不適\n- 避免過度活動\n\n如果疼痛持續加重，請隨時告訴我們。",
                response_variations=[
                    "收到！疼痛：**{score} 分**（中度）\n\n中等程度的疼痛，我們會特別留意。\n\n請問疼痛是持續性的，還是某些動作時才會痛呢？"
                ],
                trigger_keywords=["痛", "傷口", "疼"],
                follow_up_actions=["monitor"],
                author_name="示範護理師",
                author_role="nurse",
                is_approved=True,
                reviewed_by="示範主管",
                review_date=date.today()
            ),
            
            ExpertResponseTemplate(
                template_id="pain_high_001",
                category="symptom_response",
                scenario_name="重度疼痛回應",
                trigger_conditions={
                    "symptom_type": "pain",
                    "score_range": [7, 10]
                },
                response_template="收到！疼痛：**{score} 分**（重度）\n\n⚠️ 我注意到您的疼痛分數較高，個管師會特別關注您的狀況。\n\n請問：\n1. 疼痛的位置在哪裡？\n2. 疼痛是什麼感覺？（刺痛、悶痛、脹痛？）\n3. 目前有服用止痛藥嗎？\n\n如果疼痛難以忍受，請撥打個管師專線或至急診就醫。",
                response_variations=[],
                trigger_keywords=["很痛", "劇痛", "受不了"],
                follow_up_actions=["alert_nurse", "request_callback"],
                author_name="示範護理師",
                author_role="nurse",
                is_approved=True,
                reviewed_by="示範主管",
                review_date=date.today()
            ),
            
            # ============================================
            # 症狀回應 - 呼吸困難
            # ============================================
            ExpertResponseTemplate(
                template_id="dyspnea_low_001",
                category="symptom_response",
                scenario_name="輕度呼吸困難回應",
                trigger_conditions={
                    "symptom_type": "dyspnea",
                    "score_range": [0, 3]
                },
                response_template="收到！呼吸困難：**{score} 分**（輕度）\n\n呼吸狀況不錯！👍\n\n肺部手術後，輕微的喘是正常的，隨著恢復會逐漸改善。請持續練習深呼吸和腹式呼吸。",
                trigger_keywords=["喘", "呼吸", "氣"],
                follow_up_actions=[],
                author_name="示範護理師",
                author_role="nurse",
                is_approved=True,
                reviewed_by="示範主管",
                review_date=date.today()
            ),
            
            ExpertResponseTemplate(
                template_id="dyspnea_high_001",
                category="symptom_response",
                scenario_name="重度呼吸困難回應",
                trigger_conditions={
                    "symptom_type": "dyspnea",
                    "score_range": [7, 10]
                },
                response_template="收到！呼吸困難：**{score} 分**（重度）\n\n⚠️ 這個程度的呼吸困難需要特別注意！\n\n請立即確認：\n1. 是休息時就喘，還是活動後才喘？\n2. 有沒有胸痛或胸悶？\n3. 嘴唇或指甲有沒有發紫？\n\n🚨 如果休息時仍持續喘不過氣，或有嘴唇發紫的情況，請立即就醫！",
                trigger_keywords=["很喘", "喘不過氣", "透不過氣"],
                follow_up_actions=["alert_nurse", "urgent_callback"],
                author_name="示範護理師",
                author_role="nurse",
                is_approved=True,
                reviewed_by="示範主管",
                review_date=date.today()
            ),
            
            # ============================================
            # 症狀回應 - 情緒
            # ============================================
            ExpertResponseTemplate(
                template_id="mood_anxious_001",
                category="emotional_support",
                scenario_name="焦慮情緒支持",
                trigger_conditions={
                    "symptom_type": "mood",
                    "score_range": [5, 10]
                },
                response_template="收到！心情：**{score} 分**\n\n我聽到您現在的心情不太好，這是很正常的。面對手術和康復過程，感到焦慮或擔心是可以理解的。\n\n💙 一些可能有幫助的方法：\n- 和家人朋友聊聊您的感受\n- 嘗試深呼吸或放鬆練習\n- 維持規律的作息\n\n如果焦慮持續影響到您的日常生活，我們可以安排心理支持服務。",
                trigger_keywords=["擔心", "焦慮", "害怕", "難過"],
                follow_up_actions=["empathy_support"],
                author_name="示範護理師",
                author_role="nurse",
                is_approved=True,
                reviewed_by="示範主管",
                review_date=date.today()
            ),
            
            # ============================================
            # 生活建議
            # ============================================
            ExpertResponseTemplate(
                template_id="lifestyle_activity_001",
                category="lifestyle_advice",
                scenario_name="活動量建議",
                trigger_conditions={
                    "topic": "activity"
                },
                response_template="關於術後活動的建議：\n\n✅ 可以做的：\n- 每天短距離散步（從5-10分鐘開始）\n- 深呼吸練習\n- 輕微的伸展活動\n\n❌ 暫時避免：\n- 提重物（超過3公斤）\n- 劇烈運動\n- 過度彎腰\n\n活動時如有不適，請立即休息。建議循序漸進，逐步增加活動量。",
                trigger_keywords=["運動", "活動", "走路", "可以"],
                follow_up_actions=[],
                author_name="示範護理師",
                author_role="nurse",
                is_approved=True,
                reviewed_by="示範主管",
                review_date=date.today()
            ),
            
            ExpertResponseTemplate(
                template_id="lifestyle_wound_001",
                category="lifestyle_advice",
                scenario_name="傷口照護建議",
                trigger_conditions={
                    "topic": "wound_care"
                },
                response_template="關於傷口照護：\n\n✅ 每日注意事項：\n- 保持傷口清潔乾燥\n- 觀察有無紅腫熱痛或分泌物\n- 按時更換紗布（如有滲液）\n\n🚿 洗澡注意：\n- 手術後第一週建議擦澡\n- 之後可淋浴，但避免傷口長時間浸水\n- 洗後輕輕拍乾傷口\n\n⚠️ 如發現傷口紅腫、發熱、有異味分泌物，請盡快就醫檢查。",
                trigger_keywords=["傷口", "洗澡", "換藥"],
                follow_up_actions=[],
                author_name="示範護理師",
                author_role="nurse",
                is_approved=True,
                reviewed_by="示範主管",
                review_date=date.today()
            ),
            
            # ============================================
            # 完成回報
            # ============================================
            ExpertResponseTemplate(
                template_id="complete_normal_001",
                category="completion",
                scenario_name="正常完成回報",
                trigger_conditions={
                    "has_severe": False
                },
                response_template="🎉 **太棒了！您已完成今日症狀回報！**\n\n今日整體狀況看起來不錯，請繼續保持良好的恢復狀態。\n\n💡 小提醒：\n- 記得多休息，適度活動\n- 有任何不適隨時告訴我們\n\n感謝您的配合，明天見！👋",
                trigger_keywords=[],
                follow_up_actions=[],
                author_name="示範護理師",
                author_role="nurse",
                is_approved=True,
                reviewed_by="示範主管",
                review_date=date.today()
            ),
            
            ExpertResponseTemplate(
                template_id="complete_concern_001",
                category="completion",
                scenario_name="有顧慮完成回報",
                trigger_conditions={
                    "has_severe": True
                },
                response_template="✅ **已完成今日症狀回報**\n\n我注意到您今天有些症狀需要特別關注，個管師會在查看後與您聯繫。\n\n📞 如果症狀明顯惡化或有緊急狀況，請直接撥打：\n- 個管師專線：02-XXXX-XXXX\n- 急診專線：02-XXXX-XXXX\n\n請好好休息，保重身體！💪",
                trigger_keywords=[],
                follow_up_actions=["alert_nurse"],
                author_name="示範護理師",
                author_role="nurse",
                is_approved=True,
                reviewed_by="示範主管",
                review_date=date.today()
            ),
            
            # ============================================
            # 開場白
            # ============================================
            ExpertResponseTemplate(
                template_id="greeting_morning_001",
                category="greeting",
                scenario_name="早安問候",
                trigger_conditions={
                    "time_of_day": "morning"
                },
                response_template="{patient_name}您好！早安 ☀️\n\n我是您的 AI 照護助手。今天是術後第 **{post_op_day}** 天，讓我們一起完成今日的症狀回報吧！\n\n整個過程大約 2-3 分鐘，我會依序詢問您幾個症狀的狀況。\n\n準備好了嗎？讓我們開始吧！",
                response_variations=[
                    "{patient_name}您好！今天精神怎麼樣呢？ ☀️\n\n我是您的照護助手，現在來幫您完成今日的症狀回報。只需要幾分鐘的時間！"
                ],
                trigger_keywords=[],
                follow_up_actions=[],
                author_name="示範護理師",
                author_role="nurse",
                is_approved=True,
                reviewed_by="示範主管",
                review_date=date.today()
            ),
        ]
        
        return templates


# ============================================
# 全域實例
# ============================================

# 建立全域範本管理器
template_manager = ExpertTemplateManager()


# ============================================
# 便利函數
# ============================================

def get_expert_response(
    category: str,
    symptom_type: Optional[str] = None,
    score: Optional[int] = None,
    keywords: Optional[List[str]] = None,
    context: Optional[Dict[str, Any]] = None
) -> Tuple[Optional[str], Optional[str], MessageSource]:
    """取得專家回應的便利函數"""
    return template_manager.get_response(
        category=category,
        symptom_type=symptom_type,
        score=score,
        keywords=keywords,
        context=context
    )


def get_symptom_response(
    symptom_type: str,
    score: int,
    context: Optional[Dict[str, Any]] = None
) -> Tuple[str, Optional[str], MessageSource]:
    """
    取得症狀回應
    
    優先使用專家範本，若無匹配則返回 None（由 AI 生成）
    """
    if context is None:
        context = {}
    context["score"] = score
    
    response, template_id, source = get_expert_response(
        category="symptom_response",
        symptom_type=symptom_type,
        score=score,
        context=context
    )
    
    if response:
        return response, template_id, source
    
    # 無匹配範本，返回基本回應（可由 AI 補充）
    return None, None, MessageSource.AI_GENERATED
