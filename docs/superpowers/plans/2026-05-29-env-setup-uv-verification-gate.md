# 環境建置 + 驗證閘門 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 用 uv 在本機（NVIDIA 8GB、CUDA driver 13.3）建好可跑 Unsloth QLoRA 的 Python 環境，並以一支可重複執行的 `verify_env.py` 證明環境就緒。

**Architecture:** 「最新優先、失敗才降」的安裝階梯（Python 3.13→3.12、torch cu13x→cu128），由 `verify_env.py` 的紅/綠結果驅動降級決策。`verify_env.py` 先寫（紅燈），安裝把它變綠。

**Tech Stack:** uv（已裝 0.10.8）、Python（uv managed）、PyTorch CUDA wheel、Unsloth、bitsandbytes、trl/peft/accelerate/datasets。

對應 spec：`docs/superpowers/specs/2026-05-29-env-setup-uv-verification-gate-design.md`

---

## File Structure

- Create: `D:\AI_486\verify_env.py` —— 環境驗證腳本（唯一綠燈判準；進版控）
- Modify: `D:\AI_486\docs\superpowers\specs\2026-05-29-env-setup-uv-verification-gate-design.md` —— 完成後追加「## 9. 實際安裝結果」
- 不進版控（已被 .gitignore 排除）：`D:\AI_486\.venv\`、`D:\AI_486\hf_cache\`

所有指令在 `D:\AI_486` 下、且 venv 已 activate 的 PowerShell 執行（除非另註明）。

---

### Task 1: 寫驗證腳本（紅燈）

**Files:**
- Create: `D:\AI_486\verify_env.py`

- [ ] **Step 1: 寫 `verify_env.py`**

```python
"""環境驗證閘門：證明本機能跑 Unsloth QLoRA。全過 exit 0，任一失敗 exit 1。"""
import sys


def fail(msg: str) -> None:
    print(f"[FAIL] {msg}")
    sys.exit(1)


# 1. torch 是 CUDA build
try:
    import torch
except Exception as e:  # noqa: BLE001
    fail(f"import torch: {e}")
print(f"[ok] torch {torch.__version__}")
if "+cu" not in torch.__version__:
    fail(f"torch 不是 CUDA build（疑似誤裝 CPU 版）: {torch.__version__}")

# 2. CUDA 可用
if not torch.cuda.is_available():
    fail("torch.cuda.is_available() 為 False")
print(f"[ok] cuda device: {torch.cuda.get_device_name(0)}")

# 3. bitsandbytes 可 import
try:
    import bitsandbytes as bnb
except Exception as e:  # noqa: BLE001
    fail(f"import bitsandbytes: {e}")
print(f"[ok] bitsandbytes {bnb.__version__}")

# 4. unsloth 可 import
try:
    from unsloth import FastLanguageModel  # noqa: F401
except Exception as e:  # noqa: BLE001
    fail(f"import unsloth: {e}")
print("[ok] unsloth import")

# 5. GPU 4-bit 實跑（最硬的證明）
try:
    linear = bnb.nn.Linear4bit(
        64, 64, bias=False, compute_dtype=torch.float16
    ).cuda()
    x = torch.randn(2, 64, dtype=torch.float16, device="cuda")
    y = linear(x)
    assert y.shape == (2, 64), f"非預期輸出形狀 {y.shape}"
except Exception as e:  # noqa: BLE001
    fail(f"GPU 4-bit forward: {e}")
print("[ok] bitsandbytes 4-bit forward on GPU")

print("\nENV OK")
sys.exit(0)
```

- [ ] **Step 2: 跑它，確認紅燈**

此時尚未建 venv／裝 torch。用系統 python 直接跑以確認測試本身會失敗：

Run: `python D:\AI_486\verify_env.py`
Expected: 印出 `[FAIL] import torch: ...`（或系統若剛好有 torch，則於某一項失敗），exit code 非 0。重點是「測試會因環境未就緒而紅」。

- [ ] **Step 3: Commit 測試腳本**

```powershell
git add verify_env.py
git commit -m "test: add verify_env.py environment gate (red)"
```

---

### Task 2: 建 venv 並裝 GPU PyTorch（最新優先）

**Files:** 無程式碼變更（環境操作）。

- [ ] **Step 1: 建 venv（先試 Python 3.13）**

```powershell
uv venv --python 3.13 .venv
.\.venv\Scripts\Activate.ps1
python -V
```
Expected: `Python 3.13.x`。
**降級規則：** 若 uv 取不到 3.13 或後續 torch 無 cp313 wheel → 刪 `.venv` 改 `uv venv --python 3.12 .venv` 重來。

- [ ] **Step 2: 設定 HF 快取到 D:（避免塞 C:）**

```powershell
$env:HF_HOME = "D:\AI_486\hf_cache"
[System.Environment]::SetEnvironmentVariable("HF_HOME", "D:\AI_486\hf_cache", "User")
```

- [ ] **Step 3: 裝 PyTorch（先試 cu13x）**

```powershell
uv pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu130
```
Expected: 安裝成功，無「No matching distribution」。
**降級規則：** 若報找不到 wheel（cu130 對該 Python 版本無 wheel）→ 改 `--index-url https://download.pytorch.org/whl/cu128` 重裝。

