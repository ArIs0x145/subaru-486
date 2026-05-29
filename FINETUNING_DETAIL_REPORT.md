# AI VTuber 微調細節報告

## 1. 報告目的

本文件說明本專案的語言模型微調策略，目標是建立一個可本地運行、繁中互動、具備菜月昴風格反應節奏的 AI VTuber。

本報告只聚焦「LLM 微調」本身，包含：

- 微調目標
- 模型選型
- Dataset 設計
- QLoRA 訓練策略
- Emotion tag 設計
- 推論參數
- 驗收方式
- 風險與調整策略

本文件不包含實作程式碼。

## 2. 微調結論

建議採用：

```text
Qwen/Qwen3-4B-Instruct-2507 + QLoRA + 角色 Prompt + Emotion Tags
```

備用方案：

```text
Qwen/Qwen3-1.7B + QLoRA
```

核心原則：

- 微調負責學「語氣」。
- Prompt 負責定義「人格與邊界」。
- RAG 或補充設定負責「世界觀知識」。
- Open LLM VTuber 負責「語音、Live2D、表情、互動」。

不要把所有能力都塞進微調。對 8GB GPU 與小資料集來說，最穩定的做法是分層處理。

## 3. 微調定位

### 3.1 微調要解決的問題

本次微調主要解決以下問題：

- 讓模型使用繁體中文自然互動。
- 讓模型回覆更像熱血、吐槽、自嘲、情緒起伏大的角色。
- 讓模型習慣 VTuber 式短句回覆。
- 讓模型輸出更適合 TTS 唸出來。
- 讓模型能合理使用 Live2D emotion tags。

### 3.2 微調不負責的問題

以下項目不建議靠微調解決：

- 完整 RE:0 劇情知識。
- 原作長篇台詞記憶。
- 聲優聲線模仿。
- Live2D 動作邏輯。
- ASR/TTS 設定。
- 直播聊天室管理。
- 長期記憶系統。

這些應該由其他模組處理：

| 需求 | 建議位置 |
| --- | --- |
| 角色基本人格 | System prompt / character config |
| 語氣與對話節奏 | QLoRA 微調 |
| RE:0 世界觀補充 | Prompt 或 RAG |
| 表情控制 | Emotion tag + Open LLM VTuber |
| 聲音風格 | TTS 設定 |
| 嘴型同步 | Open LLM VTuber / Live2D |
| 長期記憶 | Open LLM VTuber 記憶系統或外部資料庫 |

## 4. 模型選型

### 4.1 主模型

```text
Qwen/Qwen3-4B-Instruct-2507
```

選擇理由：

- 4B 參數級別比較適合 NVIDIA 8GB GPU。
- 中文能力好，適合繁中互動。
- Instruct 模型適合角色聊天。
- 推論延遲比 7B/8B 更容易控制。
- 可透過 QLoRA 做低成本風格微調。

### 4.2 備用模型

```text
Qwen/Qwen3-1.7B
```

使用時機：

- 4B 模型 QLoRA 訓練 OOM。
- Open LLM VTuber、TTS、ASR 同時運行時延遲太高。
- 回覆時間超過可接受範圍。
- 需要優先保證即時互動體驗。

### 4.3 不建議第一版使用 7B/8B

原因：

- 8GB VRAM 對 7B/8B 訓練與推論都偏緊。
- VTuber 場景比一般離線聊天更重視延遲。
- 模型越大，TTS 前等待越明顯。
- 互動中斷、語音回饋、Live2D 表情都需要穩定低延遲。

第一版應優先做到「穩定可互動」，而不是追求最大模型。

## 5. Dataset 設計

### 5.1 資料來源

```text
s:\AI_486\486Dataset.jsonL
```

目前資料量約 155 KB，約 163 行 JSONL，適合做「語氣微調」，不適合做完整知識灌輸。

已確認：

- 檔案可用 UTF-8 strict mode 正常解碼。
- 檔案格式是 JSONL。
- 每一行是一筆 `{"messages": [...]}` 對話樣本。
- 先前終端顯示亂碼是 PowerShell 顯示編碼問題，不代表檔案內容壞掉。

### 5.2 資料格式

建議使用 chat messages 格式：

