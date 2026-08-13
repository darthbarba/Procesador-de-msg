# 1. Estado inicial

* URL del repositorio: `https://github.com/darthbarba/Procesador-de-msg.git`
* Branch actual: `main`
* Commit HEAD: `85aa435c9841f0621bae358c0edb380292df95ae`
* Listado de archivos iniciales:
  * `desarmar_msg.py`

---

# 2. Infraestructura objetivo conocida

```text
Subscription ID:
4947cae9-1f04-41f6-979e-8e05c0e9ef1c

Región:
East US

Resource Group:
IAPSER-Apps

Function App propuesta:
func-iapser-msg-extractor-eus
```

> La infraestructura todavía no fue creada ni modificada por esta tarea.

---

# 3. Integración SharePoint objetivo

```text
Site:
https://incubaconsultores.sharepoint.com/sites/IAPSER-CeluladeAutomatizaciones

Biblioteca:
Documentos compartidos

Carpeta destino:
Procesados msg
```

* Power Automate realizará la integración con SharePoint.
* Azure Function no accederá directamente a SharePoint.
* El archivo MSG original deberá conservarse.
* Los adjuntos deberán conservar su contenido.

---

# 4. Análisis del código existente

## Comportamiento actual

El repositorio contiene un único script Python, `desarmar_msg.py`, orientado a ejecución local en Windows. Su objetivo actual es recorrer una carpeta fija de entrada (`C:\Users\barba\Desktop\Entrada MSG`), abrir cada archivo `.msg`, extraer el cuerpo del correo a un archivo `.txt` y guardar los adjuntos sobre disco dentro de una carpeta de salida (`C:\Users\barba\Desktop\Procesados MSG`).

## Funciones encontradas

* `procesar_archivos_msg()` en `desarmar_msg.py:9`:
  * valida existencia de carpeta de entrada;
  * crea la carpeta de salida si no existe;
  * lista archivos `.msg`;
  * procesa cada archivo;
  * crea una subcarpeta por mensaje;
  * extrae el cuerpo del correo;
  * guarda adjuntos;
  * informa resultados por consola.

## Dependencias

* Explícita:
  * `extract_msg` importada en `desarmar_msg.py:2`.
* Estándar:
  * `os` importada en `desarmar_msg.py:1`.
* Implícita:
  * filesystem local escribible;
  * paths absolutos de Windows;
  * permisos para crear carpetas y archivos;
  * objetos `Message` y `attachments` provistos por `extract-msg`.

## Uso de `extract_msg`

* Crea un objeto `extract_msg.Message(ruta_msg)` en `desarmar_msg.py:37`.
* Lee el cuerpo con `msg.body` en `desarmar_msg.py:42`.
* Itera adjuntos con `msg.attachments` en `desarmar_msg.py:50`.
* Guarda cada adjunto mediante `adjunto.save(customPath=carpeta_especifica)` en `desarmar_msg.py:51`.
* Cierra el objeto con `msg.close()` en `desarmar_msg.py:56`.

## Entradas

* No recibe parámetros de función.
* Toma como entrada todos los archivos `.msg` presentes en la carpeta fija `CARPETA_ENTRADA`.

## Salidas

* Crea carpetas en `CARPETA_SALIDA`.
* Genera un archivo de texto por correo con sufijo `_TextoPlano.txt`.
* Extrae adjuntos como archivos físicos en la carpeta específica del mensaje.
* Emite mensajes de estado y error por consola con `print`.

## Procesamiento del cuerpo

* Usa `msg.body`.
* Si el cuerpo está vacío o es falso, reemplaza por el texto fijo `"El correo no traia texto en el cuerpo."`.
* Escribe el resultado como UTF-8 en disco.

## Procesamiento de adjuntos

* Cuenta adjuntos con un contador manual.
* Recorre `msg.attachments` y delega la persistencia a `adjunto.save`.
* No captura metadatos adicionales de adjuntos como MIME type, tamaño o contenido Base64.

## Manejo de errores

* Si la carpeta de entrada no existe, imprime error y termina.
* Si no encuentra archivos `.msg`, informa y termina.
* Envuelve el procesamiento de cada archivo en `try/except Exception`.
* El error se imprime por consola, pero no se propaga ni se estructura.
* Hay un riesgo confirmado de fuga de recurso si ocurre una excepción después de abrir `msg` y antes de `msg.close()`, porque no se usa `finally` ni context manager.

