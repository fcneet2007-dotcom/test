# カレンダー → Word 予定表

Google カレンダーの予定を Word 文書（.docx）の月間予定表に変換します。

## 成果物

- `output/2026年08月_予定表.docx` — 2026 年 8 月の予定表（予定 124 件）
- `output/2026年08月15日_予定表.docx` — 2026 年 8 月 15 日(土) の予定表
- `output/schedule_data.json`, `output/day_2026-08-15.json` — Word 生成に使った整形済みデータ

## 予定表の構成

| 列 | 内容 |
|---|---|
| 日付 | `8/1 (土)` 形式。土曜は青、日曜・祝日は赤の網掛け。祝日名も表示 |
| 時間 | `09:00〜10:00`、終日予定は `終日`。複数日にまたがる場合は `終日(8/8〜8/12)` |
| 予定 | 予定のタイトル（終日予定は太字） |
| 場所・備考 | 場所と説明文。主カレンダー以外の予定は `[domo Todo]` のようにカレンダー名を表示。Gmail 由来の定型文・URL は除去 |

- 水色の行は Google ToDo リストのタスクで、タイトルの頭に `□` が付きます。
- 1 日分の予定は日付セルを縦結合してまとめています。
- 見出し行は各ページの先頭で繰り返されます（A4 縦・余白 0.5 インチ）。
- 複数日の終日予定（休み・出勤停止など）は該当する各日に表示されます。

## 再生成の手順

1. **カレンダーから予定を取得**する。Claude の Google Calendar 連携（`list_events`）か
   Google Calendar API で、対象月の予定を JSON で保存します。
   1 回のレスポンスは最大 100 件なので、`nextPageToken` がある場合は続きも取得し、
   ファイルを複数指定してください。祝日は
   `ja.japanese#holiday@group.v.calendar.google.com` から別途取得します。

2. **データを整形する**

   ```bash
   python3 scripts/build_schedule_data.py --year 2026 --month 8 \
     --events events_page1.json events_page2.json todo_calendar.json \
     --holidays holidays.json \
     --primary "fcneet2007@gmail.com" \
     --out output/schedule_data.json
   ```

   `--events` には複数のカレンダー・複数ページの JSON を並べられます。
   `--primary` に指定したカレンダー以外の予定には、備考にカレンダー名が付きます。

3. **Word 文書を生成する**

   ```bash
   npm install docx   # 初回のみ
   node scripts/generate_schedule_docx.js output/schedule_data.json "output/2026年08月_予定表.docx"
   ```

## 必要なもの

- Python 3（標準ライブラリのみ）
- Node.js と [`docx`](https://www.npmjs.com/package/docx) パッケージ

## 備考

- 本文フォントは Yu Gothic（游ゴシック）です。別のフォントにする場合は
  `scripts/generate_schedule_docx.js` の `FONT` を変更してください。
- 終日予定の終了日はカレンダー API 上は排他的（翌日 00:00）なので、
  整形時に 1 日戻して実際の最終日に合わせています。
- 同じ時間・同じタイトルの重複予定は 1 件にまとめています。

## 1 日分の予定表

`--day` を指定すると、その日だけの予定表を作成します。

```bash
python3 scripts/build_schedule_data.py --day 2026-08-15 \
  --events today.json todo_calendar.json --holidays holidays.json \
  --primary "fcneet2007@gmail.com" \
  --out output/day_2026-08-15.json
node scripts/generate_schedule_docx.js output/day_2026-08-15.json "output/2026年08月15日_予定表.docx"
```

見出しは `2026年8月15日(土) 予定表` のように曜日つきになります。
`--generated-at 2026-08-15` で「作成日」の表記を指定することもできます。

## Google ToDo リストのタスクを含める

Google ToDo リスト（カレンダー画面にチェックボックス付きで並ぶタスク）は
カレンダーの「予定」とは別のデータで、`list_events` では取得できません。
次の形式の JSON を用意して `--tasks` で渡すと、予定と同じ表に時刻順で差し込まれます。

```json
{
  "list": "ToDo",
  "tasks": [
    { "title": "サンプル", "due": "2026-08-15T11:00:00+09:00", "notes": "補足" },
    { "title": "時刻なしのタスク", "due": "2026-08-15" }
  ]
}
```

```bash
python3 scripts/build_schedule_data.py --day 2026-08-15 \
  --events today.json todo_calendar.json --tasks todo_tasks.json \
  --primary "fcneet2007@gmail.com" --out output/day_2026-08-15.json
```

- `due` に時刻があればその時刻の行に、日付だけなら時間欄が `ToDo` の行になります。
- `status` が `completed` のタスクは出力しません。
- タスクの行は水色で塗り、タイトルの頭に `□` を付けます。
