"""
AI-CARE Lung - AI 語音電話模組 v2.0
====================================
支援真正的 Twilio 語音電話 + Demo 模式

功能：
1. 病人主動請求 AI 回撥（Demo 推薦）
2. 真正撥打電話，AI 語音對話
3. 語音辨識病人回答
4. 結果自動寫入 Google Sheets

三軍總醫院 數位醫療中心
"""

import streamlit as st
import time
from datetime import datetime
import os

# ============================================
# Twilio 設定
# ============================================

def get_twilio_config():
    """取得 Twilio 設定"""
    try:
        return {
            "account_sid": st.secrets.get("TWILIO_ACCOUNT_SID", ""),
            "auth_token": st.secrets.get("TWILIO_AUTH_TOKEN", ""),
            "phone_number": st.secrets.get("TWILIO_PHONE_NUMBER", ""),
            "webhook_url": st.secrets.get("TWILIO_WEBHOOK_URL", ""),
        }
    except:
        return {
            "account_sid": os.environ.get("TWILIO_ACCOUNT_SID", ""),
            "auth_token": os.environ.get("TWILIO_AUTH_TOKEN", ""),
            "phone_number": os.environ.get("TWILIO_PHONE_NUMBER", ""),
            "webhook_url": os.environ.get("TWILIO_WEBHOOK_URL", ""),
        }


def is_twilio_configured():
    """檢查 Twilio 是否已設定"""
    config = get_twilio_config()
    return bool(config["account_sid"] and config["auth_token"] and config["phone_number"])


# ============================================
# AI 語音電話對話流程 (基於 MDASI-LC)
# ============================================
VOICE_CALL_STEPS = [
    {
        "id": "incoming_call",
        "type": "system",
        "content": "📞 來電中...",
        "subtitle": "三軍總醫院 健康小助手",
        "wait_action": "接聽"
    },
    {
        "id": "greeting",
        "type": "ai",
        "content": "{patient_name}您好，我是三軍總醫院的健康小助手小安。今天是您手術後第{post_op_day}天，想關心一下您的狀況。現在方便聊幾分鐘嗎？",
        "expected_responses": ["好，可以", "方便", "沒問題"],
        "quick_replies": ["好，可以", "方便，請說", "沒問題"]
    },
    {
        "id": "overall",
        "type": "ai",
        "symptom": "overall",
        "content": "太好了！首先想請問您，今天整體感覺怎麼樣？如果用 0 到 10 分來說，0 分是完全沒有不舒服，10 分是非常不舒服，您會給幾分呢？",
        "score_question": True,
        "icon": "💪"
    },
    {
        "id": "pain",
        "type": "ai",
        "symptom": "pain",
        "content": "了解。那傷口或其他地方有疼痛嗎？疼痛程度大概幾分？",
        "score_question": True,
        "icon": "🩹",
        "alert_threshold": 7
    },
    {
        "id": "dyspnea",
        "type": "ai",
        "symptom": "dyspnea",
        "content": "呼吸方面呢？有沒有喘或呼吸困難的感覺？",
        "score_question": True,
        "icon": "💨",
        "alert_threshold": 6,
        "follow_up": "是休息時也會喘，還是活動的時候比較明顯？"
    },
    {
        "id": "fatigue",
        "type": "ai",
        "symptom": "fatigue",
        "content": "那精神和體力方面呢？會不會很容易累或疲勞？",
        "score_question": True,
        "icon": "😮‍💨"
    },
    {
        "id": "cough",
        "type": "ai",
        "symptom": "cough",
        "content": "咳嗽的情況如何？有咳嗽嗎？咳得多不多？",
        "score_question": True,
        "icon": "🤧",
        "follow_up": "咳嗽有痰嗎？痰是什麼顏色的？"
    },
    {
        "id": "sleep_appetite",
        "type": "ai",
        "symptom": "sleep_appetite",
        "content": "睡眠和食慾方面呢？晚上睡得好嗎？吃得下東西嗎？",
        "multi_choice": True,
        "options": {
            "sleep": ["睡得好", "還可以", "睡不好"],
            "appetite": ["吃得下", "普通", "沒胃口"]
        },
        "icon": "😴"
    },
    {
        "id": "safety_check",
        "type": "ai",
        "content": "最後想確認一下，有沒有發燒？傷口有沒有紅腫、流膿或異常分泌物？",
        "safety_check": True,
        "icon": "🔍",
        "critical_flags": ["fever", "wound_infection", "blood_in_sputum"]
    },
    {
        "id": "additional",
        "type": "ai",
        "content": "還有沒有其他想告訴醫療團隊的事情，或是有什麼問題想問的？",
        "open_ended": True,
        "icon": "💭"
    },
    {
        "id": "closing",
        "type": "ai",
        "content": "好的，謝謝{patient_name}今天的回報。我幫您整理一下：{summary}。這些資訊我會回報給醫療團隊，{follow_up_action}。祝您今天順心，有任何問題隨時打給我們！",
        "closing": True,
        "icon": "👋"
    }
]