---

# 5. Componentes reutilizables

* La lógica de filtrado de archivos `.msg` en `desarmar_msg.py:18` es reutilizable como criterio de validación de nombre/origen, aunque en Azure Function deberá aplicarse sobre el `fileName` recibido por HTTP y no sobre un directorio.
* La apertura del mensaje con `extract_msg.Message(...)` en `desarmar_msg.py:37` representa la pieza central reutilizable a nivel conceptual para parsear el MSG, sujeto a refactor para trabajar con archivo temporal o buffer compatible en Linux.
* La lectura del cuerpo mediante `msg.body` en `desarmar_msg.py:42` es reutilizable para poblar el futuro JSON de respuesta.
* La iteración de `msg.attachments` en `desarmar_msg.py:50` es reutilizable como fuente de datos para serializar adjuntos, aunque deberá reemplazarse `save(...)` por extracción a memoria o a almacenamiento temporal controlado.
* El cálculo de `nombre_base = os.path.splitext(nombre_archivo)[0]` en `desarmar_msg.py:31` puede reutilizarse para derivar nombres lógicos del mensaje original.

---

# 6. Componentes a modificar

* Rutas locales:
  * `CARPETA_ENTRADA` y `CARPETA_SALIDA` en `desarmar_msg.py:5-6` dependen de rutas absolutas de Windows y deben eliminarse del flujo principal.
* Entrada de archivos:
  * el barrido de directorio con `os.listdir(CARPETA_ENTRADA)` en `desarmar_msg.py:18` debe reemplazarse por recepción HTTP de `fileName` y `contentBase64`.
* Salida:
  * la generación de archivos y carpetas en disco debe reemplazarse por una respuesta JSON estructurada.
* Filesystem:
  * `os.makedirs(...)` en `desarmar_msg.py:15` y `desarmar_msg.py:35`, junto con `open(..., "w")` en `desarmar_msg.py:44`, no corresponden al diseño final salvo uso temporal controlado.
* Almacenamiento:
  * `adjunto.save(customPath=carpeta_especifica)` en `desarmar_msg.py:51` debe sustituirse por lectura de contenido y serialización para Power Automate.
* Formato de respuesta:
  * los `print(...)` distribuidos en el script deben sustituirse por estructura JSON y códigos HTTP.
* Manejo de archivos temporales:
  * si `extract-msg` requiere un archivo físico, habrá que usar un directorio temporal de manera explícita y con limpieza segura.

---

# 7. Riesgos técnicos

## Riesgo confirmado

* Ejecución Linux:
  * el script actual no es portable porque depende de rutas absolutas de Windows y de carpetas del escritorio.
* Filesystem temporal:
  * la implementación actual asume persistencia en disco local y estructura de carpetas fija, incompatible con el diseño objetivo basado en HTTP + JSON.
* Recursos:
  * `msg.close()` no está protegido por `finally`, por lo que una excepción intermedia puede dejar recursos abiertos.
* Formato de salida:
  * no existe hoy una salida JSON apta para Power Automate.

## Riesgo potencial

* Librería `extract-msg`:
  * debe validarse si la versión a utilizar y sus dependencias transitivas funcionan sin diferencias relevantes en Azure Functions Linux.
* Archivos MSG corruptos:
  * el script captura excepciones generales, pero no distingue errores recuperables de archivos dañados ni devuelve diagnóstico estructurado.
* Archivos grandes:
  * el futuro contrato basado en Base64 incrementará el tamaño en tránsito y en memoria.
* Adjuntos:
  * extraer todos los adjuntos en memoria para respuesta HTTP puede impactar consumo de RAM y tiempo de ejecución.
* Nombres de archivo:
  * nombres con caracteres especiales, muy largos o conflictivos para filesystem temporal pueden requerir saneamiento si se usa almacenamiento intermedio.
* Caracteres especiales:
  * se observan textos con acentos degradados en la salida revisada del archivo, lo que sugiere que habrá que validar codificación de fuente, consola y contenido extraído.
* Adjuntos embebidos:
  * debe validarse cómo expone `extract-msg` elementos embebidos o mensajes adjuntos dentro de `attachments`.

