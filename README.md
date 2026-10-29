# PDF 壓縮小工具（iPhone／iPad 捷徑版）

流程：iPhone／iPad 分享選單 → 捷徑 → 你的壓縮 API（Ghostscript）→ 壓縮後的 PDF 回到手機。

## 一、部署 API（只要做一次）

檔案：`app.py`、`requirements.txt`、`Dockerfile`

### 方式 A：Render（最簡單）
1. 把這三個檔案放進 GitHub 的一個新 repo。
2. Render → New → Web Service → 選該 repo，Runtime 選 **Docker**。
3. Environment 加一個變數：`API_TOKEN` = 自己想的一串長密碼（例如 20 字以上亂碼）。
4. 部署完成後會得到網址，例如 `https://pdf-compress-xxxx.onrender.com`。
5. 瀏覽器開網址，看到 `PDF compressor is running` 就成功。

> 免費方案閒置後會休眠，第一次呼叫要等約 30～60 秒喚醒。

### 方式 B：自己的電腦（用 Docker）
```
docker build -t pdf-compress .
docker run -p 8000:8000 -e API_TOKEN=你的密碼 pdf-compress
```
外出時需搭配 Tailscale 等工具才能從手機連回家。

## 二、iPhone／iPad 捷徑設定

打開「捷徑」App → 右上角 ＋ → 名稱取「壓縮 PDF」。

1. 點右下角 ⓘ（詳細資料）→ 開啟「**在分享工作表中顯示**」，接受類型只留「**PDF**」。
2. 加入動作「**取得 URL 內容**」，設定：
   - URL：`https://你的網址/compress?level=ebook`
   - 方法：**POST**
   - 標頭：新增 `Authorization` = `Bearer 你的API_TOKEN`
   - 要求內文：**檔案**，檔案選「**捷徑輸入**」
3. 加入動作「**儲存檔案**」（關閉「詢問儲存位置」，選一個資料夾），或加「**分享**」直接傳出去。
4. 完成。之後在「檔案」App 或任何 App 對 PDF 按分享 → 壓縮 PDF 即可。

iPad 會透過 iCloud 自動同步，同一個 Apple ID 就有；分享選單與主畫面圖示在 iPad 上各自確認一次。

## 壓縮等級（改 URL 的 level）
| level | 效果 |
|---|---|
| `screen` | 最小檔案，畫質較低（約 72 dpi） |
| `ebook` | 建議，畫質與大小平衡（約 150 dpi） |
| `printer` | 畫質較高，壓縮率較低 |

壓縮後若比原檔還大，API 會直接回傳原檔。

## 注意
- PDF 會經過你部署的伺服器，不要把 `API_TOKEN` 外流，也別壓縮高度機密的文件。
- 上限預設 100 MB，可用環境變數 `MAX_MB` 調整。
