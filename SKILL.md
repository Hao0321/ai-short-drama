---
name: ai-short-drama
description: 設計、編劇、製作與迭代爆款 AI 短劇／漫劇／仿真人直式連載。用於「AI短劇」「AI漫劇」「爽劇」「微短劇」「爆款情景」「一鏡到底」「宮格成片」「故事連鏡」「角色三視圖」「假廢物真強者」「扮豬吃虎」「重生」「轉生／穿越」「系統流」「隱藏大佬／隱藏身份」「逆襲／打臉／復仇」「真假千金」「末世」「修仙」「規則怪談」「ReelShort／DramaBox 風」「分集大綱」「每集鉤子」「季節拍」「短劇角色一致性」「把小說改短劇」「短劇為什麼不爆」「規劃一季／寫下一集」「從故事到AI成片」「一鍵做短劇」「100%自動化」「全部你來」等任務。負責題材雷達、片型路由、概念綠燈、系列 Bible、資產註冊、逐鏡時間線、爽點與揭露階梯、分集編劇、連載狀態、production pack、可續跑生成、成片 QA 與成效回填；實際媒體提示詞交給 ai-media-generator，完整剪輯交付可串接 video-autopilot 或相容執行器。
---

# AI Short Drama

把一個爽點母題做成可測試、可連載、角色不漂、每集都有下一集衝動的 AI 短劇系統。故事與連載狀態由本 Skill 擁有；圖片、影片、聲音模型只是下游執行器。

當使用者要求「全部你來」「一鍵做短劇」「100% 自動化」「從題目到成片」「自動續跑」時，啟用 **Auto mode**：先讀 [automation.md](references/automation.md) 並執行 dependency gate。若已安裝 `video-autopilot/drama_autopilot.py` 或相容執行器，就建立可恢復專案並在登入／付費／能力不符／合規阻擋與最終公開發布以外自行推進；若未安裝，仍須交付 schema-valid production pack、生成佇列與剪輯 handoff，將狀態標成 `waiting_for_executor`，不可聲稱已產生 `current.mp4`。

Auto mode 先建立 [studio-workflow.md](references/studio-workflow.md) 定義的 `studio-plan.json`，並通過 `studio_lint.py --studio-ready`；production pack 再符合 [production_pack.schema.json](scripts/production_pack.schema.json)，並通過 `drama_lint.py --production-ready`。前者控制片型、模型能力、資產與時間線，後者控制故事與連載契約；兩層都通過才可編譯生成任務。缺少選配成片執行器時仍交付兩份已驗證契約與 handoff，不聲稱已有成片。

## 1. 邊界與跨 Skill 路由

| 任務 | Owner |
|---|---|
| 題材、概念、角色關係、季弧、分集鉤子、伏筆／爽債 | 本 Skill |
| 角色圖、場景圖、影片 prompt、聲音、模型選擇 | `ai-media-generator` |
| 成片組裝、字幕、剪輯 QA、發布與成效日誌 | `video-autopilot` 或相容剪輯執行器（選配） |
| Shorts／Reels 包裝、跨平台 hook、title/caption | `video-craft-playbook` |

不要把本 Skill 併回 `ai-media-generator`。前者是 IP／敘事／連載系統，後者是媒體生成系統；只共享 production contract。

## 2. 八個 Mode

| Mode | 觸發 | 交付 |
|---|---|---|
| **Scout** | 現在什麼題材會爆、查榜、找案例 | 有日期與來源的 Opportunity Map |
| **Greenlight** | 我有幾個點子、哪個值得做 | 概念評分、風險、唯一推薦與 pilot 假設 |
| **Bible** | 建世界觀、角色、能力／系統 | Series Bible + entity registry + reveal ladder |
| **Season** | 規劃 10／30／60 集 | micro-arcs、爽債、敵人階梯、每集 turn／cliffhanger |
| **Episode** | 寫第 N 集、續寫下一集 | 可拍劇本 + state delta + 下一集 handoff |
| **Studio** | 爆款情景、一鏡到底、宮格、故事連鏡、角色三視圖 | 片型路由 + model capability + asset registry + shot timeline |
| **Produce** | 做成 AI 漫劇／仿真人短劇 | production pack；路由媒體與剪輯 Skills |
| **Audit** | 為什麼不爆、數據回填、優化 | 故事／包裝／生產分層診斷與下一輪實驗 |

Scout 遇到「現在／最新／榜單／平台政策」必須上網查。其他 Mode 若使用者未指定平台，先做最小假設，不因缺少答案停工。

本 Skill 建立時的研究來源、證據級別與不可外推限制見 [evidence-registry.md](references/evidence-registry.md)。它是研究底稿，不是永久榜單；Scout 仍須重查當下資料。

## 3. 預設工作流

### Step 1 — 定義發行表面

先決定：