## Validación pendiente

* Confirmar método compatible para procesar contenido MSG recibido como Base64 en Linux:
  * archivo temporal;
  * stream/buffer;
  * API soportada por `extract-msg`.
* Confirmar dependencias exactas del proyecto porque el repositorio no incluye `requirements.txt` ni archivo equivalente.
* Validar límites prácticos de tamaño para solicitudes HTTP con MSG y adjuntos en la futura Azure Function.
* Verificar si es necesario normalizar nombres de archivos adjuntos antes de entregarlos a Power Automate.

---

# 8. Cambios realizados

* Archivos creados:
  * `.gitignore`
  * `docs/EVIDENCIAS.md`
* Archivos modificados:
  * Ninguno
* Archivos eliminados:
  * Ninguno

---

# 9. Validaciones ejecutadas

| Comando | Exit code | Resultado |
| --- | --- | --- |
| `Get-ChildItem -Force` | `0` | Se detectó `.git` y `desarmar_msg.py` en la raíz del repositorio. |
| `rg --files` | `0` | Se listó `desarmar_msg.py` como archivo presente en el repositorio al inicio de la auditoría. |
| `Get-Content -Raw '.\desarmar_msg.py'` | `0` | Se inspeccionó el código fuente completo del script existente. |
| `git branch --show-current` | `0` | Resultado: `main`. |
| `git rev-parse HEAD` | `0` | Resultado: `85aa435c9841f0621bae358c0edb380292df95ae`. |
| `git status --short` | `0` | Sin cambios al momento de la primera ejecución. |
| `git diff --stat` | `0` | Sin diferencias al momento de la primera ejecución. |
| `git remote get-url origin` | `0` | Resultado: `https://github.com/darthbarba/Procesador-de-msg.git`. |
| `rg -n -S "password\|token\|secret\|client_secret\|connection string\|connectionstring\|local\.settings\.json\|\.env" .` | `1` | Sin coincidencias. No se detectaron patrones de secretos en los archivos inspeccionados. |
| `python -m py_compile .\desarmar_msg.py` | `1` | No fue posible ejecutar la validación porque `python` no está disponible en `PATH`. |
| `py -m py_compile .\desarmar_msg.py` | `1` | No fue posible ejecutar la validación porque `py` no está disponible en `PATH`. |
| `$i=1; Get-Content '.\desarmar_msg.py' \| ForEach-Object { '{0,4}: {1}' -f $i, $_; $i++ }` | `0` | Se obtuvo una vista numerada por línea para referenciar el análisis técnico. |

No se ejecutaron pruebas funcionales adicionales porque el entorno no dispone de un ejecutable Python accesible por `PATH` y la tarea restringe cambios no necesarios en la lógica existente.

---

# 10. Git diff

Salida real de `git diff --stat`:

```text

```

Salida real de `git status --short`:

```text
?? .gitignore
?? docs/
```

---

# 11. Pendientes para próxima etapa

* Crear `requirements.txt` o archivo equivalente con versión explícita de `extract-msg` y dependencias necesarias.
* Diseñar y acordar el contrato HTTP definitivo de entrada y salida.
* Separar la lógica reusable de parsing MSG en funciones puras o servicios sin dependencia de rutas locales.
* Definir estrategia segura para procesar el contenido Base64 del MSG en Azure Functions Linux.
* Implementar serialización de metadatos del correo y de adjuntos en JSON.
* Implementar manejo de errores estructurado con respuestas HTTP apropiadas.
* Evaluar límites de tamaño, memoria y tiempos para MSG con adjuntos grandes.
* Añadir pruebas automatizadas con casos de MSG válidos, corruptos y con adjuntos.
* Incorporar luego la estructura mínima de Azure Functions sin acoplarla a SharePoint.

---

## Etapa 2 - Creación de Azure Function local

### Fecha

* 2026-08-13

### Branch

* `main`

### HEAD inicial

* `88a621660e4a666c66ac9e2f03492f780946bf3e`

### Python

* Según `.venv/pyvenv.cfg`, el entorno virtual fue creado con Python `3.12.10`.
* La validación real `python --version` no pudo ejecutarse porque el entorno virtual apunta a `C:\Users\barba\AppData\Local\Programs\Python\Python312\python.exe` y ese ejecutable no está disponible.

