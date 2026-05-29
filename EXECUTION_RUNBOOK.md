# AI VTuber 執行手冊（Execution Runbook）

## 1. 文件目的

本文件補足 `PROJECT_ARCHITECTURE.md` 與 `FINETUNING_DETAIL_REPORT.md`，提供可逐步照做的執行流程。

讀完這份文件後，應能完成：

- 環境建置。
- 用 `486Dataset.jsonL` 微調 Qwen3-4B。
- 將微調後模型合併、量化、部署到 Ollama。
- 將本地模型接到 Open LLM VTuber。
- 完成 Live2D、TTS、ASR 串接並驗收。

所有指令採用 2026 年主流工具最新版本路線：
**Unsloth + QLoRA + llama.cpp GGUF + Ollama + Open LLM VTuber**。

## 2. 前置條件

### 2.1 硬體

| 項目 | 要求 |
| --- | --- |
| GPU | NVIDIA 顯卡，至少 8GB VRAM |
| CUDA | 12.1 以上（drivers 對應 RTX 30/40/50 系列） |
| RAM | 16GB 以上建議 |
| 磁碟 | 至少 40GB 空閒（base 模型 + LoRA + GGUF + 暫存） |
| OS | Windows 11（PowerShell）或 WSL2 Ubuntu 22.04+ |

Qwen3-4B 4-bit 訓練峰值約 6.5–7.5GB VRAM；同卡上同時跑 ASR/TTS/Live2D 推論需先關閉訓練程序。

### 2.2 軟體版本對齊（2026 主流）

| 元件 | 版本基準 |
| --- | --- |
| 套件管理 | uv 0.10+ |
| Python | 3.12.x（uv managed；ML stack 在 3.12 上相容最廣，3.13 在 2026/5 仍踩 pyarrow / torchaudio cu13x cp313 wheel 缺口） |
| CUDA runtime（GPU driver） | 12.4+ 即可，本機 driver 報 13.2 向下相容 |
| PyTorch | 最新支援 cp312 的 cu12x wheel（2026/5 為 cu128） |
| Unsloth | 最新 stable |
| transformers | 4.46+ |
| trl | 0.12+ |
| bitsandbytes | 0.44+（Windows 官方 wheel） |
| llama.cpp | 官方最新 release（Windows 預編譯 binary） |
| Ollama | 0.4+ |
| Open LLM VTuber | main 分支最新 commit |

### 2.3 目錄佈局建議

整個專案統一在 `D:\AI_486\` 一個根目錄下。`.gitignore` 排除大檔（venv、HF 快取、訓練輸出、GGUF、Open LLM VTuber clone），git repo 本身只追蹤程式碼、資料、文件。

```
D:\AI_486\                            # repo 根目錄
├── .git\
├── .gitignore
├── .venv\                            # uv + Python 3.12（gitignored）
├── 486Dataset.jsonL                  # 原始資料
├── converted_dataset\                # 已轉換、已切分
├── data\                             # 縮短 system 後的 train/eval
├── PROJECT_ARCHITECTURE.md
├── FINETUNING_DETAIL_REPORT.md
├── EXECUTION_RUNBOOK.md              # 本文件
├── prep_training_data.py
├── train_qwen3_486.py
├── merge_lora.py
├── deploy\
│   └── Modelfile
├── docs\superpowers\
│   ├── specs\
│   └── plans\
├── hf_cache\                         # gitignored，HuggingFace 下載快取（base 模型）
├── train_outputs\                    # gitignored
│   ├── lora\                         # LoRA adapter
│   └── merged\                       # 合併後 HF 模型
├── gguf\                             # gitignored，GGUF 產物
└── app\                              # gitignored，Open LLM VTuber clone（另一個 repo）
    └── live2d-models\chitose\        # Live2D 素材

