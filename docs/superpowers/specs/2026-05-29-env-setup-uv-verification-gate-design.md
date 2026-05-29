# 環境建置 + 驗證閘門設計（uv，最新優先、失敗才降）

日期：2026-05-29
對應 Runbook：§3（環境準備）、§10.1（OOM）、§11.1（環境檢核清單）

## 1. 目標與範圍

這是「做出 486 AI VTuber」整條執行鏈的第 ③ 步「環境」。目標是：在本機（NVIDIA 8GB GPU、CUDA driver 13.3）上，用 uv 建好可跑 Unsloth QLoRA 的 Python 環境，並用一支可重複執行的驗證腳本證明環境就緒。

**範圍內：**
- 用 uv 建立 venv（managed Python）。
- 安裝 GPU 版 PyTorch、Unsloth 及其相依。
- 一支 `verify_env.py`，斷言環境就緒，作為「綠燈」唯一判準。
- 記錄最後實際裝成功的版本組合，進版控。

**範圍外（後續步驟）：**
- 下載 base 模型、實際訓練（第 ④ 步）。
- 合併 / 量化 / Ollama / Open LLM VTuber（第 ⑤–⑦ 步）。

## 2. 核心策略：最新優先，失敗才降（由測試驅動）

使用者決策：版本從最新試起，跑不過再降。為避免憑感覺降版，**由 `verify_env.py` 的結果決定是否降級** ——這就是這一步的 TDD red/green 機制：

1. 先寫 `verify_env.py`（此時跑 = 紅，torch 未裝）。
2. 照「安裝階梯」從最新版裝起。
3. 每裝完一層跑一次 `verify_env.py`：紅 → 照階梯降一級重裝；綠 → 停。
4. 將最後成功組合寫入 §6 的版本筆記。

## 3. 驗證腳本 `verify_env.py`（定義「綠燈」）

放置於 `D:\AI_486\verify_env.py`。依序檢查，任一失敗即印出明確訊息並 `sys.exit(1)`；全過則 `sys.exit(0)`：

1. `import torch` 成功；印出 `torch.__version__`，且字串須含 `+cu`（排除誤裝 CPU 版）。
2. `torch.cuda.is_available()` 為 True；印出 `torch.cuda.get_device_name(0)`。
3. `import bitsandbytes` 成功。
4. `from unsloth import FastLanguageModel` 成功。
5. **GPU 4-bit 實跑**：在 CUDA 上配置一個小的 4-bit 量化 tensor（透過 bitsandbytes，例如 `bnb.nn.Linear4bit` 前向一筆 dummy 輸入），確認不丟例外。這是「真的能做 QLoRA」最硬的證明，而不只是 import 通過。

腳本須能重複執行、無副作用（不下載大模型、不寫檔）。

## 4. 安裝階梯（最新優先，失敗才降一級）

| 層 | 先試（最新） | 失敗才降 | 判定「失敗」依據 |
|---|---|---|---|
| Python | 3.13 | → 3.12 | 該 py 版本無對應 torch/unsloth wheel，或第 3 節測試於 import 層即失敗 |
| PyTorch | cu13x（優先 cu130，若有更新且裝得到的 cu13x channel 則取最新） | → cu128 | pip/uv 找不到對應 wheel，或裝完 `cuda.is_available()` 為 False |
| Unsloth + 相依 | 最新 stable（pypi） | （見 §5 陷阱，非降版而是修復步驟） | `from unsloth import FastLanguageModel` 失敗 |

說明：
- **不從 Python 3.14 起。** 3.14 目前幾乎沒有 ML wheel，試了會在 torch 安裝階段秒掛，純浪費一輪。起點定 3.13。
- CUDA driver 13.3 向下相容所有 CUDA 12.x/13.x runtime，故 cu128 wheel 也能在本機運作；cu13x 只是世代更貼近 driver。
- 相依套件：`datasets`、`trl<0.20.0`、`peft`、`accelerate`、`bitsandbytes`（沿用 Runbook §3.4）。

## 5. 已知陷阱（必寫進安裝程序）

裝完 `unsloth` 後，uv 解依賴會把先前的 GPU torch **降回 pypi 預設的 CPU 版 torch**，導致 unsloth 啟動時報「cannot find any torch accelerator」。

**對策（固定步驟）：** 裝完 unsloth 後，強制重釘一次 GPU torch——
`uv pip install --reinstall torch torchvision torchaudio --index-url <當前選定的 cuda channel>`
uv 快取會命中、秒裝。完成後再跑 `verify_env.py`。

## 6. 產出物

1. `D:\AI_486\verify_env.py` —— 驗證腳本（進版控）。
2. 版本筆記：記錄最後成功組合（Python 版本、torch 版本與 cuda channel、unsloth 版本、device 名稱）。實作完成後追加為本 spec 的「## 9. 實際安裝結果」一節，進版控。
3. uv 建立的 `.venv\`（被 .gitignore 排除，不進版控）。

## 7. 完成定義（Definition of Done）

- `python verify_env.py` 回傳 exit 0，且印出 cuda=True 與正確的 GPU 名稱。
- §3 第 5 項 GPU 4-bit 實跑通過（無例外）。
- 最後成功的版本組合已記錄並 commit。
- 對應 Runbook §11.1 環境檢核清單全部打勾。

## 8. 風險與備援

- **cu13x 生態未跟上**：bitsandbytes / xformers / unsloth 的 Windows wheel 可能還沒對 cu13x 出齊 → 由 §4 階梯自動降到 cu128。
- **3.13 wheel 缺口**：pyarrow / torchaudio / peft 在 3.13 上的相容性問題 → 降到 3.12。
- 兩條備援都由 `verify_env.py` 紅燈觸發，非人為臆測。

## 9. 實際安裝結果

- 日期：2026-05-29
- Python：3.12.13
- PyTorch：2.11.0+cu128（torchvision 0.26.0+cu128、torchaudio 2.11.0+cu128 已裝；cu128 有 Windows torchaudio wheel，故一併安裝）
- bitsandbytes：0.49.2
- unsloth：2026.5.8（unsloth-zoo 2026.5.4）
- 其他：trl 0.19.1、peft 0.19.1、transformers 5.5.0
- GPU：NVIDIA GeForce RTX 4060 Laptop GPU
- verify_env.py：exit 0，5 項全 ok（torch CUDA build、cuda device、bitsandbytes import、unsloth import、bitsandbytes 4-bit forward on GPU）
- 備註：依 §4 / §8 備援階梯，已從 cu132 降級到 cu128。原因：bitsandbytes 0.49.2 沒有 CUDA 13.2 的預編譯二進位（最高僅到 13.0），在 cu132 torch 上前四項檢查通過，但第 5 項 GPU 4-bit forward 觸發「CUDA VERSION MISMATCH（requested 13.2，無對應 libbitsandbytes_cuda132.dll）」。改用 cu128 torch 後 bitsandbytes 4-bit 實跑通過。另外安裝過程中 unsloth 與 `--reinstall bitsandbytes` 兩度把 torch 降為 CPU 版，皆已重新釘回 GPU build。Flash Attention 2 警告為無害（已自動改用 Xformers）。
