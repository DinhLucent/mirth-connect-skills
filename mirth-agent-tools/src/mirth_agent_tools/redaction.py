from __future__ import annotations

import re


EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
PHONE_RE = re.compile(r"\b(?:\+?1[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)\d{3}[-.\s]?\d{4}\b")
SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
DOB_RE = re.compile(r"\b(?:19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\b")
MRN_RE = re.compile(r"\b(?:MRN|Medical Record Number)[:=#\s-]*[A-Za-z0-9-]{4,}\b", re.IGNORECASE)
HL7_NAME_RE = re.compile(r"\b[A-Z][A-Za-z'-]{1,}\^[A-Z][A-Za-z'-]{1,}(?:\^[A-Z][A-Za-z'-]{1,})?\b")


def redact_phi(text: str, max_chars: int | None = None) -> str:
    redacted = _redact_hl7_segments(text)
    redacted = EMAIL_RE.sub("[REDACTED_EMAIL]", redacted)
    redacted = PHONE_RE.sub("[REDACTED_PHONE]", redacted)
    redacted = SSN_RE.sub("[REDACTED_SSN]", redacted)
    redacted = MRN_RE.sub("[REDACTED_MRN]", redacted)
    redacted = HL7_NAME_RE.sub("[REDACTED_NAME]", redacted)
    redacted = DOB_RE.sub("[REDACTED_DATE]", redacted)
    if max_chars and len(redacted) > max_chars:
        return redacted[:max_chars] + "\n[TRUNCATED]"
    return redacted


def _redact_hl7_segments(text: str) -> str:
    separator = "\r" if "\r" in text else "\n"
    segments = text.split(separator)
    changed = False
    for index, segment in enumerate(segments):
        if segment.startswith("PID|"):
            fields = segment.split("|")
            for field_index in (3, 5, 7, 11, 13, 19):
                if len(fields) > field_index and fields[field_index]:
                    fields[field_index] = "[REDACTED]"
                    changed = True
            segments[index] = "|".join(fields)
    return separator.join(segments) if changed else text
