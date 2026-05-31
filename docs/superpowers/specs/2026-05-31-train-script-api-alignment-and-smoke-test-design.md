# 訓練腳本 API 對齊 + Smoke Test 設計

日期：2026-05-31
對應 Runbook：§5（微調）、§10.1（OOM）
對應管線步驟：第 ④ 步「訓練」的前置（先修腳本、不真跑完整訓練）

## 1. 目標與範圍

`train_qwen3_486.py` 是照**舊版 trl API** 寫的，但實機環境是 **trl 0.19.1 / transformers 5.5.0 / unsloth 2026.5.8**（見 `2026-05-29-env-setup-uv-verification-gate-design.md` §9）。新版 trl 的 `SFTTrainer` 已把 `tokenizer=` 改名、並把 `dataset_text_field` / `max_seq_length` 從建構子移走，腳本很可能一跑就報錯。

本輪目標：把腳本對齊到實機 trl 版本，並用測試證明它「能起動」——但**不做完整 2-epoch 訓練**（省 GPU，使用者決策）。

**範圍內：**
- 重構 `train_qwen3_486.py`：拆出可測函式、加 CLI 參數（含 `--smoke`）、對齊 trl 0.19.1 API。
- 單元測試（不載 4-bit 權重）：資料載入、chat template 格式化、SFTConfig 建構。
- Smoke test：`--smoke` 跑 `max_steps=1`、存 adapter 到拋棄夾、exit 0。
- 加開發依賴 `pytest`。

**範圍外：**
- 完整訓練（2 epoch）——預設行為保留但本輪不執行。
- 合併 / 量化 / 部署（第 ⑤+ 步）。
- 處理 emotion 資料失衡（fear 53 / joy 5 / anger 4）——留待之後迭代。

## 2. 現況（已確認）

- `data/train.jsonl`（146 筆）、`data/eval.jsonl`（17 筆）已存在，system 已縮短（`prep_training_data.py` 已執行過，本輪不需重跑）。
- 每筆為 `{"messages": [system, user, assistant]}`，assistant 開頭多帶 `[emotion]` 標籤。
- 環境綠燈：torch 2.11.0+cu128、bitsandbytes 0.49.2、unsloth 2026.5.8、Python 3.12.13、RTX 4060 Laptop 8GB。

## 3. 架構：可測函式 + CLI

把 `train_qwen3_486.py` 重構成下列單一職責函式，`main` 只做組裝：

| 函式 | 職責 | 相依 |
|---|---|---|
| `build_datasets(data_dir, tokenizer)` | 載入 train/eval jsonl、用 chat template 產出 `text` 欄位 | datasets、tokenizer |
| `make_sft_config(output_dir, smoke, max_steps, epochs)` | 回傳對齊裝機版本的 `SFTConfig`；`smoke=True` 時設 `max_steps=1` 且關閉 epoch 計數 | trl |
| `load_model_and_tokenizer(model_name, max_seq_len)` | `FastLanguageModel.from_pretrained` + `get_peft_model` + `get_chat_template` | unsloth（會下載 ~3GB base） |
| `main(args)` | 解析 CLI → 組裝 → `trainer.train()` → 存 adapter | 以上全部 |

**CLI 參數（argparse）：**
- `--smoke`：smoke 模式，`max_steps=1`，輸出改到 `train_outputs/smoke/`（拋棄式）。
- `--max-steps N`：覆寫步數（預設 None = 用 epoch）。
- `--model NAME`：覆寫 base 模型名（測試/實驗用，預設 `unsloth/Qwen3-4B-Instruct-2507-bnb-4bit`）。
- `--output DIR`：覆寫輸出夾（預設 `train_outputs/lora`）。
- 無參數時 = 既有完整 2-epoch 行為（不變）。

## 4. trl 0.19.1 API 對齊（實測，不靠猜）

實作時先 inspect 裝機版本的簽名，再依結果改：

```python
import trl, inspect
print(trl.__version__)
print(inspect.signature(trl.SFTTrainer.__init__))
print([f.name for f in __import__("dataclasses").fields(trl.SFTConfig)])
```

預期需要的變更（以實測為準）：
- `SFTTrainer(tokenizer=...)` → `processing_class=...`。
- 從 `SFTTrainer(...)` 移除 `dataset_text_field` / `max_seq_length`；改放進 `SFTConfig`（欄位名以實測為準，trl 近版多用 `max_length` 與 `dataset_text_field`）。
- `SFTConfig` 補 `max_steps`（smoke 用）。

**判定原則：** 測試（§5）紅 → 依實測簽名修 → 綠。API 細節由測試結果驅動，不在 spec 寫死可能過時的欄位名。

## 5. 測試策略（TDD，兩層）

### 5.1 單元測試 `tests/test_train_qwen3_486.py`（快，不載 4-bit 權重）

1. **資料載入**：`build_datasets` 後 train=146、eval=17 筆，且每筆含非空 `text`。
2. **格式化**：`text` 含 chat template 標記（如 `<|im_start|>`）、且含原 user/assistant 內容片段。可只載 tokenizer（`AutoTokenizer.from_pretrained(model)`，數 MB，不載權重）以驗真實 template。
3. **SFTConfig 建構**：`make_sft_config(smoke=True)` 不丟例外、回傳物件且 `max_steps == 1`；`make_sft_config(smoke=False)` 的 `num_train_epochs == 2`。

### 5.2 Smoke test（重，下載 ~3GB base + 一點 GPU）

`python train_qwen3_486.py --smoke`：
- 載 base（首次約 3GB）、建 PEFT 模型與 trainer、跑 `max_steps=1`、存 adapter 到 `train_outputs/smoke/`。
- 通過條件：exit 0；`train_outputs/smoke/` 內出現 adapter 檔（如 `adapter_model.safetensors` / `adapter_config.json`）。

> Smoke 產出是 1 步的垃圾權重，僅證明路徑通，不作為正式模型；`train_outputs/` 已被 .gitignore 排除。

## 6. 依賴

- 加 `pytest`：`uv pip install pytest`（開發用，不影響推論/訓練）。

## 7. 完成定義（Definition of Done）

- `pytest tests/test_train_qwen3_486.py` 全綠（§5.1 三項）。
- `python train_qwen3_486.py --smoke` exit 0，`train_outputs/smoke/` 內有 adapter 檔。
- 無參數的預設設定仍為完整 2-epoch（行為不變，本輪不執行）。
- 重構未改變既有超參數（r=8、alpha=16、lr=1e-4、max_seq_len=1024、2 epoch）。

## 8. 風險與備援

- **trl 欄位名再變**：由 §4 的 inspect + §5 測試驅動，紅燈即時暴露，不靠記憶。
- **transformers 5.5.0 破壞性變更**：若 unsloth/trl 與 transformers 5.x 衝突，smoke 會在載模型或 `.train()` 階段失敗 → 記錄錯誤、評估是否需釘特定 transformers 版本（屬實作期排錯，不預先臆測）。
- **smoke OOM**：max_steps=1、batch=1 負載極小，理論上遠低於完整訓練；若仍 OOM 依 Runbook §10.1 降 max_seq_len。
