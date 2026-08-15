import re
from typing import Iterable


INTERNAL_DOMAINS = {
    "iapserseguros.seg.ar",
    "institutoseguro.com.ar",
}

GENERIC_DOMAINS = {
    "gmail.com",
    "hotmail.com",
    "outlook.com",
    "live.com",
    "yahoo.com",
    "icloud.com",
    "aol.com",
    "proton.me",
    "protonmail.com",
}

FORWARDED_PREFIXES = ("de:", "from:")
EMAIL_REGEX = re.compile(r"([A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,})", re.IGNORECASE)
INVALID_SHAREPOINT_CHARS = set('"#%*:<>?/\\|')
COMPOUND_SUFFIXES = (
    "com.ar",
    "net.ar",
    "org.ar",
    "gob.ar",
    "edu.ar",
)


def _normalize_domain(domain: str | None) -> str | None:
    if not isinstance(domain, str):
        return None

    normalized = domain.strip().lower().strip(".")
    if not normalized:
        return None

    return normalized


def _extract_email(value: str | None) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None

    match = EMAIL_REGEX.search(value)
    return match.group(1).lower() if match else None


def _extract_forwarded_emails(body: str | None) -> list[str]:
    if not isinstance(body, str) or not body.strip():
        return []

    emails: list[str] = []

    for line in body.splitlines():
        normalized_line = line.strip()
        if not normalized_line:
            continue

        lowered = normalized_line.lower()
        if not lowered.startswith(FORWARDED_PREFIXES):
            continue

        email = _extract_email(normalized_line)
        if email:
            emails.append(email)

    return emails


def _domain_from_email(email: str | None) -> str | None:
    if not isinstance(email, str) or "@" not in email:
        return None

    return _normalize_domain(email.rsplit("@", 1)[1])


def _is_company_domain(domain: str | None) -> bool:
    normalized = _normalize_domain(domain)
    if normalized is None:
        return False

    return normalized not in INTERNAL_DOMAINS and normalized not in GENERIC_DOMAINS


def _pick_candidate(emails: Iterable[str]) -> str | None:
    for email in emails:
        domain = _domain_from_email(email)
        if _is_company_domain(domain):
            return email
    return None


def _domain_label(domain: str) -> str:
    for suffix in COMPOUND_SUFFIXES:
        if domain.endswith(f".{suffix}"):
            remaining = domain[: -(len(suffix) + 1)]
            parts = [part for part in remaining.split(".") if part]
            return parts[-1] if parts else ""

    parts = [part for part in domain.split(".") if part]
    if len(parts) >= 2:
        return parts[-2]
    return parts[0] if parts else ""


def _to_sharepoint_safe_name(value: str) -> str:
    cleaned = value.replace("-", " ").replace("_", " ")
    cleaned = "".join(" " if char in INVALID_SHAREPOINT_CHARS else char for char in cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .")

    if not cleaned or cleaned in {".", ".."} or "@" in cleaned:
        return "Sin identificar"

    return cleaned.title()


def _company_name_from_domain(domain: str | None) -> str:
    normalized = _normalize_domain(domain)
    if normalized is None:
        return "Sin identificar"

    label = _domain_label(normalized)
    safe_name = _to_sharepoint_safe_name(label)
    return safe_name if safe_name != "Sin identificar" else "Sin identificar"


def _unknown_result() -> dict:
    return {
        "name": "Sin identificar",
        "domain": None,
        "source": "unknown",
        "confidence": "unknown",
    }


def detect_company(sender: str | None, subject: str | None, body: str | None) -> dict:
    del subject

    forwarded_email = _pick_candidate(_extract_forwarded_emails(body))
    if forwarded_email:
        domain = _domain_from_email(forwarded_email)
        name = _company_name_from_domain(domain)
        if domain and name != "Sin identificar":
            return {
                "name": name,
                "domain": domain,
                "source": "forwarded_sender",
                "confidence": "high",
            }

    sender_email = _extract_email(sender)
    sender_domain = _domain_from_email(sender_email)
    if _is_company_domain(sender_domain):
        name = _company_name_from_domain(sender_domain)
        if name != "Sin identificar":
            return {
                "name": name,
                "domain": sender_domain,
                "source": "sender",
                "confidence": "high",
            }

    return _unknown_result()
