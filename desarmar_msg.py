import os
import extract_msg


CARPETA_ENTRADA = r"C:\Users\barba\Desktop\Entrada MSG"
CARPETA_SALIDA = r"C:\Users\barba\Desktop\Procesados MSG"


def procesar_archivos_msg():
    if not os.path.exists(CARPETA_ENTRADA):
        print(f"Error: No existe la carpet: {CARPETA_ENTRADA}")
        return
    
    if not os.path.exists(CARPETA_SALIDA):
        os.makedirs(CARPETA_SALIDA)
        print(f"Se creó la carpeta: {CARPETA_SALIDA}")

    archivos = [f for f in os.listdir(CARPETA_ENTRADA) if f.lower().endswith(".msg")]

    if not archivos:
        print("No se encontraron archivos .msg para procesar en 'Entrada MSG'.")
        return

    print(f"Encontrados {len(archivos)} archivo(s) .msg. Procesando\n")

    for nombre_archivo in archivos:
        ruta_msg = os.path.join(CARPETA_ENTRADA, nombre_archivo)
        print(f"Procesando: {nombre_archivo}")

        try:
            nombre_base = os.path.splitext(nombre_archivo)[0]
            
            carpeta_especifica = os.path.join(CARPETA_SALIDA, nombre_base)
            if not os.path.exists(carpeta_especifica):
                os.makedirs(carpeta_especifica)

            msg = extract_msg.Message(ruta_msg)

            nombre_txt = f"{nombre_base}_TextoPlano.txt"
            ruta_txt = os.path.join(carpeta_especifica, nombre_txt)

            cuerpo_texto = msg.body if msg.body else "El correo no traia texto en el cuerpo."

            with open(ruta_txt, "w", encoding="utf-8") as f:
                f.write(cuerpo_texto)

            print(f"   Creado archivo de texto: {nombre_txt}")

            cant_adjuntos = 0
            for adjunto in msg.attachments:
                adjunto.save(customPath=carpeta_especifica)
                cant_adjuntos += 1

            print(f"    Adjuntos extraídos: {cant_adjuntos}\n")

            msg.close()

        except Exception as e:
            print(f"    Error al procesar {nombre_archivo}: {e}\n")

    print(" finalizado'.")


if __name__ == "__main__":
    procesar_archivos_msg()