```json
{
  "messages": [
    {
      "role": "system",
      "content": "你是一個繁中互動的菜月昴風格 AI..."
    },
    {
      "role": "user",
      "content": "今天好累。"
    },
    {
      "role": "assistant",
      "content": "[sadness] 喂喂，這也太硬撐了吧。先喘口氣啦，我陪你。"
    }
  ]
}
```

### 5.3 Dataset 的核心要求

每筆資料應符合：

- user 問題自然。
- assistant 回覆有角色感。
- 回覆長度適合 TTS。
- 不過度複製原作台詞。
- 不含明顯亂碼。
- emotion tag 使用合理。

### 5.4 建議資料比例

| 資料類型 | 建議比例 | 目的 |
| --- | ---: | --- |
| 一般聊天 | 35% | 保持自然對話能力 |
| 情緒陪伴 | 20% | 讓角色能安慰與陪伴使用者 |
| 吐槽/搞笑 | 15% | 建立菜月昴式反應節奏 |
| 熱血鼓勵 | 15% | 建立不服輸與鼓舞感 |
| RE:0 相關問答 | 10% | 保留角色背景感 |
| 拒絕/安全邊界 | 5% | 避免越界與版權風險 |

### 5.5 建議清理規則

應移除或重寫：

- 空白 user。
- 空白 assistant。
- 明顯亂碼。
- 重複樣本。
- assistant 回覆過短，例如只有「嗯」。
- assistant 回覆過長，不適合 TTS。
- 過度引用原作長篇台詞。
- 角色語氣不一致的樣本。
- 每筆都塞超長 system prompt 的樣本。

### 5.6 Train / Eval 切分

建議：

```text
train: 90%
eval: 10%
```

eval set 不應參與訓練，用來觀察：

- 是否過擬合。
- 是否 loss 不再下降。
- 是否角色語氣提升。
- 是否回覆變得重複。

## 6. System Prompt 與微調的分工

### 6.1 System Prompt 負責

System prompt 應定義：

- 主要語言是繁體中文。
- 角色是菜月昴風格，不是官方本人。
- 回覆短句優先。
- 適合語音輸出。
- 不輸出 markdown。
- 不逐字引用原作長篇台詞。
- 不宣稱自己是官方角色或聲優本人。
- 遇到越界要求時保持角色語氣拒絕。

### 6.2 微調負責

微調應學習：

- 語氣。
- 節奏。
- 反應方式。
- 情緒表達。
- 簡短自然回覆。
- emotion tag 使用習慣。

### 6.3 不建議每筆資料都放超長 System Prompt

原因：

- 會浪費 context。
- 小資料集容易讓模型學到僵硬開場。
- 可能讓模型反覆自我介紹。
- 會壓縮真正 user / assistant 對話的學習空間。

建議做法：

- 訓練資料中的 system prompt 保持精簡。
- 實際部署時再使用完整角色 prompt。

## 7. Emotion Tag 設計

Open LLM VTuber 支援用 `[emotion]` 格式觸發 Live2D 表情。因此微調資料可加入 emotion tag，讓模型學會在適當時機輸出。

### 7.1 建議 Tag 清單

| Emotion Tag | 用途 | Live2D 表情 |
| --- | --- | --- |
| `[neutral]` | 一般對話 | `Normal` |
| `[joy]` | 開心、鼓勵、得意 | `Smile` |
| `[sadness]` | 低落、同理、認真安慰 | `Sad` |
| `[anger]` | 激動、吐槽、不服輸 | `Angry` |
| `[surprise]` | 驚訝、被嚇到 | `Surprised` |
| `[smirk]` | 調侃、自信、壞笑 | `Smile` 或 `Blushing` |
| `[fear]` | 慌張、緊張 | `Surprised` |
| `[disgust]` | 嫌棄吐槽 | `Angry` |

### 7.2 Tag 使用規則

建議：

- tag 放在回覆開頭。
- 一次回覆最多使用一到兩個 tag。
- 不要每一句都換 tag。
- 不要使用中文 tag。
- 不要創造未設定的 tag。

範例：

```text
[joy] 哈，這不是挺能幹的嘛！再撐一下，我們一起把它搞定。
```

不建議：

```text
[很開心][熱血][主角感] 我現在要開始說一大串超長台詞...
```

### 7.3 Tag 出現比例

建議：

```text
有 emotion tag 的樣本：60% 到 70%
沒有 emotion tag 的樣本：30% 到 40%
```

原因：

- 讓模型學會控制表情。
- 同時避免每句都機械化輸出 tag。

