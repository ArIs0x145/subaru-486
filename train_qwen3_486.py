"""QLoRA fine-tune Qwen3-4B-Instruct-2507 on the 486 dataset.

trl / unsloth APIs evolve — if SFTConfig field names differ in your installed
version, follow the official example for that version.
"""
from pathlib import Path

from datasets import load_dataset
from unsloth import FastLanguageModel
from unsloth.chat_templates import get_chat_template
from trl import SFTTrainer, SFTConfig

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


def main() -> None:
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=MODEL_NAME,
        max_seq_length=MAX_SEQ_LEN,
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

    train_ds, eval_ds = build_datasets(DATA_DIR, tokenizer)

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
        ),
    )

    trainer.train()
    model.save_pretrained(OUTPUT_DIR)
    tokenizer.save_pretrained(OUTPUT_DIR)
    print("LoRA saved to", OUTPUT_DIR)


if __name__ == "__main__":
    main()