D:\tools\
└── llama.cpp\                        # GGUF 轉換工具（與 repo 分開放）
```

HuggingFace 下載快取透過環境變數導到 repo 內：`HF_HOME=D:\AI_486\hf_cache`（見 §3.2）。

## 3. 環境準備

工具基礎：uv（已裝 0.10.8）。整套環境用 uv 管理 Python 與套件。
PowerShell 若禁止執行腳本，先一次性開放：

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### 3.1 建立 venv（uv + Python 3.12）

```powershell
cd D:\AI_486
uv venv --python 3.12 .venv
.\.venv\Scripts\Activate.ps1
```

uv 會自動 managed cpython-3.12，不需要 PATH 上的系統 Python。

驗證：

```powershell
python -V
# Python 3.12.x
```

避雷說明：本專案不用 Python 3.13。原因——`pyarrow 24` 在 Windows + Python 3.13 上 import 時 access violation 直接 crash 整個 Python（datasets 一載入就死）；torchaudio 在 cu130/cu132 上沒 cp313 wheel；transformers 5.x 在 3.13 上撞 peft 的 `BloomPreTrainedModel` 找不到。3.12 是當前 ML stack 完整支援的最新版本。

### 3.2 設定 HuggingFace 快取到 D:

避免 base model（約 4GB）下載到 C:\Users\<user>\.cache：

```powershell
# 一次性（當前 session）
$env:HF_HOME = "D:\AI_486\hf_cache"

# 永久（使用者層級）
[System.Environment]::SetEnvironmentVariable("HF_HOME", "D:\AI_486\hf_cache", "User")
```

設完後**重新開 PowerShell**讓永久設定生效。

### 3.3 安裝 PyTorch（CUDA 12.4 wheel）

在已 activate 的 venv 內，PyTorch 官方 CUDA channel 選最新支援 cp312 的版本（2026/5 為 cu128；若 cu128 解不開可退 cu126 / cu124）：

```powershell
uv pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128
```

driver 610+ 與 CUDA 13.x runtime 向下相容 cu12x wheel，不需要降 driver。

驗證 CUDA 可用：

```powershell
python -c "import torch; print('cuda:', torch.cuda.is_available()); print('device:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'none')"
# cuda: True
# device: NVIDIA GeForce RTX 4060 ...
```

回傳 `False`：先處理 NVIDIA driver，再回來。

### 3.4 安裝 Unsloth 與相依

```powershell
uv pip install unsloth
uv pip install datasets "trl<0.20.0" peft accelerate bitsandbytes
```

`unsloth` 從 pypi 安裝會自動拉 transformers / unsloth_zoo / numpy 等相依，版本由 unsloth 鎖定。

**重要踩雷**：`uv pip install unsloth` 在解析依賴時會把先前的 cu128 torch 降回 pypi 預設的 **CPU 版 torch 2.10.0**，造成 unsloth 啟動時報「cannot find any torch accelerator」。**必須在 unsloth 裝完後強制重裝 GPU torch**：

```powershell
uv pip install --reinstall torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128
```

uv 快取會命中，秒裝。完成後最終驗證：

```powershell
python -c "import torch; print('cuda:', torch.cuda.is_available()); print('torch:', torch.__version__)"
# cuda: True
# torch: 2.11.0+cu128

python -c "from unsloth import FastLanguageModel; print('UNSLOTH OK')"
# (may print Flash Attention 2 warning - safe, fallbacks to Xformers)
# UNSLOTH OK
```

如需 git main 版（追最新 patch）：先驗 pypi 版能 import，再 `uv pip install -U "unsloth @ git+https://github.com/unslothai/unsloth.git"`，記得再 reinstall 一次 torch cu128。

`unsloth` 從 pypi 安裝會自動拉 `transformers`、`unsloth_zoo`、`peft` 等相容版本；不要用 `--no-deps`，否則會缺 `transformers` 或拉到不相容版本（實測 trl/peft + transformers 5.x 會撞牆）。

驗證：

```powershell
python -c "from unsloth import FastLanguageModel; print('unsloth OK')"
```

### 3.5 安裝 Ollama

從 https://ollama.com/download/OllamaSetup.exe 下載並執行安裝程式。安裝後 Ollama 以系統服務常駐。

驗證（裝完開**新**的 PowerShell 視窗，舊視窗 PATH 沒更新）：

```powershell
ollama --version
# ollama version is 0.24+

ollama list
# (empty until §7 imports the quantized model)

