#!/usr/bin/env python3
"""
Smart calendar event creator: parse natural language, generate ICS, open in Calendar.

Usage:
  python3 smart_calendar.py "明天下午3点在图书馆开会"
  python3 smart_calendar.py "Oct 22 7pm-8:30pm Panorama Rootes Building, WBS Social Mixer"
  python3 smart_calendar.py --title "开会" --date 2026-10-21 --start 15:00 --location "图书馆"

With a single string argument, the script parses:
  - Relative dates: 明天, 后天, today, tomorrow, next Monday, 下周三, etc.
  - Times: 下午3点, 3pm, 15:00, 7:30pm, 上午10点, etc.
  - Time ranges: 3-5pm, 15:00-17:00, 7:00–8:30 pm
  - Location keywords: 在..., @..., Location:...
  - Title: the remaining text after removing date/time/location
"""

import argparse
import re
import sys
import os
import subprocess
from datetime import datetime, timedelta

# ── Date parsing ──

WEEKDAY_MAP = {
    '周一': 0, '周二': 1, '周三': 2, '周四': 3, '周五': 4, '周六': 5, '周日': 6,
    '星期一': 0, '星期二': 1, '星期三': 2, '星期四': 3, '星期五': 4, '星期六': 5, '星期日': 6,
    'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3, 'friday': 4, 'saturday': 5, 'sunday': 6,
    'mon': 0, 'tue': 1, 'wed': 2, 'thu': 3, 'fri': 4, 'sat': 5, 'sun': 6,
}

MONTH_MAP = {
    'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
    'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12,
}

def parse_date(text, today=None):
    """Parse date from text. Returns (date_obj, consumed_text)."""
    if today is None:
        today = datetime.now().date()

    text_lower = text.lower()

    # 明天
    if '明天' in text:
        d = today + timedelta(days=1)
        return d, text.replace('明天', '')
    # 后天
    if '后天' in text:
        d = today + timedelta(days=2)
        return d, text.replace('后天', '')
    # 今天
    if '今天' in text:
        return today, text.replace('今天', '')
    # 大后天
    if '大后天' in text:
        d = today + timedelta(days=3)
        return d, text.replace('大后天', '')

    # tomorrow
    if 'tomorrow' in text_lower:
        d = today + timedelta(days=1)
        return d, re.sub(r'tomorrow', '', text, flags=re.IGNORECASE)

    # today
    if re.search(r'\btoday\b', text_lower):
        return today, re.sub(r'\btoday\b', '', text, flags=re.IGNORECASE)

    # Chinese weekday: 下周三 / 下周三
    m = re.search(r'下(?:周|星期|礼拜)([一二三四五六日天])', text)
    if m:
        day_map = {'一':0,'二':1,'三':2,'四':3,'五':4,'六':5,'日':6,'天':6}
        target_day = day_map.get(m.group(1))
        if target_day is not None:
            days_ahead = (target_day - today.weekday() + 7) % 7
            if days_ahead == 0:
                days_ahead = 7
            return today + timedelta(days=days_ahead), text[:m.start()] + text[m.end():]

    # Chinese weekday this week: 周六 / 周日 / 星期三
    m = re.search(r'(?:周|星期)([一二三四五六日天])', text)
    if m:
        day_map = {'一':0,'二':1,'三':2,'四':3,'五':4,'六':5,'日':6,'天':6}
        target_day = day_map.get(m.group(1))
        if target_day is not None:
            days_ahead = (target_day - today.weekday() + 7) % 7
            if days_ahead == 0:
                days_ahead = 7
            return today + timedelta(days=days_ahead), text[:m.start()] + text[m.end():]

    # next Monday/Tuesday/etc (English)
    m = re.search(r'next\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)', text_lower)
    if m:
        target_day = WEEKDAY_MAP[m.group(1)]
        days_ahead = (target_day - today.weekday() + 7) % 7
        if days_ahead == 0:
            days_ahead = 7
        return today + timedelta(days=days_ahead), text[:m.start()] + text[m.end():]

    # English weekday alone
    for kw, dow in WEEKDAY_MAP.items():
        if kw in text_lower and len(kw) >= 3:
            days_ahead = (dow - today.weekday() + 7) % 7
            if days_ahead == 0:
                days_ahead = 7
            return today + timedelta(days=days_ahead), re.sub(re.escape(kw), '', text, flags=re.IGNORECASE)

    # Chinese date: 10月21日 / 10月21号
    m = re.search(r'(\d{1,2})月(\d{1,2})[日号]?', text)
    if m:
        mo, d = int(m.group(1)), int(m.group(2))
        y = today.year
        return datetime(y, mo, d).date(), text[:m.start()] + text[m.end():]

    # ISO format: 2026-10-22

    # "October 22" or "Oct 22" (with optional year)
    for mon_name, mon_num in MONTH_MAP.items():
        m = re.search(rf'{mon_name}\w*\s+(\d{{1,2}})(?:st|nd|rd|th)?(?:\s*,?\s*(\d{{4}}))?', text_lower)
        if m:
            d = int(m.group(1))
            y = int(m.group(2)) if m.group(2) else today.year
            return datetime(y, mon_num, d).date(), text[:m.start()] + text[m.end():]
        # "22 October" / "22 Oct"
        m = re.search(rf'(\d{{1,2}})(?:st|nd|rd|th)?\s+{mon_name}\w*(?:\s*,?\s*(\d{{4}}))?', text_lower)
        if m:
            d = int(m.group(1))
            y = int(m.group(2)) if m.group(2) else today.year
            return datetime(y, mon_num, d).date(), text[:m.start()] + text[m.end():]

    # "22/10/2026" or "10/22/2026" (assume UK format DD/MM/YYYY)
    m = re.search(r'(\d{1,2})/(\d{1,2})/(\d{4})', text)
    if m:
        d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if mo > 12:  # US format MM/DD/YYYY
            d, mo = mo, d
        return datetime(y, mo, d).date(), text[:m.start()] + text[m.end():]

    # No date found — default to today
    return today, text


