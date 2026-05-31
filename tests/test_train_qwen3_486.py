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


def test_formatted_text_has_template_markers():
    tok = _tokenizer()
    train_ds, _ = t.build_datasets(DATA_DIR, tok)
    sample = train_ds[0]["text"]
    assert "<|im_start|>" in sample
    assert "[" in sample  # assistant 回覆帶 [emotion] 標籤
