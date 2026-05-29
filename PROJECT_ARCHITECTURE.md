# AI VTuber Project Architecture

## 1. 專案目標

本專案目標是規劃一個可在本機運行的 AI VTuber 系統，核心方向為：

- 以繁體中文為主要互動語言。
- 使用可本地推論、可微調的小型語言模型。
- 透過 Open LLM VTuber 串接 LLM、ASR、TTS 與 Live2D avatar。
- 使用角色感 prompt 與小規模微調，塑造「菜月昴風格」的互動語氣。
- 第一版專注在完整流程可運作，而不是追求最大模型或最複雜功能。

本文件只描述專案流程與架構，不包含實作程式碼。

## 2. 已知決策

| 項目 | 決策 |
| --- | --- |
| 主要語言 | 繁體中文 |
| 本機硬體 | NVIDIA 8GB GPU |
| 主模型 | `Qwen/Qwen3-4B-Instruct-2507` |
| 備用模型 | `Qwen/Qwen3-1.7B` |
| 微調方式 | QLoRA |
| VTuber 框架 | Open LLM VTuber |
| 第一版 Avatar | `C:\Users\chenb\Downloads\chitose\runtime` |
| 暫不使用 | `Subaru.vrm` |
| TTS 方針 | 角色感 TTS，不做未授權聲線克隆 |
| Dataset | `s:\AI_486\486Dataset.jsonL` |

`Subaru.vrm` 是 3D VRM 格式，不適用 Open LLM VTuber 的 Live2D 文件流程。第一版採用 `chitose` Live2D runtime，是較穩定且符合文件的路線。

## 3. 整體架構

系統分為五個主要層級：

1. **資料層**
   - 負責整理 `486Dataset.jsonL`。
   - 用於學習角色語氣、對話節奏與回應風格。
   - 不作為完整 RE:0 世界觀知識庫。

2. **模型層**
   - 使用 Qwen3 4B 作為主模型。
   - 透過 QLoRA 進行低成本微調。
   - 推論時使用本地 OpenAI-compatible API。

3. **角色層**
   - 使用 system prompt / character config 定義角色邊界。
   - 微調負責語氣慣性。
   - prompt 負責人格規則、語言風格、安全限制與輸出格式。

4. **VTuber 中介層**
   - Open LLM VTuber 負責整合 LLM、ASR、TTS、Live2D。
   - 本地 LLM 透過 OpenAI-compatible endpoint 被呼叫。
   - Live2D avatar 透過 `model_dict.json` 與角色配置綁定。

5. **互動層**
   - 使用者透過語音或文字輸入。
   - AI 回覆文字後交給 TTS。
   - TTS 音訊驅動嘴型。
   - 情緒標籤驅動 Live2D 表情。

## 4. 本地模型選型

### 4.1 主模型：Qwen3-4B-Instruct-2507

選擇原因：

- 4B 參數級別適合 8GB GPU 做保守 QLoRA 微調。
- 對繁中、中文與日文混合語境支援較好。
- Instruct 模型適合對話型角色。
- 推論速度比 7B/8B 更容易達到 VTuber 即時互動需求。

預期用途：

- 角色對話。
- 繁中互動。
- 短句語音回覆。
- 情緒明確的 VTuber 式反應。

### 4.2 備用模型：Qwen3-1.7B

使用時機：

- 4B 微調時 VRAM 不足。
- 4B 推論延遲過高。
- TTS/ASR 同時運行後 GPU 壓力太大。
- 需要優先保證即時互動體驗。

### 4.3 不建議第一版使用 7B/8B

原因：

- NVIDIA 8GB 對 7B/8B 微調與推論都較吃緊。
- VTuber 場景比離線聊天更重視延遲。
- 模型太大可能導致回覆慢、語音等待久、互動斷裂。

第一版應優先追求穩定、低延遲、可反覆測試。

## 5. Dataset 處理流程

資料來源為：

```text
s:\AI_486\486Dataset.jsonL
```

資料處理目標：

- 使用 UTF-8 讀取檔案。
- 確認 JSONL 結構可解析。
- 確認每筆資料符合 chat messages 格式。
- 移除亂碼、空白、重複與不適合訓練的資料。
- 將資料轉換成訓練框架可接受的格式。

目前已確認：

- 檔案可用 UTF-8 strict mode 正常解碼。
- 檔案為 JSONL。
- 總行數約 163 行。
- 每行格式為 `{"messages": [...]}`。
- 先前在 PowerShell 預設輸出中看到的亂碼是終端顯示編碼問題，不代表檔案內容壞掉。

### 5.1 驗證項目

需要確認：

- 檔案是否以 UTF-8 讀取。
- 每一行是否都是合法 JSON。
- 每筆資料是否包含 `messages`。
- `messages` 內是否包含合理的 `system`、`user`、`assistant`。
- 內容是否為繁中或可接受的中日混合。
- 是否存在實際 mojibake，而不是終端顯示問題。
- assistant 回覆是否過短、過長或無意義。

### 5.2 清理規則

建議移除：