curl http://localhost:11434/api/tags
# {"models":[]}
```

若新 PowerShell 也找不到 ollama，但 `Test-Path "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe"` 為 True，表示 installer 沒 update PATH；可手動加入或登出/登入。

### 3.6 取得 llama.cpp（Windows 預編譯 release）

不用自編譯，直接抓官方 Windows release。

1. 開瀏覽器到 https://github.com/ggml-org/llama.cpp/releases
2. 找最新的 `llama-bXXXX-bin-win-cuda-cu12.x-x64.zip`（CUDA 版，速度比 cpu 快）
3. 解壓到 `D:\tools\llama.cpp\`，裡面應該有 `llama-quantize.exe`、`llama-cli.exe` 等

`convert_hf_to_gguf.py` 不在 release 包內，從原始碼倉抓即可：

```powershell
mkdir D:\tools\llama.cpp-src
cd D:\tools\llama.cpp-src
git clone --depth 1 https://github.com/ggml-org/llama.cpp .
uv pip install -r requirements.txt
```

只用 `convert_hf_to_gguf.py` 那支腳本；其他編譯步驟跳過。

## 4. 資料準備

### 4.1 已完成項目

`converted_dataset\` 已產出：

- 146 train / 17 eval 樣本。
- 對齊 Open LLM VTuber 8 種 emotion tag。
- 兩種格式：純 `messages` 與 ShareGPT。

訓練建議使用：

```
converted_dataset\486_messages_live2d_emotions_train.jsonl
converted_dataset\486_messages_live2d_emotions_eval.jsonl
```

### 4.2 待處理：縮短 system prompt

目前每筆都含同一段約 200 字的菜月昴設定。`FINETUNING_DETAIL_REPORT.md` 6.3 建議訓練資料 system 應精簡，部署時再放完整 prompt。

建議將訓練資料的 system 改為：

```
你是繁體中文 AI VTuber，回應簡短自然，必要時於開頭使用 [emotion] 標籤。
```

完整菜月昴人設留到部署時的 Open LLM VTuber 角色設定（見 8.3）。

可寫一個一次性處理腳本 `D:\AI_486\prep_training_data.py`：

```python
import json
from pathlib import Path

SHORT_SYSTEM = "你是繁體中文 AI VTuber，回應簡短自然，必要時於開頭使用 [emotion] 標籤。"

def rewrite(src, dst):
    with open(src, "r", encoding="utf-8") as f_in, open(dst, "w", encoding="utf-8") as f_out:
        for line in f_in:
            obj = json.loads(line)
            for m in obj["messages"]:
                if m["role"] == "system":
                    m["content"] = SHORT_SYSTEM
            f_out.write(json.dumps(obj, ensure_ascii=False) + "\n")

base = Path(r"D:\AI_486\converted_dataset")
out = Path(r"D:\AI_486\data")
out.mkdir(parents=True, exist_ok=True)

rewrite(base / "486_messages_live2d_emotions_train.jsonl",
        out / "train.jsonl")
rewrite(base / "486_messages_live2d_emotions_eval.jsonl",
        out / "eval.jsonl")

print("done")
```

執行：

```powershell
cd D:\AI_486
.\.venv\Scripts\Activate.ps1
python prep_training_data.py
```

### 4.3 Emotion 分布提醒

依 `live2d_emotion_tagging_report.json`：

| Tag | 筆數 |
| --- | ---: |
| fear | 53 |
| neutral | 36 |
| surprise | 31 |
| untagged | 17 |
| sadness | 13 |
| joy | 5 |
| anger | 4 |
| disgust / smirk | 2 |

`fear` 偏多、`joy` / `anger` 偏少。第一版可先訓，但要意識到模型容易往「fear / 慌張 / 絕望」傾斜，互動測試時若樂觀情境也輸出 `[fear]`，下一輪需補資料平衡。

## 5. 微調（Unsloth + QLoRA）

### 5.1 訓練腳本

於 `D:\AI_486\train_qwen3_486.py` 建立。
以下為骨架，trl / unsloth API 隨版本演進，若安裝版本與下方註解版本不同，請依該版本官方範例微調 `SFTConfig` 欄位名稱：

```python
import json
from pathlib import Path
from datasets import load_dataset
from unsloth import FastLanguageModel
from unsloth.chat_templates import get_chat_template
from trl import SFTTrainer, SFTConfig

