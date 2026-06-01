# 菜月昴 AI VTuber — 專案成果報告

> 本機可運行的繁體中文 AI VTuber：以小型語言模型 QLoRA 微調出「菜月昴風格」語氣，量化部署於消費級 8GB 筆電 GPU，並透過 Open LLM VTuber 串接 Live2D 表情與語音輸出。
>
> 性質：個人學習用、非官方二創實驗。不宣稱官方授權，不複製原作長篇台詞，不做未授權聲線克隆。

---

## 目錄

1. [專案摘要](#1-專案摘要)
2. [問題與動機](#2-問題與動機)
3. [價值與應用場景](#3-價值與應用場景)
4. [系統架構](#4-系統架構)
5. [資料集設計](#5-資料集設計)
6. [模型訓練](#6-模型訓練)
7. [合併、量化與部署](#7-合併量化與部署)
8. [VTuber 串接](#8-vtuber-串接)
9. [成果與驗收](#9-成果與驗收)
10. [工作日誌（里程碑式）](#10-工作日誌里程碑式)
11. [踩雷與解法](#11-踩雷與解法)
12. [限制與未來工作](#12-限制與未來工作)
13. [附錄](#13-附錄)

---

## 1. 專案摘要

本專案在一台 **NVIDIA RTX 4060 Laptop GPU（8GB VRAM）** 的 Windows 11 筆電上，從零打造一個可離線運行的 **AI VTuber**：一個以《Re:從零開始的異世界生活》主角「菜月昴」為風格的繁體中文虛擬角色，能用文字或語音對話、用繁中男聲開口說話，並讓 Live2D avatar 的表情隨對話情緒切換。

完成的完整管線（8 步）：

```
① 規劃 → ② 資料 → ③ 環境 → ④ 訓練 → ⑤ 合併/量化 → ⑥ Ollama 部署 → ⑦ VTuber 串接 → ⑧ 驗收
```

**核心成果**

| 項目 | 成果 |
| --- | --- |
| 基底模型 | Qwen3-4B-Instruct-2507（4-bit） |
| 微調方法 | Unsloth + QLoRA（LoRA r=8 / alpha=16） |
| 訓練資料 | 163 筆繁中角色對話（146 train / 17 eval），帶 emotion 標籤 |
| 量化成品 | GGUF **Q4_K_M，2.33 GB**，8GB GPU 可即時推論 |
| 部署 | Ollama 本地服務 `qwen3-486`，OpenAI 相容 API |
| 互動 | 文字/語音對話、**繁中男聲 TTS**、Live2D 表情隨語音切換 |
| 全程成本 | 0 元雲端費用，全本地、消費級硬體 |

一句話：**用消費級筆電，把一個開源小模型微調＋量化成有角色感的繁中 VTuber，並完整串起「語言模型 → 表情 → 語音」的互動迴圈。**

---

## 2. 問題與動機

### 2.1 想解決的問題

市面上的 AI 角色／VTuber 服務多半有三個痛點：

1. **依賴雲端、要付費、資料外流** —— 對話內容送到第三方伺服器，長期使用有成本與隱私疑慮。
2. **角色感薄弱** —— 通用聊天模型講話像客服，沒有穩定的人格語氣與情緒節奏。
3. **繁體中文與在地語感不足** —— 多數模型偏簡體或英文，台灣用語、繁中口吻常需額外調教。

### 2.2 本專案的切入點

> **在消費級硬體（8GB GPU）上，用小模型 + 小資料微調，做出一個「能本地離線跑、有穩定角色語氣、講道地繁中」的 AI VTuber。**

關鍵設計取捨：

- **小模型優先**：選 4B 而非 7B/8B —— VTuber 重「即時互動延遲」，小模型在 8GB 上才跑得順。
- **微調只學語氣、不灌知識**：資料量小（163 筆），定位為「風格微調」，避免過擬合與版權風險；世界觀知識交給 prompt。
- **分層職責**：微調負責語氣節奏與 emotion 標籤習慣；system prompt 負責人格規則、語言、安全邊界。
- **全本地、零雲端**：訓練、量化、推論、語音、表情全部跑在本機。

---

## 3. 價值與應用場景

### 3.1 技術價值

- **可重現的低成本微調範本**：完整示範「開源模型 → QLoRA 微調 → GGUF 量化 → 本地部署 → 多模態串接」的全流程，每一步都有腳本與文件。適合作為個人／教學用的 LLM 落地參考。
- **消費級硬體可行性驗證**：證明 8GB 筆電 GPU 足以完成 4B 模型的 QLoRA 微調與即時推論，降低入門門檻。
- **多模態整合**：把語言模型的文字輸出，透過 emotion 標籤管線同時驅動「語音」與「Live2D 表情」，形成完整的角色互動迴圈。

### 3.2 應用場景

| 場景 | 說明 |
| --- | --- |
| 個人陪伴型 VTuber | 桌面虛擬角色，繁中語音陪聊、吐槽、打氣 |
| 直播虛擬主播（雛形） | 可接 OBS／聊天室，作為直播互動角色的技術底座 |
| LLM 教學 / 作品集 | 完整的「微調到部署」教材，含踩雷紀錄 |
| 在地化對話模型實驗 | 繁中語氣微調、emotion 標籤驅動表情的可複用模式 |

### 3.3 邊界與責任

本專案明確定位為**非官方二創、私人學習用途**：不宣稱官方授權、不逐字複製原作長台詞、不使用未授權聲優音源做聲線克隆。Live2D 與資料素材的授權於正式使用前需再確認。

---

## 4. 系統架構

### 4.1 五層架構

```
┌─────────────────────────────────────────────────────────┐
│ 互動層    文字 / 語音輸入  →  回覆文字 + 語音 + 表情       │
├─────────────────────────────────────────────────────────┤
│ VTuber 中介層   Open LLM VTuber（FastAPI + WebSocket）     │
│                整合 LLM / ASR / TTS / Live2D              │
├─────────────────────────────────────────────────────────┤
│ 角色層    system prompt（人格/語言/安全）+ 微調（語氣）    │
├─────────────────────────────────────────────────────────┤
│ 模型層    Qwen3-4B QLoRA 微調 → GGUF Q4_K_M → Ollama API  │
├─────────────────────────────────────────────────────────┤
│ 資料層    163 筆繁中角色對話（帶 emotion 標籤）           │
└─────────────────────────────────────────────────────────┘
```

### 4.2 執行期資料流

```
使用者打字／說話
   │（語音時先經 ASR：sherpa-onnx → 文字）
   ▼
Open LLM VTuber server ──OpenAI 相容 API──► Ollama (qwen3-486)
   │                                            │
   │  ◄────── 回覆：「[emotion] 繁中短句」 ──────┘
   ▼
extract_emotion 解析 [emotion] → Live2D 表情 index
   │
   ├──► edge-tts 合成繁中男聲 mp3 ──(ffmpeg→wav)──► 瀏覽器播放
   │                                                   │
   └──► 表情指令綁定音頻播放 ──────────────────────────┘
                                                       ▼
                                  Live2D（mao_pro）嘴型開合 + 表情切換
```

**關鍵設計**：LLM 回覆開頭帶 `[emotion]` 標籤 → server 解析成表情索引 → 表情指令**綁定在音頻播放事件上**，因此「語音」與「表情」是同步觸發的（這也是後述 TTS 必須先就緒、表情才會動的原因）。

---

## 5. 資料集設計

### 5.1 資料概況

| 項目 | 內容 |
| --- | --- |
| 總量 | 約 163 筆（~155 KB），定位為「語氣微調」而非知識灌輸 |
| 格式 | ShareGPT / chat `messages`（system / user / assistant） |
| 切分 | train **146** 筆 / eval **17** 筆（約 90 / 10） |
| 編碼 | UTF-8（strict mode 驗證可解碼） |
| 標籤 | assistant 回覆開頭帶 `[emotion]`，如 `[joy]`、`[sadness]` |

單筆範例：

```json
{"messages": [
  {"role": "system", "content": "你是繁體中文 AI VTuber，回應簡短自然，必要時於開頭使用 [emotion] 標籤。"},
  {"role": "user", "content": "今天好累。"},
  {"role": "assistant", "content": "[sadness] 喂喂，這也太硬撐了吧。先喘口氣啦，我陪你。"}
]}
```

### 5.2 內容比例設計（目標）

| 資料類型 | 目標比例 | 目的 |
| --- | ---: | --- |
| 一般聊天 | 35% | 保持自然對話能力 |
| 情緒陪伴 | 20% | 安慰與陪伴 |
| 吐槽／搞笑 | 15% | 菜月昴式反應節奏 |
| 熱血鼓勵 | 15% | 不服輸與鼓舞感 |
| RE:0 角色背景 | 10% | 保留角色感 |
| 拒絕／安全邊界 | 5% | 避免越界與版權風險 |

### 5.3 Emotion 標籤系統

採用 8 種標準標籤，與 Live2D 表情一一對應：

```
neutral / joy / sadness / anger / surprise / smirk / fear / disgust
```

由微調學習「在開頭輸出合理 emotion 標籤」的習慣，推論時由 VTuber 端 `extract_emotion` 解析、映射到 avatar 表情索引。

> **已知資料偏態**：資料中 `fear` 偏多（與原作「死亡回歸」苦痛橋段相關），第二版需平衡情緒分布，避免模型過度輸出恐懼語氣。

### 5.4 System Prompt 與微調的職責分工

| 由 **System Prompt** 負責 | 由 **微調** 負責 |
| --- | --- |
| 主要語言＝繁中、禁簡體 | 語氣、節奏、反應方式 |
| 角色定位（非官方本人） | 情緒表達、emotion 標籤習慣 |
| 短句、適合語音、不用 markdown | 簡短自然的角色化回覆 |
| 安全邊界與拒絕規則 | —— |

---

## 6. 模型訓練

### 6.1 模型選型

| 模型 | 角色 | 理由 |
| --- | --- | --- |
| **Qwen3-4B-Instruct-2507** | 主模型 | 4B 適合 8GB GPU 保守 QLoRA；繁中／中日語境佳；Instruct 適合對話；延遲低於 7B/8B |
| Qwen3-1.7B | 備用 | 4B OOM 或延遲過高時的退路 |
| 7B/8B | 不採用 | 8GB 上微調與推論皆吃緊，傷害 VTuber 即時性 |

實際載入：`unsloth/Qwen3-4B-Instruct-2507-bnb-4bit`（4-bit 量化權重）。

### 6.2 訓練方法：Unsloth + QLoRA

選 **Unsloth** 而非 LLaMA-Factory：對單卡、低 VRAM、Windows 環境最友善，記憶體優化與啟動速度好。QLoRA = 4-bit 量化基底 + LoRA 低秩adapter，讓 4B 模型能在 8GB 上微調。

**實際超參數**（見 [`train_qwen3_486.py`](train_qwen3_486.py)）：

| 參數 | 值 |
| --- | --- |
| max_seq_length | 1024 |
| LoRA rank (r) | 8 |
| LoRA alpha | 16 |
| LoRA dropout | 0.05 |
| target modules | q/k/v/o + gate/up/down proj（全注意力＋MLP） |
| per_device_batch_size | 1 |
| gradient_accumulation_steps | 8（有效 batch ≈ 8） |
| learning_rate | 1e-4，cosine scheduler，warmup 0.03 |
| epochs | 2 |
| optimizer | adamw_8bit |
| 精度 | bf16 |
| seed | 42 |
| gradient checkpointing | unsloth（省 VRAM） |

2 epoch × 146 筆 ÷ 有效 batch 8 ≈ **38 個 optimizer step**。

### 6.3 工程品質（TDD）

訓練腳本不是一次寫成，而是以 **TDD + 單元拆解**逐步對齊實際安裝的套件 API：

- 把流程拆成 `build_datasets()` / `make_sft_config()` / `load_model_and_tokenizer()` / `main()` 可測單元。
- 用 pytest 驗證 chat template 套用後含正確標記、SFTConfig 欄位對齊 trl 0.19.1。
- 加 `--smoke` 旗標（`max_steps=1`）先做最小煙霧測試確認管線通，再跑完整訓練。

### 6.4 避免過擬合

資料量小，因此：epoch 控制在 2、以 eval loss + **人工角色語氣測試**共同判斷（不只看 loss）、保留 base model 的基本對話能力。最終 adapter 在人工測試中能穩定輸出菜月昴風繁中短句，且未退化成複讀資料集。

---

## 7. 合併、量化與部署

訓練只產出 LoRA adapter，要讓它能被 Ollama 高效本地推論，需經「合併 → 轉檔 → 量化 → 部署」：

### 7.1 合併 LoRA（[`merge_lora.py`](merge_lora.py)）

把 LoRA adapter 合回基底權重，輸出 16-bit 完整模型（`train_outputs/merged/`）。

> **踩雷**：合併時若以 fp16 載入基底（~9GB）會超出 8GB GPU。解法：**以 4-bit 載入基底**，由 Unsloth 在合併時 dequantize，才塞得進 8GB。

### 7.2 轉 GGUF + 量化

- `convert_hf_to_gguf.py` 把 16-bit 模型轉成 GGUF f16。
- `llama-quantize` 量化為 **Q4_K_M**。
- 工具：llama.cpp **b9442**（Windows 預編譯 cuda-13.3）。

**成品：`gguf/qwen3-486-q4km.gguf`，2.33 GB**。`llama-cli` 實測輸出正常繁中。

### 7.3 部署到 Ollama

以 [`deploy/Modelfile`](deploy/Modelfile)（`FROM` GGUF + 菜月昴 SYSTEM + emotion 標籤指示）建立模型：

```bash
ollama create qwen3-486 -f deploy/Modelfile
```

API（`/v1/chat/completions`）實測：回繁中、2–4 句、帶合理 `[emotion]`、有角色感。

> **為什麼訓練完還要這幾步？** 訓練產出的是 adapter，不能直接給 Ollama 用；量化把 2.33GB 模型壓到能在 8GB 上即時跑；Ollama 提供 OpenAI 相容 API 讓 VTuber 框架能直接呼叫。

---

## 8. VTuber 串接

採 **Open LLM VTuber**（FastAPI + WebSocket server + React 前端，內建 Web UI 於 `localhost:12393`），分階段串接：

| 階段 | 內容 | 狀態 |
| --- | --- | --- |
| 一 | LLM 文字對話（繁中、菜月昴） | ✅ 完成 |
| 二 | Live2D 表情（emotion 管線） | ✅ 完成（mao_pro） |
| TTS | 繁中男聲語音輸出（edge-tts） | ✅ 完成 |
| 三 | ASR 語音輸入（sherpa-onnx） | ⬜ 待做 |
| 驗收 | 五階段體驗驗收 | ⬜ 待做 |

### 8.1 LLM 串接

conf.yaml 指向本地 Ollama：`llm_provider: ollama_llm`、`base_url: http://localhost:11434/v1`、`model: qwen3-486`。對話流即第 4.2 節資料流。

### 8.2 Live2D 表情

emotion 管線（已驗證）：LLM 輸出 `[joy]` → `extract_emotion` 解析 → server 送 `{"actions":{"expressions":[3]}}` → 前端套用表情。
角色採內建 **mao_pro**（Cubism 3+，前端相容）。

### 8.3 TTS（繁中男聲）

- 引擎：**edge-tts**（微軟線上、免費、不耗 GPU）。
- 聲線：**`zh-TW-YunJheNeural`**（台灣繁中男聲，貼近菜月昴男性角色）。
- 流程：LLM 回覆 → edge-tts 產 mp3 → pydub（ffmpeg）轉 wav → 瀏覽器播放，同步觸發表情。

### 8.4 角色 prompt 定稿

VTuber 端 persona_prompt 採「熱血中二吐槽版」菜月昴：誇張有戲、愛吐槽、自嘲卻死不放棄、對喜歡的人事物超狂熱，關鍵時刻認真可靠；一律繁中、回覆 2–4 句適合語音。

---

## 9. 成果與驗收

### 9.1 已達成（端到端可運作）

- ✅ 環境綠燈：`verify_env.py` 一鍵驗證 GPU/torch/unsloth 就緒（exit 0）。
- ✅ 完整 QLoRA 微調，產出角色化 adapter。
- ✅ 量化部署：Q4_K_M 2.33GB 於 Ollama，API 回繁中＋emotion。
- ✅ VTuber：瀏覽器文字對話 → **聽到繁中男聲** → **mao_pro 表情隨語音切換**（升職 joy、遲到 smirk、貓走 surprise 皆觸發）。

### 9.2 對話範例（實測語氣）

| 使用者 | 菜月昴（qwen3-486） |
| --- | --- |
| 我剛剛升職了，超開心！ | `[joy]` 升職？！原來是這種事啊，太棒了吧！ |
| 我今天又遲到被罵了，真不爽！ | `[smirk]` 原來是個被罵了的人啊……真不巧，這種事我也遇過好多次喔！ |
| 我家的貓今天離家出走了… | `[surprise]` 喔喔！貓也離家出走？！這可太不對勁了！ |

### 9.3 對照規劃驗收標準

對照 [`PROJECT_ARCHITECTURE.md`](PROJECT_ARCHITECTURE.md) §11：模型驗收（繁中穩定、角色語氣明顯、回覆適合 TTS、不複讀長台詞）與 VTuber 驗收（LLM 連線、文字對話、TTS 唸出、Live2D 載入、表情切換）皆已通過；ASR 語音輸入與長時間體驗驗收列為下一步。

---

## 10. 工作日誌（里程碑式）

依 8 步管線分段，對應實際 git 提交時間（2026-05-29 ~ 06-01）。

### 里程碑 ① 規劃（2026-05-29）
- 完成架構文件 `PROJECT_ARCHITECTURE.md`、微調細節 `FINETUNING_DETAIL_REPORT.md`、執行手冊 `EXECUTION_RUNBOOK.md`。
- 確定路線：Qwen3-4B、QLoRA、Open LLM VTuber、繁中、8GB GPU。
- 專案遷移到單一根目錄 `D:\AI_486`，對齊 Open LLM VTuber quick-start。

### 里程碑 ② + ③ 資料與環境（2026-05-29）
- 資料：163 筆 UTF-8 JSONL 驗證可解碼、切分 146/17。
- 環境：uv + Python 3.12 建 venv；裝 GPU torch、Unsloth、Ollama、llama.cpp。
- 建 `verify_env.py` 紅燈→綠燈閘門（CUDA True、torch 2.11.0+cu128、UNSLOTH OK）。
- **踩雷**：CUDA 13.2 無 bitsandbytes 預編譯 binary → 退到 cu128 wheel。

### 里程碑 ④ 訓練（2026-05-31）
- 以 TDD 重寫訓練腳本，對齊實際安裝的 trl 0.19.1（`processing_class`、SFTConfig 欄位）。
- 拆成可測單元 + pytest（chat template 標記、config 欄位）。
- `--smoke`（1 step）煙霧測試綠燈 → 跑完整 2-epoch QLoRA（≈38 step），LoRA 落在 `train_outputs/lora/`。
- **踩雷**：Windows cp950 主控台遇 Unsloth emoji 崩潰 → 腳本強制 UTF-8 stdout。

### 里程碑 ⑤ 合併 / 量化（2026-06-01）
- 合併 LoRA → 16-bit → 轉 GGUF f16 → 量化 Q4_K_M（2.33GB）。
- `llama-cli` 實測繁中輸出正常。
- **踩雷**：合併 OOM → 改 4-bit 載入基底才塞進 8GB。

### 里程碑 ⑥ Ollama 部署（2026-06-01）
- `ollama create qwen3-486`，API 實測繁中＋emotion＋角色感。
- **踩雷**：PowerShell `Invoke-RestMethod` 把 UTF-8 body 當 latin1 解 → 亂碼；改用 Python urllib 驗證中文 API。

### 里程碑 ⑦ VTuber 串接（2026-06-01）
- 階段一：clone app、`uv sync`、補 git submodule 前端；文字對話通。
- 階段二：emotion 管線驗通；發現 **chitose 是 Cubism 2.x（前端僅支援 3–5）→ 改用 mao_pro**；釐清「表情依賴音頻播放」。
- TTS：voice 改 `zh-TW-YunJheNeural`、離線合成測試、瀏覽器驗收聽到語音＋表情切換。
- **踩雷（最關鍵）**：首次無聲 —— 真因是**缺 ffmpeg**（pydub 轉 mp3→wav 需要），`winget install Gyan.FFmpeg` 後重啟 server 即通。
- **踩雷**：預設 persona 是簡體「Mili」角色會覆寫 SYSTEM → 改 conf.yaml persona 為菜月昴＋明確禁簡體。

### 里程碑 ⑧ 驗收（進行中）
- 已完成 LLM / Live2D / TTS 三項驗收；ASR 與長時間體驗驗收待做。

---

## 11. 踩雷與解法

整個專案最有價值的工程經驗集中在此 —— 多數是 **Windows + 消費級 GPU + 中文編碼**的交叉問題。

| # | 問題 | 根因 | 解法 |
| --- | --- | --- | --- |
| 1 | bitsandbytes 找不到 CUDA 13.2 binary | bnb 0.49.2 無 cu132 預編譯 | 退到 cu128 torch wheel，`verify_env.py` 紅綠閘門把關 |
| 2 | trl API 不符（`tokenizer=`/`dataset_text_field`） | trl 0.19.1 改用 `processing_class=`、欄位移到 SFTConfig | 以 TDD 探測實際 API 後對齊 |
| 3 | cp950 主控台遇 emoji 崩潰 | Windows 預設編碼非 UTF-8 | 腳本頂部 `sys.stdout/stderr.reconfigure(encoding="utf-8")` |
| 4 | 合併 LoRA 時 OOM | fp16 基底 ~9GB > 8GB | 改 `load_in_4bit=True` 載入基底 |
| 5 | Ollama API 中文亂碼 | PowerShell IRM 以 latin1 解 UTF-8 body | 改用 Python urllib 驗證 |
| 6 | VTuber 回簡體＋錯角色 | 預設 persona_prompt 覆寫 Modelfile SYSTEM | conf.yaml persona 改菜月昴＋禁簡體 |
| 7 | Live2D 表情不動（其一） | chitose 是 Cubism 2.x，前端只支援 3–5 | 改用內建 mao_pro（Cubism 3+） |
| 8 | Live2D 表情不動（其二） | 表情指令綁在音頻播放，無 TTS 不觸發 | 先接 TTS，表情隨語音一起驗 |
| 9 | TTS 完全無聲（最關鍵） | pydub 轉 mp3→wav 需 ffmpeg，機器沒裝（`WinError 2`） | `winget install Gyan.FFmpeg`，帶 ffmpeg PATH 重啟 server |
| 10 | OLV server log 中文亂碼 | PowerShell 寫檔 cp950（loguru sink）顯示假象 | 以前端 console / WebSocket 探針為準，不信 log 中文 |

**共通教訓**：Windows 上的中文與編碼問題常是「顯示假象」而非資料損壞；診斷要找對的觀測點（API 用 Python、封包用 WebSocket 探針、無聲先看 server log 而非前端）。

---

## 12. 限制與未來工作

### 12.1 目前限制

- **資料量小且情緒偏態**（fear 偏多）：角色語氣已成立，但情緒分布需平衡。
- **ASR 尚未驗收**：目前以文字輸入為主，語音輸入（sherpa-onnx）待測。
- **TTS 為線上服務**：edge-tts 需網路；聲線為通用男聲，非客製。
- **avatar 暫用 mao_pro**：原訂 chitose 因 Cubism 2.x 不相容，需取得 Cubism 3+ 版本。
- **conf.yaml 未進版控**（app/ 為 gitignore）：VTuber 端設定重裝會遺失。

### 12.2 未來工作

| 優先 | 項目 |
| --- | --- |
| 高 | 完成 ASR 語音輸入 + 五階段體驗驗收 |
| 高 | 平衡資料情緒分布，擴充資料量做第二版微調 |
| 中 | chitose 取得 Cubism 3+ 版本，換上專屬 avatar |
| 中 | 離線／客製 TTS（GPT-SoVITS / CosyVoice）提升角色聲線 |
| 低 | 直播聊天室、OBS、長期記憶、RAG 世界觀知識 |

---

## 13. 附錄

### 13.1 環境版本

| 元件 | 版本 |
| --- | --- |
| OS | Windows 11 Pro |
| GPU | NVIDIA RTX 4060 Laptop（8GB VRAM） |
| Python | 3.12.13（uv 管理） |
| PyTorch | 2.11.0+cu128 |
| bitsandbytes | 0.49.2 |
| Unsloth | 2026.5.8 |
| trl / transformers | 0.19.1 / 5.5.0 |
| llama.cpp | b9442（win-cuda-13.3） |
| Ollama | 0.24.0 |
| ffmpeg | 8.1.1（Gyan.FFmpeg, winget） |
| VTuber 框架 | Open LLM VTuber（localhost:12393） |

### 13.2 關鍵檔案

| 檔案 | 用途 |
| --- | --- |
| [`PROJECT_ARCHITECTURE.md`](PROJECT_ARCHITECTURE.md) | 架構與規劃 |
| [`FINETUNING_DETAIL_REPORT.md`](FINETUNING_DETAIL_REPORT.md) | 微調細節設計 |
| [`EXECUTION_RUNBOOK.md`](EXECUTION_RUNBOOK.md) | 逐步執行手冊 |
| [`verify_env.py`](verify_env.py) | 環境驗證閘門 |
| [`prep_training_data.py`](prep_training_data.py) | 資料準備 |
| [`train_qwen3_486.py`](train_qwen3_486.py) | QLoRA 訓練 |
| [`merge_lora.py`](merge_lora.py) | LoRA 合併 |
| [`deploy/Modelfile`](deploy/Modelfile) | Ollama 部署設定 |
| `data/train.jsonl`, `data/eval.jsonl` | 訓練／驗證資料 |
| `gguf/qwen3-486-q4km.gguf` | 量化成品（gitignored） |

### 13.3 復現指令（摘要）

```bash
# 1. 驗證環境
python verify_env.py                      # exit 0 = 就緒

# 2. 訓練（先煙霧測試，再完整）
python train_qwen3_486.py --smoke         # max_steps=1，確認管線
python train_qwen3_486.py                 # 完整 2-epoch QLoRA

# 3. 合併 → 轉 GGUF → 量化
python merge_lora.py
python convert_hf_to_gguf.py <merged> --outtype f16 ...
llama-quantize <f16.gguf> qwen3-486-q4km.gguf Q4_K_M

# 4. 部署
ollama create qwen3-486 -f deploy/Modelfile

# 5. 啟動 VTuber（app/ 內，需 ffmpeg 在 PATH）
cd app && uv run python run_server.py     # http://localhost:12393
```

---

*本報告為個人學習用、非官方二創實驗紀錄。所有角色、素材與資料的授權於正式或商業使用前需另行確認。*
