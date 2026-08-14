#!/usr/bin/env python3
"""Google カレンダーの list_events 出力(JSON)を Word 生成用のデータに整形する。

使い方:
    python scripts/build_schedule_data.py --year 2026 --month 8 \
        --events page1.json page2.json --holidays holiday.json \
        --out output/schedule_data.json
"""

import argparse
import calendar
import json
from datetime import date, datetime, timedelta

WEEKDAY_JA = ["月", "火", "水", "木", "金", "土", "日"]


def load_events(paths):
    events = []
    for path in paths:
        with open(path, encoding="utf-8") as f:
            events.extend(json.load(f).get("events", []))
    return events


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
                "summary": event.get("summary", "(無題)"),
                "location": event.get("location", ""),
                "note": clean_note(event.get("description", ""))}

    start_dt = datetime.fromisoformat(start["dateTime"])
    end_dt = datetime.fromisoformat(end["dateTime"]) if end.get("dateTime") else start_dt
    return {"days": [start_dt.date()],
            "time": f"{start_dt:%H:%M}〜{end_dt:%H:%M}",
            "all_day": False,
            "sort_key": start_dt.hour * 60 + start_dt.minute,
            "summary": event.get("summary", "(無題)"),
            "location": event.get("location", ""),
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


def build(year, month, event_paths, holiday_paths):
    holidays = {}
    for holiday in load_events(holiday_paths):
        for day in normalize(holiday)["days"]:
            holidays[day] = holiday.get("summary", "祝日")

    by_day = {}
    for event in load_events(event_paths):
        if event.get("status") == "cancelled":
            continue
        item = normalize(event)
        for day in item["days"]:
            if day.year == year and day.month == month:
                by_day.setdefault(day, []).append(item)

    days = []
    for day_num in range(1, calendar.monthrange(year, month)[1] + 1):
        day = date(year, month, day_num)
        items = sorted(by_day.get(day, []), key=lambda i: (i["sort_key"], i["summary"]))
        seen, unique = set(), []
        for item in items:
            key = (item["time"], item["summary"])
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
    return {
        "year": year,
        "month": month,
        "generated_at": datetime.now().strftime("%Y-%m-%d"),
        "total_events": total,
        "busiest": max(days, key=lambda d: len(d["events"]))["date"] if total else "",
        "days": days,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--month", type=int, required=True)
    parser.add_argument("--events", nargs="+", required=True)
    parser.add_argument("--holidays", nargs="*", default=[])
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    data = build(args.year, args.month, args.events, args.holidays)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"{args.out}: {data['total_events']} 件 / {len(data['days'])} 日")


if __name__ == "__main__":
    main()