- [ ] **Step 4: 跑 verify_env 的前兩項（torch + cuda）**

Run: `python D:\AI_486\verify_env.py`
Expected: 通過 `[ok] torch ...` 與 `[ok] cuda device: ...`，在 `import bitsandbytes` 處 `[FAIL]`（還沒裝）。
**判定：** 若停在 `cuda.is_available() 為 False` → 此 torch/cuda 組合不可用，照 Step 3 降級規則改 cu128（或 Task 2 Step 1 降 Python）後重跑。

- [ ] **Step 5: Commit 進度筆記（暫記當前嘗試的組合）**

```powershell
git commit --allow-empty -m "chore: venv + torch installed, cuda verified"
```

---

### Task 3: 裝 Unsloth 與相依，處理 torch 被降版陷阱（綠燈）

**Files:** 無程式碼變更（環境操作）。

- [ ] **Step 1: 裝 unsloth 與相依**

```powershell
uv pip install unsloth
uv pip install datasets "trl<0.20.0" peft accelerate bitsandbytes
```
Expected: 安裝成功。

- [ ] **Step 2: 重釘 GPU torch（Runbook §3.4 陷阱）**

裝完 unsloth 後 torch 可能被降回 CPU 版，強制重裝（channel 用 Task 2 Step 3 最終選定的那個）：

```powershell
uv pip install --reinstall torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu130
```
（若 Task 2 最終用的是 cu128，這裡也改 cu128。）
Expected: uv 快取命中、秒裝。

- [ ] **Step 3: 跑完整 verify_env，目標綠燈**

Run: `python D:\AI_486\verify_env.py`
Expected: 依序印出 5 個 `[ok]`，最後 `ENV OK`，exit code 0。
**若紅：**
- 卡在 `import unsloth` → 多半是 torch 又被降版，回 Step 2 重釘。
- 卡在 `GPU 4-bit forward` → bitsandbytes 對當前 cuda channel 的 Windows wheel 不相容，降級 torch 到 cu128（Task 2 Step 3）後，回 Step 1/2 重裝重跑。
- 卡在 import 層且降 cu128 仍不過 → 回 Task 2 Step 1 把 Python 降 3.12，整段重來。

- [ ] **Step 4: 記錄成功組合到 spec §9**

讀出實際版本：

```powershell
python -c "import torch, bitsandbytes, sys; print('python', sys.version.split()[0]); print('torch', torch.__version__); print('bnb', bitsandbytes.__version__)"
python -c "import unsloth, importlib.metadata as m; print('unsloth', m.version('unsloth'))"
```

把輸出填入 `docs\superpowers\specs\2026-05-29-env-setup-uv-verification-gate-design.md` 新增的一節（用實際數值取代範例）：

```markdown
## 9. 實際安裝結果

- 日期：2026-05-29
- Python：3.13.x（或實際降到的版本）
- PyTorch：2.x.x+cu130（或實際 channel）
- bitsandbytes：0.xx.x
- unsloth：20xx.x.x
- GPU：NVIDIA GeForce RTX xxxx
- verify_env.py：exit 0，5 項全 ok
```

- [ ] **Step 5: Commit 成功結果**

```powershell
git add docs/superpowers/specs/2026-05-29-env-setup-uv-verification-gate-design.md
git commit -m "docs: record working env combo; verify_env.py green"
```

---

## Self-Review

**1. Spec coverage：**
- spec §3 驗證腳本 5 項 → Task 1 Step 1 全數實作。✅
- spec §4 安裝階梯（Python 3.13→3.12、cu13x→cu128）→ Task 2 Step 1/3 + Task 3 Step 3 的降級規則。✅
- spec §5 unsloth 降 torch 陷阱 → Task 3 Step 2。✅
- spec §6 產出物（verify_env.py 進版控、版本筆記）→ Task 1 Step 3、Task 3 Step 4/5。✅
- spec §7 DoD（exit 0 + 4-bit 實跑 + 記錄組合）→ Task 3 Step 3/4。✅
- spec §8 兩條備援由紅燈觸發 → Task 2/3 各 Step 的「降級規則/若紅」。✅

**2. Placeholder scan：** verify_env.py 為完整可跑程式；spec §9 範本標明「用實際數值取代」，非交付物中的 placeholder。無 TODO/TBD。✅

**3. Type consistency：** 全程使用 `verify_env.py` 同一檔名與同一組指令；cuda channel 在 Task 2 選定後 Task 3 沿用同一個。✅
