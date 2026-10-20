#!/usr/bin/env python3
"""
Generate an ICS calendar file from extracted event info and open it in macOS Calendar.

Usage:
  python3 generate_ics.py --title "Event Title" --date 2026-10-22 --start 19:00 --end 20:30 --location "Some Place" --description "..." --reminder 10 --output /path/to/output.ics

All arguments except --title, --date, --start are optional.
  --end defaults to start+1h
  --reminder defaults to 10 (minutes before). Set to 0 for no alarm.
  --output defaults to ./event.ics in CWD
  --timezone defaults to Europe/London
"""

import argparse
import sys
from datetime import datetime, timedelta

def parse_args():
    p = argparse.ArgumentParser(description="Generate ICS calendar file")
    p.add_argument("--title", required=True, help="Event title")
    p.add_argument("--date", required=True, help="Event date YYYY-MM-DD")
    p.add_argument("--start", required=True, help="Start time HH:MM (24h)")
    p.add_argument("--end", default=None, help="End time HH:MM (24h), defaults to start+1h")
    p.add_argument("--location", default="", help="Event location")
    p.add_argument("--description", default="", help="Event description")
    p.add_argument("--reminder", type=int, default=10, help="Minutes before to remind (0=no alarm)")
    p.add_argument("--timezone", default="Europe/London", help="TZID timezone")
    p.add_argument("--output", default="event.ics", help="Output .ics file path")
    return p.parse_args()

def fmt_dt(date_str, time_str):
    """Convert YYYY-MM-DD and HH:MM to ICS format YYYYMMDDTHHMMSS"""
    dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
    return dt.strftime("%Y%m%dT%H%M%S")

def main():
    args = parse_args()

    # Parse end time or default to start+1h
    if args.end:
        end_str = args.end
    else:
        start_dt = datetime.strptime(f"{args.date} {args.start}", "%Y-%m-%d %H:%M")
        end_dt = start_dt + timedelta(hours=1)
        end_str = end_dt.strftime("%H:%M")

    dtstart = fmt_dt(args.date, args.start)
    dtend = fmt_dt(args.date, end_str)

    # Escape text fields for ICS (commas, semicolons, newlines)
    def esc(text):
        if not text:
            return ""
        return text.replace("\\", "\\\\").replace("\n", "\\n").replace(",", "\\,").replace(";", "\\;")

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//WorkBuddy//Calendar Event//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "BEGIN:VEVENT",
        f"UID:{args.title.lower().replace(' ', '-')}-{args.date}@workbuddy",
        f"DTSTART;TZID={args.timezone}:{dtstart}",
        f"DTEND;TZID={args.timezone}:{dtend}",
        f"SUMMARY:{esc(args.title)}",
        f"LOCATION:{esc(args.location)}",
        f"DESCRIPTION:{esc(args.description)}",
        "STATUS:CONFIRMED",
    ]

    if args.reminder > 0:
        lines.extend([
            "BEGIN:VALARM",
            f"TRIGGER:-PT{args.reminder}M",
            "ACTION:DISPLAY",
            f"DESCRIPTION:{esc(args.title)}",
            "END:VALARM",
        ])

    lines.extend([
        "END:VEVENT",
        "END:VCALENDAR",
    ])

    ics_content = "\r\n".join(lines) + "\r\n"

    with open(args.output, "w", encoding="utf-8") as f:
        f.write(ics_content)

    print(f"ICS written to: {args.output}")
    print(f"  Title: {args.title}")
    print(f"  Date: {args.date}")
    print(f"  Time: {args.start} - {end_str}")
    if args.location:
        print(f"  Location: {args.location}")
    if args.reminder > 0:
        print(f"  Reminder: {args.reminder} min before")
    else:
        print(f"  Reminder: none")

if __name__ == "__main__":
    main()