### Ubicación del intérprete

* Según `.venv/pyvenv.cfg`: `C:\Users\barba\AppData\Local\Programs\Python\Python312\python.exe`
* La validación real `python -c "import sys; print(sys.executable)"` no pudo ejecutarse por la misma causa.

### Azure Functions Core Tools

* La validación real `func --version` no pudo ejecutarse porque `func` no está disponible en `PATH` en este entorno de trabajo.

### Archivos creados

* `.funcignore`
* `README.md`
* `function_app.py`
* `host.json`
* `local.settings.json.example`
* `requirements.txt`
* `services/__init__.py`
* `services/msg_parser.py`
* `tests/__init__.py`
* `tests/test_function_app.py`
* `tests/test_msg_parser.py`

### Archivos modificados

* `.gitignore`
* `docs/EVIDENCIAS.md`

### Dependencias

Archivo `requirements.txt` creado con:

* `azure-functions`
* `extract-msg`
* `pytest`

### Cambios funcionales implementados

* Se creó una Azure Function Python Programming Model v2 en `function_app.py`.
* Se definió el endpoint HTTP `POST /api/procesar-msg` con `auth_level=func.AuthLevel.FUNCTION`.
* Se implementaron validaciones de:
  * JSON válido;
  * `fileName`;
  * `contentBase64`;
  * extensión `.msg`;
  * Base64 válido.
* Se separó el parser MSG en `services/msg_parser.py`.
* Se implementó uso de archivo temporal para desacoplar el procesamiento de rutas persistentes de Windows.
* Se agregó limpieza del archivo temporal en `finally`.
* Se agregó logging sin exponer cuerpo completo, adjuntos ni Base64.
* Se agregaron tests con mocking para parser y capa HTTP.

### Pruebas ejecutadas

| Comando | Exit code | Resultado |
| --- | --- | --- |
| `& .\.venv\Scripts\Activate.ps1; python --version` | `1` | Falló con `No Python at '"C:\Users\barba\AppData\Local\Programs\Python\Python312\python.exe"'`. |
| `& .\.venv\Scripts\Activate.ps1; python -c "import sys; print(sys.executable)"` | `1` | Falló con `No Python at '"C:\Users\barba\AppData\Local\Programs\Python\Python312\python.exe"'`. |
| `& .\.venv\Scripts\Activate.ps1; func --version` | `1` | Falló porque `func` no se reconoce como comando en el entorno. |
| `& .\.venv\Scripts\Activate.ps1; python -m pip install -r requirements.txt` | `1` | No pudo ejecutarse porque el intérprete configurado por el `.venv` no existe. |
| `& .\.venv\Scripts\Activate.ps1; python -m py_compile function_app.py` | `1` | No pudo ejecutarse porque el intérprete configurado por el `.venv` no existe. |
| `& .\.venv\Scripts\Activate.ps1; python -m py_compile services/msg_parser.py` | `1` | No pudo ejecutarse porque el intérprete configurado por el `.venv` no existe. |
| `& .\.venv\Scripts\Activate.ps1; python -m pytest -v` | `1` | No pudo ejecutarse porque el intérprete configurado por el `.venv` no existe. |
| `& .\.venv\Scripts\Activate.ps1; func start` | `1` | Falló porque `func` no se reconoce como comando en el entorno. |

### Resultado de pytest

* No ejecutado realmente.
* Motivo: el entorno virtual no puede iniciar Python.

### Resultado de compilación Python

* No ejecutado realmente sobre `function_app.py` ni `services/msg_parser.py`.
* Motivo: el entorno virtual no puede iniciar Python.

### Resultado de descubrimiento de Azure Functions

* No fue posible validar el descubrimiento del endpoint porque `func start` no pudo iniciar.
* Error real: `func` no se reconoce como comando en el entorno.

### Errores encontrados

* El archivo `.venv/pyvenv.cfg` referencia una instalación base de Python no disponible:
  * `C:\Users\barba\AppData\Local\Programs\Python\Python312\python.exe`
* No hay `python` accesible en `PATH`.
* No hay `py` accesible en `PATH`.
* No hay `func` accesible en `PATH`.

### Pendientes

