"""Merge LoRA adapter back into Qwen3 base and save as 16-bit HF model.

Output is consumed by llama.cpp/convert_hf_to_gguf.py downstream.
"""
from unsloth import FastLanguageModel

LORA_DIR = r"D:\AI_486\train_outputs\lora"
MERGED_DIR = r"D:\AI_486\train_outputs\merged"


def main() -> None:
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=LORA_DIR,
        max_seq_length=1024,
        load_in_4bit=True,  # 8GB GPU: load 4-bit (~3GB), unsloth dequantizes to 16-bit on merge
        dtype=None,
    )
    model.save_pretrained_merged(MERGED_DIR, tokenizer, save_method="merged_16bit")
    print("merged ->", MERGED_DIR)


if __name__ == "__main__":
    main()