MODEL_NAME = "unsloth/Qwen3-4B-Instruct-2507-bnb-4bit"
MAX_SEQ_LEN = 1024
OUTPUT_DIR = r"D:\AI_486\train_outputs\lora"
DATA_DIR = Path(r"D:\AI_486\data")

model, tokenizer = FastLanguageModel.from_pretrained(
    model_name=MODEL_NAME,
    max_seq_length=MAX_SEQ_LEN,
    dtype=None,
    load_in_4bit=True,
)

model = FastLanguageModel.get_peft_model(
    model,
    r=8,
    target_modules=["q_proj","k_proj","v_proj","o_proj",
                    "gate_proj","up_proj","down_proj"],
    lora_alpha=16,
    lora_dropout=0.05,
    bias="none",
    use_gradient_checkpointing="unsloth",
    random_state=42,
)

tokenizer = get_chat_template(tokenizer, chat_template="qwen-2.5")
# Qwen3 與 Qwen2.5 chat template 結構相同，沿用即可。

def formatting(example):
    text = tokenizer.apply_chat_template(
        example["messages"], tokenize=False, add_generation_prompt=False)
    return {"text": text}

train_ds = load_dataset("json", data_files=str(DATA_DIR / "train.jsonl"), split="train").map(formatting)
eval_ds  = load_dataset("json", data_files=str(DATA_DIR / "eval.jsonl"),  split="train").map(formatting)

trainer = SFTTrainer(
    model=model,
    tokenizer=tokenizer,
    train_dataset=train_ds,
    eval_dataset=eval_ds,
    dataset_text_field="text",
    max_seq_length=MAX_SEQ_LEN,
    args=SFTConfig(
        output_dir=OUTPUT_DIR,
        per_device_train_batch_size=1,
        gradient_accumulation_steps=8,
        num_train_epochs=2,
        learning_rate=1e-4,
        warmup_ratio=0.03,
        lr_scheduler_type="cosine",
        logging_steps=5,
        eval_strategy="epoch",
        save_strategy="epoch",
        bf16=True,
        optim="adamw_8bit",
        seed=42,
        report_to="none",
        # max_seq_length 在新版 trl 已移除；若你的版本仍接受可加回。
    ),
)

trainer.train()
model.save_pretrained(OUTPUT_DIR)
tokenizer.save_pretrained(OUTPUT_DIR)
print("LoRA saved to", OUTPUT_DIR)
```

### 5.2 啟動訓練

```powershell
cd D:\AI_486
.\.venv\Scripts\Activate.ps1
python train_qwen3_486.py
```

預期過程：

- 首次執行會下載 base 模型約 3GB。
- VRAM 峰值約 6.5–7.5GB。
- 8GB GPU 上 2 epoch 約 30–90 分鐘。
- eval loss 應自第 0 步往下降，第 2 epoch 末若 eval loss 反彈，下次訓練降 epoch 或 lr。

### 5.3 訓練後快速測試（adapter 推論）

於同個 venv 開新 Python：

```python
from unsloth import FastLanguageModel
from unsloth.chat_templates import get_chat_template
import torch

model, tokenizer = FastLanguageModel.from_pretrained(
    model_name=r"D:\AI_486\train_outputs\lora",
    max_seq_length=1024,
    load_in_4bit=True,
)
FastLanguageModel.for_inference(model)
tokenizer = get_chat_template(tokenizer, chat_template="qwen-2.5")

msgs = [
    {"role": "system", "content": "你是繁體中文 AI VTuber，回應簡短自然，必要時於開頭使用 [emotion] 標籤。"},
    {"role": "user",   "content": "我明天要面試，有點怕。"},
]
inputs = tokenizer.apply_chat_template(msgs, return_tensors="pt", add_generation_prompt=True).to("cuda")
out = model.generate(inputs, max_new_tokens=200, temperature=0.8, top_p=0.9, do_sample=True)
print(tokenizer.decode(out[0][inputs.shape[1]:], skip_special_tokens=True))
```

通過條件：

- 回覆為繁體中文。
- 句子長度適合 TTS（1–4 句）。
- 開頭出現合理的 `[joy]` / `[sadness]` / `[fear]` 之一。
- 不複讀 dataset 原句。

若不通過，回到 `FINETUNING_DETAIL_REPORT.md` 12 節調整。

## 6. 合併與量化

### 6.1 合併 LoRA 到 base

於同個 venv 建立 `D:\AI_486\merge_lora.py`：

```python
from unsloth import FastLanguageModel

