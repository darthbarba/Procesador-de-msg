from datetime import datetime
from unittest.mock import Mock, PropertyMock, patch

import pytest

pytest.importorskip("extract_msg")

from services.msg_parser import (
    MsgParseError,
    _is_allowed_extension,
    _is_inline_or_logo_png,
    _should_include_attachment,
    _get_attachment_filename,
    _get_attachment_mime_type,
    _serialize_attachment,
    parse_msg,
)


def test_get_attachment_filename_prefers_reported_name():
    attachment = Mock()
    attachment.name = r"..\factura.pdf"
    attachment.longFilename = "factura_larga.pdf"
    attachment.shortFilename = "factura.pdf"
    attachment.displayName = None
    attachment.contentId = None
    attachment.cid = None
    attachment.extension = ".pdf"

    assert _get_attachment_filename(attachment, 0) == "factura.pdf"


def test_get_attachment_filename_falls_back_when_missing():
    attachment = Mock()
    attachment.name = ""
    attachment.longFilename = None
    attachment.shortFilename = None
    attachment.displayName = None
    attachment.contentId = None
    attachment.cid = None
    attachment.extension = None
    attachment.type = "unknown"

    assert _get_attachment_filename(attachment, 1) == "attachment_1.bin"


def test_get_attachment_mime_type_uses_guess_from_extension():
    attachment = Mock()
    attachment.mimetype = None

    assert _get_attachment_mime_type(attachment, "documento.pdf") == "application/pdf"


def test_get_attachment_mime_type_prefers_guess_when_reported_is_octet_stream():
    attachment = Mock()
    attachment.mimetype = "application/octet-stream"

    assert _get_attachment_mime_type(attachment, "factura.pdf") == "application/pdf"


def test_get_attachment_mime_type_uses_guess_for_png_without_reported_mime():
    attachment = Mock()
    attachment.mimetype = None

    assert _get_attachment_mime_type(attachment, "imagen.png") == "image/png"


def test_get_attachment_mime_type_falls_back_to_octet_stream():
    attachment = Mock()
    attachment.mimetype = None

    assert _get_attachment_mime_type(attachment, "archivo_extension_desconocida.xyzabc") == "application/octet-stream"


def test_get_attachment_mime_type_preserves_specific_reported_mime():
    attachment = Mock()
    attachment.mimetype = "image/jpeg"

    assert _get_attachment_mime_type(attachment, "archivo.bin") == "image/jpeg"


@pytest.mark.parametrize(
    "filename",
    [
        "factura.pdf",
        "documento.docx",
        "planilla.xlsx",
        "captura.png",
        "FACTURA.PDF",
        "CAPTURA.PNG",
    ],
)
def test_is_allowed_extension_accepts_expected_files(filename):
    assert _is_allowed_extension(filename) is True


@pytest.mark.parametrize(
    "filename",
    [
        "07097587 - 11_12_2020",
        "archivo.exe",
        "archivo.zip",
        "foto.jpg",
    ],
)
def test_is_allowed_extension_rejects_missing_or_disallowed_extensions(filename):
    assert _is_allowed_extension(filename) is False


@pytest.mark.parametrize(
    "filename",
    [
        "image001.png",
        "image023.png",
        "logo.png",
        "logo_empresa.png",
        "signature.png",
        "firma-correo.png",
        "spacer.png",
    ],
)
def test_is_inline_or_logo_png_rejects_known_inline_name_patterns(filename):
    attachment = Mock()
    attachment.hidden = False

    assert _is_inline_or_logo_png(attachment, filename) is True


@pytest.mark.parametrize(
    "filename",
    [
        "factura_escaneada.png",
        "captura_documentacion.png",
        "CAPTURA.PNG",
    ],
)
def test_is_inline_or_logo_png_keeps_regular_png_files(filename):
    attachment = Mock()
    attachment.hidden = False

    assert _is_inline_or_logo_png(attachment, filename) is False


def test_is_inline_or_logo_png_rejects_hidden_png_from_real_extract_msg_signal():
    attachment = Mock()
    attachment.hidden = True

    assert _is_inline_or_logo_png(attachment, "captura.png") is True


def test_is_inline_or_logo_png_does_not_apply_png_rules_to_non_png_files():
    attachment = Mock()
    attachment.hidden = True

    assert _is_inline_or_logo_png(attachment, "factura.pdf") is False


def test_should_include_attachment_accepts_allowed_pdf():
    attachment = Mock()
    attachment.name = "factura.pdf"
    attachment.longFilename = "factura.pdf"
    attachment.shortFilename = "factura.pdf"
    attachment.displayName = None
    attachment.contentId = None
    attachment.cid = None
    attachment.hidden = False
    attachment.extension = ".pdf"

    assert _should_include_attachment(attachment, 0) is True


