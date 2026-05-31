# 訓練腳本 API 對齊 + Smoke Test Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 `train_qwen3_486.py` 對齊實機 trl 0.19.1 / transformers 5.5.0 / unsloth 2026.5.8，重構成可測函式 + `--smoke` CLI，並用單元測試與 1 步 smoke test 證明它能起動（不做完整訓練）。

**Architecture:** 把腳本拆成 `build_datasets()` / `make_sft_config()` / `load_model_and_tokenizer()` / `main(args)` 單一職責函式；argparse 提供 `--smoke`、`--max-steps`、`--model`、`--output`，預設行為仍是完整 2-epoch。單元測試不載 4-bit 權重；smoke test 載 base 跑 1 步。

**Tech Stack:** Python 3.12、unsloth、trl、transformers、datasets、pytest。venv 在 `D:\AI_486\.venv`（用 `.\.venv\Scripts\python.exe`）。

對應 spec：`docs/superpowers/specs/2026-05-31-train-script-api-alignment-and-smoke-test-design.md`

---

## File Structure

- Modify: `D:\AI_486\train_qwen3_486.py` —— 重構為可測函式 + argparse；對齊 trl API。
- Create: `D:\AI_486\tests\__init__.py` —— 空檔，讓 tests 成為 package。
- Create: `D:\AI_486\tests\test_train_qwen3_486.py` —— 不載權重的單元測試。
- 不進版控（.gitignore 已排除）：`train_outputs/`（含 smoke 產物）。

所有指令在 `D:\AI_486` 下用 venv python 跑：`.\.venv\Scripts\python.exe`。先裝 pytest。

---

### Task 1: 裝 pytest + 探測實機 trl API

**Files:** 無（環境操作 + 探測）。

- [ ] **Step 1: 裝 pytest**

```powershell
uv pip install pytest
```
Expected: 安裝成功（uv 自動用本地 `.venv`）。

- [ ] **Step 2: 探測 trl 簽名（決定 §後續欄位名，不靠猜）**

```powershell
.\.venv\Scripts\python.exe -c "import trl, inspect, dataclasses; print('trl', trl.__version__); print('SFTTrainer', inspect.signature(trl.SFTTrainer.__init__)); print('SFTConfig fields:', sorted(f.name for f in dataclasses.fields(trl.SFTConfig)))"
```
Expected: 印出 trl 版本、`SFTTrainer.__init__` 參數（確認有無 `processing_class` / `tokenizer` / `dataset_text_field` / `max_seq_length`）、`SFTConfig` 欄位清單（確認 `max_steps`、`num_train_epochs`、以及文字欄位是 `dataset_text_field`、長度欄位是 `max_length` 或 `max_seq_length`）。
**記下實測結果** —— Task 3/4 依此填正確欄位名。

- [ ] **Step 3: Commit**

```powershell
git commit --allow-empty -m "chore: install pytest; probe trl 0.19.1 SFT API"
```

---

### Task 2: 抽出 `build_datasets()` 並測試（不載權重）

**Files:**
- Modify: `D:\AI_486\train_qwen3_486.py`
- Create: `D:\AI_486\tests\__init__.py`
- Create: `D:\AI_486\tests\test_train_qwen3_486.py`

- [ ] **Step 1: 寫失敗測試**

建 `tests\__init__.py`（空檔）。建 `tests\test_train_qwen3_486.py`：

```python
"""不載 4-bit 權重的單元測試：資料載入與格式化。"""
from pathlib import Path

from transformers import AutoTokenizer
from unsloth.chat_templates import get_chat_template

import train_qwen3_486 as t

DATA_DIR = Path(r"D:\AI_486\data")
MODEL_NAME = "unsloth/Qwen3-4B-Instruct-2507-bnb-4bit"


def _tokenizer():
    tok = AutoTokenizer.from_pretrained(MODEL_NAME)
    return get_chat_template(tok, chat_template="qwen-2.5")


def test_build_datasets_counts_and_text():
    tok = _tokenizer()
    train_ds, eval_ds = t.build_datasets(DATA_DIR, tok)
    assert len(train_ds) == 146
    assert len(eval_ds) == 17
    assert all(isinstance(r["text"], str) and r["text"] for r in train_ds)
```