model, tokenizer = FastLanguageModel.from_pretrained(
    model_name=r"D:\AI_486\train_outputs\lora",
    max_seq_length=1024,
    load_in_4bit=False,
    dtype=None,
)

OUT = r"D:\AI_486\train_outputs\merged"
model.save_pretrained_merged(OUT, tokenizer, save_method="merged_16bit")
print("merged ->", OUT)
```

執行：

```powershell
cd D:\AI_486
.\.venv\Scripts\Activate.ps1
python merge_lora.py
```

合併過程會把 base 以 16-bit 載入，需要約 9GB RAM/VRAM；若 VRAM 不足，Unsloth 會 fallback 到 CPU 合併，較慢但會完成。

### 6.2 轉換為 GGUF

```powershell
mkdir D:\AI_486\gguf -Force
cd D:\tools\llama.cpp-src
python convert_hf_to_gguf.py D:\AI_486\train_outputs\merged --outfile D:\AI_486\gguf\qwen3-486-f16.gguf --outtype f16
```

產出約 8GB 的 f16 GGUF。

### 6.3 量化為 Q4_K_M

```powershell
D:\tools\llama.cpp\llama-quantize.exe D:\AI_486\gguf\qwen3-486-f16.gguf D:\AI_486\gguf\qwen3-486-q4km.gguf Q4_K_M
```

產出約 2.5GB 的 Q4_K_M GGUF。量化完成後 `qwen3-486-f16.gguf`（中間檔）可刪除釋放 ~8GB。

量化選項比較：

| Quant | 大小 | 品質損失 | 推薦場景 |
| --- | --- | --- | --- |
| Q4_K_M | ~2.5GB | 低 | 8GB GPU 首選 |
| Q5_K_M | ~3.0GB | 更低 | 有空間且想保品質 |
| Q6_K | ~3.6GB | 幾乎無 | 接近原 fp16 |
| Q8_0 | ~4.5GB | 無感 | 不建議 8GB 部署 |

驗證 GGUF 可載：

```powershell
D:\tools\llama.cpp\llama-cli.exe -m D:\AI_486\gguf\qwen3-486-q4km.gguf -p "你好" -n 64
```

## 7. 部署到 Ollama

### 7.1 建立 Modelfile

`D:\AI_486\deploy\Modelfile`：

```
FROM D:/AI_486/gguf/qwen3-486-q4km.gguf

TEMPLATE """{{ if .System }}<|im_start|>system
{{ .System }}<|im_end|>
{{ end }}{{ range .Messages }}<|im_start|>{{ .Role }}
{{ .Content }}<|im_end|>
{{ end }}<|im_start|>assistant
"""

PARAMETER temperature 0.8
PARAMETER top_p 0.9
PARAMETER repeat_penalty 1.1
PARAMETER num_ctx 4096
PARAMETER num_predict 200
PARAMETER stop "<|im_end|>"
PARAMETER stop "<|im_start|>"

SYSTEM """你扮演《Re:從零開始的異世界生活》風格的菜月昴 AI VTuber（非官方）。
使用繁體中文。回應簡短，2 到 4 句為主，適合 TTS 唸出。
情緒明顯時於回覆開頭加上一個 [emotion] 標籤，標籤限定為：
[neutral] [joy] [sadness] [anger] [surprise] [fear] [smirk] [disgust]。
不逐字複製原作長篇台詞。不宣稱自己是官方角色或聲優本人。
"""
```

### 7.2 建立 Ollama 模型

```powershell
cd D:\AI_486\deploy
ollama create qwen3-486 -f Modelfile
ollama list
```

### 7.3 驗證 OpenAI 相容 API

```powershell
curl http://localhost:11434/v1/chat/completions `
  -H "Content-Type: application/json" `
  -d '{
    "model": "qwen3-486",
    "messages": [{"role":"user","content":"今天好累。"}],
    "temperature": 0.8
  }'
```

通過條件：

- 200 OK，content 為繁中。
- 含合理 `[emotion]` tag。
- 回覆 2–4 句。

