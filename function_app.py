import base64
import binascii
import json
import logging
import os
import tempfile

import azure.functions as func

from services.msg_parser import MsgParseError, parse_msg


LOGGER = logging.getLogger(__name__)
app = func.FunctionApp()


def _json_response(payload: dict, status_code: int) -> func.HttpResponse:
    return func.HttpResponse(
        body=json.dumps(payload, ensure_ascii=False),
        status_code=status_code,
        mimetype="application/json; charset=utf-8",
    )


def _normalize_base64(value: str) -> str:
    return "".join(value.split())


def _extract_request_data(req: func.HttpRequest) -> tuple[str, str, bytes]:
    try:
        payload = req.get_json()
    except ValueError as exc:
        raise ValueError("El cuerpo debe ser JSON válido.") from exc

    if not isinstance(payload, dict):
        raise ValueError("El cuerpo JSON debe ser un objeto.")

    file_name = payload.get("fileName")
    content_base64 = payload.get("contentBase64")

    if not isinstance(file_name, str) or not file_name.strip():
        raise ValueError("El campo 'fileName' es obligatorio.")

    if not file_name.lower().endswith(".msg"):
        raise ValueError("El archivo debe tener extensión .msg.")

    if not isinstance(content_base64, str) or not content_base64.strip():
        raise ValueError("El campo 'contentBase64' es obligatorio.")

    normalized_base64 = _normalize_base64(content_base64)

    try:
        content = base64.b64decode(normalized_base64, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("El campo 'contentBase64' no contiene Base64 válido.") from exc

    return file_name, normalized_base64, content


@app.route(
    route="procesar-msg",
    methods=["POST"],
    auth_level=func.AuthLevel.FUNCTION,
)
def procesar_msg(req: func.HttpRequest) -> func.HttpResponse:
    temp_path = None

    try:
        file_name, normalized_base64, content = _extract_request_data(req)
        LOGGER.info(
            "Inicio de procesamiento de archivo MSG: %s, size=%s",
            file_name,
            len(content),
        )

        with tempfile.NamedTemporaryFile(delete=False, suffix=".msg") as temp_file:
            temp_file.write(content)
            temp_path = temp_file.name

        parsed_email = parse_msg(temp_path)
        attachment_count = parsed_email.get("attachmentCount", 0)

        response_payload = {
            "success": True,
            "sourceFile": {
                "fileName": file_name,
                "size": len(content),
                "contentBase64": normalized_base64,
            },
            "email": {
                "subject": parsed_email.get("subject", ""),
                "sender": parsed_email.get("sender", ""),
                "to": parsed_email.get("to", ""),
                "cc": parsed_email.get("cc", ""),
                "date": parsed_email.get("date"),
                "body": parsed_email.get("body", ""),
            },
            "company": parsed_email.get(
                "company",
                {
                    "name": "Sin identificar",
                    "domain": None,
                    "source": "unknown",
                    "confidence": "unknown",
                },
            ),
            "attachments": parsed_email.get("attachments", []),
            "attachmentCount": attachment_count,
        }

        LOGGER.info(
            "Procesamiento finalizado para %s con %s adjunto(s).",
            file_name,
            attachment_count,
        )
        return _json_response(response_payload, 200)
    except ValueError as exc:
        LOGGER.warning("Solicitud inválida: %s", exc)
        return _json_response({"success": False, "error": str(exc)}, 400)
    except MsgParseError as exc:
        LOGGER.warning("No fue posible interpretar el MSG: %s", exc)
        return _json_response({"success": False, "error": str(exc)}, 422)
    except Exception:
        LOGGER.exception("Error inesperado al procesar el archivo MSG.")
        return _json_response(
            {
                "success": False,
                "error": "Ocurrió un error interno al procesar el archivo MSG.",
            },
            500,
        )
    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)