# ── Time parsing ──

def parse_time(text):
    """Parse start/end time from text. Returns (start_hhmm, end_hhmm, consumed_text)."""
    text_lower = text.lower()

    # Pattern: 15:00-17:00 / 09:30-11:00 (24h range)
    m = re.search(r'(\d{1,2}):(\d{2})\s*[-–]\s*(\d{1,2}):(\d{2})', text)
    if m:
        sh, sm = int(m.group(1)), int(m.group(2))
        eh, em = int(m.group(3)), int(m.group(4))
        if 0 <= sh <= 23 and 0 <= eh <= 23:
            start = f"{sh:02d}:{sm:02d}"
            end = f"{eh:02d}:{em:02d}"
            return start, end, text[:m.start()] + text[m.end():]

    # Pattern: 3-5pm / 3:00-5:00pm / 7-8:30pm (12h with suffix)
    m = re.search(r'(\d{1,2})(?::(\d{2}))?\s*[-–]\s*(\d{1,2})(?::(\d{2}))?\s*(am|pm)', text_lower)
    if not m:
        # Also try: 7pm - 8:30pm (suffix on both)
        m2 = re.search(r'(\d{1,2})(?::(\d{2}))?\s*(am|pm)\s*[-–]\s*(\d{1,2})(?::(\d{2}))?\s*(am|pm)', text_lower)
        if m2:
            sh = int(m2.group(1))
            sm = int(m2.group(2)) if m2.group(2) else 0
            eh = int(m2.group(4))
            em = int(m2.group(5)) if m2.group(5) else 0
            if m2.group(3) == 'pm' and sh < 12: sh += 12
            elif m2.group(3) == 'am' and sh == 12: sh = 0
            if m2.group(6) == 'pm' and eh < 12: eh += 12
            elif m2.group(6) == 'am' and eh == 12: eh = 0
            start = f"{sh:02d}:{sm:02d}"
            end = f"{eh:02d}:{em:02d}"
            return start, end, text[:m2.start()] + text[m2.end():]
    if m:
        sh = int(m.group(1))
        sm = int(m.group(2)) if m.group(2) else 0
        eh = int(m.group(3))
        em = int(m.group(4)) if m.group(4) else 0
        suffix = m.group(5)

        if suffix == 'pm':
            if sh < 12: sh += 12
            if eh < 12: eh += 12
        elif suffix == 'am':
            if sh == 12: sh = 0
            if eh == 12: eh = 0

        start = f"{sh:02d}:{sm:02d}"
        end = f"{eh:02d}:{em:02d}"
        return start, end, text[:m.start()] + text[m.end():]

    # 下午3点 / 下午3:30 / 上午10点 / 晚上7点 / 晚上7:30
    m = re.search(r'(下午|上午|傍晚|晚上|中午)(\d{1,2})(?::(\d{2}))?点?', text)
    if m:
        h = int(m.group(2))
        mi = int(m.group(3)) if m.group(3) else 0
        if m.group(1) in ('下午', '傍晚', '晚上') and h < 12:
            h += 12
        elif m.group(1) == '上午' and h == 12:
            h = 0
        start = f"{h:02d}:{mi:02d}"
        return start, None, text[:m.start()] + text[m.end():]

    # 3pm / 3:30pm / 15:00 / 7pm
    m = re.search(r'(\d{1,2})(?::(\d{2}))?\s*(am|pm)', text_lower)
    if m:
        h = int(m.group(1))
        mi = int(m.group(2)) if m.group(2) else 0
        if m.group(3) == 'pm' and h < 12:
            h += 12
        elif m.group(3) == 'am' and h == 12:
            h = 0
        start = f"{h:02d}:{mi:02d}"
        return start, None, text[:m.start()] + text[m.end():]

    # 24h format: 15:00, 09:30
    m = re.search(r'\b(\d{1,2}):(\d{2})\b', text)
    if m:
        h = int(m.group(1))
        mi = int(m.group(2))
        if 0 <= h <= 23:
            start = f"{h:02d}:{mi:02d}"
            return start, None, text[:m.start()] + text[m.end():]

    # No time found
    return None, None, text