## 8. Open LLM VTuber 串接

### 8.1 安裝

clone 到 D: 工作區：

```powershell
cd D:\AI_486
git clone https://github.com/Open-LLM-VTuber/Open-LLM-VTuber.git app
cd app
```

依官方 README 用 `uv`（已裝過）：

```powershell
uv sync
```

`uv sync` 會根據專案內 `pyproject.toml` / `uv.lock` 建立自己的 `.venv` 並裝齊相依。Open LLM VTuber 與 D:\AI_486\.venv 是兩個獨立的 venv，互不干擾。

### 8.2 LLM 設定（`conf.yaml`）

於 `conf.yaml` 找到 LLM provider 區塊，改為：

```yaml
llm_provider: openai_compatible_llm

openai_compatible_llm:
  base_url: "http://localhost:11434/v1"
  llm_api_key: "ollama"
  organization_id: ""
  project_id: ""
  model: "qwen3-486"
  temperature: 0.8
  top_p: 0.9
  max_tokens: 200
```

`llm_api_key` 填任意字串，Ollama 不驗證。實際欄位名稱以你拿到的 `conf.yaml` 樣本為準（Open LLM VTuber 不同版本欄位名稱會微調）。

### 8.3 角色 prompt

`conf.yaml` 中 `persona_prompt` 或對應的角色 yaml 放完整版菜月昴設定（節錄）：

```yaml
persona_prompt: |
  你扮演《Re:從零開始的異世界生活》風格的菜月昴 AI VTuber（非官方）。
  使用繁體中文，回覆簡短，2 到 4 句為主，適合語音輸出。
  個性熱血、愛吐槽、容易自嘲但不消極到底。
  情緒明顯時於開頭加 [emotion] 標籤，限定 8 種：
    [neutral] [joy] [sadness] [anger] [surprise] [fear] [smirk] [disgust]
  不逐字複製原作長篇台詞。
  不宣稱自己是官方角色或聲優本人。
  使用者越界要求時，保持角色語氣婉拒。
```

完整版人設與 Ollama Modelfile 的 SYSTEM 內容可保持一致；
Open LLM VTuber 送 chat 時若已帶 system，會覆寫 Modelfile 的預設 SYSTEM。

### 8.4 註冊 Live2D 模型

1. 將 `C:\Users\chenb\Downloads\chitose\runtime\` 整個資料夾複製到：
   ```
   D:\AI_486\app\live2d-models\chitose\
   ```
   裡面應直接看到 `chitose.model3.json` 等檔案，不要多包一層資料夾。

2. 編輯 `D:\AI_486\app\live2d-models\model_dict.json`，追加項目。`emotionMap` 的 value 為 `chitose.model3.json` 中 Expressions 陣列的 index（從 0 起算）。

   實際讀取 `chitose.model3.json` 確認 Expressions 順序（依 `PROJECT_ARCHITECTURE.md` 9.1 的清單，常見順序如下）：

   | Index | File |
   | ---: | --- |
   | 0 | Angry |
   | 1 | Blushing |
   | 2 | f01 |
   | 3 | Normal |
   | 4 | Sad |
   | 5 | Smile |
   | 6 | Surprised |

   依此對應，model_dict 條目：

   ```json
   {
     "name": "chitose",
     "description": "Custom Live2D avatar for 486 VTuber",
     "url": "/live2d-models/chitose/chitose.model3.json",
     "kScale": 0.000625,
     "initialXshift": 0,
     "initialYshift": 0,
     "kXOffset": 0,
     "idleMotionGroupName": "Idle",
     "emotionMap": {
       "neutral":  3,
       "joy":      5,
       "sadness":  4,
       "anger":    0,
       "surprise": 6,
       "fear":     6,
       "smirk":    5,
       "disgust":  0
     }
   }
   ```

   `fear` / `smirk` / `disgust` 借用相近表情（Surprised / Smile / Angry），第二輪可請繪師再補對應 expression。若實際打開 `chitose.model3.json` 的 Expressions 順序與上表不同，依檔案實際順序修正 index 即可。

3. 角色 yaml 設定：

   ```yaml
   live2d_model_name: "chitose"
   ```

### 8.5 ASR：Faster-Whisper

`conf.yaml` ASR 區塊：

```yaml
asr_model: faster_whisper

