# Radar de mazos Marvel Snap

Proyecto local que consulta estadísticas públicas de mazos, guarda en SQLite cada combinación nueva de 12 cartas y mantiene observaciones históricas de sus resultados.

También puede publicarse con GitHub Pages. El flujo incluido en `.github/workflows/update-pages.yml` actualiza y publica el panel automáticamente a las 10:00 y 19:00, hora de Madrid, además de permitir una ejecución manual desde la pestaña Actions.

## Qué considera un mazo nuevo

Un mazo es único por su conjunto de 12 cartas, sin importar el orden ni el nombre. La primera vez que aparece se guarda `first_seen`; las siguientes revisiones actualizan `last_seen`, estadísticas y el contador de apariciones sin duplicarlo.

La fuente inicial es [SnapComplete](https://snapcomplete.com/play/decks), cuyo conjunto público se basa en partidas registradas, excluye bots y se ofrece gratuitamente. Los nombres y metadatos de cartas se completan con el JSON público de Untapped. Las fuentes pueden cambiar sus interfaces; los errores quedan registrados y nunca borran el histórico local.

## Instalación

La forma más sencilla es hacer doble clic en `INSTALAR.bat`. Solo es necesario la primera vez.

Después, haz doble clic en `ACTUALIZAR_Y_ABRIR.bat` para descargar los datos nuevos y abrir el panel. Si únicamente quieres ver lo ya guardado, usa `ABRIR_PANEL.bat`.

Como alternativa, desde PowerShell puedes ejecutar:

```powershell
.\setup.ps1
```

## Buscar y guardar mazos

```powershell
.\.venv\Scripts\python.exe main.py --update
```

La primera ejecución guardará como nuevos todos los mazos encontrados. En las siguientes, solo serán nuevos los conjuntos de cartas que no existían en la base de datos.

## Abrir el panel

```powershell
.\.venv\Scripts\python.exe main.py --open
```

El panel permite buscar cualquier carta, filtrar por arquetipo, mostrar solo mazos nuevos y copiar un código de mazo compatible con Marvel Snap.

## Estadísticas

```powershell
.\.venv\Scripts\python.exe main.py --stats
```

## Automatización opcional

Después de ejecutar `setup.ps1`, instala dos revisiones diarias (10:00 y 19:00):

```powershell
.\setup_scheduler.ps1
```

Para eliminarlas:

```powershell
.\setup_scheduler.ps1 -Uninstall
```

## Configuración

`config.json` permite ajustar el periodo, el mínimo de partidas y el máximo de mazos. Un mínimo bajo descubre más combinaciones, pero también incluye resultados menos fiables.