# ── Location parsing ──

def parse_location(text):
    """Parse location from text. Returns (location, consumed_text)."""
    # 在...开会/见面 etc — extract location, keep action word in title
    m = re.search(r'在(.+?)(开会|见面|碰面|集合|出发|见|碰头|自习|考试|上课|聚餐|约|打球|健身|讨论|培训|面试|讲座|活动|参加)', text)
    if m:
        loc = m.group(1).strip()
        return loc, text[:m.start()] + m.group(2) + text[m.end():]

    # 在... (Chinese, no action word)
    m = re.search(r'在(.+?)(?:，|,|$)', text)
    if m:
        loc = m.group(1).strip()
        return loc, text[:m.start()] + text[m.end():]

    # "at Location" (English) - capture up to comma or end, must start with capital
    m = re.search(r'\bat\s+([A-Z][^,]*?)(?:,|，|$)', text)
    if m:
        loc = m.group(1).strip()
        # Don't treat the rest of the event title as location
        return loc, text[:m.start()] + text[m.end():]

    # @ Location
    m = re.search(r'@\s*(.+?)(?:,|，|$)', text)
    if m:
        return m.group(1).strip(), text[:m.start()] + text[m.end():]

    m = re.search(r'(?:location|地点)[:：]\s*(.+?)(?:,|，|$)', text, re.IGNORECASE)
    if m:
        return m.group(1).strip(), text[:m.start()] + text[m.end():]

    # "at Location" (English) - be careful not to grab time
    m = re.search(r'\bat\s+([A-Z][^,]+?)(?:,|，|$)', text)
    if m:
        return m.group(1).strip(), text[:m.start()] + text[m.end():]

    return "", text


# ── Main parse function ──

def parse_natural_language(text):
    """Parse natural language event description into structured fields."""
    today = datetime.now().date()
    remaining = text

    # Parse date
    date_obj, remaining = parse_date(remaining, today)

    # Parse time
    start_time, end_time, remaining = parse_time(remaining)

    # Parse location
    location, remaining = parse_location(remaining)

    # Default end time: +1h
    if start_time and not end_time:
        h, mi = int(start_time[:2]), int(start_time[3:5])
        end_dt = datetime(2000, 1, 1, h, mi) + timedelta(hours=1)
        end_time = end_dt.strftime("%H:%M")

    # Default time if none found
    if not start_time:
        start_time = "09:00"
        end_time = "10:00"

    # Title = remaining text, cleaned up
    title = remaining.strip().strip('，,。.!！').strip()
    if not title:
        title = "Event"

    return {
        'title': title,
        'date': date_obj.strftime("%Y-%m-%d"),
        'start': start_time,
        'end': end_time,
        'location': location,
    }


