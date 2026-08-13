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