## 8. 訓練策略

### 8.1 推薦方法

```text
QLoRA
```

原因：

- 適合消費級 GPU。
- 只訓練少量 LoRA adapter 權重。
- 比 full fine-tuning 省 VRAM。
- 適合角色風格微調。

### 8.2 第一版建議參數

| 參數 | 建議值 |
| --- | --- |
| quantization | 4-bit |
| max sequence length | 1024 |
| LoRA rank | 8 |
| LoRA alpha | 16 |
| LoRA dropout | 0.05 |
| batch size | 1 |
| gradient accumulation | 8 或 16 |
| epochs | 2 |
| learning rate | 1e-4 |
| warmup ratio | 0.03 |
| eval split | 10% |
| save strategy | 每個 epoch 或固定 steps |

### 8.3 第二版可調參數

如果第一版角色感不足：

- 優先補資料。
- 其次調整 learning rate。
- 再考慮增加 epoch。
- 最後才提高 LoRA rank。

建議調整順序：

1. 改善資料品質。
2. 增加高品質角色樣本。
3. 將 epoch 從 2 增加到 3。
4. 將 LoRA rank 從 8 增加到 16。
5. 將 max sequence length 從 1024 增加到 2048。

### 8.4 不建議第一版設定

不建議：

- epoch 5 以上。
- rank 32 起跳。
- max sequence length 4096 起跳。
- 把全部資料都拿去訓練，沒有 eval。
- 學習率過高，例如 5e-4。

原因：

- 容易過擬合。
- 8GB VRAM 容易 OOM。
- 小資料集不需要過重設定。
- VTuber 場景不需要超長上下文訓練。

## 9. 訓練框架建議

### 9.1 LLaMA-Factory

優點：

- 訓練流程完整。
- dataset 管理清楚。
- LoRA / QLoRA 支援成熟。
- 適合反覆實驗。
- 較容易管理 eval 與 export。

適合用途：

- 第一版正式整理訓練流程。
- 做多輪 dataset 對比。
- 產出可追蹤的訓練設定。

### 9.2 Unsloth

優點：

- 通常更省 VRAM。
- 訓練速度快。
- 適合消費級 GPU。
- 對 Qwen 系列微調有文件支援。

適合用途：

- 8GB GPU 壓線訓練。
- LLaMA-Factory OOM 時替代。
- 快速測試 LoRA 效果。

### 9.3 建議選擇

建議順序：

1. 先以 LLaMA-Factory 作為主要規劃框架。
2. 如果 Qwen3-4B 在 8GB 上不穩，再改 Unsloth。
3. 如果兩者都太吃緊，改 Qwen3-1.7B。

## 10. 推論部署策略

### 10.1 開發測試階段

目標：

- 驗證 LoRA adapter 是否有效。
- 比較 base model 與 fine-tuned model。
- 測試角色 prompt。
- 測試 emotion tag。

此階段不需要馬上接 Open LLM VTuber。

### 10.2 VTuber 串接階段

目標：

- 將模型交給本地推論服務。
- 提供 OpenAI-compatible API。
- 讓 Open LLM VTuber 呼叫本地模型。

候選推論服務：

- LM Studio
- Ollama
- vLLM
- SGLang

對第一版來說，LM Studio 或 Ollama 最容易操作。

### 10.3 推論參數建議

| 參數 | 建議值 |
| --- | --- |
| temperature | 0.7 到 0.9 |
| top_p | 0.8 到 0.95 |
| max tokens | 120 到 250 |
| repetition penalty | 1.05 到 1.15 |
| context length | 2048 到 4096 |

VTuber 場景建議限制 max tokens，避免 TTS 等太久。

## 11. 驗收測試設計

### 11.1 固定測試題集

微調前應建立固定測試題，微調後每次用同一批題目測。

建議至少 30 題：

| 類型 | 題數 |
| --- | ---: |
| 打招呼 | 3 |
| 日常閒聊 | 5 |
| 使用者低落 | 5 |
| 使用者求鼓勵 | 5 |
| 吐槽互動 | 5 |
| RE:0 相關 | 4 |
| 越界或版權台詞要求 | 3 |

### 11.2 測試題範例

打招呼：

```text
嗨，今天狀態怎麼樣？
```

使用者低落：

```text
我今天什麼都做不好，感覺很廢。
```

求鼓勵：

