"""Rewrite per-row system prompt to a short one before training.

Source: converted_dataset (with full Subaru persona in every system message)
Output: data/ (with a single short system; long persona moves to deploy-time prompt)
"""
import json
from pathlib import Path

SHORT_SYSTEM = "你是繁體中文 AI VTuber，回應簡短自然，必要時於開頭使用 [emotion] 標籤。"


def rewrite(src: Path, dst: Path) -> int:
    count = 0
    with open(src, "r", encoding="utf-8") as f_in, open(dst, "w", encoding="utf-8") as f_out:
        for line in f_in:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            for m in obj["messages"]:
                if m["role"] == "system":
                    m["content"] = SHORT_SYSTEM
            f_out.write(json.dumps(obj, ensure_ascii=False) + "\n")
            count += 1
    return count


def main() -> None:
    base = Path(r"D:\AI_486\converted_dataset")
    out = Path(r"D:\AI_486\data")
    out.mkdir(parents=True, exist_ok=True)

    train_count = rewrite(
        base / "486_messages_live2d_emotions_train.jsonl",
        out / "train.jsonl",
    )
    eval_count = rewrite(
        base / "486_messages_live2d_emotions_eval.jsonl",
        out / "eval.jsonl",
    )
    print(f"train: {train_count}")
    print(f"eval:  {eval_count}")
    print(f"out:   {out}")


if __name__ == "__main__":
    main()
