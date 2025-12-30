"""
AI-CARE Lung - Voice Webhook Server（病人端）
=============================================

處理 Twilio 語音通話的 Webhook
當病人請求 AI 回撥時，此服務處理通話流程

部署：Google Cloud Run / Heroku / Railway

三軍總醫院 數位醫療中心
"""

from flask import Flask, request, jsonify
from twilio.twiml.voice_response import VoiceResponse, Gather
import os
import json
import logging
from datetime import datetime

# ============================================
# 設定
# ============================================

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 語音設定（台灣中文）
VOICE_CONFIG = {
    "voice": "Google.zh-TW-Standard-A",
    "language": "zh-TW"
}

# Google Sheets 設定（從環境變數）
GSHEET_ID = os.environ.get("GSHEET_ID", "")
GSHEET_CREDENTIALS = os.environ.get("GSHEET_CREDENTIALS", "")


# ============================================
# 對話腳本
# ============================================

CALL_SCRIPT = {
    "greeting": "您好，{patient_name}，我是三軍總醫院的健康小助手小安。今天是您手術後第{post_op_day}天，想關心一下您的狀況。現在方便聊幾分鐘嗎？請說「可以」或「不方便」。",
    
    "questions": [
        {
            "id": "overall",
            "text": "太好了！首先想請問您，今天整體感覺怎麼樣？0 分是完全沒有不舒服，10 分是非常不舒服，請說一個數字。",
            "type": "numeric",
            "hints": ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10"]
        },
        {
            "id": "pain",
            "text": "了解。那傷口或其他地方有疼痛嗎？疼痛程度大概幾分？",
            "type": "numeric",
            "hints": ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "沒有", "不痛"]
        },
        {
            "id": "breathing",
            "text": "呼吸方面呢？有沒有喘或呼吸困難的感覺？請說「有」或「沒有」。",
            "type": "yesno",
            "hints": ["有", "沒有", "會喘", "不會"]
        },
        {
            "id": "fever",
            "text": "請問您今天有沒有發燒？請說「有」或「沒有」。",
            "type": "yesno",
            "hints": ["有", "沒有", "有發燒", "沒發燒"],
            "is_alert": True
        },
        {
            "id": "wound",
            "text": "傷口有沒有紅腫或異常分泌物？請說「有」或「沒有」。",
            "type": "yesno",
            "hints": ["有", "沒有", "正常", "紅腫"],
            "is_alert": True
        }
    ],
    
    "closing_normal": "好的，謝謝您的回報。您今天的狀況我們已經記錄下來了。如果有任何不舒服，請撥打服務專線。祝您早日康復，再見！",
    "closing_alert": "好的，我們注意到您有一些症狀需要關注。個管師會盡快與您聯繫。如果狀況變嚴重，請立即就醫。謝謝，再見！"
}


# ============================================
# Session 管理
# ============================================

call_sessions = {}

def get_session(call_sid):
    return call_sessions.get(call_sid, {})

def update_session(call_sid, data):
    if call_sid not in call_sessions:
        call_sessions[call_sid] = {}
    call_sessions[call_sid].update(data)

def clear_session(call_sid):
    if call_sid in call_sessions:
        del call_sessions[call_sid]


# ============================================
# Webhook 路由
# ============================================

@app.route("/voice/start", methods=["POST"])
def voice_start():
    """通話開始 - 播放問候語"""
    call_sid = request.values.get("CallSid")
    patient_id = request.args.get("patient_id", "")
    patient_name = request.args.get("patient_name", "先生小姐")
    post_op_day = request.args.get("post_op_day", "1")
    
    logger.info(f"Call started: {call_sid} | Patient: {patient_name}")
    
    # 初始化 session
    update_session(call_sid, {
        "patient_id": patient_id,
        "patient_name": patient_name,
        "post_op_day": post_op_day,
        "current_question": 0,
        "answers": {},
        "started_at": datetime.now().isoformat()
    })
    
    response = VoiceResponse()
    
    # 問候語 + 確認可否通話
    greeting = CALL_SCRIPT["greeting"].format(
        patient_name=patient_name,
        post_op_day=post_op_day
    )
    
    gather = Gather(
        input="speech",
        action=f"/voice/confirm?call_sid={call_sid}",
        method="POST",
        language="zh-TW",
        timeout=5,
        speech_timeout="auto",
        hints="可以,不方便,好,沒問題"
    )
    gather.say(greeting, **VOICE_CONFIG)
    response.append(gather)
    
    # 沒回應的處理
    response.redirect(f"/voice/no_response?call_sid={call_sid}&step=greeting")
    
    return str(response), 200, {"Content-Type": "text/xml"}