- 市場：華語國內／華語海外／全球英文或多語
- 表面：抖音／紅果／快手／Bilibili／YouTube Shorts／TikTok／Reels／ReelShort／DramaBox 類 App
- 形態：AI 仿真人、2D 漫劇、3D 動畫、表情包／動物荒誕劇
- 集長與集數：依實際平台與商業模式，不把 60–100 集當全域預設

再依 [studio-workflow.md](references/studio-workflow.md) 選發行單位：`serial_episode`、`micro_drama`、`viral_one_take`、`grid_moment` 或 `continuous_long_take`。先分清「完整故事」與「單一高衝擊瞬間」；不得用同一份節奏模板硬套所有片型。

最新平台、案例與驗證策略讀 [platform-strategy.md](references/platform-strategy.md)。

### Step 2 — 選「已驗證引擎 × 新鮮變量」

用 [genre-engines.md](references/genre-engines.md) 選一個主引擎，最多兩個輔引擎。概念必同時包含：

1. **熟悉承諾：** 觀眾一秒理解會得到哪種爽感。
2. **新鮮變量：** 新職業、新規則、新關係、新世界或反常代價。
3. **AI 優勢：** 真人預算難拍、AI 卻能穩定呈現的奇觀／角色／世界。

禁止只換名字重抄熱門劇。經典結構可以沿用，核心角色、具體事件、台詞、視覺設計與世界規則必須原創或有合法授權。

### Step 3 — 跑 Greenlight Score

每項 0–5 分：

| 維度 | 問題 |
|---|---|
| Instant legibility | 3 秒內懂主角受什麼壓制、藏什麼牌？ |
| Emotional voltage | 羞辱、危機、慾望或不公是否立即可感？ |
| Escalation runway | 對手、真相與代價能否升至少 4 級？ |
| Reveal runway | 秘密能否分段揭露，不一次洩光？ |
| Freshness | 與同題材相比，哪一點非它不可？ |
| AI-native spectacle | AI 是否帶來實質視覺／世界優勢？ |
| Production repeatability | 角色、場景、聲音能否資產化重用？ |
| Compliance / IP | 權利、標識與平台內容風險是否可控？ |

建議門檻：總分 ≥30/40 才做 pilot；`Freshness`、`Escalation runway`、`Production repeatability` 任一低於 3，先改概念。這是內部 heuristic，不宣稱為平台官方演算法。

### Step 4 — 建 Series Bible

先讀 [story-architecture.md](references/story-architecture.md)，建立：

- Premise Contract：公開身份、隱藏真相、核心不公、觀眾承諾、季問題、新鮮變量
- Character Bible：欲望、恐懼、錯誤信念、能力／資源、關係、表演與聲線錨
- World／System Rules：能做什麼、不能做什麼、成本、升級條件、漏洞
- Reveal Ladder：技能 → 資源 → 人脈 → 身份 → 世界真相
- Antagonist Ladder：身邊羞辱者 → 地方守門人 → 組織權力 → 幕後鏡像敵人
- Payoff Debt Ledger：每次羞辱／承諾何時償還
- Entity Registry：角色、場景、道具、服裝、傷勢、聲音的固定 ID

已持久化的系列與角色要先讀使用者提供或本地保存的 `series-<slug>.md`，再續寫或投產；其中已核准的角色關係、視覺 ID、台詞、episode state delta 與 continuation capsule 均視為唯讀，除非使用者明確要求重新設計。公開套件不附帶任何使用者私人系列；不得把另一個專案的角色或設定當成新短劇預設。

### Step 5 — 先做 Pilot，不直接展開整季

預設先寫 **3–5 集 pilot**：

1. 第 1 集證明 premise 與秘密差距。
2. 第 2 集交付第一個小爽點，但擴大風險。
3. 第 3 集完成第一次公開反轉，開更大敵人／代價。
4. 第 4–5 集只在題材需要更多世界驗證時加入。

Pilot 通過後才擴成 10／30／60 集。不可一次生成整季台詞後直接投產。

### Step 6 — 編譯單集

每集只能有一個 dominant turn，且至少交付一項：小爽點、證據、能力進展、關係變化或真相碎片。基本結構：

```text
Cold open：衝突已發生，不從起床／自我介紹開始
Pressure：對手加碼，主角必須選
Turn：資訊、權力或關係發生不可逆變化
Payoff / Progress：償還一筆爽債，或明確逼近償還
Cliffhanger：切在新資訊／新危機／即將揭露前，不是假裝卡住
State Delta：本集結束後，世界有哪些事永久改變
```

詳細節奏與 cliffhanger 類型見 [story-architecture.md](references/story-architecture.md)。

### Step 7 — 編譯 Studio Plan

讀 [studio-workflow.md](references/studio-workflow.md)，交付並驗證：