* Reparar o recrear el entorno local para disponer de un intérprete Python funcional.
* Asegurar que Azure Functions Core Tools quede accesible como `func`.
* Ejecutar instalación real de dependencias.
* Ejecutar compilación real.
* Ejecutar tests reales.
* Ejecutar `func start` y confirmar descubrimiento del endpoint.
* Implementar en una etapa posterior la extracción avanzada de adjuntos y contenidos Base64.

---

## Etapa 3 - Extracción completa del MSG

### Fecha

* 2026-08-13

### HEAD inicial

* `88a621660e4a666c66ac9e2f03492f780946bf3e`

### Branch

* `main`

### Archivos modificados

* `function_app.py`
* `services/msg_parser.py`
* `tests/test_function_app.py`
* `tests/test_msg_parser.py`
* `README.md`
* `docs/EVIDENCIAS.md`

### Archivos creados

* Ninguno adicional en esta etapa.

### Baseline pytest

* No fue posible ejecutar un baseline real de `python -m pytest -v` antes de modificar porque el entorno virtual sigue apuntando a un ejecutable Python inexistente.
* Resultado real de cualquier intento de invocar `python` con `.venv` activo:
  * `No Python at '"C:\Users\barba\AppData\Local\Programs\Python\Python312\python.exe"'`

### API de `extract-msg` inspeccionada

Se inspeccionó el código fuente instalado de `extract_msg 0.56.0` en `.venv/Lib/site-packages/extract_msg`.

Propiedades reales utilizadas para la estrategia de attachments:

* `AttachmentBase.name`
* `AttachmentBase.longFilename`
* `AttachmentBase.shortFilename`
* `AttachmentBase.displayName`
* `AttachmentBase.contentId`
* `AttachmentBase.cid`
* `AttachmentBase.extension`
* `AttachmentBase.mimetype`
* `AttachmentBase.data`
* `AttachmentBase.dataType`
* `SignedAttachment.asBytes`
* `MSGFile.exportBytes()`

Hallazgos relevantes de tipos:

* `Attachment.data` devuelve `bytes` para adjuntos binarios normales.
* `CustomAttachment.data` devuelve `bytes` o `None`.
* `EmbeddedMsgAttachment.data` devuelve `MSGFile`.
* `SignedAttachment.data` puede devolver `bytes` o `MSGFile`.
* `SignedAttachment.asBytes` conserva los bytes originales firmados.
* `WebAttachment.data` lanza `NotImplementedError`.
* `UnsupportedAttachment.data` devuelve `None`.
* `BrokenAttachment.data` devuelve `None`.

### Estrategia de attachments

* Se mantuvo la separación de responsabilidades:
  * `function_app.py`:
    * HTTP;
    * validaciones;
    * normalización Base64;
    * archivo temporal;
    * respuesta JSON;
    * manejo de errores.
  * `services/msg_parser.py`:
    * apertura del MSG;
    * extracción de metadata;
    * serialización de adjuntos;
    * normalización de fecha;
    * manejo de tipos especiales.
* Se implementó `_get_attachment_filename(attachment, index)` con búsqueda por:
  * `name`;
  * `longFilename`;
  * `shortFilename`;
  * `displayName`;
  * `contentId`;
  * `cid`.
* Si no hay nombre usable:
  * `attachment_0.bin`
  * `attachment_1.bin`
  * etc.
* Se sanea el nombre para evitar:
  * rutas completas;
  * `../`;
  * separadores del sistema operativo;
  * nombres vacíos.
* Se implementó `_get_attachment_bytes(attachment)` con esta prioridad:
  * `attachment.data` si ya es `bytes`;
  * `attachment.data.tobytes()` si es `memoryview`;
  * `attachment.data.exportBytes()` si el dato es un `MSGFile` embebido;
  * `attachment.asBytes` como respaldo para adjuntos firmados.
* Si no se puede convertir un adjunto a bytes:
  * no se aborta todo el mensaje;
  * se registra warning;
  * se devuelve una entrada estructurada con:
    * `index`;
    * `fileName`;
    * `contentType`;
    * `size`;
    * `success: false`;
    * `error`.

### Estrategia MIME

* Primero se usa `attachment.mimetype` si la propiedad existe y trae valor.
* Si no, se usa `mimetypes.guess_type(filename)`.
* Si tampoco se puede inferir:
  * `application/octet-stream`

### Estrategia de nombres