@app.route("/voice/confirm", methods=["POST"])
def voice_confirm():
    """確認病人是否方便通話"""
    call_sid = request.args.get("call_sid") or request.values.get("CallSid")
    speech_result = request.values.get("SpeechResult", "").lower()
    
    logger.info(f"Confirm response: {speech_result}")
    
    response = VoiceResponse()
    
    # 檢查是否同意
    positive = ["可以", "好", "沒問題", "方便", "ok", "yes"]
    if any(word in speech_result for word in positive):
        response.say("好的，那我們開始吧。", **VOICE_CONFIG)
        response.pause(length=0.5)
        response.redirect(f"/voice/question?call_sid={call_sid}")
    else:
        response.say("好的，那我們改天再打給您。祝您早日康復，再見！", **VOICE_CONFIG)
        response.hangup()
    
    return str(response), 200, {"Content-Type": "text/xml"}


@app.route("/voice/question", methods=["POST", "GET"])
def voice_question():
    """詢問問題"""
    call_sid = request.args.get("call_sid") or request.values.get("CallSid")
    session = get_session(call_sid)
    
    if not session:
        response = VoiceResponse()
        response.say("抱歉，系統發生錯誤。再見！", **VOICE_CONFIG)
        response.hangup()
        return str(response), 200, {"Content-Type": "text/xml"}
    
    questions = CALL_SCRIPT["questions"]
    current_idx = session.get("current_question", 0)
    
    # 檢查是否還有問題
    if current_idx >= len(questions):
        return redirect_to_closing(call_sid, session)
    
    question = questions[current_idx]
    
    response = VoiceResponse()
    
    gather = Gather(
        input="speech",
        action=f"/voice/answer?call_sid={call_sid}&question_id={question['id']}",
        method="POST",
        language="zh-TW",
        timeout=5,
        speech_timeout="auto",
        hints=",".join(question.get("hints", []))
    )
    gather.say(question["text"], **VOICE_CONFIG)
    response.append(gather)
    
    # 沒回應的處理
    response.redirect(f"/voice/no_response?call_sid={call_sid}&step={question['id']}")
    
    return str(response), 200, {"Content-Type": "text/xml"}


@app.route("/voice/answer", methods=["POST"])
def voice_answer():
    """處理回答"""
    call_sid = request.args.get("call_sid") or request.values.get("CallSid")
    question_id = request.args.get("question_id")
    speech_result = request.values.get("SpeechResult", "")
    
    logger.info(f"Answer for {question_id}: {speech_result}")
    
    session = get_session(call_sid)
    if not session:
        response = VoiceResponse()
        response.say("系統錯誤，再見！", **VOICE_CONFIG)
        response.hangup()
        return str(response), 200, {"Content-Type": "text/xml"}
    
    # 解析答案
    parsed = parse_answer(question_id, speech_result)
    
    # 儲存答案
    answers = session.get("answers", {})
    answers[question_id] = {
        "raw": speech_result,
        "parsed": parsed
    }
    
    # 更新 session
    current_idx = session.get("current_question", 0)
    update_session(call_sid, {
        "answers": answers,
        "current_question": current_idx + 1
    })
    
    response = VoiceResponse()
    response.say("好的。", **VOICE_CONFIG)
    response.pause(length=0.3)
    response.redirect(f"/voice/question?call_sid={call_sid}")
    
    return str(response), 200, {"Content-Type": "text/xml"}


@app.route("/voice/no_response", methods=["POST", "GET"])
def voice_no_response():
    """處理沒有回應"""
    call_sid = request.args.get("call_sid") or request.values.get("CallSid")
    step = request.args.get("step", "")
    
    session = get_session(call_sid)
    retry_key = f"retry_{step}"
    retry_count = session.get(retry_key, 0)
    
    response = VoiceResponse()
    
    if retry_count < 2:
        update_session(call_sid, {retry_key: retry_count + 1})
        response.say("抱歉，我沒有聽清楚。請再說一次。", **VOICE_CONFIG)
        
        if step == "greeting":
            response.redirect(f"/voice/start?patient_id={session.get('patient_id')}&patient_name={session.get('patient_name')}&post_op_day={session.get('post_op_day')}")
        else:
            response.redirect(f"/voice/question?call_sid={call_sid}")
    else:
        # 跳過這個問題
        answers = session.get("answers", {})
        answers[step] = {"raw": "", "parsed": "no_response"}
        
        current_idx = session.get("current_question", 0)
        update_session(call_sid, {
            "answers": answers,
            "current_question": current_idx + 1
        })
        
        response.say("好的，我們先跳過這個問題。", **VOICE_CONFIG)
        response.redirect(f"/voice/question?call_sid={call_sid}")
    
    return str(response), 200, {"Content-Type": "text/xml"}