- 空 user 或空 assistant。
- 明顯亂碼。
- 大量重複樣本。
- 超長 system prompt。
- 直接複製原作長篇台詞的資料。
- 不符合目標人格的資料。

### 5.3 切分方式

建議：

- 90% 作為 train set。
- 10% 作為 eval set。

因資料量約 155 KB，定位應為「風格微調資料」，不是知識灌輸資料。

## 6. 微調流程

### 6.1 微調目標

微調只負責讓模型更穩定地學到：

- 繁中對話習慣。
- 熱血、吐槽、自嘲的反應節奏。
- VTuber 風格短回覆。
- 情緒起伏較明顯的角色語氣。

不建議把微調當作：

- 完整劇情記憶。
- 原作台詞複製。
- 聲音訓練。
- Live2D 動作控制邏輯。

### 6.2 建議訓練策略

使用 QLoRA：

- 4-bit quantization。
- LoRA rank 從 8 或 16 開始。
- 小 batch size。
- 使用 gradient accumulation。
- 訓練 1 到 3 epochs 起步。
- 以 eval loss 與人工測試共同判斷，不只看 loss。

### 6.3 避免過擬合

資料量不大，因此應避免：

- 訓練 epoch 過多。
- 讓模型只會重複 dataset 句子。
- 讓模型失去基本對話能力。
- 讓模型過度模仿特定台詞。

若回覆開始變得僵硬、重複、固定套路，應降低訓練強度。

## 7. 角色 Prompt 設計

角色 prompt 應放在 Open LLM VTuber 的角色設定中，而不是完全依賴微調。

### 7.1 角色定位

建議定位為：

- 「菜月昴風格」AI 角色。
- 使用繁中互動。
- 情緒直接、熱血、容易吐槽。
- 會自嘲但不消極到底。
- 對使用者友善，像陪伴型 VTuber。

### 7.2 輸出風格

建議規則：

- 回覆以短句為主。
- 適合被 TTS 唸出來。
- 不使用 markdown。
- 不輸出太長條列。
- 不長篇解釋架構或設定。
- 可以穿插少量日文感嘆詞，但不要影響繁中理解。

### 7.3 邊界與風險

角色設定應明確：

- 不宣稱自己是官方角色。
- 不宣稱自己是聲優本人。
- 不逐字複製原作長篇台詞。
- 不輸出侵犯版權的大段文本。
- 遇到越界要求時，保持角色語氣但拒絕。

## 8. Open LLM VTuber 串接流程

### 8.1 LLM 串接

Open LLM VTuber 透過 OpenAI-compatible API 呼叫本地模型。

本地推論可使用：

- LM Studio
- Ollama
- vLLM
- 其他支援 OpenAI-compatible API 的推論服務

設定重點：

- `base_url` 必須指向本地 LLM endpoint。
- `model name` 必須與推論服務中的模型名稱一致。
- API key 若本地服務不需要，可使用佔位值。
- context length 不宜過大，以降低延遲與 VRAM 壓力。

### 8.2 建議階段

第一階段：

- 只測文字輸入與文字輸出。
- 確認模型人格與回覆速度。

第二階段：

- 加入 ASR。
- 測語音輸入穩定度。

第三階段：

- 加入 TTS。
- 測完整語音對話。

第四階段：

- 加入 Live2D 表情與 motion。
- 測 VTuber 體驗。

第五階段：

- 視需要加入直播聊天室、OBS、長期記憶或主動發話。

## 9. Live2D Avatar 流程

第一版 Live2D asset 使用：

```text
C:\Users\chenb\Downloads\chitose\runtime
```

已確認包含：

- `chitose.model3.json`
- `chitose.moc3`
- `chitose.physics3.json`
- `chitose.pose3.json`
- `chitose.cdi3.json`
- texture
- expressions
- motions

### 9.1 表情資源

現有 expressions：

- `Angry.exp3.json`
- `Blushing.exp3.json`
- `f01.exp3.json`
- `Normal.exp3.json`
- `Sad.exp3.json`
- `Smile.exp3.json`
- `Surprised.exp3.json`

### 9.2 動作資源

現有 motions：

- `chitose_handwave.motion3.json`
- `chitose_idle.motion3.json`
- `chitose_kime01.motion3.json`
- `chitose_kime02.motion3.json`

### 9.3 Emotion Mapping

建議對應：

| AI emotion | Live2D expression |
| --- | --- |
| neutral | `Normal` |
| happy | `Smile` |
| sad | `Sad` |
| angry | `Angry` |
| surprised | `Surprised` |
| embarrassed | `Blushing` |

### 9.4 Motion Mapping

建議對應：

| 場景 | Motion |
| --- | --- |
| 待機 | `chitose_idle.motion3.json` |
| 打招呼 | `chitose_handwave.motion3.json` |
| 點擊反應 | `chitose_kime01.motion3.json` |
| 強調反應 | `chitose_kime02.motion3.json` |

### 9.5 Open LLM VTuber 設定重點

需要在 Open LLM VTuber 的 Live2D 設定中完成：

- 將模型放入 `live2d-models`。
- 在 `model_dict.json` 註冊模型。
- 設定模型名稱，例如 `chitose`。
- 在角色配置中指定 `live2d_model_name` 為相同名稱。

