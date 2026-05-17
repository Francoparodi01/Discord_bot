# Dj Monaco

Bot de musica para Discord con reproduccion desde YouTube, cola, autoplay con feedback persistente y soporte para Docker.

## Funciones

- Reproduce busquedas o URLs directas con `!play`.
- Gestiona cola con `!queue`, `!clear`, `!remove` y `!shuffle`.
- Controla reproduccion con `!pause`, `!resume`, `!skip`, `!next`, `!stop` y `!loop`.
- Muestra el tema actual con `!nowplaying`.
- Aprende del autoplay:
  - si se saltea una recomendacion, la penaliza;
  - si luego se pide manualmente otro tema del mismo artista, favorece esa direccion;
  - guarda el aprendizaje en `data/autoplay_feedback.json`.
- Se desconecta automaticamente despues de 5 minutos si el canal queda sin usuarios humanos.

## Requisitos

- Python 3.13 o Docker.
- Token de bot de Discord.
- `ffmpeg`.

## Configuracion local

1. Copia `.env.example` como `.env`.
2. Completa `DISCORD_TOKEN`.
3. Instala dependencias:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

4. Inicia el bot:

```powershell
.\.venv\Scripts\python.exe app.py
```

## Docker

Levantar:

```powershell
docker compose up -d --build
```

Ver logs en PowerShell:

```powershell
docker compose logs -f | Select-String "Feedback|Autoplay"
```

Ver logs en `cmd`:

```cmd
docker compose logs -f | findstr "Feedback Autoplay"
```

Detener:

```powershell
docker compose down
```

El volumen `./data:/app/data` conserva el aprendizaje de autoplay entre reinicios.

## Comandos

| Comando | Descripcion |
| --- | --- |
| `!play [busqueda o URL]` | Agrega un tema y reproduce si hace falta. |
| `!pause` / `!resume` | Pausa o reanuda. |
| `!skip` / `!next` | Salta el tema actual. |
| `!stop` | Detiene y limpia la cola. |
| `!queue` | Muestra el tema actual y lo que sigue. |
| `!nowplaying` | Muestra el tema actual. |
| `!clear` | Limpia la cola pendiente. |
| `!remove [numero]` | Quita un tema de la cola. |
| `!shuffle` | Mezcla la cola pendiente. |
| `!loop` | Activa o desactiva repeticion del tema actual. |
| `!autoplay on/off` | Activa o desactiva recomendaciones automaticas. |
| `!feedback` | Muestra lo aprendido por autoplay en el servidor. |
| `!volume [0-100]` | Ajusta volumen. |
| `!leave` | Desconecta el bot. |
| `!help` | Lista comandos. |

## Tests

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

## Seguridad

- No subas `.env`.
- No subas `cookies.txt`; si necesitas cookies para videos restringidos, exportalas localmente usando `cookies.example.txt` como referencia.
- Si alguna vez un token o cookie se expone, revocalo y genera uno nuevo.
