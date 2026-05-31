"""QLoRA fine-tune Qwen3-4B-Instruct-2507 on the 486 dataset.

trl / unsloth APIs evolve — if SFTConfig field names differ in your installed
version, follow the official example for that version.
"""
import argparse
import sys
from pathlib import Path

from datasets import load_dataset
from unsloth import FastLanguageModel
from unsloth.chat_templates import get_chat_template
from trl import SFTTrainer, SFTConfig

# Windows console may be cp950; force UTF-8 so unsloth's emoji prints don't crash.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

MODEL_NAME = "unsloth/Qwen3-4B-Instruct-2507-bnb-4bit"
MAX_SEQ_LEN = 1024
OUTPUT_DIR = r"D:\AI_486\train_outputs\lora"
DATA_DIR = Path(r"D:\AI_486\data")


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
