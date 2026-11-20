""".ics for Outlook (UTC, stable UID). P6 XML progress export is TODO(feat/export)."""
from datetime import UTC, datetime, timedelta


def _ics_time(dt: datetime) -> str:
    return dt.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")


def _esc(text: str) -> str:
    return text.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def captures_to_ics(captures: list[dict], host: str = "tagwerk") -> str:
    """captures: [{capture_id, ts_server (ISO), zone_id, summary, description}] -> iCalendar text."""
    now = _ics_time(datetime.now(UTC))
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Tagwerk//Site log//EN", "CALSCALE:GREGORIAN"]
    for c in captures:
        start = datetime.fromisoformat(c["ts_server"].replace("Z", "+00:00"))
        lines += [
            "BEGIN:VEVENT",
            f"UID:capture-{c['capture_id']}@{host}",
            f"DTSTAMP:{now}",
            f"DTSTART:{_ics_time(start)}",
            f"DTEND:{_ics_time(start + timedelta(minutes=15))}",
            f"SUMMARY:{_esc(c.get('summary') or 'Site capture ' + c['zone_id'])}",
            f"DESCRIPTION:{_esc(c.get('description', ''))}",
            f"LOCATION:{_esc(c['zone_id'])}",
            "END:VEVENT",
        ]
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"


def p6_progress_xml(activities: list[dict]) -> str:
    """TODO(feat/export): update PhysicalPercentComplete, ActualStartDate, ActualFinishDate,
    RemainingDuration, Status and DataDate on a copy of the imported P6 XML (same ObjectIds)."""
    raise NotImplementedError