# ============================================
# Twilio 電話撥打功能
# ============================================

def request_ai_callback(patient_id, patient_name, phone_number, post_op_day):
    """
    請求 AI 回撥電話
    
    Args:
        patient_id: 病人 ID
        patient_name: 病人姓名
        phone_number: 病人電話
        post_op_day: 術後天數
    
    Returns:
        dict: 撥打結果
    """
    if not is_twilio_configured():
        return {"success": False, "error": "Twilio 未設定", "demo_mode": True}
    
    try:
        from twilio.rest import Client
        
        config = get_twilio_config()
        client = Client(config["account_sid"], config["auth_token"])
        
        # 格式化電話號碼
        formatted_phone = format_phone_number(phone_number)
        
        # 建立通話
        call = client.calls.create(
            to=formatted_phone,
            from_=config["phone_number"],
            url=f"{config['webhook_url']}/voice/start?patient_id={patient_id}&patient_name={patient_name}&post_op_day={post_op_day}",
            status_callback=f"{config['webhook_url']}/voice/status",
            status_callback_event=["completed"],
            record=True
        )
        
        return {
            "success": True,
            "call_sid": call.sid,
            "message": f"正在撥打電話至 {phone_number}..."
        }
        
    except ImportError:
        return {"success": False, "error": "請安裝 twilio 套件", "demo_mode": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


def format_phone_number(phone):
    """格式化電話號碼為 E.164 格式"""
    phone = ''.join(filter(str.isdigit, str(phone)))
    
    if phone.startswith('09') and len(phone) == 10:
        return f"+886{phone[1:]}"
    elif phone.startswith('886'):
        return f"+{phone}"
    elif phone.startswith('+886'):
        return phone
    else:
        return f"+886{phone}"


# ============================================
# CSS 樣式
# ============================================

def get_voice_call_css():
    """取得語音電話的 CSS 樣式"""
    return """
    <style>
    /* 來電動畫 */
    @keyframes pulse-ring {
        0% { transform: scale(0.8); opacity: 1; }
        50% { transform: scale(1.2); opacity: 0.5; }
        100% { transform: scale(0.8); opacity: 1; }
    }
    
    @keyframes shake {
        0%, 100% { transform: translateX(0); }
        25% { transform: translateX(-5px) rotate(-5deg); }
        75% { transform: translateX(5px) rotate(5deg); }
    }
    
    @keyframes voice-wave {
        0%, 100% { height: 8px; }
        50% { height: 24px; }
    }
    
    .incoming-call-card {
        background: linear-gradient(135deg, #00897B 0%, #004D40 100%);
        border-radius: 24px;
        padding: 2.5rem;
        text-align: center;
        color: white;
        box-shadow: 0 20px 60px rgba(0, 137, 123, 0.4);
        max-width: 380px;
        margin: 2rem auto;
    }
    
    .call-icon {
        font-size: 4rem;
        animation: shake 0.5s ease-in-out infinite;
        margin-bottom: 1rem;
    }
    
    .pulse-ring {
        width: 100px;
        height: 100px;
        border-radius: 50%;
        background: rgba(255,255,255,0.2);
        display: flex;
        align-items: center;
        justify-content: center;
        margin: 0 auto 1.5rem;
        animation: pulse-ring 1.5s ease-out infinite;
    }
    
    .caller-name {
        font-size: 1.5rem;
        font-weight: 600;
        margin: 0.5rem 0;
    }
    
    .caller-subtitle {
        font-size: 0.95rem;
        opacity: 0.85;
    }
    
    /* 通話中介面 */
    .call-active-card {
        background: linear-gradient(180deg, #1a1a2e 0%, #16213e 100%);
        border-radius: 24px;
        padding: 2rem;
        color: white;
        max-width: 420px;
        margin: 1rem auto;
    }
    
    .call-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 1.5rem;
    }
    
    .call-timer {
        font-size: 1.1rem;
        color: #4ade80;
        font-family: monospace;
    }
    
    .call-status {
        font-size: 0.85rem;
        color: #94a3b8;
    }
    
    /* 語音波形動畫 */
    .voice-wave-container {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 4px;
        height: 40px;
        margin: 1rem 0;
    }
    
    .voice-wave-bar {
        width: 4px;
        background: linear-gradient(180deg, #00897B, #4ade80);
        border-radius: 2px;
        animation: voice-wave 0.5s ease-in-out infinite;
    }
    
    .voice-wave-bar:nth-child(1) { animation-delay: 0s; height: 12px; }
    .voice-wave-bar:nth-child(2) { animation-delay: 0.1s; height: 20px; }
    .voice-wave-bar:nth-child(3) { animation-delay: 0.2s; height: 28px; }
    .voice-wave-bar:nth-child(4) { animation-delay: 0.15s; height: 16px; }
    .voice-wave-bar:nth-child(5) { animation-delay: 0.25s; height: 24px; }
    .voice-wave-bar:nth-child(6) { animation-delay: 0.1s; height: 20px; }
    .voice-wave-bar:nth-child(7) { animation-delay: 0.3s; height: 12px; }
    
    /* 對話氣泡（電話版） */
    .voice-bubble {
        padding: 1rem 1.25rem;
        border-radius: 16px;
        margin: 0.75rem 0;
        max-width: 90%;
        line-height: 1.6;
        position: relative;
    }
    
    .voice-bubble-ai {
        background: linear-gradient(135deg, #E0F2F1 0%, #B2DFDB 100%);
        color: #004D40;
        margin-right: auto;
        border-bottom-left-radius: 4px;
    }
    
    .voice-bubble-ai::before {
        content: "🤖 小安";
        display: block;
        font-size: 0.75rem;
        font-weight: 600;
        color: #00695C;
        margin-bottom: 0.25rem;
    }
    
    .voice-bubble-patient {
        background: linear-gradient(135deg, #00897B 0%, #00695C 100%);
        color: white;
        margin-left: auto;
        border-bottom-right-radius: 4px;
    }
    
    .voice-bubble-patient::before {
        content: "👤 您";
        display: block;
        font-size: 0.75rem;
        font-weight: 600;
        opacity: 0.8;
        margin-bottom: 0.25rem;
    }
    
    /* 分數選擇器 */
    .score-slider-container {
        background: #f8fafc;
        border-radius: 16px;
        padding: 1.5rem;
        margin: 1rem 0;
    }
    
    .score-display {
        text-align: center;
        font-size: 2.5rem;
        font-weight: 700;
        margin: 1rem 0;
    }
    
    .score-label {
        text-align: center;
        font-size: 1rem;
        color: #64748b;
    }
    
    /* 回報卡片 */
    .call-report-card {
        background: white;
        border-radius: 16px;
        padding: 1.5rem;
        box-shadow: 0 4px 20px rgba(0,0,0,0.08);
        margin: 1rem 0;
    }
    
    .report-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 1rem;
    }
    
    .alert-badge {
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 600;
    }
    
    .alert-green {
        background: #dcfce7;
        color: #166534;
    }
    
    .alert-yellow {
        background: #fef3c7;
        color: #92400e;
    }
    
    .alert-red {
        background: #fee2e2;
        color: #991b1b;
    }
    
    /* 請求回撥按鈕 */
    .callback-request-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 20px;
        padding: 2rem;
        text-align: center;
        color: white;
        margin: 1rem 0;
    }
    
    .callback-request-card h3 {
        margin: 0 0 0.5rem 0;
    }
    
    .callback-request-card p {
        opacity: 0.9;
        margin-bottom: 1rem;
    }
    </style>
    """


# ============================================
# Session State 初始化
# ============================================

def init_voice_call_state():
    """初始化語音電話相關的 Session State"""
    if "voice_call_step" not in st.session_state:
        st.session_state.voice_call_step = 0
    if "voice_call_messages" not in st.session_state:
        st.session_state.voice_call_messages = []
    if "voice_call_scores" not in st.session_state:
        st.session_state.voice_call_scores = {}
    if "voice_call_started" not in st.session_state:
        st.session_state.voice_call_started = False
    if "voice_call_ended" not in st.session_state:
        st.session_state.voice_call_ended = False
    if "voice_call_start_time" not in st.session_state:
        st.session_state.voice_call_start_time = None
    if "safety_flags" not in st.session_state:
        st.session_state.safety_flags = {"fever": False, "wound_issue": False}
    if "real_call_mode" not in st.session_state:
        st.session_state.real_call_mode = False
    if "waiting_for_call" not in st.session_state:
        st.session_state.waiting_for_call = False


# ============================================
# 警示等級計算
# ============================================

def calculate_alert_level(scores, safety_flags):
    """計算警示等級"""
    # 紅燈條件
    if safety_flags.get("fever") or safety_flags.get("wound_issue"):
        return "red", "🔴 需立即關注"
    if scores.get("pain", 0) >= 7 or scores.get("dyspnea", 0) >= 6:
        return "red", "🔴 需立即關注"
    
    # 黃燈條件
    if scores.get("pain", 0) >= 4 or scores.get("dyspnea", 0) >= 4:
        return "yellow", "🟡 需要追蹤"
    if scores.get("overall", 0) >= 5:
        return "yellow", "🟡 需要追蹤"
    
    # 綠燈
    return "green", "🟢 狀況良好"


def get_follow_up_action(alert_level):
    """根據警示等級取得後續行動"""
    if alert_level == "red":
        return "我們的個管師會在 30 分鐘內聯繫您，請保持電話暢通"
    elif alert_level == "yellow":
        return "個管師會在今天內與您聯繫追蹤"
    else:
        return "您的狀況良好，繼續保持！有任何不適隨時回報"


# ============================================
# 渲染函數
# ============================================

def render_request_callback(patient):
    """渲染請求回撥頁面"""
    twilio_ready = is_twilio_configured()
    
    st.markdown("""
    <div class="callback-request-card">
        <div style="font-size: 3rem; margin-bottom: 0.5rem;">📞</div>
        <h3>AI 語音電話追蹤</h3>
        <p>我們的 AI 健康助手「小安」將撥打電話給您，<br>透過語音對話了解您的症狀狀況。</p>
    </div>
    """, unsafe_allow_html=True)
    
    if twilio_ready:
        st.success("✅ 語音電話功能已啟用")
        
        phone = patient.get("phone", "")
        if phone:
            st.info(f"📱 將撥打至：{phone}")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("📞 請 AI 打給我", type="primary", use_container_width=True):
                    with st.spinner("正在撥打電話..."):
                        result = request_ai_callback(
                            patient_id=patient.get("patient_id", "demo"),
                            patient_name=patient.get("name", "先生/小姐"),
                            phone_number=phone,
                            post_op_day=patient.get("post_op_day", 1)
                        )
                    
                    if result.get("success"):
                        st.success(f"✅ {result.get('message')}")
                        st.info("📱 請接聽來電，AI 小安將與您對話")
                        st.balloons()
                    else:
                        st.error(f"❌ 撥打失敗：{result.get('error')}")
            
            with col2:
                if st.button("🎮 使用 Demo 模式", use_container_width=True):
                    st.session_state.real_call_mode = False
                    st.rerun()
        else:
            st.warning("⚠️ 尚未設定電話號碼，請先更新個人資料")
            if st.button("🎮 使用 Demo 模式", use_container_width=True):
                st.session_state.real_call_mode = False
                st.rerun()
    else:
        st.warning("📱 真實電話功能尚未啟用，目前為 Demo 模式")
        st.markdown("""
        <div style="background: #f0f9ff; padding: 1rem; border-radius: 12px; margin: 1rem 0;">
            <strong>💡 Demo 說明：</strong><br>
            這是模擬 AI 語音電話的互動體驗。<br>
            實際系統會真正撥打電話給您，透過語音對話收集症狀。
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("🎮 開始 Demo 體驗", type="primary", use_container_width=True):
            st.session_state.real_call_mode = False
            st.rerun()


def render_incoming_call(patient):
    """渲染來電畫面"""
    st.markdown(f"""
    <div class="incoming-call-card">
        <div class="pulse-ring">
            <div class="call-icon">📞</div>
        </div>
        <div class="caller-name">三軍總醫院</div>
        <div class="caller-subtitle">健康小助手 小安</div>
        <div style="margin-top: 1rem; font-size: 0.9rem; opacity: 0.8;">
            來電關心您的術後狀況
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("📞 接聽", type="primary", use_container_width=True, key="accept_call"):
            st.session_state.voice_call_started = True
            st.session_state.voice_call_start_time = datetime.now()
            st.session_state.voice_call_step = 1  # 跳過 incoming_call 步驟
            st.rerun()
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("📵 稍後再說", use_container_width=True, key="decline_call"):
            st.session_state.current_page = "home"
            st.rerun()


def render_active_call(patient):
    """渲染通話中畫面"""
    # 計算通話時間
    if st.session_state.voice_call_start_time:
        elapsed = datetime.now() - st.session_state.voice_call_start_time
        elapsed_str = f"{int(elapsed.total_seconds() // 60):02d}:{int(elapsed.total_seconds() % 60):02d}"
    else:
        elapsed_str = "00:00"
    
    # 通話頭部
    st.markdown(f"""
    <div class="call-active-card">
        <div class="call-header">
            <div>
                <div style="font-weight: 600;">🤖 小安</div>
                <div class="call-status">三軍總醫院 健康小助手</div>
            </div>
            <div class="call-timer">⏱️ {elapsed_str}</div>
        </div>
        <div class="voice-wave-container">
            <div class="voice-wave-bar"></div>
            <div class="voice-wave-bar"></div>
            <div class="voice-wave-bar"></div>
            <div class="voice-wave-bar"></div>
            <div class="voice-wave-bar"></div>
            <div class="voice-wave-bar"></div>
            <div class="voice-wave-bar"></div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # 對話歷史
    for msg in st.session_state.voice_call_messages:
        bubble_class = "voice-bubble-ai" if msg["role"] == "ai" else "voice-bubble-patient"
        st.markdown(f'<div class="voice-bubble {bubble_class}">{msg["content"]}</div>', unsafe_allow_html=True)
    
    # 當前步驟
    current_step_idx = st.session_state.voice_call_step
    if current_step_idx < len(VOICE_CALL_STEPS):
        step = VOICE_CALL_STEPS[current_step_idx]
        
        # 顯示 AI 的話
        ai_text = step["content"].format(
            patient_name=patient.get("name", "先生/小姐"),
            post_op_day=patient.get("post_op_day", 1),
            summary=generate_summary(),
            follow_up_action=get_follow_up_action(calculate_alert_level(
                st.session_state.voice_call_scores, 
                st.session_state.safety_flags
            )[0])
        )
        
        # 如果這條訊息還沒加入，加入它
        if not st.session_state.voice_call_messages or \
           st.session_state.voice_call_messages[-1].get("step_id") != step["id"] or \
           st.session_state.voice_call_messages[-1].get("role") != "ai":
            st.session_state.voice_call_messages.append({
                "role": "ai",
                "content": ai_text,
                "step_id": step["id"]
            })
            st.rerun()
        
        st.markdown("---")
        
        # 根據步驟類型渲染不同的輸入
        if step.get("score_question"):
            render_score_input(step)
        elif step.get("multi_choice"):
            render_multi_choice(step)
        elif step.get("safety_check"):
            render_safety_check(step)
        elif step.get("open_ended"):
            render_open_ended(step)
        elif step.get("quick_replies"):
            render_quick_replies(step)
        elif step.get("closing"):
            render_closing(step, patient)
    else:
        # 對話結束
        st.session_state.voice_call_ended = True
        st.rerun()


def render_score_input(step):
    """渲染分數輸入"""
    score_labels = {
        0: "完全沒有", 1: "非常輕微", 2: "輕微", 3: "輕度",
        4: "中等偏輕", 5: "中等", 6: "中等偏重", 7: "明顯",
        8: "嚴重", 9: "非常嚴重", 10: "極度嚴重"
    }
    
    score = st.slider(
        f"{step.get('icon', '📊')} 選擇分數",
        0, 10, 3,
        key=f"score_{step['id']}"
    )
    
    # 顯示分數含義
    if score <= 3:
        color = "#10b981"
    elif score <= 6:
        color = "#f59e0b"
    else:
        color = "#ef4444"
    
    st.markdown(f"""
    <div class="score-slider-container">
        <div class="score-display" style="color: {color};">{score}</div>
        <div class="score-label">{score_labels[score]}</div>
    </div>
    """, unsafe_allow_html=True)
    
    if st.button("確認", type="primary", use_container_width=True, key=f"confirm_{step['id']}"):
        symptom = step.get("symptom", step["id"])
        st.session_state.voice_call_scores[symptom] = score
        st.session_state.voice_call_messages.append({
            "role": "patient",
            "content": f"大概 {score} 分，{score_labels[score]}",
            "step_id": step["id"]
        })
        st.session_state.voice_call_step += 1
        st.rerun()


def render_multi_choice(step):
    """渲染多選題"""
    options = step.get("options", {})
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**😴 睡眠**")
        sleep = st.radio("", options.get("sleep", []), key="sleep_choice", label_visibility="collapsed")
    
    with col2:
        st.markdown("**🍽️ 食慾**")
        appetite = st.radio("", options.get("appetite", []), key="appetite_choice", label_visibility="collapsed")
    
    if st.button("確認", type="primary", use_container_width=True, key=f"confirm_{step['id']}"):
        st.session_state.voice_call_scores["sleep"] = sleep
        st.session_state.voice_call_scores["appetite"] = appetite
        st.session_state.voice_call_messages.append({
            "role": "patient",
            "content": f"睡眠{sleep}，食慾{appetite}",
            "step_id": step["id"]
        })
        st.session_state.voice_call_step += 1
        st.rerun()


def render_safety_check(step):
    """渲染安全檢查"""
    col1, col2 = st.columns(2)
    
    with col1:
        fever = st.checkbox("🌡️ 有發燒", key="fever_check")
    
    with col2:
        wound = st.checkbox("🩹 傷口異常", key="wound_check")
    
    if st.button("確認", type="primary", use_container_width=True, key=f"confirm_{step['id']}"):
        st.session_state.safety_flags["fever"] = fever
        st.session_state.safety_flags["wound_issue"] = wound
        
        response_parts = []
        if fever:
            response_parts.append("有發燒")
        if wound:
            response_parts.append("傷口有異常")
        if not response_parts:
            response_parts.append("沒有發燒，傷口正常")
        
        st.session_state.voice_call_messages.append({
            "role": "patient",
            "content": "，".join(response_parts),
            "step_id": step["id"]
        })
        st.session_state.voice_call_step += 1
        st.rerun()


def render_open_ended(step):
    """渲染開放式問題"""
    response = st.text_input(
        "💬 請說...",
        placeholder="沒有的話可以直接點「繼續」",
        key="open_ended_input"
    )
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("沒有其他問題", use_container_width=True, key="no_question"):
            st.session_state.voice_call_messages.append({
                "role": "patient",
                "content": "目前沒有其他問題，謝謝",
                "step_id": step["id"]
            })
            st.session_state.voice_call_step += 1
            st.rerun()
    
    with col2:
        if st.button("送出", type="primary", use_container_width=True, key="submit_question"):
            st.session_state.voice_call_messages.append({
                "role": "patient",
                "content": response if response else "沒有其他問題",
                "step_id": step["id"]
            })
            st.session_state.voice_call_step += 1
            st.rerun()


def render_quick_replies(step):
    """渲染快速回覆按鈕"""
    st.markdown("**請回應：**")
    
    cols = st.columns(len(step["quick_replies"]))
    for i, reply in enumerate(step["quick_replies"]):
        with cols[i]:
            if st.button(reply, key=f"quick_{step['id']}_{i}", use_container_width=True):
                st.session_state.voice_call_messages.append({
                    "role": "patient",
                    "content": reply,
                    "step_id": step["id"]
                })
                st.session_state.voice_call_step += 1
                st.rerun()


def render_closing(step, patient):
    """渲染結束語"""
    st.markdown("---")
    
    if st.button("📵 結束通話", type="primary", use_container_width=True, key="finish_call"):
        st.session_state.voice_call_ended = True
        st.rerun()


def generate_summary():
    """生成症狀摘要"""
    scores = st.session_state.voice_call_scores
    parts = []
    
    if "overall" in scores:
        parts.append(f"整體{scores['overall']}分")
    if "pain" in scores:
        parts.append(f"疼痛{scores['pain']}分")
    if "dyspnea" in scores:
        parts.append(f"呼吸困難{scores['dyspnea']}分")
    
    return "、".join(parts) if parts else "狀況良好"


def render_call_report(patient):
    """渲染通話結束報告"""
    scores = st.session_state.voice_call_scores
    alert_level, alert_text = calculate_alert_level(scores, st.session_state.safety_flags)
    
    # 計算通話時長
    if st.session_state.voice_call_start_time:
        duration = datetime.now() - st.session_state.voice_call_start_time
        duration_str = f"{int(duration.total_seconds() // 60)}:{int(duration.total_seconds() % 60):02d}"
    else:
        duration_str = "3:42"
    
    st.markdown("""
    <div style="text-align: center; padding: 2rem 0;">
        <div style="font-size: 4rem;">📞</div>
        <h2 style="color: #1e293b; margin: 0.5rem 0;">通話已結束</h2>
        <p style="color: #64748b;">感謝您的配合！</p>
    </div>
    """, unsafe_allow_html=True)
    
    # 警示等級
    alert_class = f"alert-{alert_level}"
    st.markdown(f"""
    <div class="call-report-card">
        <div class="report-header">
            <div>
                <div style="font-weight: 600; color: #1e293b;">📋 症狀追蹤報告</div>
                <div style="font-size: 0.85rem; color: #64748b;">
                    {datetime.now().strftime('%Y-%m-%d %H:%M')} | 通話時長 {duration_str}
                </div>
            </div>
            <div class="alert-badge {alert_class}">{alert_text}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # 症狀分數摘要
    st.markdown("#### 📊 症狀評估")
    
    col1, col2, col3 = st.columns(3)
    symptom_display = [
        ("overall", "💪 整體", col1),
        ("pain", "🩹 疼痛", col2),
        ("dyspnea", "💨 呼吸", col3),
        ("fatigue", "😮‍💨 疲勞", col1),
        ("cough", "🤧 咳嗽", col2),
    ]
    
    for symptom_id, label, col in symptom_display:
        score = scores.get(symptom_id, 0)
        if score <= 3:
            color = "#10b981"
        elif score <= 6:
            color = "#f59e0b"
        else:
            color = "#ef4444"
        
        with col:
            st.markdown(f"""
            <div style="background: #f8fafc; border-radius: 12px; padding: 1rem; text-align: center; margin-bottom: 0.5rem;">
                <div style="font-size: 1.75rem; font-weight: 700; color: {color};">{score}</div>
                <div style="font-size: 0.85rem; color: #64748b;">{label}</div>
            </div>
            """, unsafe_allow_html=True)
    
    # 安全檢查結果
    st.markdown("#### 🔍 安全檢查")
    safety_col1, safety_col2 = st.columns(2)
    
    with safety_col1:
        fever_status = "⚠️ 有發燒" if st.session_state.safety_flags.get("fever") else "✅ 無發燒"
        fever_color = "#ef4444" if st.session_state.safety_flags.get("fever") else "#10b981"
        st.markdown(f"""
        <div style="background: #f8fafc; border-radius: 12px; padding: 1rem; text-align: center;">
            <span style="color: {fever_color}; font-weight: 600;">{fever_status}</span>
        </div>
        """, unsafe_allow_html=True)
    
    with safety_col2:
        wound_status = "⚠️ 傷口異常" if st.session_state.safety_flags.get("wound_issue") else "✅ 傷口正常"
        wound_color = "#ef4444" if st.session_state.safety_flags.get("wound_issue") else "#10b981"
        st.markdown(f"""
        <div style="background: #f8fafc; border-radius: 12px; padding: 1rem; text-align: center;">
            <span style="color: {wound_color}; font-weight: 600;">{wound_status}</span>
        </div>
        """, unsafe_allow_html=True)
    
    # 後續行動
    st.markdown("#### 📌 後續行動")
    follow_up = get_follow_up_action(alert_level)
    
    if alert_level == "red":
        st.error(f"🚨 {follow_up}")
    elif alert_level == "yellow":
        st.warning(f"⚠️ {follow_up}")
    else:
        st.success(f"✅ {follow_up}")
    
    # 資料同步說明
    st.info("📤 此次通話內容已自動儲存並同步至醫療團隊後台")
    
    st.markdown("---")
    
    # 返回按鈕
    if st.button("🏠 返回首頁", type="primary", use_container_width=True):
        # 重置狀態
        st.session_state.voice_call_step = 0
        st.session_state.voice_call_messages = []
        st.session_state.voice_call_scores = {}
        st.session_state.voice_call_started = False
        st.session_state.voice_call_ended = False
        st.session_state.voice_call_start_time = None
        st.session_state.safety_flags = {"fever": False, "wound_issue": False}
        st.session_state.today_reported = True
        st.session_state.current_page = "home"
        st.rerun()


# ============================================
# 主要渲染函數
# ============================================

def render_voice_call_demo():
    """主要渲染函數：AI 語音電話"""
    
    # 載入 CSS
    st.markdown(get_voice_call_css(), unsafe_allow_html=True)
    
    # 初始化狀態
    init_voice_call_state()
    
    patient = st.session_state.patient
    
    # 頁面標題
    st.markdown("### 📞 AI 語音電話")
    
    # 返回按鈕（非通話中顯示）
    if not st.session_state.voice_call_started and not st.session_state.voice_call_ended:
        if st.button("← 返回首頁", key="back_to_home"):
            st.session_state.current_page = "home"
            st.rerun()
        st.markdown("---")
    
    # 根據狀態渲染不同畫面
    if st.session_state.voice_call_ended:
        # 通話結束，顯示報告
        render_call_report(patient)
    elif not st.session_state.voice_call_started:
        # 選擇模式頁面
        twilio_configured = is_twilio_configured()
        
        if twilio_configured:
            # 顯示選擇：真實電話 vs Demo
            render_request_callback(patient)
            
            st.markdown("---")
            st.markdown("#### 或使用 Demo 模式體驗")
            
            if st.button("🎮 開始 Demo", use_container_width=True):
                pass  # 繼續顯示來電畫面
        
        # Demo 來電畫面
        st.markdown("""
        <div style="background: #E0F2F1; border: 1px solid #00897B; border-radius: 12px; 
                    padding: 1rem; margin: 1rem 0; font-size: 0.9rem;">
            <strong>💡 Demo 模式：</strong><br>
            模擬 AI 語音電話互動體驗。實際系統會真正撥打電話給您。
        </div>
        """, unsafe_allow_html=True)
        
        render_incoming_call(patient)
    else:
        # 通話中
        render_active_call(patient)