- [ ] **Step 2: 跑測試確認失敗**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_train_qwen3_486.py::test_build_datasets_counts_and_text -v`
Expected: FAIL —— `AttributeError: module 'train_qwen3_486' has no attribute 'build_datasets'`。

- [ ] **Step 3: 在 `train_qwen3_486.py` 抽出 `build_datasets`**

把現有 `main` 內的 dataset 載入邏輯抽成模組層級函式（保留既有 import）：

```python
def build_datasets(data_dir, tokenizer):
    def formatting(example):
        text = tokenizer.apply_chat_template(
            example["messages"], tokenize=False, add_generation_prompt=False
        )
        return {"text": text}

    train_ds = load_dataset(
        "json", data_files=str(Path(data_dir) / "train.jsonl"), split="train"
    ).map(formatting)
    eval_ds = load_dataset(
        "json", data_files=str(Path(data_dir) / "eval.jsonl"), split="train"
    ).map(formatting)
    return train_ds, eval_ds
```

- [ ] **Step 4: 跑測試確認通過**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_train_qwen3_486.py::test_build_datasets_counts_and_text -v`
Expected: PASS（首次會下載小的 tokenizer，數 MB，不會下載 3GB 權重）。

- [ ] **Step 5: Commit**

```powershell
git add train_qwen3_486.py tests/__init__.py tests/test_train_qwen3_486.py
git commit -m "refactor: extract build_datasets() with unit test"
```

---

### Task 3: 格式化內容測試（驗 chat template 標記與原文）

**Files:**
- Modify: `D:\AI_486\tests\test_train_qwen3_486.py`

- [ ] **Step 1: 加失敗測試**

在 `tests\test_train_qwen3_486.py` 末尾追加：

```python
def test_formatted_text_has_template_markers():
    tok = _tokenizer()
    train_ds, _ = t.build_datasets(DATA_DIR, tok)
    sample = train_ds[0]["text"]
    assert "<|im_start|>" in sample
    assert "[" in sample  # assistant 回覆帶 [emotion] 標籤
```

- [ ] **Step 2: 跑測試**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_train_qwen3_486.py::test_formatted_text_has_template_markers -v`
Expected: PASS（`build_datasets` 已存在，格式化已產出含 `<|im_start|>` 的文字）。若 FAIL（template 標記不同），依實際輸出把斷言字串改成實際 template 的 turn 標記，再跑一次至 PASS。

- [ ] **Step 3: Commit**

```powershell
git add tests/test_train_qwen3_486.py
git commit -m "test: assert chat-template markers in formatted text"
```

---

### Task 4: 抽出 `make_sft_config()` + 測試 + 對齊 trl 欄位

**Files:**
- Modify: `D:\AI_486\train_qwen3_486.py`
- Modify: `D:\AI_486\tests\test_train_qwen3_486.py`

- [ ] **Step 1: 加失敗測試**

在 `tests\test_train_qwen3_486.py` 末尾追加：

```python
def test_make_sft_config_smoke_and_full():
    smoke_cfg = t.make_sft_config(output_dir="train_outputs/smoke", smoke=True)
    assert smoke_cfg.max_steps == 1

    full_cfg = t.make_sft_config(output_dir="train_outputs/lora", smoke=False)
    assert full_cfg.num_train_epochs == 2
```

- [ ] **Step 2: 跑測試確認失敗**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_train_qwen3_486.py::test_make_sft_config_smoke_and_full -v`
Expected: FAIL —— `AttributeError: module 'train_qwen3_486' has no attribute 'make_sft_config'`。