1. format profile：故事範圍、目標片長、時間線策略
2. model capability：單次時長、參考資產上限、驗證日期
3. inherited globals：畫風、比例、光線、色調、語言、聲音基線
4. canonical assets：角色／場景／道具的 recurring／one-off 標記與 identity views
5. shot timeline：時間、景別、運鏡、角度、場景、情緒、轉場、動作、台詞、聲音
6. variation policy：批次變體的 seed、shuffle bag 與近期重複抑制
7. output／handoff：整段或逐鏡 prompt、草稿位置、asset inbox、剪輯交接

執行：

```powershell
python scripts/studio_lint.py studio-plan.json --studio-ready
```

### Step 8 — 編譯 Production Pack

讀 [production-pipeline.md](references/production-pipeline.md) 與 [templates.md](references/templates.md)，交付：

1. locked entity registry
2. episode script + scene cards
3. character／location／prop／costume／voice references
4. 每鏡 observable action、frame intent、audio、end state
5. state delta 與下一集 continuation capsule
6. AI 媒體生成 brief
7. edit／caption／QA brief

之後才呼叫 `ai-media-generator`，並在可用時呼叫 `video-autopilot` 或相容剪輯執行器。長敘事不要用單一 prompt 一次生成；先腳本、角色視覺錨、逐場景 I2V，再組裝。

## 4. 爽劇硬規則

1. **主角的弱是表象、限制或代價，不是編劇讓他突然變笨。**
2. **每次受辱都開一筆爽債。** 連續受虐而不回收會消耗信任。
3. **一次只揭一層牌。** 小勝證明能力，大勝改變權力結構。
4. **反派必須會學習。** 只會重複羞辱的紙片反派撐不起連載。
5. **系統必須有成本與盲區。** 無限外掛會讓勝負失去懸念。
6. **重生知識不能全知。** 蝴蝶效應、資訊過期或另一名知情者會創造新風險。
7. **每 3–5 集完成一個 micro-arc。** 結束舊問題，同時打開更高階問題。
8. **集尾不是任意斷句。** 必須改變觀眾對下一秒的預測。
9. **角色先有可辨識欲望，再有標籤。** 「總裁／戰神／假千金」不是人物弧。
10. **新鮮度來自具體機制，不來自形容詞。** 換職業、規則、代價、敘事視角或情感關係。

## 5. AI 生產硬規則

- 角色、場景、道具、服裝與聲音使用固定 ID；禁止同義詞漂移。
- 先鎖角色／場景 still，再做 I2V；生成錯臉回 still 階段修，動作錯才重做 video。
- 不以靜態圖縮放、輪流口型、全文朗讀假裝劇情演出；每場至少有有效行為互動或空間變化。
- 每集輸出 `state_before → event → state_after`；傷勢、秘密知情人、物品持有人與關係不得重置。
- 先生成 1 個代表性場景作 style／cost probe，再批量生成。
- 每次投產前建立模型能力快照；單鏡時長與參考資產數不得超過已驗證上限。未知能力標成 `unverified`，不可猜測。
- recurring 角色先鎖正面近景、正面全身、側面全身三個 identity views；one-off 資產不浪費參考額度。
- 全局畫風／比例／光線／聲音由 Studio Plan 繼承到每鏡；只有敘事必要時才局部覆寫。
- 一鍵預設必須展開為可編輯時間線後再投產；不得把黑箱模板直接當最終生成指令。
- 先審 story cut，再加音樂、字幕與特效；漂亮不能補救事件不清楚。
- 合規與低質護欄見 [quality-compliance.md](references/quality-compliance.md)。

## 6. Audit 與學習

把問題分層，不把所有低留存都怪 prompt：

| 層 | 觀察 |
|---|---|
| Concept | 點擊後是否立刻理解承諾？題材有需求但是否同質？ |
| Episode | 首秒留存、turn 是否太晚、payoff 是否欠太久、cliffhanger 是否真改變預測？ |
| Series | 追更率、集間掉點、角色弧、重複打臉、揭露是否過早／過晚？ |
| Production | 角色／聲音漂移、口型、事件可讀性、PPT 感、字幕／音訊？ |
| Packaging | title、封面、caption、平台原生 hook？ |

每次只測一個主要變量。記錄：適用市場、題材、形態、集數、變量、結果、反例。單次成功只算候選 pattern；跨至少 3 個作品方向一致，才升格預設。

可用 [scripts/studio_lint.py](scripts/studio_lint.py) 檢查片型、模型限制、資產鎖與逐鏡時間線；用 [scripts/drama_lint.py](scripts/drama_lint.py) 檢查 production pack 的必填欄位、連續集號、引用 ID 與爽債期限。

## 7. 交付格式

除非使用者只要單一片段，預設交付：

1. **一句話推薦**：唯一主方向與原因
2. **Premise Contract**
3. **主角／反派／系統卡**
4. **Reveal + Antagonist + Payoff ladders**
5. **3 集 pilot 表**
6. **第 1 集可拍腳本**
7. **Format Profile + Studio Plan 摘要**
8. **Production Pack 摘要**
9. **風險與驗證計畫**

需要完整結構時直接套 [templates.md](references/templates.md)，不要臨場發明欄位。
