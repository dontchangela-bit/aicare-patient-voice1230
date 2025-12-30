# AI-CARE Lung 病人端 v2.3

肺癌術後智慧照護系統 - 病人端介面

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://streamlit.io/)

## 🆕 v2.3 新功能：真實 AI 語音電話

支援 **Twilio** 真實語音電話撥打，病人可以請求 AI 回撥！

```
┌─────────────────────────────────────────────────────────────┐
│                    AI 語音電話流程                           │
├─────────────────────────────────────────────────────────────┤
│  1️⃣ 病人在 App 按下「請 AI 打給我」                           │
│      ↓                                                      │
│  2️⃣ Twilio 撥打電話到病人手機                                │
│      ↓                                                      │
│  3️⃣ AI 語音問候 + 逐一詢問症狀問題                            │
│      ↓                                                      │
│  4️⃣ 語音辨識病人回答 → 判斷警示等級                           │
│      ↓                                                      │
│  5️⃣ 結果自動寫入 Google Sheets                               │
└─────────────────────────────────────────────────────────────┘
```

---

## 📱 三種回報方式

| 方式 | 說明 | 適用場景 |
|------|------|----------|
| 💬 **AI 對話回報** | 文字對話式症狀回報 | 喜歡打字的用戶 |
| 📋 **數位問卷回報** | 快速問卷式回報 | 快速完成回報 |
| 📞 **AI 語音電話** | 真實電話 or Demo | 被動接聽 / 體驗 |

---

## 📁 專案結構

```
aicare-patient-voice/
│
├── patient_app/                # 病人端 Streamlit App
│   ├── .streamlit/
│   │   ├── config.toml
│   │   └── secrets.toml.example
│   ├── app.py                  # 主程式
│   ├── voice_call_module.py    # 🆕 AI 語音電話模組（支援真實電話）
│   ├── google_sheet_db.py      # Google Sheet 資料庫
│   ├── models.py               # 資料模型
│   ├── conversation_store.py   # 對話儲存
│   ├── expert_templates.py     # 專家回應範本
│   ├── requirements.txt
│   └── GOOGLE_SHEET_SETUP.md
│
├── voice_server/               # Voice Webhook Server
│   ├── voice_server.py         # Flask Webhook 處理
│   ├── requirements.txt
│   └── Dockerfile
│
└── README.md
```

---

## 🚀 快速開始

### 模式 1：Demo 模式（最簡單）

不需要 Twilio，直接體驗 AI 語音電話的互動流程。

```bash
cd patient_app
pip install -r requirements.txt
streamlit run app.py
```

進入 App 後選擇「📞 AI 語音電話」→ 開始 Demo 體驗

### 模式 2：真實電話（需設定 Twilio）

#### Step 1: 申請 Twilio
1. 前往 [Twilio](https://www.twilio.com/try-twilio) 註冊
2. 購買台灣號碼 (+886)
3. 取得 Account SID 和 Auth Token

#### Step 2: 部署 Voice Server
```bash
cd voice_server

# 部署到 Google Cloud Run
gcloud run deploy aicare-voice \
  --source . \
  --platform managed \
  --region asia-east1 \
  --allow-unauthenticated
```

記下部署後的 URL（例如：`https://aicare-voice-xxx.run.app`）

#### Step 3: 設定 Twilio Webhook
在 Twilio Console → Phone Numbers → 選擇你的號碼：
- Voice Webhook URL: `https://your-url.run.app/voice/start`

#### Step 4: 設定 Streamlit Secrets
```toml
# .streamlit/secrets.toml

TWILIO_ACCOUNT_SID = "ACxxxxxxxx"
TWILIO_AUTH_TOKEN = "your_token"
TWILIO_PHONE_NUMBER = "+886xxxxxxxxx"
TWILIO_WEBHOOK_URL = "https://your-url.run.app"

[spreadsheet]
id = "your_sheet_id"

[gcp_service_account]
# ... Google 憑證
```

#### Step 5: 執行
```bash
cd patient_app
streamlit run app.py
```

---

## 📞 AI 語音電話對話流程

```
AI：王先生您好，我是三軍總醫院的健康小助手小安。
    今天是您手術後第 5 天，想關心一下您的狀況。
    現在方便聊幾分鐘嗎？

病人：好，可以

AI：太好了！首先想請問您，今天整體感覺怎麼樣？
    0 分是完全沒有不舒服，10 分是非常不舒服，
    請說一個數字。

病人：大概 4 分

AI：了解。那傷口或其他地方有疼痛嗎？疼痛程度大概幾分？

病人：5 分左右

AI：呼吸方面呢？有沒有喘或呼吸困難的感覺？

病人：沒有

AI：請問您今天有沒有發燒？

病人：沒有

AI：傷口有沒有紅腫或異常分泌物？

病人：沒有

AI：好的，謝謝您的回報。您今天的狀況我們已經記錄下來了。
    如果有任何不舒服，請撥打服務專線。
    祝您早日康復，再見！
```

---

## 🚨 警示機制

| 等級 | 條件 | 後續行動 |
|------|------|----------|
| 🔴 紅燈 | 疼痛≥7, 呼吸困難≥6, 發燒, 傷口異常 | 個管師 30 分鐘內聯繫 |
| 🟡 黃燈 | 疼痛 4-6, 整體 5-7 | 當日追蹤 |
| 🟢 綠燈 | 所有症狀 < 4 | 常規監控 |

---

## 💰 Twilio 費用參考

| 項目 | 費用 |
|------|------|
| 台灣號碼租用 | ~$30 USD/月 |
| 撥出通話（台灣手機）| ~$0.045 USD/分鐘 |
| 語音辨識（STT）| ~$0.02 USD/分鐘 |

每通 3 分鐘的電話約 **NT$6**

---

## 📊 資料儲存

通話結果會自動寫入 Google Sheets 的「症狀回報」工作表：

| 欄位 | 說明 |
|------|------|
| 回報ID | CALL-20241230120000 |
| 病人ID | P001 |
| 回報方式 | voice_call |
| 疼痛分數 | 5 |
| 發燒 | no |
| 傷口 | no |
| 備註 | AI語音通話 |

---

## 🔧 開發選項

### 本地測試 Voice Server

```bash
cd voice_server

# 安裝 ngrok
brew install ngrok  # macOS

# 啟動 server
python voice_server.py

# 另一個終端機
ngrok http 5000

# 將 ngrok URL 設定到 Twilio Console
```

---

## 📞 聯絡

三軍總醫院 數位醫療中心

---

## License

MIT License
