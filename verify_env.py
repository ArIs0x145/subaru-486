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
