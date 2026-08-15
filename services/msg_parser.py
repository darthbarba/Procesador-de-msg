import base64
import logging
import mimetypes
import os
import re
from datetime import date, datetime
from typing import Any

import extract_msg

from services.company_detector import detect_company


LOGGER = logging.getLogger(__name__)
ALLOWED_ATTACHMENT_EXTENSIONS = {
    ".pdf",
    ".docx",
    ".xlsx",
    ".png",
}
INLINE_PNG_NAME_PATTERN = re.compile(r"^image\d+\.png$", re.IGNORECASE)
INLINE_PNG_TERMS = ("logo", "signature", "firma", "spacer")


class MsgParseError(Exception):
    """Raised when a MSG file cannot be parsed into the expected structure."""


def _serialize_date(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time()).isoformat()
    if isinstance(value, str):
        return value
    return str(value)


def _sanitize_filename(candidate: Any) -> str:
    if not isinstance(candidate, str):
        return ""

    normalized = candidate.replace("\\", "/").split("/")[-1].strip().strip(".")
    if not normalized:
        return ""

    safe_chars = []
    for char in normalized:
        if char.isalnum() or char in {" ", ".", "_", "-"}:
            safe_chars.append(char)
        else:
            safe_chars.append("_")

    sanitized = "".join(safe_chars).strip(" .")
    return sanitized


def _default_attachment_name(index: int, attachment: Any) -> str:
    extension = ".bin"

    reported_extension = getattr(attachment, "extension", None)
    if isinstance(reported_extension, str) and reported_extension.strip():
        extension = reported_extension if reported_extension.startswith(".") else f".{reported_extension}"
    elif getattr(attachment, "type", None).__class__.__name__ == "AttachmentType":
        if str(getattr(attachment, "type", "")).lower().endswith("msg"):
            extension = ".msg"

    return f"attachment_{index}{extension}"


def _get_attachment_filename(attachment: Any, index: int) -> str:
    candidates = (
        getattr(attachment, "name", None),
        getattr(attachment, "longFilename", None),
        getattr(attachment, "shortFilename", None),
        getattr(attachment, "displayName", None),
        getattr(attachment, "contentId", None),
        getattr(attachment, "cid", None),
    )

    for candidate in candidates:
        sanitized = _sanitize_filename(candidate)
        if sanitized:
            return sanitized

    return _default_attachment_name(index, attachment)


def _get_attachment_bytes(attachment: Any) -> bytes:
    data = getattr(attachment, "data", None)

    if isinstance(data, bytes):
        return data
    if isinstance(data, bytearray):
        return bytes(data)
    if isinstance(data, memoryview):
        return data.tobytes()
    if hasattr(data, "exportBytes"):
        return data.exportBytes()

    as_bytes = getattr(attachment, "asBytes", None)
    if isinstance(as_bytes, bytes):
        return as_bytes
    if isinstance(as_bytes, bytearray):
        return bytes(as_bytes)
    if isinstance(as_bytes, memoryview):
        return as_bytes.tobytes()

    raise TypeError(f"unsupported attachment data type: {type(data).__name__}")


def _get_attachment_mime_type(attachment: Any, filename: str) -> str:
    reported = getattr(attachment, "mimetype", None)
    if isinstance(reported, str):
        normalized_reported = reported.strip().lower()
        if normalized_reported and normalized_reported != "application/octet-stream":
            return normalized_reported

    guessed, _ = mimetypes.guess_type(filename)
    if guessed:
        return guessed

    return "application/octet-stream"


def _get_attachment_extension(filename: str) -> str:
    _, extension = os.path.splitext(filename)
    return extension.lower()


def _is_allowed_extension(filename: str) -> bool:
    extension = _get_attachment_extension(filename)
    return bool(extension) and extension in ALLOWED_ATTACHMENT_EXTENSIONS


def _is_inline_or_logo_png(attachment: Any, filename: str) -> bool:
    if _get_attachment_extension(filename) != ".png":
        return False

    if getattr(attachment, "hidden", False) is True:
        return True

    normalized_name = filename.lower()
    if INLINE_PNG_NAME_PATTERN.match(normalized_name):
        return True

    return any(term in normalized_name for term in INLINE_PNG_TERMS)


def _should_include_attachment(attachment: Any, index: int) -> bool:
    file_name = _get_attachment_filename(attachment, index)

    if not _is_allowed_extension(file_name):
        return False

    if _is_inline_or_logo_png(attachment, file_name):
        return False

    return True


def _serialize_attachment(attachment: Any, index: int) -> dict:
    file_name = _get_attachment_filename(attachment, index)

    try:
        binary_data = _get_attachment_bytes(attachment)
        content_type = _get_attachment_mime_type(attachment, file_name)
        size = len(binary_data)

        LOGGER.info(
            "Adjunto extraído: index=%s, fileName=%s, size=%s",
            index,
            file_name,
            size,
        )

        return {
            "index": index,
            "fileName": file_name,
            "contentType": content_type,
            "size": size,
            "contentBase64": base64.b64encode(binary_data).decode("ascii"),
            "success": True,
        }
    except Exception as exc:
        LOGGER.warning(
            "No se pudo serializar el adjunto index=%s, fileName=%s: %s",
            index,
            file_name,
            exc,
        )
        return {
            "index": index,
            "fileName": file_name,
            "contentType": _get_attachment_mime_type(attachment, file_name),
            "size": 0,
            "success": False,
            "error": str(exc),
        }


def parse_msg(file_path: str) -> dict:
    msg = None

    try:
        msg = extract_msg.Message(file_path)
        attachments = [
            _serialize_attachment(attachment, index)
            for index, attachment in enumerate(msg.attachments or [])
            if _should_include_attachment(attachment, index)
        ]
        company = detect_company(msg.sender, msg.subject, msg.body)

        return {
            "subject": msg.subject or "",
            "sender": msg.sender or "",
            "to": msg.to or "",
            "cc": msg.cc or "",
            "date": _serialize_date(msg.date),
            "body": msg.body or "",
            "company": company,
            "attachments": attachments,
            "attachmentCount": len(attachments),
        }
    except Exception as exc:
        LOGGER.exception("Error while parsing MSG file: %s", file_path)
        raise MsgParseError(f"No fue posible procesar el archivo MSG: {os.path.basename(file_path)}") from exc
    finally:
        if msg is not None:
            msg.close()