* Los nombres reportados por `extract-msg` se tratan como candidatos, no como rutas confiables.
* La respuesta JSON expone solamente el nombre final saneado del archivo.
* El nombre fallback no depende de Windows ni de rutas locales persistentes.

### Cambios funcionales implementados

* `sourceFile` ahora incluye:
  * `fileName`;
  * `size`;
  * `contentBase64`.
* `parse_msg` ahora devuelve:
  * metadata del email;
  * lista completa de adjuntos serializables;
  * `attachmentCount`.
* Cada adjunto exitoso devuelve:
  * `index`;
  * `fileName`;
  * `contentType`;
  * `size`;
  * `contentBase64`;
  * `success: true`.
* La Function ahora normaliza `contentBase64` de entrada removiendo espacios y saltos de línea antes de validar.
* Se incorporó `MsgParseError` para diferenciar fallas de interpretación del MSG.
* La respuesta HTTP ahora utiliza:
  * `400` para input inválido;
  * `422` para MSG no procesable;
  * `500` para errores inesperados.

### Tests nuevos o ampliados

Se agregaron o ampliaron tests para cubrir:

* attachment con nombre y bytes;
* attachment sin nombre;
* MIME inferido desde extensión;
* MIME desconocido;
* cálculo de `size`;
* Base64 correcto;
* múltiples attachments;
* mensaje sin attachments;
* fecha `datetime`;
* metadata faltante;
* uso de `exportBytes()` para MSG embebido;
* response definitivo de `function_app.py`;
* respuesta `422` para error de parsing;
* normalización de Base64 con whitespace.

### Prueba con archivo MSG real

* Se ejecutó:
  * `rg --files -g '*.msg'`
* Resultado:
  * sin archivos `.msg` de ejemplo en el repositorio.
* Estado:
  * `Prueba real pendiente: se requiere archivo MSG de ejemplo.`

### Validaciones ejecutadas

| Comando | Exit code | Resultado |
| --- | --- | --- |
| `rg --files -g '*.msg'` | `1` | No se encontraron archivos `.msg` de ejemplo en el repositorio. |
| `& .\.venv\Scripts\Activate.ps1; python -m py_compile function_app.py` | `1` | Falló con `No Python at '"C:\Users\barba\AppData\Local\Programs\Python\Python312\python.exe"'`. |
| `& .\.venv\Scripts\Activate.ps1; python -m py_compile services/msg_parser.py` | `1` | Falló con `No Python at '"C:\Users\barba\AppData\Local\Programs\Python\Python312\python.exe"'`. |
| `& .\.venv\Scripts\Activate.ps1; python -m pytest -v` | `1` | Falló con `No Python at '"C:\Users\barba\AppData\Local\Programs\Python\Python312\python.exe"'`. |
| `& .\.venv\Scripts\Activate.ps1; func start` | `1` | Falló porque `func` no se reconoce como comando en el entorno. |
| `git status --short` | `0` | Se confirmó que no aparecen `local.settings.json` ni `.venv/` en el estado de Git. |
| `git diff --stat` | `0` | Se obtuvo el resumen actual del diff para esta revisión. |

### Pytest final

* No ejecutado realmente.
* Motivo:
  * el entorno virtual no puede iniciar Python.

### Compilación

* No ejecutada realmente.
* Motivo:
  * el entorno virtual no puede iniciar Python.

### Function discovery

* No fue posible validar el discovery real del endpoint con `func start`.
* Error observado:
  * `func` no se reconoce como comando en el entorno.

### Warnings

* Warning persistente de entorno local:
  * el `.venv` referencia un Python base inexistente.
* Warning persistente para desarrollo local:
  * `func` no está disponible en `PATH`.
* Warning pendiente de infraestructura:
  * `AzureWebJobsStorage` vacío no fue modificado en esta etapa.
* Warning de Git:
  * conversión `LF -> CRLF` advertida por `git diff --stat` en archivos versionados.

### Pendientes

* Reparar el entorno para poder ejecutar:
  * `python -m py_compile function_app.py`
  * `python -m py_compile services/msg_parser.py`
  * `python -m pytest -v`
  * `func start`
