# Open LLM VTuber 串接 — TTS 階段（edge-tts 繁中男聲）（第 ⑦ 步之三）

日期：2026-06-01
對應 Runbook：§8.6（TTS：edge-tts）、§9.3（TTS 驗收）、§9.4（Live2D 表情驗收）
對應管線步驟：第 ⑦ 步「VTuber 串接」的 TTS 階段（原階段四，提前做；因表情依賴音頻播放）

## 1. 目標與範圍

讓菜月昴用繁體中文語音「開口說話」（edge-tts），並驗證 Live2D 表情隨語音播放切換 —— 一併完成上輪（階段二）卡住的表情驗收。

**範圍內：**
- 改 `app/conf.yaml`：`edge_tts.voice` → `zh-TW-YunJheNeural`（繁中男聲）。
- 確認該 voice 可用（edge-tts 線上合成測試）。
- 重啟 server。
- 瀏覽器驗收：打字 → 聽到繁中語音 + mao_pro 表情隨語音切換。

**範圍外（後續）：**
- ASR（faster-whisper，語音輸入，下一階段）。
- chitose 相容性（需 Cubism 3+ 版本，暫用 mao_pro）。
- TTS 聲線升級（GPT-SoVITS/CosyVoice，第二版）。

## 2. 現況（已確認）

- 階段一完成：LLM 文字對話繁中正常。
- 階段二：emotion 後端管線已驗通（server 送 `expressions:[3]`、前端 console 收到）；但表情**綁在音頻播放**，無 TTS 不觸發。avatar 用 mao_pro（Cubism 3+，相容）。
- `conf.yaml` `tts_config.tts_model` 已是 `'edge_tts'`。
- `conf.yaml` `edge_tts.voice` 目前為 `zh-CN-XiaoxiaoNeural`（簡中女聲）→ 需改繁中。
- edge-tts 為微軟線上服務，免費、不耗本地 GPU、需網路。

## 3. 使用者決策

| 項目 | 決策 |
| --- | --- |
| TTS 引擎 | edge-tts（已是預設） |
| 聲線 | `zh-TW-YunJheNeural`（台灣繁中男聲，貼近菜月昴原作男性角色） |
| 驗收深度 | 聽到繁中語音 + 表情隨語音切換 |

## 4. 架構：改 voice → 確認可用 → 重啟 → 驗收

| 步驟 | 動作 | 驗證 |
| --- | --- | --- |
| 1 | `conf.yaml` `edge_tts.voice: 'zh-TW-YunJheNeural'` | conf.yaml 該行為目標 voice |
| 2 | edge-tts 合成測試（app venv 跑一句，存 mp3） | 產出非空 mp3、無錯誤（確認 voice 名稱有效、網路通） |
| 3 | 重啟 `run_server.py` | log `Uvicorn running`、`Initializing TTS: edge_tts`、無錯誤 |
| 4 | 瀏覽器打字對話（最硬證明） | 聽到繁中男聲語音；mao_pro 表情隨語音切換；回覆繁中、菜月昴風 |

## 5. 驗證策略（TDD 精神）

無新 Python 邏輯。「測試」分兩層：
1. **離線**（步驟 2）：用 edge-tts 直接合成一句繁中，確認 voice 有效、能出非空音檔 —— 在進瀏覽器前先排除 voice 名稱/網路問題。
2. **端到端**（步驟 4）：瀏覽器實際對話，聽到語音 + 看到表情切換。這也驗證上輪「表情依賴 TTS」的推論。

通過條件（Definition of Done）：
- `conf.yaml` `edge_tts.voice` 為 `zh-TW-YunJheNeural`。
- edge-tts 合成測試產出非空 mp3。
- server 重啟成功、TTS 初始化為 edge_tts。
- 瀏覽器對話：聽到繁中男聲、回覆菜月昴風繁中、mao_pro 表情隨語音切換（至少 2 種情緒可見變化）。

## 6. 風險與備援

- **瀏覽器擋自動播放音訊**：首次可能需點一下頁面或允許音訊播放；若無聲，先確認瀏覽器分頁未靜音、點頁面互動一次再對話。
- **edge-tts 需網路/voice 名稱正確**：步驟 2 的離線合成測試先擋掉拼錯/斷網；voice 清單可用 `edge-tts --list-voices` 查（zh-TW 開頭）。
- **麥克風權限被拒不影響 TTS**：TTS 是輸出（喇叭），ASR 才需麥克風（輸入）。OLV 可能仍跳麥克風要求 → 可忽略/拒絕，不影響聽語音。
- **中文/log 假象**：沿用上輪教訓 —— OLV server log 經 PowerShell 寫檔會 cp950 亂碼，是顯示假象非實際；驗證以瀏覽器實聽 + 前端 console 為準，不信 log 中文。
- **表情仍不動**：若有語音但表情不動，回到 console 看 `actions {expressions:...}` 是否到前端、mao_pro 是否載入；參考官方文件 https://docs.llmvtuber.com/docs/user-guide/live2d/。
- **app/ gitignored**：conf.yaml 變更不進版控；本步唯一版控變更為最後把結果記到 spec。

## 7. 實際結果（TTS 階段）— 達成

日期：2026-06-01。**通過**：菜月昴用繁中男聲開口說話，mao_pro 表情隨語音切換。一併完成上輪（階段二）卡住的表情驗收，證實「表情依賴音頻播放」的推論。

### 完成 / 驗證
- `conf.yaml` `edge_tts.voice` 改為 `zh-TW-YunJheNeural`，edge-tts 離線合成測試產出非空 mp3（25KB）、聲線正確。
- server 重啟，TTS 初始化 `edge_tts`，瀏覽器對話：**聽到繁中男聲** + 回覆菜月昴風繁中 + **mao_pro 表情隨語音切換**（升職 [joy]、遲到 [smirk]、貓走 [surprise] 皆觸發）。

### 關鍵根因：缺 ffmpeg（最初無聲的真因）
- 第一次驗收**無聲**。前端 console 每段都 `{type:'audio', audio: null}` + `[AudioManager] No current audio playing`，表情雖解析出（`actions {expressions:[..]}`）但因綁音頻而不觸發。
- server log 揭露真因：`Error preparing audio payload: Error loading or converting generated audio file to wav file 'cache\\...mp3': [WinError 2] 系統找不到指定的檔案。`
- 根因：OLV 的 `utils/stream_audio.py:63` `AudioSegment.from_file()`（pydub）把 edge_tts 產的 mp3 轉 wav，**pydub 轉檔依賴 ffmpeg**；機器未裝 ffmpeg → `WinError 2`（找不到 ffmpeg.exe，非 mp3）→ audio=null → 無聲 + 表情不觸發（同一根因）。
- 對策：`winget install Gyan.FFmpeg`（裝 8.1.1）。winget 已更新 user PATH，**新開的終端**會自動有 ffmpeg；但安裝當下正在跑的進程／既有 shell 仍是舊 PATH，需用含 ffmpeg bin 的 PATH 重啟 server 才生效。重啟後語音 + 表情全通。

### 對 app/ 的變更（gitignored，不進版控）
- `conf.yaml` `edge_tts.voice` = `zh-TW-YunJheNeural`。
- 系統層裝了 ffmpeg（winget，machine/user PATH，永久）。