# ── ICS generation ──

def generate_ics(fields, reminder=10, timezone="Europe/London", output_path=None):
    """Generate ICS file from fields dict and open it."""
    def esc(t):
        if not t:
            return ""
        return t.replace("\\", "\\\\").replace("\n", "\\n").replace(",", "\\,").replace(";", "\\;")

    def fmt(date_str, time_str):
        dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
        return dt.strftime("%Y%m%dT%H%M%S")

    dtstart = fmt(fields['date'], fields['start'])
    dtend = fmt(fields['date'], fields['end'])

    uid = fields['title'].lower().replace(' ', '-')[:20] + '-' + fields['date'] + '@workbuddy'

    lines = [
        "BEGIN:VCALENDAR", "VERSION:2.0",
        "PRODID:-//WorkBuddy//Calendar Event//EN",
        "CALSCALE:GREGORIAN", "METHOD:PUBLISH",
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTART;TZID={timezone}:{dtstart}",
        f"DTEND;TZID={timezone}:{dtend}",
        f"SUMMARY:{esc(fields['title'])}",
    ]
    if fields.get('location'):
        lines.append(f"LOCATION:{esc(fields['location'])}")
    if fields.get('description'):
        lines.append(f"DESCRIPTION:{esc(fields['description'])}")
    lines.append("STATUS:CONFIRMED")

    if reminder > 0:
        lines.extend([
            "BEGIN:VALARM",
            f"TRIGGER:-PT{reminder}M",
            "ACTION:DISPLAY",
            f"DESCRIPTION:{esc(fields['title'])}",
            "END:VALARM",
        ])
    lines.extend(["END:VEVENT", "END:VCALENDAR"])

    ics = "\r\n".join(lines) + "\r\n"

    if not output_path:
        output_path = os.path.join(os.getcwd(), fields['title'][:20].replace(' ', '_') + ".ics")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(ics)

    return output_path


def main():
    parser = argparse.ArgumentParser(description="Smart calendar event creator")
    parser.add_argument("text", nargs="?", help="Natural language event description")
    parser.add_argument("--title", help="Event title (overrides parsing)")
    parser.add_argument("--date", help="Event date YYYY-MM-DD (overrides parsing)")
    parser.add_argument("--start", help="Start time HH:MM (overrides parsing)")
    parser.add_argument("--end", help="End time HH:MM")
    parser.add_argument("--location", help="Event location (overrides parsing)")
    parser.add_argument("--description", default="")
    parser.add_argument("--reminder", type=int, default=10)
    parser.add_argument("--timezone", default="Europe/London")
    parser.add_argument("--output", default=None)
    parser.add_argument("--no-open", action="store_true", help="Don't open in Calendar")
    args = parser.parse_args()

    if args.title and args.date and args.start:
        # Explicit fields mode
        fields = {
            'title': args.title,
            'date': args.date,
            'start': args.start,
            'end': args.end or (f"{int(args.start[:2])+1:02d}:{args.start[3:5]}"),
            'location': args.location or '',
            'description': args.description,
        }
    elif args.text:
        # Natural language mode
        fields = parse_natural_language(args.text)
        if args.title: fields['title'] = args.title
        if args.date: fields['date'] = args.date
        if args.start: fields['start'] = args.start
        if args.end: fields['end'] = args.end
        if args.location: fields['location'] = args.location
        fields['description'] = args.description
    else:
        print("Error: provide event text or --title/--date/--start")
        sys.exit(1)

    path = generate_ics(fields, args.reminder, args.timezone, args.output)

    # Print compact summary for AI to relay
    print(f"✅ {fields['title']} | {fields['date']} {fields['start']}-{fields['end']}")
    if fields.get('location'):
        print(f"   📍 {fields['location']}")
    print(f"   🔔 {args.reminder}min before | {path}")

    if not args.no_open:
        subprocess.run(["open", path], capture_output=True)


if __name__ == "__main__":
    main()
