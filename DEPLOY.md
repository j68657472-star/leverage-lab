# 部署上線指南（給完全新手）

這份指南帶你把 app 從「只在程式碼裡」變成「網路上有網址、任何人都能用」。
全程**在瀏覽器操作，不用在自己電腦裝任何東西**。預計 20–30 分鐘。

---

## 先理解兩個名詞（30 秒）

- **GitHub**：放程式碼的「雲端硬碟」。部署平台會從這裡讀你的程式。
  （就像 Google Drive，但專門放程式碼。）
- **Render**：幫你把程式「跑起來」並給你網址的雲端平台。
  它會去 GitHub 抓你的程式，自動架好前端、後端、資料庫。

流程：**你的程式 → 上傳到 GitHub → Render 讀取 → 變成網站**

---

## 步驟 1：註冊 GitHub 帳號（5 分鐘）

1. 開啟 https://github.com/signup
2. 輸入 email、設定密碼、取一個使用者名稱
3. 收信驗證即可

---

## 步驟 2：把程式放上 GitHub（10 分鐘）

你不用學指令，用 GitHub 網頁就能上傳。

1. 登入 GitHub 後，右上角點 **「+」→ New repository**
2. Repository name 填：`leverage-lab`（隨意）
3. 選 **Private**（私人，只有你看得到）或 Public 都可以
4. 先**不要**勾任何 README/gitignore 選項，直接按 **Create repository**
5. 在新頁面找到 **「uploading an existing file」** 連結並點它
6. 把 `leveraged-etf-lab` 資料夾裡的**所有檔案**拖進去上傳
   - 💡 注意：要上傳「資料夾內的內容」，讓 `backend/`、`frontend/`、
     `render.yaml` 都在 repo 的最上層
   - 不用上傳 `node_modules`、`.next`、`previews`、`.price_cache`
     這些資料夾（`.gitignore` 已經幫你排除大部分）
7. 最下方按 **Commit changes**

> 上傳後，你的 repo 最上層應該要看得到 `render.yaml` 這個檔案——這是關鍵。

---

## 步驟 3：在 Render 一鍵部署（10 分鐘）

1. 開啟 https://render.com → 點 **Get Started**
2. 選 **「Sign in with GitHub」**（用剛剛的 GitHub 帳號登入，最省事）
3. 授權 Render 讀取你的 GitHub
4. 進到後台後，點右上角 **「New +」→ 「Blueprint」**
5. 選你剛上傳的 `leverage-lab` repo
6. Render 會自動偵測到 `render.yaml`，列出 3 個服務：
   - `etf-lab-db`（資料庫）
   - `etf-lab-backend`（後端）
   - `etf-lab-frontend`（前端）
7. 按 **Apply**（或 Create Services）
8. 等它建置（第一次約 5–10 分鐘，會看到 build log 在跑）

完成後，點 **etf-lab-frontend** 服務，最上面就會有一個網址，像：
```
https://etf-lab-frontend.onrender.com
```
**這就是你的網站！** 打開就能跑回測了。

---

## 免費方案要注意的事

| 限制 | 說明 | 怎麼解決 |
|------|------|---------|
| 閒置會休眠 | 15 分鐘沒人用會睡著，下次打開要等 30–60 秒喚醒 | 升級該服務到付費（約 $7/月）即可不休眠 |
| 免費資料庫 90 天 | 免費 Postgres 90 天後會被回收 | 之後升級資料庫方案 |
| 首次較慢 | 喚醒 + 第一次抓股價會慢一點 | 屬正常，第二次就快了 |

> 這些限制對「自己用、給朋友試」完全夠用。等你想正式營運再升級。

---

## 之後要改東西怎麼辦？

1. 在 GitHub 網頁直接編輯檔案（或重新上傳）
2. Render 偵測到變更會**自動重新部署**
3. 等幾分鐘，網站就更新了

---

## 遇到問題？

- **build 失敗**：點該服務的 **Logs** 看紅字錯誤，通常是某個檔案沒上傳到。
- **前端打不開後端**：確認 `render.yaml` 有上傳、且 3 個服務都建立成功。
- **資料庫連不上**：Render 的 Blueprint 會自動接好，通常不用手動設定。

把錯誤訊息貼給我，我可以幫你看。