- [ ] **Step 3: 實作 `make_sft_config`（依 Task 1 Step 2 實測欄位名）**

在 `train_qwen3_486.py` 加。下方為依 trl 0.19.x 慣例（`dataset_text_field`、`max_length`）的版本；若 Task 1 探測結果欄位名不同，**以實測為準**修改：

```python
def make_sft_config(output_dir, smoke=False, max_steps=None, epochs=2):
    kwargs = dict(
        output_dir=output_dir,
        per_device_train_batch_size=1,
        gradient_accumulation_steps=8,
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
        dataset_text_field="text",
        max_length=MAX_SEQ_LEN,
    )
    if smoke:
        kwargs["max_steps"] = 1
        kwargs["eval_strategy"] = "no"
        kwargs["save_strategy"] = "no"
    elif max_steps is not None:
        kwargs["max_steps"] = max_steps
    else:
        kwargs["num_train_epochs"] = epochs
    return SFTConfig(**kwargs)
```

- [ ] **Step 4: 跑測試確認通過**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_train_qwen3_486.py::test_make_sft_config_smoke_and_full -v`
Expected: PASS。若 `SFTConfig(**kwargs)` 報未知欄位（如 `max_length` / `dataset_text_field` 不被接受），依 Task 1 探測的合法欄位名改 `kwargs` key，再跑至 PASS。

- [ ] **Step 5: Commit**

```powershell
git add train_qwen3_486.py tests/test_train_qwen3_486.py
git commit -m "refactor: extract make_sft_config() aligned to installed trl"
```

---

### Task 5: 重構 `load_model_and_tokenizer` + `main(args)` + argparse

**Files:**
- Modify: `D:\AI_486\train_qwen3_486.py`

- [ ] **Step 1: 重寫 `train_qwen3_486.py` 的模型載入、main 與 CLI**

把模型載入抽成函式，`main` 用 argparse 組裝，trainer 用 Task 1 實測的參數名（`processing_class` 取代 `tokenizer`，移除建構子內的 `dataset_text_field`/`max_seq_length`）。完整替換 `load_model_and_tokenizer` / `main` / `__main__` 區塊為：

```python
import argparse


def load_model_and_tokenizer(model_name=MODEL_NAME, max_seq_len=MAX_SEQ_LEN):
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=model_name,
        max_seq_length=max_seq_len,
        dtype=None,
        load_in_4bit=True,
    )
    model = FastLanguageModel.get_peft_model(
        model,
        r=8,
        target_modules=[
            "q_proj", "k_proj", "v_proj", "o_proj",
            "gate_proj", "up_proj", "down_proj",
        ],
        lora_alpha=16,
        lora_dropout=0.05,
        bias="none",
        use_gradient_checkpointing="unsloth",
        random_state=42,
    )
    tokenizer = get_chat_template(tokenizer, chat_template="qwen-2.5")
    return model, tokenizer


def main(args):
    model, tokenizer = load_model_and_tokenizer(args.model)
    train_ds, eval_ds = build_datasets(DATA_DIR, tokenizer)
    config = make_sft_config(
        output_dir=args.output, smoke=args.smoke, max_steps=args.max_steps
    )
    trainer = SFTTrainer(
        model=model,
        processing_class=tokenizer,
        train_dataset=train_ds,
        eval_dataset=eval_ds,
        args=config,
    )
    trainer.train()
    model.save_pretrained(args.output)
    tokenizer.save_pretrained(args.output)
    print("LoRA saved to", args.output)


def parse_args():
    p = argparse.ArgumentParser(description="QLoRA fine-tune Qwen3-4B on 486 dataset")
    p.add_argument("--smoke", action="store_true",
                   help="max_steps=1, output to throwaway dir")
    p.add_argument("--max-steps", type=int, default=None, dest="max_steps")
    p.add_argument("--model", default=MODEL_NAME)
    p.add_argument("--output", default=None)
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    if args.output is None:
        args.output = r"D:\AI_486\train_outputs\smoke" if args.smoke else OUTPUT_DIR
    main(args)
