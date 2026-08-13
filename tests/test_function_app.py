import base64
import json
from unittest.mock import patch

import pytest

pytest.importorskip("azure.functions")

from services.msg_parser import MsgParseError
from function_app import _extract_request_data, procesar_msg


class DummyRequest:
    def __init__(self, payload=None, error=None):
        self._payload = payload
        self._error = error

    def get_json(self):
        if self._error is not None:
            raise self._error
        return self._payload


def test_extract_request_data_validates_required_fields():
    request = DummyRequest(payload={"fileName": "correo.msg"})

    with pytest.raises(ValueError, match="contentBase64"):
        _extract_request_data(request)


def test_extract_request_data_rejects_invalid_extension():
    request = DummyRequest(
        payload={"fileName": "correo.txt", "contentBase64": base64.b64encode(b"ok").decode()}
    )

    with pytest.raises(ValueError, match=r"\.msg"):
        _extract_request_data(request)


def test_extract_request_data_decodes_base64_and_normalizes_whitespace():
    request = DummyRequest(
        payload={"fileName": "correo.msg", "contentBase64": "bW Vu\nc2FqZQ==".replace(" ", "")}
    )

    file_name, normalized_base64, raw_content = _extract_request_data(request)

    assert file_name == "correo.msg"
    assert normalized_base64 == "bWVuc2FqZQ=="
    assert raw_content == b"mensaje"


def test_procesar_msg_returns_success_response():
    content = base64.b64encode(b"contenido msg").decode()
    request = DummyRequest(
        payload={"fileName": "correo.msg", "contentBase64": content}
    )

    with patch("function_app.parse_msg") as parse_msg_mock:
        parse_msg_mock.return_value = {
            "subject": "Asunto",
            "sender": "remitente@empresa.com",
            "to": "destinatario@empresa.com",
            "cc": "cc@empresa.com",
            "date": "2026-08-13T10:30:00",
            "body": "Hola",
            "attachments": [
                {
                    "index": 0,
                    "fileName": "documento.pdf",
                    "contentType": "application/pdf",
                    "size": 123,
                    "contentBase64": "UERG",
                    "success": True,
                }
            ],
            "attachmentCount": 1,
        }
        response = procesar_msg(request)

    payload = json.loads(response.get_body().decode("utf-8"))

    assert response.status_code == 200
    assert payload["success"] is True
    assert payload["sourceFile"]["fileName"] == "correo.msg"
    assert payload["sourceFile"]["size"] == len(b"contenido msg")
    assert payload["sourceFile"]["contentBase64"] == content
    assert payload["email"]["subject"] == "Asunto"
    assert payload["attachmentCount"] == 1
    assert payload["attachments"][0]["fileName"] == "documento.pdf"


def test_procesar_msg_returns_400_for_invalid_request():
    request = DummyRequest(error=ValueError("invalid json"))

    response = procesar_msg(request)
    payload = json.loads(response.get_body().decode("utf-8"))

    assert response.status_code == 400
    assert payload["success"] is False


def test_procesar_msg_returns_422_for_invalid_msg():
    content = base64.b64encode(b"contenido msg").decode()
    request = DummyRequest(
        payload={"fileName": "correo.msg", "contentBase64": content}
    )

    with patch("function_app.parse_msg", side_effect=MsgParseError("msg parse failure")):
        response = procesar_msg(request)

    payload = json.loads(response.get_body().decode("utf-8"))

    assert response.status_code == 422
    assert payload["success"] is False


def test_procesar_msg_returns_500_for_unexpected_error():
    content = base64.b64encode(b"contenido msg").decode()
    request = DummyRequest(
        payload={"fileName": "correo.msg", "contentBase64": content}
    )

    with patch("function_app._extract_request_data", side_effect=RuntimeError("failure")):
        response = procesar_msg(request)

    payload = json.loads(response.get_body().decode("utf-8"))

    assert response.status_code == 500
    assert payload["success"] is False
