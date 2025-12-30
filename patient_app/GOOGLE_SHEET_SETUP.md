# AI-CARE Lung - Google Sheet 設定指南

本文件說明如何設定 Google Sheet 作為系統資料庫。

## 📋 設定步驟總覽

1. 建立 Google Cloud 專案
2. 啟用 Google Sheets API
3. 建立服務帳戶
4. 建立 Google Sheet 試算表
5. 設定 Streamlit Secrets
6. 部署應用程式

---

## 步驟 1：建立 Google Cloud 專案

1. 前往 [Google Cloud Console](https://console.cloud.google.com/)
2. 點擊上方的專案選擇器 → **新增專案**
3. 輸入專案名稱：`aicare-lung`
4. 點擊 **建立**

---

## 步驟 2：啟用 Google Sheets API

1. 在 Google Cloud Console 中，搜尋 **Google Sheets API**
2. 點擊 **啟用**
3. 同樣搜尋並啟用 **Google Drive API**

---

## 步驟 3：建立服務帳戶

1. 前往 **IAM 與管理** → **服務帳戶**
2. 點擊 **建立服務帳戶**
3. 填寫資訊：
   - 服務帳戶名稱：`aicare-lung-service`
   - 服務帳戶 ID：`aicare-lung-service`
4. 點擊 **建立並繼續**
5. 跳過角色設定，點擊 **完成**

### 產生金鑰

1. 在服務帳戶列表中，點擊剛建立的帳戶
2. 切換到 **金鑰** 分頁
3. 點擊 **新增金鑰** → **建立新金鑰**
4. 選擇 **JSON** 格式
5. 點擊 **建立**
6. 金鑰檔案會自動下載（請妥善保管！）

---

## 步驟 4：建立 Google Sheet 試算表

1. 前往 [Google Sheets](https://sheets.google.com/)
2. 建立新的試算表
3. 命名為：`AI-CARE Lung 資料庫`
4. 記下試算表的 ID（網址中的一串字元）：
   ```
   https://docs.google.com/spreadsheets/d/【這裡就是ID】/edit
   ```

### 分享給服務帳戶

1. 點擊右上角的 **共用**
2. 在「新增使用者和群組」欄位，貼上服務帳戶的電子郵件：
   ```
   aicare-lung-service@你的專案ID.iam.gserviceaccount.com
   ```
   （可以在金鑰 JSON 檔的 `client_email` 欄位找到）
3. 權限設為 **編輯者**
4. 點擊 **傳送**

---

## 步驟 5：設定 Streamlit Secrets

### 本地開發

在專案根目錄建立 `.streamlit/secrets.toml` 檔案：

```toml
# Google Sheet 試算表 ID
[spreadsheet]
id = "你的試算表ID"

# Google Cloud 服務帳戶憑證
[gcp_service_account]
type = "service_account"
project_id = "你的專案ID"
private_key_id = "金鑰ID"
private_key = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
client_email = "服務帳戶email@專案ID.iam.gserviceaccount.com"
client_id = "用戶端ID"
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "https://www.googleapis.com/robot/v1/metadata/x509/..."
```

> **注意**：直接從下載的 JSON 金鑰檔複製內容，但要轉換成 TOML 格式。

### Streamlit Cloud 部署

1. 前往 [Streamlit Cloud](https://share.streamlit.io/)
2. 選擇您的應用程式
3. 點擊 **Settings** → **Secrets**
4. 貼上上述 secrets.toml 的內容
5. 點擊 **Save**

---

## 步驟 6：部署應用程式

### 方法 A：Streamlit Cloud（推薦）

1. 將程式碼推送到 GitHub
2. 在 Streamlit Cloud 連結 GitHub repo
3. 設定 Secrets（如步驟 5）
4. 點擊 Deploy

### 方法 B：本地執行

```bash
# 安裝套件
pip install -r requirements.txt

# 執行
streamlit run app.py
```

---

## 📊 資料表結構

系統會自動建立以下工作表：

### 1. 病人資料
| 欄位 | 說明 |
|------|------|
| 病人ID | 病歷號碼（主鍵）|
| 姓名 | 病人姓名 |
| 性別 | 男/女 |
| 年齡 | 數字 |
| 生日 | YYYY-MM-DD |
| 手機號碼 | 聯絡電話 |
| 手術日期 | YYYY-MM-DD |
| 手術類型 | 手術名稱 |
| 癌症分期 | IA/IB/IIA... |
| 密碼雜湊 | SHA-256 雜湊 |
| 註冊時間 | 時間戳記 |
| 最後登入 | 時間戳記 |
| 狀態 | active/inactive |

### 2. 症狀回報
| 欄位 | 說明 |
|------|------|
| 回報ID | 唯一識別碼 |
| 病人ID | 關聯病人 |
| 回報日期 | YYYY-MM-DD |
| 回報時間 | HH:MM:SS |
| 回報方式 | ai_chat/questionnaire |
| 疼痛分數 | 0-10 |
| 疲勞分數 | 0-10 |
| ... | 其他症狀 |

### 3. 對話記錄
| 欄位 | 說明 |
|------|------|
| 訊息ID | 唯一識別碼 |
| 會話ID | 會話識別碼 |
| 病人ID | 關聯病人 |
| 角色 | patient/ai_assistant |
| 內容 | 訊息文字 |
| 訊息來源 | 來源分類 |

### 4. 成就記錄
| 欄位 | 說明 |
|------|------|
| 記錄ID | 唯一識別碼 |
| 病人ID | 關聯病人 |
| 成就ID | 成就類型 |
| 成就名稱 | 顯示名稱 |
| 解鎖日期 | YYYY-MM-DD |
| 獲得積分 | 數字 |

---

## 🔒 安全注意事項

1. **永遠不要**將 `secrets.toml` 或金鑰 JSON 檔提交到 Git
2. 將以下加入 `.gitignore`：
   ```
   .streamlit/secrets.toml
   *-key.json
   ```
3. 服務帳戶只需要最小權限（Sheets 編輯權限）
4. 定期輪替金鑰

---

## ❓ 常見問題

### Q: 無法連接 Google Sheet？
- 確認服務帳戶已被加入試算表的共用名單
- 確認 Sheets API 和 Drive API 都已啟用
- 檢查 secrets.toml 格式是否正確

### Q: 註冊時顯示「此病歷號已註冊」？
- 病歷號必須唯一
- 可以在 Google Sheet 中直接刪除該筆資料重試

### Q: 部署到 Streamlit Cloud 後無法使用？
- 確認已在 Streamlit Cloud 的 Secrets 中正確設定
- 檢查 private_key 中的換行符號是否正確（應為 \n）

---

## 📞 技術支援

如有問題，請聯繫：
- 三軍總醫院數位醫療中心
- Email: digital.medicine@tsgh.ndmctsgh.edu.tw