* Validar el endpoint local con un `400` real para input inválido una vez que `func` esté disponible.
* Ejecutar una prueba real con archivo `.msg` de ejemplo.
* Confirmar el comportamiento exacto de adjuntos `WEB`, `UNSUPPORTED` y `BROKEN` con muestras reales.
* Validar límites de tamaño por expansión Base64 antes de producción.

---

## Etapa 4 - GitHub Actions y despliegue OIDC

### Fecha

* 2026-08-13

### Workflow creado

* `.github/workflows/deploy-azure-function.yml`

### Trigger

* `push` sobre `main`
* `workflow_dispatch`

### Permisos

* `contents: read`
* `id-token: write`

`id-token: write` se configuró de forma explícita para autenticación OIDC con Azure.

### Versión Python

* `actions/setup-python@v5`
* `python-version: "3.12"`

### Estrategia de tests

El job `test-and-deploy` ejecuta:

* `python -m pip install --upgrade pip`
* `python -m pip install -r requirements.txt`
* `python -m pytest -v`

El deployment queda secuenciado después de los tests dentro del mismo job, por lo que no se ejecuta si `pytest` falla.

### Estrategia de autenticación OIDC

Se configuró `azure/login@v2` con:

* `client-id: ${{ vars.AZURE_CLIENT_ID }}`
* `tenant-id: ${{ vars.AZURE_TENANT_ID }}`
* `subscription-id: ${{ vars.AZURE_SUBSCRIPTION_ID }}`

No se utilizó:

* `creds`
* client secret
* publish profile
* credenciales embebidas en YAML

### Estrategia de deployment

Se configuró `Azure/functions-action@v1` con:

* `app-name: ${{ vars.AZURE_FUNCTIONAPP_NAME }}`
* `package: "."`
* `remote-build: true`

No se incluyó:

* `publish-profile`
* `scm-do-build-during-deployment`
* `enable-oryx-build`

### Archivos modificados

* `.github/workflows/deploy-azure-function.yml`
* `README.md`
* `docs/EVIDENCIAS.md`

### Referencias oficiales consultadas

Fuentes oficiales revisadas para esta etapa:

* Microsoft Learn:
  * `Deploy to Azure Functions by using GitHub Actions`
  * `Authenticate to Azure from GitHub Actions by OpenID Connect`
* Repositorios oficiales:
  * `Azure/functions-action`
  * `Azure/login`

### Validaciones locales posibles

| Comando | Exit code | Resultado |
| --- | --- | --- |
| `python -m pytest -v` | Pendiente de ejecución real | El entorno local debe ejecutar este comando antes de publicar el workflow. |

No se afirmó éxito en GitHub Actions ni en Azure porque esta etapa no incluye `commit`, `push` ni corrida remota real del workflow.

### Pendientes

* Ejecutar `python -m pytest -v` localmente con el entorno funcional.
* Hacer `commit`.
* Hacer `push`.
* Verificar la primera ejecución real en GitHub Actions.
* Validar el deployment real sobre Azure una vez publicado el workflow.

---

## Etapa 5 - Procesamiento end-to-end con Power Automate

### Fecha

* 2026-08-13

### Circuito validado

Se validó exitosamente el siguiente circuito completo:

`SharePoint Entrada MSG → Power Automate → Azure Function → procesamiento extract-msg → respuesta JSON → Power Automate → SharePoint Procesados msg`

### Resultado de la prueba end-to-end

La prueba real confirmó:

* detección automática de un `.msg` nuevo;
* obtención del contenido del MSG;
* llamada HTTP exitosa a la Azure Function;
* análisis de la respuesta JSON;
* creación automática de una carpeta por MSG;
* almacenamiento del MSG original;
* creación del archivo con los datos y cuerpo del correo;
* extracción de los adjuntos;
* reconstrucción de los adjuntos desde Base64;
* almacenamiento de los adjuntos en SharePoint;
* validación visual de los archivos resultantes.

### Evidencia visual

![Captura del flujo en Power Automate](evidencias/Captura%20de%20pantalla%202026-08-13%20190653.png)

![Captura de los archivos generados en SharePoint](evidencias/Captura%20de%20pantalla%202026-08-13%20191002.png)

### Observaciones

* La evidencia visual ya se encuentra almacenada en `docs/evidencias/`.
* Esta etapa documenta una prueba exitosa del circuito completo, sin modificar código ni infraestructura.
