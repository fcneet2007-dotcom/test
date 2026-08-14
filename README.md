# カレンダー → Word 予定表

Google カレンダーの予定を Word 文書（.docx）の月間予定表に変換します。

## 成果物

- `output/2026年08月_予定表.docx` — 2026 年 8 月の予定表（予定 117 件）
- `output/schedule_data.json` — Word 生成に使った整形済みデータ

## 予定表の構成

| 列 | 内容 |
|---|---|
| 日付 | `8/1 (土)` 形式。土曜は青、日曜・祝日は赤の網掛け。祝日名も表示 |
| 時間 | `09:00〜10:00`、終日予定は `終日`。複数日にまたがる場合は `終日(8/8〜8/12)` |
| 予定 | 予定のタイトル（終日予定は太字） |
| 場所・備考 | 場所と説明文。Gmail 由来の定型文・URL は除去 |

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
     --events events_page1.json events_page2.json \
     --holidays holidays.json \
     --out output/schedule_data.json
   ```

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
python3 scripts/build_schedule_data.py --day 2026-08-14 \
  --events today.json --holidays holidays.json \
  --out output/day_2026-08-14.json
node scripts/generate_schedule_docx.js output/day_2026-08-14.json "output/2026年08月14日_予定表.docx"
```

見出しは `2026年8月14日(金) 予定表` のように曜日つきになります。
