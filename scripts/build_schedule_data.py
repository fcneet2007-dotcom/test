#!/usr/bin/env python3
"""Google カレンダーの list_events 出力(JSON)を Word 生成用のデータに整形する。

使い方:
    # 月間の予定表
    python scripts/build_schedule_data.py --year 2026 --month 8 \
        --events page1.json page2.json --holidays holiday.json \
        --out output/schedule_data.json

    # 1 日分の予定表（Google ToDo リストのタスクも含める）
    python scripts/build_schedule_data.py --day 2026-08-15 \
        --events today.json --tasks todo.json --out output/day_data.json
"""

import argparse
import calendar
import json
from datetime import date, datetime, timedelta

WEEKDAY_JA = ["月", "火", "水", "木", "金", "土", "日"]


def load_events(paths):
    """複数のカレンダーの JSON を読み、各予定に取得元カレンダー名を付けて返す。"""
    events = []
    for path in paths:
        with open(path, encoding="utf-8") as f:
            payload = json.load(f)
        source = payload.get("summary", "")
        for event in payload.get("events", []):
            events.append({**event, "_calendar": source})
    return events


def load_tasks(paths):
    """Google ToDo リストのタスクを予定と同じ形に整形する。

    受け付ける JSON:
        {"list": "リスト名", "tasks": [
            {"title": "...", "due": "2026-08-15T10:00:00+09:00", "notes": "..."},
            {"title": "...", "due": "2026-08-15"}
        ]}
    `due` に時刻があればその時刻、日付だけなら時間欄を「ToDo」として扱う。
    `status` が "completed" のタスクは除外する。
    """
    items = []
    for path in paths:
        with open(path, encoding="utf-8") as f:
            payload = json.load(f)
        list_name = payload.get("list", "ToDo")
        for task in payload.get("tasks", []):
            if task.get("status") == "completed":
                continue
            due = task.get("due", "")
            if not due:
                continue
            day = parse_day(due)
            if len(due) > 10 and "T" in due:
                due_dt = datetime.fromisoformat(due)
                time_label = f"{due_dt:%H:%M}"
                sort_key = due_dt.hour * 60 + due_dt.minute
            else:
                time_label, sort_key = "ToDo", -1
            items.append({
                "days": [day],
                "time": time_label,
                "all_day": False,
                "is_task": True,
                "sort_key": sort_key,
                "summary": task.get("title", "(無題)"),
                "location": "",
                "calendar": list_name,
                "note": clean_note(task.get("notes", "")),
            })
    return items


def parse_day(value):
    """'2026-08-01T00:00:00Z' / '2026-08-01' のどちらでも日付として読む。"""
    return date.fromisoformat(value[:10])


def normalize(event):
    """1 件の予定を {days, time, summary, location, note, all_day} に整形する。"""
    start, end = event.get("start", {}), event.get("end", {})

    if "date" in start:
        first = parse_day(start["date"])
        # 終日予定の終了日は排他的なので 1 日戻す
        last = parse_day(end.get("date", start["date"])) - timedelta(days=1)
        if last < first:
            last = first
        days = [first + timedelta(days=i) for i in range((last - first).days + 1)]
        label = "終日"
        if first != last:
            label = f"終日({first.month}/{first.day}〜{last.month}/{last.day})"
        return {"days": days, "time": label, "all_day": True, "sort_key": -1,
                "is_task": False,
                "summary": event.get("summary", "(無題)"),
                "location": event.get("location", ""),
                "calendar": event.get("_calendar", ""),
                "note": clean_note(event.get("description", ""))}

    start_dt = datetime.fromisoformat(start["dateTime"])
    end_dt = datetime.fromisoformat(end["dateTime"]) if end.get("dateTime") else start_dt
    return {"days": [start_dt.date()],
            "time": f"{start_dt:%H:%M}〜{end_dt:%H:%M}",
            "all_day": False,
            "is_task": False,
            "sort_key": start_dt.hour * 60 + start_dt.minute,
            "summary": event.get("summary", "(無題)"),
            "location": event.get("location", ""),
            "calendar": event.get("_calendar", ""),
            "note": clean_note(event.get("description", ""))}