def redirect_to_closing(call_sid, session):
    """重導向到結束"""
    response = VoiceResponse()
    
    # 檢查是否有警示
    answers = session.get("answers", {})
    has_alert = check_alerts(answers)
    
    if has_alert:
        response.say(CALL_SCRIPT["closing_alert"], **VOICE_CONFIG)
    else:
        response.say(CALL_SCRIPT["closing_normal"], **VOICE_CONFIG)
    
    response.hangup()
    
    # 儲存結果
    try:
        save_call_result(session)
    except Exception as e:
        logger.error(f"Failed to save: {e}")
    
    clear_session(call_sid)
    
    return str(response), 200, {"Content-Type": "text/xml"}


@app.route("/voice/status", methods=["POST"])
def voice_status():
    """通話狀態回調"""
    call_sid = request.values.get("CallSid")
    status = request.values.get("CallStatus")
    duration = request.values.get("CallDuration")
    
    logger.info(f"Call status: {call_sid} -> {status} ({duration}s)")
    
    return jsonify({"status": "ok"})


# ============================================
# 輔助函數
# ============================================

def parse_answer(question_id, speech):
    """解析語音回答"""
    text = speech.lower().strip()
    
    # 數字問題
    if question_id in ["overall", "pain"]:
        import re
        numbers = re.findall(r'\d+', text)
        if numbers:
            return min(10, max(0, int(numbers[0])))
        if any(w in text for w in ["沒有", "不", "零"]):
            return 0
        return None
    
    # 是否問題
    if question_id in ["breathing", "fever", "wound"]:
        if any(w in text for w in ["有", "會", "是"]):
            return "yes"
        if any(w in text for w in ["沒有", "沒", "不", "不會"]):
            return "no"
        return "unclear"
    
    return text


def check_alerts(answers):
    """檢查是否有警示"""
    if answers.get("fever", {}).get("parsed") == "yes":
        return True
    if answers.get("wound", {}).get("parsed") == "yes":
        return True
    if (answers.get("pain", {}).get("parsed") or 0) >= 7:
        return True
    return False


def save_call_result(session):
    """儲存通話結果到 Google Sheets"""
    if not GSHEET_ID or not GSHEET_CREDENTIALS:
        logger.warning("Google Sheets not configured")
        return
    
    try:
        import gspread
        from google.oauth2.service_account import Credentials
        
        creds_dict = json.loads(GSHEET_CREDENTIALS)
        creds = Credentials.from_service_account_info(
            creds_dict,
            scopes=[
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive"
            ]
        )
        client = gspread.authorize(creds)
        sheet = client.open_by_key(GSHEET_ID)
        
        # 寫入症狀回報表
        try:
            ws = sheet.worksheet("症狀回報")
        except:
            ws = sheet.worksheet("Reports")
        
        answers = session.get("answers", {})
        
        row = [
            f"CALL-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            session.get("patient_id", ""),
            datetime.now().strftime("%Y-%m-%d"),
            datetime.now().strftime("%H:%M:%S"),
            "voice_call",
            answers.get("pain", {}).get("parsed", ""),
            "",  # fatigue
            answers.get("breathing", {}).get("parsed", ""),
            "",  # cough
            "",  # sleep
            "",  # appetite
            "",  # mood
            "",  # descriptions...
            "",
            answers.get("breathing", {}).get("raw", ""),
            "",
            "",
            "",
            "",
            "",  # open ended
            "",
            f"AI語音通話 | 發燒:{answers.get('fever', {}).get('parsed', '')} | 傷口:{answers.get('wound', {}).get('parsed', '')}",
            answers.get("overall", {}).get("parsed", ""),
            "",
            datetime.now().isoformat()
        ]
        
        ws.append_row(row)
        logger.info(f"Saved call result for {session.get('patient_id')}")
        
    except Exception as e:
        logger.error(f"Save failed: {e}")
        raise


# ============================================
# 健康檢查
# ============================================

@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    })


@app.route("/", methods=["GET"])
def index():
    return """
    <h1>🏥 AI-CARE Lung Voice Server</h1>
    <p>病人端語音電話 Webhook 服務</p>
    <p><a href="/health">Health Check</a></p>
    <p>© 三軍總醫院 數位醫療中心</p>
    """


# ============================================
# 主程式
# ============================================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    
    print(f"""
    ╔══════════════════════════════════════════════╗
    ║   AI-CARE Lung Voice Server (Patient)        ║
    ║   Port: {port}                                  ║
    ╚══════════════════════════════════════════════╝
    """)
    
    app.run(host="0.0.0.0", port=port, debug=debug)
