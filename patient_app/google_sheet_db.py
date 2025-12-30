"""
AI-CARE Lung - Google Sheet 資料庫模組
======================================
使用 Google Sheet 作為輕量級資料庫

功能：
1. 病人註冊與登入驗證
2. 症狀回報記錄儲存
3. 順從度追蹤
4. 成就系統

三軍總醫院 數位醫療中心
"""

import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta, date
import json
import hashlib
from typing import Optional, Dict, List, Any, Tuple

# ============================================
# Google Sheet 連接設定
# ============================================

# Google API 範圍
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

# 工作表名稱
SHEET_PATIENTS = "病人資料"
SHEET_REPORTS = "症狀回報"
SHEET_CONVERSATIONS = "對話記錄"
SHEET_ACHIEVEMENTS = "成就記錄"


def get_google_client():
    """
    取得 Google Sheets 客戶端
    
    憑證從 Streamlit Secrets 讀取
    """
    try:
        # 從 Streamlit Secrets 讀取憑證
        credentials_dict = st.secrets["gcp_service_account"]
        
        credentials = Credentials.from_service_account_info(
            credentials_dict,
            scopes=SCOPES
        )
        
        client = gspread.authorize(credentials)
        return client
    
    except Exception as e:
        st.error(f"無法連接 Google Sheets: {e}")
        return None


def get_spreadsheet():
    """取得指定的 Google Spreadsheet"""
    client = get_google_client()
    if not client:
        return None
    
    try:
        # 從 secrets 讀取試算表 ID
        spreadsheet_id = st.secrets["spreadsheet"]["id"]
        spreadsheet = client.open_by_key(spreadsheet_id)
        return spreadsheet
    except Exception as e:
        st.error(f"無法開啟試算表: {e}")
        return None


def init_spreadsheet():
    """
    初始化試算表結構
    
    如果工作表不存在，自動建立
    """
    spreadsheet = get_spreadsheet()
    if not spreadsheet:
        return False
    
    try:
        existing_sheets = [ws.title for ws in spreadsheet.worksheets()]
        
        # 病人資料表
        if SHEET_PATIENTS not in existing_sheets:
            ws = spreadsheet.add_worksheet(title=SHEET_PATIENTS, rows=1000, cols=20)
            ws.append_row([
                "病人ID", "姓名", "性別", "年齡", "生日", 
                "手機號碼", "手術日期", "手術類型", "癌症分期",
                "密碼雜湊", "註冊時間", "最後登入", "狀態"
            ])
        
        # 症狀回報表
        if SHEET_REPORTS not in existing_sheets:
            ws = spreadsheet.add_worksheet(title=SHEET_REPORTS, rows=10000, cols=30)
            ws.append_row([
                "回報ID", "病人ID", "回報日期", "回報時間", "回報方式",
                "疼痛分數", "疲勞分數", "呼吸困難分數", "咳嗽分數", 
                "睡眠分數", "食慾分數", "心情分數",
                "疼痛描述", "疲勞描述", "呼吸困難描述", "咳嗽描述",
                "睡眠描述", "食慾描述", "心情描述",
                "開放式回答1", "開放式回答2", "額外備註",
                "平均分數", "最高分數項目", "建立時間"
            ])
        
        # 對話記錄表
        if SHEET_CONVERSATIONS not in existing_sheets:
            ws = spreadsheet.add_worksheet(title=SHEET_CONVERSATIONS, rows=50000, cols=15)
            ws.append_row([
                "訊息ID", "會話ID", "病人ID", "角色", "內容",
                "訊息來源", "輸入方式", "範本ID",
                "偵測意圖", "偵測情緒", "時間戳記"
            ])
        
        # 成就記錄表
        if SHEET_ACHIEVEMENTS not in existing_sheets:
            ws = spreadsheet.add_worksheet(title=SHEET_ACHIEVEMENTS, rows=5000, cols=10)
            ws.append_row([
                "記錄ID", "病人ID", "成就ID", "成就名稱", 
                "解鎖日期", "獲得積分"
            ])
        
        return True
    
    except Exception as e:
        st.error(f"初始化試算表失敗: {e}")
        return False


# ============================================
# 密碼處理
# ============================================

def hash_password(password: str) -> str:
    """密碼雜湊（使用 SHA-256）"""
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(password: str, hashed: str) -> bool:
    """驗證密碼"""
    return hash_password(password) == hashed