def clean_note(description):
    """Gmail 由来の定型文などを落とし、1 行の備考にまとめる。"""
    if not description:
        return ""
    text = " ".join(description.split())
    for marker in ("このように自動作成された予定", "この予定は Gmail", "http"):
        idx = text.find(marker)
        if idx != -1:
            text = text[:idx]
    text = text.strip()
    return text if len(text) <= 80 else text[:79] + "…"


def build(year, month, event_paths, holiday_paths, only_day=None,
          primary="", generated_at="", task_paths=()):
    holidays = {}
    for holiday in load_events(holiday_paths):
        for day in normalize(holiday)["days"]:
            holidays[day] = holiday.get("summary", "祝日")

    by_day = {}
    for event in load_events(event_paths):
        if event.get("status") == "cancelled":
            continue
        item = normalize(event)
        # 主カレンダーの予定にはカレンダー名を出さない（他カレンダーのみ区別する）
        if item["calendar"] == primary:
            item["calendar"] = ""
        for day in item["days"]:
            if day.year == year and day.month == month:
                by_day.setdefault(day, []).append(item)

    for item in load_tasks(task_paths):
        for day in item["days"]:
            if day.year == year and day.month == month:
                by_day.setdefault(day, []).append(item)

    day_range = [only_day.day] if only_day else range(1, calendar.monthrange(year, month)[1] + 1)
    days = []
    for day_num in day_range:
        day = date(year, month, day_num)
        items = sorted(by_day.get(day, []), key=lambda i: (i["sort_key"], i["summary"]))
        seen, unique = set(), []
        for item in items:
            key = (item["time"], item["summary"], item["is_task"])
            if key not in seen:
                seen.add(key)
                unique.append(item)
        days.append({
            "date": day.isoformat(),
            "day": day_num,
            "weekday": WEEKDAY_JA[day.weekday()],
            "is_saturday": day.weekday() == 5,
            "is_sunday": day.weekday() == 6,
            "holiday": holidays.get(day, ""),
            "events": [{k: v for k, v in item.items() if k != "days"} for item in unique],
        })

    total = sum(len(d["events"]) for d in days)
    if only_day:
        title = f"{year}年{month}月{only_day.day}日({days[0]['weekday']}) 予定表"
    else:
        title = f"{year}年{month}月 予定表"
    return {
        "year": year,
        "month": month,
        "title": title,
        "generated_at": generated_at or datetime.now().strftime("%Y-%m-%d"),
        "total_events": total,
        "busiest": max(days, key=lambda d: len(d["events"]))["date"] if total else "",
        "days": days,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", type=int)
    parser.add_argument("--month", type=int)
    parser.add_argument("--day", help="1 日分だけ出力する場合の日付 (YYYY-MM-DD)")
    parser.add_argument("--events", nargs="+", required=True,
                        help="list_events のレスポンス JSON。複数カレンダー・複数ページを並べられる")
    parser.add_argument("--holidays", nargs="*", default=[])
    parser.add_argument("--tasks", nargs="*", default=[],
                        help="Google ToDo リストのタスク JSON")
    parser.add_argument("--primary", default="",
                        help="主カレンダー名。これ以外のカレンダーの予定には備考に名前を出す")
    parser.add_argument("--generated-at", default="", help="作成日の表記 (既定: 実行日)")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    only_day = date.fromisoformat(args.day) if args.day else None
    if only_day:
        year, month = only_day.year, only_day.month
    elif args.year and args.month:
        year, month = args.year, args.month
    else:
        parser.error("--day か --year/--month のどちらかを指定してください")

    data = build(year, month, args.events, args.holidays, only_day,
                 args.primary, args.generated_at, args.tasks)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"{args.out}: {data['total_events']} 件 / {len(data['days'])} 日")


if __name__ == "__main__":
    main()
