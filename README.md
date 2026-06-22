# 菜月昴 AI VTuber（qwen3-486）

**一台 8GB 顯卡的筆電，一個開源 4B 小模型，163 筆自製對話——做出會用繁中男聲說話、表情隨情緒變化的本地 AI VTuber。**

從資料設計、QLoRA 微調、GGUF 量化、Ollama 部署，到 Live2D 表情與語音串接，全程離線、零雲端費用。

![Python](https://img.shields.io/badge/Python-3.12-3776AB)
![Qwen3](https://img.shields.io/badge/Qwen3--4B--Instruct-base%20model-615CED)
![Unsloth](https://img.shields.io/badge/Unsloth-QLoRA-00B4D8)
![GGUF](https://img.shields.io/badge/GGUF-Q4__K__M%202.33GB-FF6B35)
![Ollama](https://img.shields.io/badge/Ollama-local%20serving-000000)
![RTX 4060](https://img.shields.io/badge/RTX%204060%20Laptop-8GB%20VRAM-76B900)

> 開發於 2026 年 5–6 月　·　個人學習用的非官方二創實驗

---

## 成果

| 項目 | 結果 |
|:--|:--|
| 基底模型 | Qwen3-4B-Instruct-2507（4-bit 載入） |
| 微調 | Unsloth + QLoRA，LoRA r=8 / alpha=16，2 epoch ≈ 38 step |
| 訓練資料 | 163 筆自製繁中角色對話（146 train / 17 eval），附 emotion 標籤 |
| 量化成品 | GGUF **Q4_K_M，2.33 GB** |
| 部署 | Ollama 本地服務 `qwen3-486`，OpenAI 相容 API |
| 互動 | 文字／語音輸入 → 繁中男聲 TTS → Live2D 表情同步切換 |
| 硬體 | RTX 4060 Laptop（8GB VRAM）單機完成訓練與推論 |
| 雲端費用 | **0 元** |

### 實測對話

模型輸出會自帶 `[emotion]` 標籤，這個標籤同時驅動語音與 Live2D 表情：

| 使用者 | qwen3-486 |
|:--|:--|
| 我剛剛升職了，超開心！ | `[joy]` 升職？！原來是這種事啊，太棒了吧！ |
| 我今天又遲到被罵了，真不爽！ | `[smirk]` 原來是個被罵了的人啊……真不巧，這種事我也遇過好多次喔！ |
| 我家的貓今天離家出走了… | `[surprise]` 喔喔！貓也離家出走？！這可太不對勁了！ |

三句的表情（joy / smirk / surprise）在瀏覽器端皆實際觸發，語音同步唸出。

---

## 系統架構

```
  使用者（文字 / 麥克風）
          │
          ▼
  ┌───────────────────────────────────────────┐
  │  Open LLM VTuber（瀏覽器前端 + Python 後端） │
  │                                           │
  │   ASR ──► LLM ──► emotion 標籤解析          │
  │            │            │                 │
  │            │            ├──► TTS 繁中男聲   │
  │            │            └──► Live2D 表情    │
  └────────────┼──────────────────────────────┘
               │ OpenAI 相容 API（localhost）
               ▼
      ┌──────────────────────┐
      │ Ollama · qwen3-486   │
      │ GGUF Q4_K_M 2.33GB   │
      └──────────────────────┘
               ▲
               │  ⑤ 合併 → f16 → 量化
      ┌────────┴─────────┐
      │ QLoRA adapter    │ ◄── ④ Unsloth 微調
      └──────────────────┘
               ▲
      ┌────────┴─────────┐
      │ 163 筆繁中對話     │ ◄── ② 自製資料集 + emotion 標註
      └──────────────────┘
```

完整八步：**規劃 → 資料 → 環境 → 訓練 → 合併／量化 → Ollama 部署 → VTuber 串接 → 驗收**

---

## 關鍵設計決策

### 選 4B 而不是 7B／8B

VTuber 的體驗瓶頸是**互動延遲**，不是知識廣度。4B 模型量化後 2.33 GB，在 8GB VRAM 上還留得下 KV cache 與其他程序的空間，能即時回應；7B 以上就得在延遲與顯存之間妥協。

### 微調只教語氣，不灌知識

163 筆資料的定位是**風格微調**而非知識注入。灌世界觀知識需要的資料量遠不止於此，硬塞只會過擬合，也踩版權紅線。因此分層處理：

| 層 | 負責 |
|:--|:--|
| QLoRA 微調 | 語氣節奏、句長、情緒表達習慣、`[emotion]` 標籤的輸出慣性 |
| System prompt | 人格規則、語言限定（繁中）、安全邊界、輸出格式 |

### 用一個 emotion 標籤同時驅動兩種模態

模型在回覆開頭輸出 `[joy]`、`[surprise]` 這類標籤，前端解析後**同時**餵給 TTS 與 Live2D。不需要為表情另外跑一個情緒分類模型，語言模型本身就是情緒來源——這也是為什麼資料集在標註階段就把 emotion 寫進去。

### 訓練腳本以 TDD 方式重寫

ML 腳本常見的問題是「跑一次三小時才發現參數名錯了」。這裡把 chat template 標記與 SFTConfig 欄位拆成可測單元、配 pytest 先驗證，再用 `--smoke`（單 step）煙霧測試，最後才跑完整訓練。

實際救場：`trl` 0.19.1 把參數改成 `processing_class`，測試在訓練開始前就抓到。

### 環境先過閘門再開工

`verify_env.py` 一鍵檢查 GPU、torch+CUDA、Unsloth 是否就緒，紅燈就別往下走。這在踩到「CUDA 13.2 沒有 bitsandbytes 預編譯 binary」時直接省下大量除錯時間——退回 cu128 wheel 後綠燈，才進訓練。

---

## 踩過的雷

真實紀錄，完整版見 [`REPORT.md`](REPORT.md) §11：

| 現象 | 真因 | 解法 |
|:--|:--|:--|
| VTuber 完全無聲 | 缺 ffmpeg，pydub 無法把 mp3 轉 wav | `winget install Gyan.FFmpeg` |
| 合併 LoRA 時 OOM | 以 16-bit 載入基底模型撐爆 8GB | 改 4-bit 載入再合併 |
| Windows 主控台崩潰 | cp950 編碼遇到 Unsloth 的 emoji | 腳本強制 UTF-8 stdout |
| API 回傳中文亂碼 | PowerShell `Invoke-RestMethod` 把 UTF-8 當 latin1 解 | 改用 Python urllib 驗證 |
| Live2D 模型載不進來 | chitose 是 Cubism 2.x，前端僅支援 3–5 | 改用 mao_pro |
| 角色突然說簡體 | 預設 persona 覆寫了 SYSTEM prompt | 改 `conf.yaml` persona 並明確禁簡體 |

---

## 目前限制

- **資料量小且情緒分布偏態**（fear 偏多）。角色語氣已經成立，但情緒覆蓋不均，需要擴充與再平衡。
- **TTS 依賴線上服務**：edge-tts 需要網路，聲線是通用繁中男聲，不是為角色客製的。整條管線只有這一環不是離線的。
- **avatar 非原訂角色**：原本要用的 chitose 因 Cubism 版本不相容，暫以 mao_pro 代替。
- **長時間體驗未驗收**：LLM／Live2D／TTS／ASR 四項功能驗收已通過，長時間連續對話的穩定性尚未測試。

---

## 延伸：同一批資料，再用 No-Code 跑一次

微調完成後，我用 **Unsloth Studio**（官方推出的本地網頁 UI）拿同一張顯卡、同一個基底模型、同一批資料，重跑了一次 QLoRA，把兩條路線的差異完整記錄下來。

| | Code（本 repo 根目錄） | No-Code（[`studio/`](studio/)） |
|:--|:--|:--|
| 交付物 | 4 支腳本 + 環境驗證閘門 | 一個 `docker compose up` |
| 首次跑通 | 數天（含環境踩坑） | 約 1 小時 |
| 坑的型態 | Python / CUDA 環境 | Docker 埠與掛載 |
| 換來的 | 完整重現性、可自動化、可客製 | 即時儀表板、內建 Compare、一鍵匯出 GGUF |

結論不是「哪個比較強」——兩邊底層是同一個 Unsloth 引擎，同參數下訓出來的模型理論上一致——而是**控制權與上手成本怎麼取捨**：探索與快速迭代用 Studio，需要重現性、批次實驗、自訂訓練邏輯就回到腳本。

報告裡另外記錄了一個與介面無關、兩條路都會遇到的問題：**v2 資料集引發的重複退化**（模型無限吐同一個字直到截斷），以及往下挖到資料、推論、訓練三層的診斷過程與取捨。

▸ [**完整對比報告**](studio/README.md)

---

## 文件

這個 repo 的文件不是事後補的，是隨開發推進寫的：

| 文件 | 內容 |
|:--|:--|
| [`REPORT.md`](REPORT.md) | **完整成果報告**（630 行）：動機、架構、資料、訓練、量化、串接、驗收、踩雷、限制 |
| [`PROJECT_ARCHITECTURE.md`](PROJECT_ARCHITECTURE.md) | 系統架構與設計決策、驗收標準定義 |
| [`FINETUNING_DETAIL_REPORT.md`](FINETUNING_DETAIL_REPORT.md) | 微調的參數選擇與細節 |
| [`EXECUTION_RUNBOOK.md`](EXECUTION_RUNBOOK.md) | 可逐步照做的執行手冊，從環境建置到驗收 |
| [`WORKLOG.md`](WORKLOG.md) | 開發過程的工作日誌 |
| [`docs/dataset-emotion-tags.md`](docs/dataset-emotion-tags.md) | emotion 標籤的設計與標註規則 |
| [`studio/README.md`](studio/README.md) | **Code vs No-Code 微調兩條路線實測對比**（含 33 張 Studio 操作截圖） |
| [`studio/docs/PIPELINE.md`](studio/docs/PIPELINE.md) | v2 資料集的萃取流水線設計 |

---

## 專案結構

```
486Dataset.jsonL              原始自製對話資料（163 筆）
prep_training_data.py         轉換為 ShareGPT／messages 格式、標註 emotion、切分訓練/驗證
converted_dataset/            各格式的轉換產物與轉換報告
data/                         train.jsonl · eval.jsonl（146 / 17）

verify_env.py                 環境閘門：GPU · torch+CUDA · Unsloth
train_qwen3_486.py            QLoRA 微調（支援 --smoke 單步煙霧測試）
tests/                        訓練腳本的單元測試
merge_lora.py                 LoRA 合併回基底模型

deploy/Modelfile              Ollama 模型定義（chat template · 取樣參數 · 角色 system prompt）
```

> 不進版控：`app/`（Open LLM VTuber，獨立 repo 就地 clone）、`tools/`（llama.cpp）、`gguf/`、`train_outputs/`、`hf_cache/`、Live2D 素材——皆為大型檔案或授權受限的外部資產。

---

## 快速開始

需要 NVIDIA GPU（8GB VRAM 以上）、Python 3.12、[uv](https://docs.astral.sh/uv/)、[Ollama](https://ollama.com)。

```bash
# 0. 環境閘門：紅燈就先別往下
uv run verify_env.py

# 1. 資料轉換與切分
uv run prep_training_data.py

# 2. 煙霧測試（1 step，確認流程可跑）
uv run train_qwen3_486.py --smoke

# 3. 正式微調
uv run train_qwen3_486.py

# 4. 合併 LoRA → 轉 GGUF → 量化 Q4_K_M（llama.cpp）
uv run merge_lora.py

# 5. 部署到 Ollama
ollama create qwen3-486 -f deploy/Modelfile
```

VTuber 前端串接（Open LLM VTuber 的安裝、`conf.yaml` persona 與 TTS 設定、Live2D 模型掛載）詳見 [`EXECUTION_RUNBOOK.md`](EXECUTION_RUNBOOK.md)。

---

## 聲明

個人學習用的**非官方二創**實驗，與《Re:從零開始的異世界生活》的原作者及版權方無任何關係，不宣稱任何授權，亦未經原作審訂。

本 repo 含兩份性質不同的資料集，請分別看待：

| 資料集 | 來源與性質 |
|:--|:--|
| [`486Dataset.jsonL`](486Dataset.jsonL)（163 筆） | **自行撰寫**的風格模仿對話，不複製原作長篇台詞 |
| [`studio/dataset/subaru_all.jsonl`](studio/dataset/subaru_all.jsonl)（189 筆） | v2 版，對話內容**萃取自原作小說**，僅供微調技術研究與本 repo 實驗的重現參考，**不作任何商業用途** |

原作著作權歸屬原權利人所有。TTS 使用通用繁中男聲，**不做未授權的聲線克隆**；Live2D 素材依其各自授權使用，不隨本 repo 散布。

基底模型 Qwen3-4B-Instruct-2507 依其原始授權條款使用。