# ============================================
# 病人管理功能
# ============================================

class PatientManager:
    """病人資料管理"""
    
    def __init__(self):
        self.spreadsheet = get_spreadsheet()
    
    def _get_patients_sheet(self):
        """取得病人資料工作表"""
        if not self.spreadsheet:
            return None
        try:
            return self.spreadsheet.worksheet(SHEET_PATIENTS)
        except:
            return None
    
    def register_patient(
        self,
        patient_id: str,
        name: str,
        gender: str,
        age: int,
        birthday: str,
        phone: str,
        surgery_date: str,
        surgery_type: str,
        cancer_stage: str,
        password: str
    ) -> Tuple[bool, str]:
        """
        註冊新病人
        
        Returns:
            (success, message)
        """
        ws = self._get_patients_sheet()
        if not ws:
            return False, "無法連接資料庫"
        
        try:
            # 檢查病人ID是否已存在
            existing = ws.findall(patient_id, in_column=1)
            if existing:
                return False, "此病歷號已註冊"
            
            # 新增病人資料
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ws.append_row([
                patient_id,
                name,
                gender,
                age,
                birthday,
                phone,
                surgery_date,
                surgery_type,
                cancer_stage,
                hash_password(password),
                now,  # 註冊時間
                now,  # 最後登入
                "active"  # 狀態
            ])
            
            return True, "註冊成功！"
        
        except Exception as e:
            return False, f"註冊失敗: {e}"
    
    def login(self, patient_id: str, password: str) -> Tuple[bool, Optional[Dict]]:
        """
        病人登入驗證
        
        Returns:
            (success, patient_data or None)
        """
        ws = self._get_patients_sheet()
        if not ws:
            return False, None
        
        try:
            # 尋找病人
            cell = ws.find(patient_id, in_column=1)
            if not cell:
                return False, None
            
            # 取得該行資料
            row = ws.row_values(cell.row)
            
            # 驗證密碼
            stored_hash = row[9] if len(row) > 9 else ""
            if not verify_password(password, stored_hash):
                return False, None
            
            # 更新最後登入時間
            ws.update_cell(cell.row, 12, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            
            # 計算術後天數
            surgery_date = datetime.strptime(row[6], "%Y-%m-%d").date() if row[6] else date.today()
            post_op_day = (date.today() - surgery_date).days
            
            # 回傳病人資料
            patient_data = {
                "id": row[0],
                "name": row[1],
                "gender": row[2],
                "age": int(row[3]) if row[3] else 0,
                "birthday": row[4],
                "phone": row[5],
                "surgery_date": surgery_date,
                "surgery_type": row[7],
                "cancer_stage": row[8],
                "post_op_day": post_op_day
            }
            
            return True, patient_data
        
        except Exception as e:
            st.error(f"登入錯誤: {e}")
            return False, None
    
    def get_patient(self, patient_id: str) -> Optional[Dict]:
        """取得病人資料"""
        ws = self._get_patients_sheet()
        if not ws:
            return None
        
        try:
            cell = ws.find(patient_id, in_column=1)
            if not cell:
                return None
            
            row = ws.row_values(cell.row)
            
            surgery_date = datetime.strptime(row[6], "%Y-%m-%d").date() if row[6] else date.today()
            post_op_day = (date.today() - surgery_date).days
            
            return {
                "id": row[0],
                "name": row[1],
                "gender": row[2],
                "age": int(row[3]) if row[3] else 0,
                "surgery_date": surgery_date,
                "surgery_type": row[7],
                "cancer_stage": row[8],
                "post_op_day": post_op_day
            }
        except:
            return None
    
    def update_patient(self, patient_id: str, updates: Dict) -> bool:
        """更新病人資料"""
        ws = self._get_patients_sheet()
        if not ws:
            return False
        
        try:
            cell = ws.find(patient_id, in_column=1)
            if not cell:
                return False
            
            # 欄位對應
            column_map = {
                "name": 2, "gender": 3, "age": 4, "birthday": 5,
                "phone": 6, "surgery_date": 7, "surgery_type": 8, 
                "cancer_stage": 9
            }
            
            for field, value in updates.items():
                if field in column_map:
                    ws.update_cell(cell.row, column_map[field], value)
            
            return True
        except:
            return False


# ============================================
# 症狀回報管理
# ============================================

class ReportManager:
    """症狀回報管理"""
    
    def __init__(self):
        self.spreadsheet = get_spreadsheet()
    
    def _get_reports_sheet(self):
        """取得症狀回報工作表"""
        if not self.spreadsheet:
            return None
        try:
            return self.spreadsheet.worksheet(SHEET_REPORTS)
        except:
            return None
    
    def save_report(
        self,
        patient_id: str,
        scores: Dict[str, int],
        descriptions: Dict[str, str] = None,
        open_ended: List[str] = None,
        method: str = "ai_chat"
    ) -> Tuple[bool, str]:
        """
        儲存症狀回報
        
        Args:
            patient_id: 病人ID
            scores: 各症狀分數 {"pain": 3, "fatigue": 2, ...}
            descriptions: 各症狀描述
            open_ended: 開放式回答
            method: 回報方式 (ai_chat, questionnaire)
        
        Returns:
            (success, report_id)
        """
        ws = self._get_reports_sheet()
        if not ws:
            return False, ""
        
        descriptions = descriptions or {}
        open_ended = open_ended or []
        
        try:
            now = datetime.now()
            report_id = f"RPT_{patient_id}_{now.strftime('%Y%m%d%H%M%S')}"
            
            # 計算平均分數
            score_values = list(scores.values())
            avg_score = sum(score_values) / len(score_values) if score_values else 0
            
            # 找出最高分項目
            max_symptom = max(scores, key=scores.get) if scores else ""
            
            row_data = [
                report_id,
                patient_id,
                now.strftime("%Y-%m-%d"),
                now.strftime("%H:%M:%S"),
                method,
                scores.get("pain", 0),
                scores.get("fatigue", 0),
                scores.get("dyspnea", 0),
                scores.get("cough", 0),
                scores.get("sleep", 0),
                scores.get("appetite", 0),
                scores.get("mood", 0),
                descriptions.get("pain", ""),
                descriptions.get("fatigue", ""),
                descriptions.get("dyspnea", ""),
                descriptions.get("cough", ""),
                descriptions.get("sleep", ""),
                descriptions.get("appetite", ""),
                descriptions.get("mood", ""),
                open_ended[0] if len(open_ended) > 0 else "",
                open_ended[1] if len(open_ended) > 1 else "",
                descriptions.get("additional", ""),
                round(avg_score, 2),
                max_symptom,
                now.strftime("%Y-%m-%d %H:%M:%S")
            ]
            
            ws.append_row(row_data)
            
            return True, report_id
        
        except Exception as e:
            st.error(f"儲存回報失敗: {e}")
            return False, ""
    
    def get_today_report(self, patient_id: str) -> Optional[Dict]:
        """取得今日回報"""
        ws = self._get_reports_sheet()
        if not ws:
            return None
        
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            
            # 取得所有資料
            records = ws.get_all_records()
            
            for record in records:
                if record.get("病人ID") == patient_id and record.get("回報日期") == today:
                    return {
                        "report_id": record.get("回報ID"),
                        "date": record.get("回報日期"),
                        "time": record.get("回報時間"),
                        "method": record.get("回報方式"),
                        "scores": {
                            "pain": record.get("疼痛分數", 0),
                            "fatigue": record.get("疲勞分數", 0),
                            "dyspnea": record.get("呼吸困難分數", 0),
                            "cough": record.get("咳嗽分數", 0),
                            "sleep": record.get("睡眠分數", 0),
                            "appetite": record.get("食慾分數", 0),
                            "mood": record.get("心情分數", 0)
                        }
                    }
            
            return None
        except:
            return None
    
    def get_patient_reports(self, patient_id: str, days: int = 30) -> List[Dict]:
        """取得病人的回報歷史"""
        ws = self._get_reports_sheet()
        if not ws:
            return []
        
        try:
            records = ws.get_all_records()
            patient_reports = []
            
            cutoff_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
            
            for record in records:
                if record.get("病人ID") == patient_id and record.get("回報日期", "") >= cutoff_date:
                    patient_reports.append({
                        "report_id": record.get("回報ID"),
                        "date": record.get("回報日期"),
                        "time": record.get("回報時間"),
                        "method": record.get("回報方式"),
                        "scores": {
                            "pain": record.get("疼痛分數", 0),
                            "fatigue": record.get("疲勞分數", 0),
                            "dyspnea": record.get("呼吸困難分數", 0),
                            "cough": record.get("咳嗽分數", 0),
                            "sleep": record.get("睡眠分數", 0),
                            "appetite": record.get("食慾分數", 0),
                            "mood": record.get("心情分數", 0)
                        },
                        "avg_score": record.get("平均分數", 0)
                    })
            
            # 按日期排序（最新在前）
            patient_reports.sort(key=lambda x: x["date"], reverse=True)
            
            return patient_reports
        except:
            return []
    
    def get_compliance_stats(self, patient_id: str, surgery_date: date) -> Dict:
        """計算順從度統計"""
        reports = self.get_patient_reports(patient_id, days=90)
        
        # 計算術後總天數
        total_days = (date.today() - surgery_date).days
        total_days = max(1, total_days)  # 至少1天
        
        # 計算完成天數
        completed_dates = set(r["date"] for r in reports)
        total_completed = len(completed_dates)
        
        # 計算連續天數
        current_streak = 0
        check_date = date.today()
        
        while check_date.strftime("%Y-%m-%d") in completed_dates:
            current_streak += 1
            check_date -= timedelta(days=1)
        
        # 如果今天還沒回報，從昨天開始算
        if date.today().strftime("%Y-%m-%d") not in completed_dates:
            current_streak = 0
            check_date = date.today() - timedelta(days=1)
            while check_date.strftime("%Y-%m-%d") in completed_dates:
                current_streak += 1
                check_date -= timedelta(days=1)
        
        # 計算積分
        base_points = total_completed * 10
        streak_bonus = 0
        if current_streak >= 7:
            streak_bonus += 30
        if current_streak >= 14:
            streak_bonus += 50
        if current_streak >= 21:
            streak_bonus += 80
        
        total_points = base_points + streak_bonus
        
        # 計算等級
        level = 1
        thresholds = [0, 50, 150, 300, 500, 800, 1200]
        for i, threshold in enumerate(thresholds):
            if total_points >= threshold:
                level = i + 1
        
        return {
            "total_days": total_days,
            "total_completed": total_completed,
            "current_streak": current_streak,
            "completion_rate": round(total_completed / total_days * 100, 1),
            "points": total_points,
            "level": level
        }


# ============================================
# 對話記錄管理
# ============================================

class ConversationManager:
    """對話記錄管理"""
    
    def __init__(self):
        self.spreadsheet = get_spreadsheet()
    
    def _get_conversations_sheet(self):
        """取得對話記錄工作表"""
        if not self.spreadsheet:
            return None
        try:
            return self.spreadsheet.worksheet(SHEET_CONVERSATIONS)
        except:
            return None
    
    def save_message(
        self,
        session_id: str,
        patient_id: str,
        role: str,
        content: str,
        source: str = "",
        input_method: str = "",
        template_id: str = "",
        intent: str = "",
        emotion: str = ""
    ) -> bool:
        """儲存對話訊息"""
        ws = self._get_conversations_sheet()
        if not ws:
            return False
        
        try:
            now = datetime.now()
            message_id = f"MSG_{now.strftime('%Y%m%d%H%M%S%f')}"
            
            ws.append_row([
                message_id,
                session_id,
                patient_id,
                role,
                content[:500],  # 限制長度
                source,
                input_method,
                template_id,
                intent,
                emotion,
                now.strftime("%Y-%m-%d %H:%M:%S")
            ])
            
            return True
        except:
            return False


# ============================================
# 成就管理
# ============================================

class AchievementManager:
    """成就管理"""
    
    # 成就定義
    ACHIEVEMENTS = {
        "first_report": {"name": "初次回報", "icon": "🌟", "requirement": 1, "type": "completion", "points": 10},
        "streak_3": {"name": "連續3天", "icon": "🌱", "requirement": 3, "type": "streak", "points": 10},
        "streak_7": {"name": "連續7天", "icon": "🔥", "requirement": 7, "type": "streak", "points": 30},
        "streak_14": {"name": "連續14天", "icon": "⭐", "requirement": 14, "type": "streak", "points": 50},
        "streak_21": {"name": "連續21天", "icon": "🏅", "requirement": 21, "type": "streak", "points": 80},
        "streak_30": {"name": "連續30天", "icon": "🏆", "requirement": 30, "type": "streak", "points": 150},
        "complete_50": {"name": "完成50次", "icon": "💎", "requirement": 50, "type": "completion", "points": 100},
        "first_description": {"name": "詳細描述者", "icon": "✍️", "requirement": 1, "type": "special", "points": 15},
    }
    
    def __init__(self):
        self.spreadsheet = get_spreadsheet()
    
    def _get_achievements_sheet(self):
        """取得成就記錄工作表"""
        if not self.spreadsheet:
            return None
        try:
            return self.spreadsheet.worksheet(SHEET_ACHIEVEMENTS)
        except:
            return None
    
    def get_patient_achievements(self, patient_id: str) -> List[Dict]:
        """取得病人已解鎖的成就"""
        ws = self._get_achievements_sheet()
        if not ws:
            return []
        
        try:
            records = ws.get_all_records()
            unlocked = []
            
            for record in records:
                if record.get("病人ID") == patient_id:
                    unlocked.append({
                        "id": record.get("成就ID"),
                        "name": record.get("成就名稱"),
                        "date": record.get("解鎖日期"),
                        "points": record.get("獲得積分")
                    })
            
            return unlocked
        except:
            return []
    
    def check_and_unlock(self, patient_id: str, stats: Dict) -> List[Dict]:
        """
        檢查並解鎖成就
        
        Returns:
            新解鎖的成就列表
        """
        ws = self._get_achievements_sheet()
        if not ws:
            return []
        
        # 取得已解鎖成就
        unlocked_ids = [a["id"] for a in self.get_patient_achievements(patient_id)]
        
        new_unlocks = []
        
        for achievement_id, achievement in self.ACHIEVEMENTS.items():
            if achievement_id in unlocked_ids:
                continue
            
            should_unlock = False
            
            if achievement["type"] == "streak":
                if stats.get("current_streak", 0) >= achievement["requirement"]:
                    should_unlock = True
            
            elif achievement["type"] == "completion":
                if stats.get("total_completed", 0) >= achievement["requirement"]:
                    should_unlock = True
            
            if should_unlock:
                # 解鎖成就
                try:
                    now = datetime.now()
                    record_id = f"ACH_{patient_id}_{achievement_id}_{now.strftime('%Y%m%d')}"
                    
                    ws.append_row([
                        record_id,
                        patient_id,
                        achievement_id,
                        achievement["name"],
                        now.strftime("%Y-%m-%d"),
                        achievement["points"]
                    ])
                    
                    new_unlocks.append({
                        "id": achievement_id,
                        "name": achievement["name"],
                        "icon": achievement["icon"],
                        "points": achievement["points"]
                    })
                except:
                    pass
        
        return new_unlocks
    
    def get_all_achievements_status(self, patient_id: str) -> List[Dict]:
        """取得所有成就的狀態"""
        unlocked = self.get_patient_achievements(patient_id)
        unlocked_ids = [a["id"] for a in unlocked]
        
        all_achievements = []
        
        for achievement_id, achievement in self.ACHIEVEMENTS.items():
            status = {
                "id": achievement_id,
                "name": achievement["name"],
                "icon": achievement["icon"],
                "points": achievement["points"],
                "unlocked": achievement_id in unlocked_ids,
                "date": None
            }
            
            # 找到解鎖日期
            for u in unlocked:
                if u["id"] == achievement_id:
                    status["date"] = u["date"]
                    break
            
            all_achievements.append(status)
        
        return all_achievements


# ============================================
# 全域實例（方便使用）
# ============================================

@st.cache_resource
def get_patient_manager():
    """取得病人管理器（快取）"""
    return PatientManager()

@st.cache_resource
def get_report_manager():
    """取得回報管理器（快取）"""
    return ReportManager()

@st.cache_resource
def get_conversation_manager():
    """取得對話管理器（快取）"""
    return ConversationManager()

@st.cache_resource
def get_achievement_manager():
    """取得成就管理器（快取）"""
    return AchievementManager()


# ============================================
# 測試連線
# ============================================

def test_connection() -> bool:
    """測試 Google Sheets 連線"""
    try:
        spreadsheet = get_spreadsheet()
        if spreadsheet:
            st.success(f"✅ 已連接到試算表: {spreadsheet.title}")
            return True
        return False
    except Exception as e:
        st.error(f"❌ 連線失敗: {e}")
        return False