`live2d_model_name` 必須與 `model_dict.json` 中的 `name` 完全一致。

## 10. TTS / ASR 流程

### 10.1 ASR

建議候選：

- Faster-Whisper base 或 small。
- FunASR。

選擇標準：

- 中文辨識準確。
- 延遲低。
- 本地可跑。
- 不過度佔用 GPU。

### 10.2 TTS

第一版目標是角色感，而不是聲線複製。

建議方向：

- 使用支援中文或中日混合的 TTS。
- 調整語速、停頓、音高與情緒。
- 讓 LLM 回覆短一點，避免 TTS 唸太久。

不建議第一版做：

- 未授權聲優聲線克隆。
- 大量音訊資料訓練。
- 過重的 TTS 模型，導致整體延遲升高。

### 10.3 LLM 回覆格式

為了 TTS 體驗，LLM 應：

- 避免 markdown。
- 避免表格。
- 避免過長句子。
- 避免一次講太多。
- 在情緒強烈時仍保持可唸性。

## 11. 測試與驗收標準

### 11.1 Dataset 驗收

通過條件：

- JSON 可完整解析。
- 至少抽樣 30 筆無明顯亂碼。
- user/assistant 對話合理。
- 不存在大量重複樣本。
- train/eval 已清楚切分。

### 11.2 模型驗收

通過條件：

- 可使用繁中穩定回覆。
- 角色語氣明顯，但不只會複讀資料集。
- 回覆長度適合 TTS。
- 不會大量輸出原作長台詞。
- 不會自稱官方角色或聲優本人。
- 固定 20 到 50 題測試集表現比 base model 更有角色感。

### 11.3 Open LLM VTuber 驗收

通過條件：

- 本地 LLM endpoint 可連線。
- Open LLM VTuber 可完成文字對話。
- ASR 可辨識使用者語音。
- TTS 可唸出 AI 回覆。
- Live2D 可載入並顯示。
- 表情可依 emotion 切換。
- 嘴型可隨語音開合。

### 11.4 體驗驗收

通過條件：

- 連續互動 10 分鐘不崩潰。
- 單輪對話延遲可接受。
- AI 不會頻繁打斷自己。
- 表情不亂跳。
- 聲音不過慢、不過長。
- 使用者感覺是在和角色互動，而不是一般客服聊天機器人。

## 12. 風險與注意事項

### 12.1 硬體風險

NVIDIA 8GB 對本地 AI VTuber 是可行但偏緊的配置。

主要風險：

- 4B 微調時 OOM。
- TTS/ASR/LLM 同時運行導致延遲高。
- context length 太大造成 VRAM 不足。

應對策略：

- 降低 batch size。
- 降低 LoRA rank。
- 降低 context length。
- 改用 Qwen3-1.7B。
- 將 ASR 或 TTS 改用 CPU 或較小模型。

### 12.2 資料風險

資料量偏小，可能導致：

- 過擬合。
- 回覆重複。
- 角色語氣單一。
- 知識不足。

應對策略：

- 微調只學風格。
- 劇情知識放 prompt 或 RAG。
- 建立固定測試題。
- 控制訓練 epoch。

### 12.3 版權與角色風險

本專案應避免：

- 宣稱官方授權。
- 複製官方長篇台詞。
- 使用未授權聲優音源做聲音克隆。
- 商業使用未確認授權的素材。

建議定位為：

- 私人學習用途。
- 菜月昴風格 AI。
- 非官方二創實驗。

### 12.4 Live2D 授權風險

`chitose` 應保留原始 Readme 與授權資訊。

正式使用前需確認：

- 是否允許個人使用。
- 是否允許直播使用。
- 是否允許商業使用。
- 是否允許修改與再發布。

## 13. 推薦里程碑

### Milestone 1: 規劃完成

成果：

- 架構文件完成。
- 模型、資料、VTuber、Live2D、TTS/ASR 路線確定。

### Milestone 2: 資料可訓練

成果：

- Dataset 可解析。
- 資料清理完成。
- train/eval 切分完成。
- 測試題集完成。

### Milestone 3: 模型可用

成果：

- QLoRA 微調完成。
- 本地推論可啟動。
- 角色語氣初步成立。

### Milestone 4: VTuber 可互動

成果：

- Open LLM VTuber 可連本地 LLM。
- Live2D 可顯示。
- TTS/ASR 可完成一輪語音對話。

### Milestone 5: 體驗調整

成果：

- 延遲降低。
- 回覆長度穩定。
- 表情對應自然。
- 角色 prompt 與微調效果平衡。

## 14. 最終交付定義

第一版完成時，應達成：

- 使用者可用繁中語音或文字與 AI 對話。
- AI 回覆具有菜月昴風格，但不侵犯官方內容。
- 本地模型可穩定推論。
- Open LLM VTuber 可驅動 Live2D avatar。
- TTS 可輸出角色感語音。
- 系統可連續互動至少 10 分鐘。
- 架構仍保留後續擴充空間，例如直播聊天室、記憶系統、RAG 或更換 avatar。
