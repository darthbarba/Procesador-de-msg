# Procesador de MSG

## Objetivo

Este proyecto prepara una Azure Function HTTP en Python para recibir archivos `.msg`, extraer metadatos básicos del correo y devolver un JSON consumible por Power Automate.

## Arquitectura

```text
SharePoint
→ Power Automate
→ Azure Function
→ Power Automate
→ SharePoint
```

## Requisitos locales

* Python 3.12
* Azure Functions Core Tools v4
* `.venv`

## Preparación local

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## Ejecución

```powershell
func start
```

## Endpoint

```text
POST /api/procesar-msg
```

## Ejemplo de request

```json
{
  "fileName": "correo.msg",
  "contentBase64": "BASE64_DEL_ARCHIVO_MSG"
}
```

## Response

```json
{
  "success": true,
  "sourceFile": {
    "fileName": "correo.msg",
    "size": 123456,
    "contentBase64": "BASE64_DEL_MSG_ORIGINAL"
  },
  "email": {
    "subject": "Asunto",
    "sender": "usuario@empresa.com",
    "to": "destino@empresa.com",
    "cc": "copia@empresa.com",
    "date": "2026-08-13T10:30:00",
    "body": "Texto completo del mensaje"
  },
  "attachments": [
    {
      "index": 0,
      "fileName": "documento.pdf",
      "contentType": "application/pdf",
      "size": 12345,
      "contentBase64": "BASE64_DEL_ADJUNTO",
      "success": true
    }
  ],
  "attachmentCount": 1
}
```

## Attachments

`contentBase64` representa los bytes reales del archivo codificados en Base64. La respuesta puede incluir adjuntos sin nombre original, adjuntos MSG embebidos y entradas con `success: false` cuando un attachment no puede serializarse sin abortar todo el mensaje.

## Source file

El MSG original también vuelve en Base64 para que Power Automate pueda guardarlo posteriormente en SharePoint sin tener que reconstruirlo.

## Limitaciones

El uso de Base64 incrementa el tamaño transferido y el consumo de memoria. Antes de producción habrá que validar el tamaño máximo de MSG y adjuntos aceptable para Azure Functions y Power Automate.
