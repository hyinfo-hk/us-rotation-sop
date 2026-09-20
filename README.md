# 美股資金輪動 SOP（免費自動更新）

靜態網站 + GitHub Actions 每日拉 Yahoo Finance，覆蓋 `data/latest.json`。  
月費 $0。唔使 Gmail、唔使 N8N、唔使 Gist。

## 5 步上線

1. 去 [github.com/new](https://github.com/new) 開一個 **Public** repo，例如 `us-rotation-sop`
2. 把呢個資料夾全部檔案 Upload / push 上去（要包括隱藏資料夾 `.github`）
3. 打開 **Settings → Pages**
   - Source: **Deploy from a branch**
   - Branch: `main` / `/ (root)`
4. 打開 **Actions** → **Refresh SOP market data** → **Run workflow**（第一次手動跑）
5. 幾分鐘後打開  
   `https://你的帳號.github.io/us-rotation-sop/`

之後每個交易日港時約 20:20 同美股收市後會自動更新。

## 檔案

| 檔 | 用途 |
|---|---|
| `index.html` | SOP 網站 |
| `data/latest.json` | 每日報價（Actions 覆蓋） |
| `scripts/fetch_data.py` | 拉指數 + 11 板塊 |
| `.github/workflows/refresh.yml` | 定時任務 |

## 同 Grok 20:20 報告點分工

- 呢個網站：表格、評分、日曆、自動價
- Grok Automation：文字結論、風險開關（你已開咗每日 20:20）

價格區間係分析框架，不是買賣建議。