def test_should_include_attachment_rejects_inline_png_before_serialization():
    attachment = Mock()
    attachment.name = "image001.png"
    attachment.longFilename = "image001.png"
    attachment.shortFilename = "image001.png"
    attachment.displayName = None
    attachment.contentId = "image001.png@cid"
    attachment.cid = "image001.png@cid"
    attachment.hidden = True
    attachment.extension = ".png"
    attachment.data = None
    attachment.asBytes = None

    assert _should_include_attachment(attachment, 0) is False


def test_serialize_attachment_returns_base64_and_size():
    attachment = Mock()
    attachment.name = "imagen.png"
    attachment.longFilename = "imagen.png"
    attachment.shortFilename = "imagen.png"
    attachment.displayName = None
    attachment.contentId = None
    attachment.cid = None
    attachment.data = b"\x01\x02\x03"
    attachment.mimetype = None
    attachment.extension = ".png"

    result = _serialize_attachment(attachment, 0)

    assert result["success"] is True
    assert result["fileName"] == "imagen.png"
    assert result["size"] == 3
    assert result["contentType"] == "image/png"
    assert result["contentBase64"] == "AQID"


def test_serialize_attachment_handles_unsupported_attachment():
    attachment = Mock()
    attachment.name = ""
    attachment.longFilename = None
    attachment.shortFilename = None
    attachment.displayName = None
    attachment.contentId = None
    attachment.cid = None
    attachment.data = None
    attachment.asBytes = None
    attachment.mimetype = None
    attachment.extension = None
    attachment.type = "unsupported"

    result = _serialize_attachment(attachment, 2)

    assert result["success"] is False
    assert result["fileName"] == "attachment_2.bin"
    assert "unsupported attachment data type" in result["error"]


def test_parse_msg_returns_expected_structure_with_multiple_attachments():
    first_attachment = Mock()
    first_attachment.name = "documento.pdf"
    first_attachment.longFilename = "documento.pdf"
    first_attachment.shortFilename = "documento.pdf"
    first_attachment.displayName = None
    first_attachment.contentId = None
    first_attachment.cid = None
    first_attachment.data = b"pdf-data"
    first_attachment.mimetype = None
    first_attachment.extension = ".pdf"

    second_attachment = Mock()
    second_attachment.name = "planilla.xlsx"
    second_attachment.longFilename = "planilla.xlsx"
    second_attachment.shortFilename = "planilla.xlsx"
    second_attachment.displayName = None
    second_attachment.contentId = None
    second_attachment.cid = None
    second_attachment.data = b"\x00\x01"
    second_attachment.mimetype = None
    second_attachment.extension = ".xlsx"
    second_attachment.hidden = False

    fake_msg = Mock()
    fake_msg.subject = "Asunto"
    fake_msg.sender = "remitente@empresa.com"
    fake_msg.to = "destinatario@empresa.com"
    fake_msg.cc = ""
    fake_msg.date = datetime(2026, 8, 13, 10, 30, 0)
    fake_msg.body = "Cuerpo del correo"
    fake_msg.attachments = [first_attachment, second_attachment]

    with patch("services.msg_parser.extract_msg.Message", return_value=fake_msg):
        result = parse_msg("correo.msg")

    assert result["subject"] == "Asunto"
    assert result["sender"] == "remitente@empresa.com"
    assert result["to"] == "destinatario@empresa.com"
    assert result["cc"] == ""
    assert result["date"] == "2026-08-13T10:30:00"
    assert result["body"] == "Cuerpo del correo"
    assert result["company"] == {
        "name": "Empresa",
        "domain": "empresa.com",
        "source": "sender",
        "confidence": "high",
    }
    assert result["attachmentCount"] == 2
    assert result["attachments"][0]["fileName"] == "documento.pdf"
    assert result["attachments"][0]["contentType"] == "application/pdf"
    assert result["attachments"][1]["fileName"] == "planilla.xlsx"
    assert result["attachments"][1]["size"] == 2
    fake_msg.close.assert_called_once_with()


def test_parse_msg_handles_missing_metadata_and_no_attachments():
    fake_msg = Mock()
    fake_msg.subject = None
    fake_msg.sender = None
    fake_msg.to = None
    fake_msg.cc = None
    fake_msg.date = None
    fake_msg.body = None
    fake_msg.attachments = []

    with patch("services.msg_parser.extract_msg.Message", return_value=fake_msg):
        result = parse_msg("correo.msg")

    assert result == {
        "subject": "",
        "sender": "",
        "to": "",
        "cc": "",
        "date": None,
        "body": "",
        "company": {
            "name": "Sin identificar",
            "domain": None,
            "source": "unknown",
            "confidence": "unknown",
        },
        "attachments": [],
        "attachmentCount": 0,
    }


