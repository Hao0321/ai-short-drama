# Studio Workflow

## 目錄

1. 核心原則
2. 片型路由
3. Model Capability Snapshot
4. Global Inheritance
5. Canonical Asset Registry
6. Shot Timeline
7. Variation Policy
8. Output 與剪輯交接
9. 驗證流程
10. 研究來源與原創邊界

## 1. 核心原則

先把創意編譯成可編輯、可驗證、可續作的 `studio-plan.json`，再交給媒體模型。不要把「一鍵生成」理解成一個不可見的巨型 prompt；它應是：

```text
preset → editable plan → capability gate → asset lock → timeline lint → generation → editor handoff
```

Studio Plan 與 Production Pack 分工：

- Studio Plan 決定片型、模型限制、全局設定、資產與鏡頭時間線。
- Production Pack 決定角色弧、事件、爽債、連載狀態與下一集銜接。
- 同一個 Studio Plan 可承接單支爆點，也可承接 Production Pack 的一集。

## 2. 片型路由

先問輸出單位要完成什麼，不要先問用哪個模型。

| `format_profile.id` | 適用 | `story_scope` | 預設策略 |
|---|---|---|---|
| `serial_episode` | 連載中的單集 | `episode` | 多鏡時間線；集尾改變下一秒預測 |
| `micro_drama` | 一支內完成的短故事 | `complete_micro_story` | setup → pressure → turn → payoff |
| `viral_one_take` | 單一強衝突／情緒／反轉 | `single_high_impact_moment` | 一鏡或偽一鏡；只保留一個 dominant turn |
| `grid_moment` | 多格構圖、前後對比、時間推進 | `single_high_impact_moment` | 2–24 格；每格都推進資訊 |
| `continuous_long_take` | 空間調度或連續表演 | `scene` | 全部 beat 保持連續，禁止隱性硬切 |

路由規則：

1. 使用者只給「一個爆點」時，選 `viral_one_take` 或 `grid_moment`，不要硬補完整世界觀。
2. 使用者要完整起承轉合時，選 `micro_drama`。
3. 使用者要追更、下一集鉤子或狀態延續時，選 `serial_episode`。
4. 使用者把「一鏡到底」當視覺噱頭時，仍先檢查模型能否在單次時長內完成。
5. 宮格不是縮小版分鏡表；每格必須形成角度、時間或狀態差異。

## 3. Model Capability Snapshot

模型能力會變，投產前建立當次快照：

```json
{
  "model_id": "provider/model/version",
  "status": "verified",
  "max_duration_seconds": 10,
  "max_reference_assets": 8,
  "supported_reference_types": ["image"],
  "verified_at": "2026-08-13",
  "evidence": "official model documentation or observed UI"
}
```

- 不把舊頁面顯示的上限當永久事實。
- `status=unverified` 時，先做最小 probe，不得直接批量生成。
- 每個 shot 不得超過單次時長上限；連續長鏡的總長也不得超過上限。
- 只把實際傳入模型的去重 reference files 計入額度。
- 能力不符時，縮短鏡頭、拆鏡或換模型；不要默默丟失資產。

## 4. Global Inheritance

全局設定只定義一次，每鏡繼承：

```yaml
global_settings:
  aspect_ratio: "9:16"
  visual_style: "cinematic grounded realism"
  lighting: "soft motivated practical lighting"
  color_tone: "warm skin, cool shadows"
  language: "zh-TW"
  audio_baseline: "dialogue-forward, controlled room tone"
```

局部 override 必須寫出原因，例如夢境、監視器、回憶或情緒斷裂。無理由的風格漂移視為錯誤，不視為創意。

## 5. Canonical Asset Registry

所有可重用資產使用固定 ASCII ID：

```yaml
assets:
  - id: char_lead_01
    kind: character
    name: lead
    recurrence: recurring
    visual_anchor: "approved character sheet v1"
    voice_anchor: "licensed voice profile v1"
    identity_views: [front_closeup, front_full, side_full]
    reference_files: [lead_close.png, lead_front.png, lead_side.png]
```

規則：

- `recurring` 角色先鎖 `front_closeup`、`front_full`、`side_full` 三視圖。
- `recurring` 場景與關鍵道具要有可重用 visual anchor。
- `one_off` 不強迫三視圖，避免浪費參考額度。
- 身份錨與服裝變體分開；換衣服不等於換角色 ID。
- 聲線必須記錄授權／同意狀態；未知時不得模仿真人。
- reference files 只登記真實存在、會投入生成的檔案。