```

確認檔案頂部仍保有原 import（`argparse` 若放頂部則此處不重複）與 `MODEL_NAME` / `MAX_SEQ_LEN` / `OUTPUT_DIR` / `DATA_DIR` 常數。

- [ ] **Step 2: 跑全部單元測試確認沒被改壞**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_train_qwen3_486.py -v`
Expected: 3 passed（Task 2/3/4 的測試仍綠）。

- [ ] **Step 3: import 健檢（語法/簽名沒寫錯）**

Run: `.\.venv\Scripts\python.exe -c "import train_qwen3_486 as t; print('ok', t.parse_args.__name__, t.main.__name__, t.load_model_and_tokenizer.__name__)"`
Expected: 印出 `ok parse_args main load_model_and_tokenizer`，無 import error。

- [ ] **Step 4: Commit**

```powershell
git add train_qwen3_486.py
git commit -m "refactor: argparse + processing_class; main() assembled from units"
```

---

### Task 6: Smoke test（下載 base、跑 1 步、存 adapter）

**Files:** 無程式碼變更（執行驗證）。

- [ ] **Step 1: 跑 smoke**

Run: `.\.venv\Scripts\python.exe train_qwen3_486.py --smoke`
Expected: 首次下載 base（約 3GB）；建 trainer；跑 1 個 step；印出 `LoRA saved to D:\AI_486\train_outputs\smoke`；exit 0。
**若失敗：**
- `SFTTrainer` 報未知參數（如 `processing_class`）→ 依 Task 1 探測結果改參數名，回 Task 5 修，重跑。
- `.train()` 內報 `dataset_text_field` / `max_length` 相關 → 依探測結果調 `make_sft_config`（Task 4），重跑。
- OOM → 依 Runbook §10.1 把 `MAX_SEQ_LEN` 降到 768，重跑。

- [ ] **Step 2: 驗證 adapter 產出**

Run: `.\.venv\Scripts\python.exe -c "import os; d=r'D:\AI_486\train_outputs\smoke'; print(sorted(os.listdir(d)))"`
Expected: 清單含 `adapter_config.json` 與 `adapter_model.safetensors`（或 `adapter_model.bin`）。

- [ ] **Step 3: Commit 結果標記**

```powershell
git commit --allow-empty -m "test: smoke run (--smoke) green; adapter saved, 1 step"
```

---

## Self-Review

**1. Spec coverage：**
- spec §3 可測函式（build_datasets / make_sft_config / load_model_and_tokenizer / main）→ Task 2/4/5。✅
- spec §3 CLI（--smoke/--max-steps/--model/--output，預設不變）→ Task 5。✅
- spec §4 trl API 對齊（實測 + processing_class + 欄位）→ Task 1 探測、Task 4/5 套用、Task 6 驗證。✅
- spec §5.1 單元測試三項（資料載入、格式化、SFTConfig）→ Task 2/3/4。✅
- spec §5.2 smoke（--smoke 跑 1 步、存 adapter、exit 0）→ Task 6。✅
- spec §6 依賴 pytest → Task 1。✅
- spec §7 DoD（pytest 全綠 + smoke exit 0 + 預設超參不變）→ Task 5 Step 2、Task 6、以及超參數在 Task 4/5 原值保留。✅

**2. Placeholder scan：** 所有程式步驟皆有完整程式碼；「以實測為準」是 spec 明定的設計策略（trl 欄位名）並附明確的 fallback 修法，非 TODO。無 TBD。✅

**3. Type consistency：** 全程 `build_datasets(data_dir, tokenizer)`、`make_sft_config(output_dir, smoke, max_steps, epochs)`、`load_model_and_tokenizer(model_name, max_seq_len)`、`main(args)` 簽名一致；測試呼叫與實作定義相符；`processing_class` 在 Task 5 與 Task 6 一致。✅