def test_parse_msg_closes_message_when_processing_fails():
    fake_msg = Mock()
    fake_msg.subject = "Asunto"
    fake_msg.sender = "remitente@empresa.com"
    fake_msg.to = "destinatario@empresa.com"
    fake_msg.cc = "cc@empresa.com"
    fake_msg.date = datetime(2026, 8, 13, 10, 30, 0)
    fake_msg.attachments = []
    type(fake_msg).body = PropertyMock(side_effect=RuntimeError("boom"))

    with patch("services.msg_parser.extract_msg.Message", return_value=fake_msg):
        with pytest.raises(MsgParseError):
            parse_msg("correo.msg")

    fake_msg.close.assert_called_once_with()


def test_parse_msg_uses_export_bytes_for_embedded_msg():
    embedded_data = Mock()
    embedded_data.exportBytes.return_value = b"embedded-msg"

    attachment = Mock()
    attachment.name = "correo_adjunto.msg"
    attachment.longFilename = "correo_adjunto.msg"
    attachment.shortFilename = "correo_adjunto.msg"
    attachment.displayName = None
    attachment.contentId = None
    attachment.cid = None
    attachment.data = embedded_data
    attachment.asBytes = None
    attachment.mimetype = None
    attachment.extension = ".msg"

    result = _serialize_attachment(attachment, 0)

    assert result["success"] is True
    assert result["size"] == len(b"embedded-msg")
    assert result["contentBase64"] == "ZW1iZWRkZWQtbXNn"


def test_parse_msg_filters_disallowed_and_inline_attachments():
    pdf_attachment = Mock()
    pdf_attachment.name = "factura.pdf"
    pdf_attachment.longFilename = "factura.pdf"
    pdf_attachment.shortFilename = "factura.pdf"
    pdf_attachment.displayName = None
    pdf_attachment.contentId = None
    pdf_attachment.cid = None
    pdf_attachment.data = b"pdf-data"
    pdf_attachment.mimetype = None
    pdf_attachment.extension = ".PDF"
    pdf_attachment.hidden = False

    png_attachment = Mock()
    png_attachment.name = "captura.png"
    png_attachment.longFilename = "captura.png"
    png_attachment.shortFilename = "captura.png"
    png_attachment.displayName = None
    png_attachment.contentId = None
    png_attachment.cid = None
    png_attachment.data = b"png-data"
    png_attachment.mimetype = None
    png_attachment.extension = ".PNG"
    png_attachment.hidden = False

    inline_attachment = Mock()
    inline_attachment.name = "image001.png"
    inline_attachment.longFilename = "image001.png"
    inline_attachment.shortFilename = "image001.png"
    inline_attachment.displayName = None
    inline_attachment.contentId = "image001.png@cid"
    inline_attachment.cid = "image001.png@cid"
    inline_attachment.data = None
    inline_attachment.asBytes = None
    inline_attachment.mimetype = "image/png"
    inline_attachment.extension = ".png"
    inline_attachment.hidden = True

    disallowed_attachment = Mock()
    disallowed_attachment.name = "archivo.zip"
    disallowed_attachment.longFilename = "archivo.zip"
    disallowed_attachment.shortFilename = "archivo.zip"
    disallowed_attachment.displayName = None
    disallowed_attachment.contentId = None
    disallowed_attachment.cid = None
    disallowed_attachment.data = None
    disallowed_attachment.asBytes = None
    disallowed_attachment.mimetype = "application/zip"
    disallowed_attachment.extension = ".zip"
    disallowed_attachment.hidden = False

    no_extension_attachment = Mock()
    no_extension_attachment.name = "07097587 - 11_12_2020"
    no_extension_attachment.longFilename = "07097587 - 11_12_2020"
    no_extension_attachment.shortFilename = "07097587 - 11_12_2020"
    no_extension_attachment.displayName = None
    no_extension_attachment.contentId = None
    no_extension_attachment.cid = None
    no_extension_attachment.data = None
    no_extension_attachment.asBytes = None
    no_extension_attachment.mimetype = None
    no_extension_attachment.extension = None
    no_extension_attachment.hidden = False

    fake_msg = Mock()
    fake_msg.subject = "Asunto"
    fake_msg.sender = "remitente@empresa.com"
    fake_msg.to = "destinatario@empresa.com"
    fake_msg.cc = ""
    fake_msg.date = datetime(2026, 8, 15, 9, 0, 0)
    fake_msg.body = "Cuerpo"
    fake_msg.attachments = [
        pdf_attachment,
        png_attachment,
        inline_attachment,
        disallowed_attachment,
        no_extension_attachment,
    ]

    with patch("services.msg_parser.extract_msg.Message", return_value=fake_msg):
        result = parse_msg("correo.msg")

    assert result["attachmentCount"] == 2
    assert [item["fileName"] for item in result["attachments"]] == [
        "factura.pdf",
        "captura.png",
    ]
    assert [item["contentType"] for item in result["attachments"]] == [
        "application/pdf",
        "image/png",
    ]
    assert result["company"] == {
        "name": "Empresa",
        "domain": "empresa.com",
        "source": "sender",
        "confidence": "high",
    }