## 6. Shot Timeline

每鏡至少包含：

```yaml
- id: shot_001
  start_seconds: 0
  duration_seconds: 3
  shot_size: medium_closeup
  camera_move: slow_push_in
  angle: eye_level
  location_id: loc_office_01
  emotion: contained_panic
  transition: cut
  entity_ids: [char_lead_01, prop_phone_01]
  observable_action: "主角把亮起的手機扣到桌面，仍盯著門口。"
  dialogue: []
  sound: "門外腳步逼近，手機震動被桌面壓低。"
```

硬規則：

1. `start_seconds` 連續，總時長等於發行單位目標片長。
2. observable action 必須可拍，不寫抽象內心。
3. shot size、camera move、angle 分欄，避免生成器誤解混合描述。
4. `entity_ids`、`location_id` 只能引用 registry 內 ID。
5. `viral_one_take` 只允許一個 dominant turn；其他 beat 服務它。
6. `continuous_long_take` 的轉場一律為 `continuous`。
7. 每鏡輸出可獨立生成，也能編譯成帶時間碼的整段 prompt。

## 7. Variation Policy

批次生成不能只靠「再隨機一次」。建立可重現變體：

```yaml
variation_policy:
  seed: 1847
  dimensions: [genre, pace, dialogue_density]
  shuffle_bag: true
  avoid_recent: 3
```

- 使用 shuffle bag 走完一輪候選後才重置。
- 保留 seed，失敗時才能重現與比較。
- `avoid_recent` 抑制連續選到相同預設，不保證品質。
- 變體只改指定維度；不要同時改故事、角色、模型、節奏與包裝。

## 8. Output 與剪輯交接

支援兩種 prompt 輸出：

- `long_timeline`：適合模型能可靠承接時間碼與長輸出的情況。
- `shot_by_shot`：適合逐鏡生成、資產引用與失敗重試。
- `both`：同時保存導演版時間線與下游逐鏡任務。

Studio Plan 必須保存：

- `draft_path`：可續作的 JSON 草稿。
- `asset_inbox`：已核准媒體的本地收件夾。
- `editor_handoff`：目標剪輯器、軌道／字幕／音訊要求。

實際成片交給 `video-autopilot` 或已核准的剪輯工具。交接時不得只丟素材資料夾；要附鏡頭順序、時間碼、字幕語言、音訊基線與 QA 條件。

## 9. 驗證流程

```powershell
python scripts/studio_lint.py studio-plan.json
python scripts/studio_lint.py studio-plan.json --studio-ready --json
```

Studio-ready gate 檢查：

- 必填片型與全局設定
- 時間線連續與總長
- 單鏡／長鏡是否超過模型上限
- reference files 是否超過模型額度
- recurring 資產是否有錨；recurring 角色是否有三視圖與聲線
- 鏡頭是否引用不存在的資產或場景
- 一鏡到底是否混入 cut
- 批次變體是否可重現且抑制近期重複
- 草稿、asset inbox 與剪輯交接是否存在

## 10. 研究來源與原創邊界

本工作流在 2026-08-13 觀察 AI 追光公開頁面的產品行為後獨立重構：

- [漫劇工坊](https://aizhuiguang.tech/tools/manju.html)：長／短發行單位與可續作腳本庫。
- [長鏡工坊](https://aizhuiguang.tech/tools/longshot.html)：模型能力快照、全局繼承、資產註冊、時間線與雙輸出。
- [角色三視圖](https://aizhuiguang.tech/tools/character-turnaround.html)：角色 identity views。
- [爆款情景](https://aizhuiguang.tech/gallery/viral-scene.html)：單一高衝擊情景與完整短劇分流。
- [宮格成片](https://aizhuiguang.tech/gallery/grid-story.html)：多格高衝擊瞬間與完整故事分流。
- [資產庫](https://aizhuiguang.tech/tools/assets.html)：本地資產收件箱與跨工具交接。
- [追光剪輯台](https://aizhuiguang.tech/tools/lightcut.html)：時間線、字幕、音訊與成片交接需求。

只學習可泛化的產品／工作流機制。禁止複製該站文案、提示詞模板、品牌、介面、圖片、音訊、程式碼或未授權內容；來源中的模型上限只作研究觀察，投產前一律重新驗證。