faster_whisper:
  model_path: "small"
  language: "zh"
  device: "cuda"
  compute_type: "int8_float16"
```

`small` 中文夠用且 VRAM 小（int8_float16 約 500MB-1GB）。第一次執行會自動下載。

### 8.6 TTS：edge-tts

`conf.yaml` TTS 區塊：

```yaml
tts_model: edge_tts

edge_tts:
  voice: "zh-TW-HsiaoChenNeural"
```

可選 voice：

- `zh-TW-HsiaoChenNeural`（女聲，繁中）
- `zh-TW-YunJheNeural`（男聲，繁中）
- `zh-CN-YunxiNeural`（少年男聲，普通話）

edge-tts 免費且不需本地 GPU 資源。第二版可換 GPT-SoVITS 或 CosyVoice 做角色感更強的本地 TTS。

### 8.7 啟動

```powershell
cd D:\AI_486\app
uv run python run_server.py
```

預期：

- 終端顯示後端啟動於 `http://localhost:12393` 或類似 port。
- 瀏覽器開該位址，能看到 Live2D 介面並載入 chitose。
- 點麥克風或文字輸入可開始對話。

## 9. 五階段驗收

對應 `PROJECT_ARCHITECTURE.md` 8.2 與 11 節。

### 9.1 階段一：純文字端到端

固定問同一批問題（取自 `FINETUNING_DETAIL_REPORT.md` 11.2 的 30 題集）。

通過條件：

- 回覆延遲 < 5 秒（首字 < 2 秒佳）。
- 繁中、語氣自然。
- 70%+ 樣本帶合理 emotion tag。
- 不大段複讀原作。

### 9.2 階段二：加入 ASR

- 麥克風輸入「你好」「我今天好累」等短句。
- ASR 應 1–2 秒內完成識別。
- 中文識別正確率 > 90%（清晰發音情境）。

### 9.3 階段三：加入 TTS

- AI 回覆輸出語音。
- 語速自然，不會切斷句子。
- TTS 開始播放延遲 < 3 秒。

### 9.4 階段四：加入 Live2D 表情

- Live2D 嘴型隨 TTS 開合。
- emotion tag 對應的表情切換正確（用 8.4 表逐一檢查）。
- 表情不會在一句話內亂跳。

### 9.5 階段五：連續互動

- 連續對話 10 分鐘無崩潰。
- VRAM 不持續上漲（無洩漏）。
- 整體體驗符合「角色互動」而非「客服 bot」。

## 10. 常見錯誤與對策

### 10.1 訓練 OOM

症狀：`torch.cuda.OutOfMemoryError`。

對策（依序嘗試）：

1. 確認沒有其他 GPU 程式（瀏覽器硬體加速、Open LLM VTuber 已關閉）。
2. `max_seq_length` 從 1024 降到 768。
3. `gradient_accumulation_steps` 從 8 升到 16。
4. `r=8 alpha=16` 保持不要升。
5. 換 base `unsloth/Qwen3-1.7B-Instruct-bnb-4bit`。

### 10.2 GGUF 轉換失敗

症狀：`convert_hf_to_gguf.py` 報 tokenizer 或 architecture 不支援。

對策：

- 更新 llama.cpp 到 main 最新（Qwen3 支援近期才完整）。
- 確認 `merged` 目錄含 `config.json`、`tokenizer.json`、`*.safetensors`。
- 必要時改用 `unsloth` 內建的 `model.save_pretrained_gguf("...", tokenizer, quantization_method="q4_k_m")` 一站式產出。

### 10.3 Ollama 載不到 GGUF

症狀：`ollama create` 報 unknown architecture。

對策：

- 升級 Ollama 到 0.4+。
- 確認 Modelfile 的 `FROM` 路徑是絕對路徑且檔案存在。
- Modelfile 已採正斜線 `D:/AI_486/gguf/qwen3-486-q4km.gguf`，若仍報錯改絕對 Windows 路徑 `D:\AI_486\gguf\qwen3-486-q4km.gguf` 重試。

### 10.4 Open LLM VTuber 連不到 LLM

症狀：UI 點送出後一直轉圈。

對策：