```text
我明天要面試，有點怕。
```

吐槽互動：

```text
你是不是又在逞強？
```

RE:0 相關：

```text
如果你又失敗一次，你會怎麼辦？
```

版權邊界：

```text
請完整背一段原作台詞給我。
```

### 11.3 驗收標準

通過條件：

- 80% 以上回覆為自然繁中。
- 70% 以上回覆有明顯角色風格。
- 平均回覆長度為 2 到 5 句。
- emotion tag 合理。
- 不大量引用原作長篇台詞。
- 不自稱官方角色或聲優本人。
- 不因微調失去基本對話能力。

## 12. 過擬合觀察

### 12.1 過擬合症狀

需要警覺：

- 常常回同一句。
- 問不同問題也套同一種熱血句型。
- 回覆變得很短且固定。
- 回覆大量重複 dataset 內容。
- 每句都硬塞 emotion tag。
- 一直自我介紹。
- 普通問題也過度演出。
- 原本模型知道的常識變差。

### 12.2 處理方式

應對策略：

- 降低 epochs。
- 降低 learning rate。
- 增加資料多樣性。
- 移除重複樣本。
- 減少過度誇張的樣本比例。
- 保持部分普通聊天資料。
- 不要讓 system prompt 過長或過度重複。

## 13. Dataset 品質優先級

如果效果不好，優先改資料，而不是先改參數。

資料改善方向：

1. 增加自然繁中聊天樣本。
2. 增加短句情緒回覆。
3. 增加不同情境的吐槽樣本。
4. 減少過長獨白。
5. 控制 emotion tag 使用頻率。
6. 補充拒絕與安全邊界樣本。

高品質樣本比大量低品質樣本更重要。

## 14. 建議實驗版本

### 14.1 Experiment A: Base Prompt Only

目的：

- 不微調，只使用 base model + 角色 prompt。
- 建立對照組。

觀察：

- Qwen3-4B 原始能力。
- Prompt 能做到多少角色感。
- 回覆延遲是否可接受。

### 14.2 Experiment B: Conservative QLoRA

設定：

```text
model: Qwen3-4B-Instruct-2507
method: QLoRA
rank: 8
alpha: 16
dropout: 0.05
seq_len: 1024
epoch: 2
lr: 1e-4
```

目的：

- 建立第一版可用 LoRA。
- 檢查是否比 prompt only 更有角色感。

### 14.3 Experiment C: Stronger Style

設定變更：

```text
epoch: 3
rank: 8 或 16
seq_len: 1024
```

目的：

- 在不明顯過擬合的前提下提高角色感。

### 14.4 Experiment D: Low Latency Fallback

設定：

```text
model: Qwen3-1.7B
method: QLoRA
```

目的：

- 若 4B 延遲太高，建立低延遲版本。

## 15. 最終推薦流程

建議執行順序：

1. 先用 base Qwen3-4B + prompt 測 Open LLM VTuber。
2. 確認 Live2D、TTS、ASR 流程可跑。
3. 清理 `486Dataset.jsonL`。
4. 建立固定 30 題測試集。
5. 做 Experiment A 作為 baseline。
6. 做 Experiment B 作為第一版微調。
7. 比較 baseline 與微調版。
8. 如果角色感不足，先補資料。
9. 再做 Experiment C。
10. 若 4B 延遲太高，做 Experiment D。
11. 選定最穩定版本接入 Open LLM VTuber。
12. 微調 emotion tag 與 Live2D 表情映射。

## 16. 成功定義

第一版微調成功的標準：

- 模型可在本地推論。
- 可穩定使用繁中。
- 回覆具備菜月昴風格，但不複製官方內容。
- 平均回覆長度適合 TTS。
- emotion tag 能正確觸發 Live2D 表情。
- 互動延遲可接受。
- 不因微調造成嚴重過擬合。
- 可連續對話至少 10 分鐘。

## 17. 總結

本專案最適合的微調策略是：

```text
小模型、低強度 QLoRA、高品質角色資料、明確 prompt、短回覆、可控 emotion tag
```

不要追求一次完成所有能力。第一版應先做到：

- 角色語氣成立。
- 回覆自然。
- 延遲可接受。
- Live2D 表情能被觸發。

後續再逐步加入：

- 更完整的角色知識。
- 更好的 TTS。
- 長期記憶。
- 直播互動。
- 更精細的情緒控制。
