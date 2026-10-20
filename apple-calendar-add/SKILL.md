---
name: apple-calendar-add
description: "Add events to macOS Apple Calendar from images, PDFs, or text. This skill should be used when the user provides event information (an image of a ticket/poster/notice, a PDF booking confirmation, or plain text with date/time/location) and wants it added to their Apple Calendar. Triggers: '加到日历', '添加日程', '加日历', 'add to calendar', 'put on my calendar', 'calendar', '日历', '日程', 'ics'. The skill generates a .ics file with a 10-min reminder and opens it in Calendar app."
agent_created: true
---

# Apple Calendar Add

Add events to macOS Apple Calendar. Script path: `/Users/huxinlei/.workbuddy-ai/skills/apple-calendar-add/scripts/smart_calendar.py`

## Decision: pick ONE path based on input type

**A. Plain text** (user wrote the event info in chat):
```bash
python3 /Users/huxinlei/.workbuddy-ai/skills/apple-calendar-add/scripts/smart_calendar.py "USER TEXT" --output "WORKSPACE/event.ics"
```
Script auto-parses: 明天/后天/周六/10月21日, 下午3点/7pm/15:00, time ranges, 在..., etc. Outputs .ics + opens Calendar. Relay summary + `present_files`.

**B. Image** (screenshot/photo):
1. Read the image to extract: title, date, start/end time, location, description.
2. Run script with flags:
```bash
python3 /Users/huxinlei/.workbuddy-ai/skills/apple-calendar-add/scripts/smart_calendar.py --title "Title" --date 2026-10-24 --start 14:30 --end 17:30 --location "Venue" --description "Seat info etc" --output "WORKSPACE/event.ics"
```

**C. PDF** (ticket/booking):
1. Extract text: `/Users/huxinlei/.workbuddy-ai/binaries/python/envs/default/bin/python3 -c "import pdfplumber; ..."` (see pdf skill)
2. Parse fields, run script with flags (same as B).

## Notes
- Default reminder: 10 min. TZ: Europe/London.
- Override end time with `--end HH:MM` if user specifies duration (e.g. 3h → compute end).
- Script opens Calendar automatically. Just `present_files` + brief summary after.