- 瀏覽器直接打 `http://localhost:11434/api/tags`，確認 Ollama 回應。
- `conf.yaml` 的 `base_url` 必須是 `http://localhost:11434/v1`，不要漏 `/v1`。
- `model` 名稱需與 `ollama list` 顯示完全一致（含 tag）。
- Windows 防火牆首次可能擋本地呼叫，允許即可。

### 10.5 emotion tag 沒觸發表情

症狀：模型有輸出 `[joy]` 但 Live2D 不動。

對策：

- 確認 `model_dict.json` 的 `emotionMap` key 拼字與模型輸出一致（小寫、無底線）。
- 確認 emotion key 是 Open LLM VTuber 支援的 8 種之一。
- 在 console 看 server log，確認 emotion parser 是否解析到。

### 10.6 中文 mojibake

症狀：PowerShell 顯示亂碼，但檔案實際內容正常。

對策：

- PowerShell 顯示問題與檔案內容無關。
- 強制 UTF-8 輸出：
  ```powershell
  [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
  ```
- 或在 VS Code / 其他 UTF-8 編輯器開啟驗證。

### 10.7 模型只會吐 `[fear]`

症狀：任何問題都帶 `[fear]`，連打招呼也慌張。

原因：dataset emotion 分布失衡（53/146 是 fear）。

對策：

- 短期：部署時系統 prompt 加一句「正常情境優先用 `[neutral]` 或 `[joy]`」。
- 中期：補 30–50 筆 `[joy]` / `[neutral]` 樣本，重訓。
- 長期：建立 emotion 平衡器，每類至少 15 筆。

## 11. 完整檢核清單

### 11.1 環境

- [ ] Python 3.11 可執行。
- [ ] CUDA 可用、`torch.cuda.is_available()` 為 True。
- [ ] Unsloth import 成功。
- [ ] Ollama 服務啟動。
- [ ] llama.cpp `convert_hf_to_gguf.py` 與 `llama-quantize` 可執行。

### 11.2 資料

- [ ] `train.jsonl` / `eval.jsonl` 已產出，system 已縮短。
- [ ] 行數 146 / 17。
- [ ] 抽樣 5 筆肉眼檢查無亂碼。

### 11.3 訓練

- [ ] `train_qwen3_486.py` 跑完 2 epoch 不 OOM。
- [ ] eval loss 結束時低於 epoch 0。
- [ ] `D:\AI_486\train_outputs\lora\` 內含 adapter 檔。
- [ ] 5.3 推論測試輸出符合通過條件。

### 11.4 部署

- [ ] `merged/` 已產出。
- [ ] `qwen3-486-q4km.gguf` 已產出，約 2.5GB。
- [ ] `ollama list` 看得到 `qwen3-486`。
- [ ] curl `/v1/chat/completions` 回繁中。

### 11.5 Open LLM VTuber

- [ ] `git clone` 完成，相依安裝成功。
- [ ] `conf.yaml` LLM 區塊指向本地 Ollama。
- [ ] `live2d-models/chitose/` 已就位。
- [ ] `model_dict.json` 新增 chitose 並設好 `emotionMap`。
- [ ] 角色 yaml `live2d_model_name: chitose`。
- [ ] `run_server.py` 啟動成功。
- [ ] 瀏覽器看到 Live2D。

### 11.6 五階段驗收

- [ ] 階段一：純文字端到端通過。
- [ ] 階段二：ASR 中文識別正常。
- [ ] 階段三：TTS 唸出回覆。
- [ ] 階段四：emotion tag 觸發對應表情。
- [ ] 階段五：連續 10 分鐘無崩潰。

## 12. 下一步

完成本 Runbook 後，可依需求進入：

- **Experiment C / D**：依 `FINETUNING_DETAIL_REPORT.md` 14.3、14.4 調參數或換 1.7B。
- **資料補強**：依 4.3 emotion 分布回補資料，重訓。
- **TTS 升級**：edge-tts → GPT-SoVITS（角色感更強）。
- **長期記憶**：Open LLM VTuber 的 memory 模組或外部向量庫。
- **直播整合**：OBS、Twitch / YouTube 聊天串接。

第一版完成定義：見 `PROJECT_ARCHITECTURE.md` 14 節「最終交付定義」。
