# TC Downloader

Script de Python que descarga automáticamente todos los archivos disponibles en la página de descargas de [templatesclarion.com](https://templatesclarion.com/downloads/).

---

## Características

- Extrae todos los enlaces de descarga de la página principal usando `BeautifulSoup` y expresiones regulares como fallback.
- Valida que los links pertenezcan al dominio correcto y cumplan el formato esperado (`sdm_process_download=1` + `download_id=<número>`).
- Soporta **reanudación de descargas interrumpidas** mediante el header HTTP `Range`.
- Detecta el nombre del archivo desde el header `Content-Disposition` (soporta `filename*` RFC 5987 y `filename` estándar).
- Sanitiza nombres de archivo para evitar caracteres inválidos en Windows/Linux.
- Evita re-descargar archivos que ya existen con el tamaño correcto.
- Pausa breve entre descargas para no saturar el servidor.

---

## Requisitos

- Python 3.8 o superior
- Dependencias externas:

```
requests
beautifulsoup4
```

Instálalas con:

```bash
pip install requests beautifulsoup4
```

---

## Uso

```bash
python "import os.py" [carpeta_destino]
```

| Argumento         | Descripción                                                        | Default          |
|-------------------|--------------------------------------------------------------------|------------------|
| `carpeta_destino` | Ruta donde se guardarán los archivos descargados (se crea si no existe) | `TC_Downloads/` |

**Ejemplos:**

```bash
# Descarga a la carpeta por defecto (TC_Downloads/)
python "import os.py"

# Descarga a una carpeta personalizada
python "import os.py" D:\Clarion\Templates
```

---

## Flujo de ejecución

```
1. Conecta a https://templatesclarion.com/downloads/
2. Parsea el HTML y extrae todos los links de descarga válidos
3. Por cada link:
   a. Realiza HEAD para obtener nombre y tamaño del archivo
   b. Si el archivo ya existe y el tamaño coincide → lo omite
   c. Si existe pero está incompleto → reanuda desde el byte faltante
   d. Si no existe → descarga completo
4. Muestra resumen final: OK / Fallos / Carpeta
```

---

## Salida esperada

```
Leyendo pagina: https://templatesclarion.com/downloads/
Encontrados 12 links de descarga.

[1/12] https://templatesclarion.com/?sdm_process_download=1&download_id=101
DESCARGADO: MiTemplate.zip (45231 bytes)

[2/12] https://templatesclarion.com/?sdm_process_download=1&download_id=102
OK (ya estaba): OtroTemplate.zip

...

Listo. OK: 11 | Fallos: 1 | Carpeta: D:\Clarion\Templates
```

**Códigos de salida:**

| Código | Significado                                      |
|--------|--------------------------------------------------|
| `0`    | Todas las descargas completadas con éxito        |
| `1`    | Al menos una descarga falló                      |
| `2`    | No se encontraron links de descarga en la página |

---

## Estructura del proyecto

```
Playground.Python/
├── import os.py    # Script principal
└── README.md       # Este archivo
```

---

## Notas

- El script no requiere autenticación. Si la página cambia su estructura HTML o requiere login/cookies en el futuro, la extracción de links podría fallar y se mostrará el mensaje correspondiente.
- El User-Agent enviado se identifica como `PythonDownloader/1.1`.
- Los archivos con nombre no determinable se guardan como `download_<id>.bin`.

---

## Licencia

Uso personal / educativo. Respeta los términos de uso de templatesclarion.com.
