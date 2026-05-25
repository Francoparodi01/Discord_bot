import asyncio
import difflib
import json
import logging
import os
import random
import re
from collections import Counter, deque

import discord
import yt_dlp
from dotenv import load_dotenv
from youtube_search import YoutubeSearch


load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
AUDIO_MODE = os.getenv("AUDIO_MODE", "download").strip().lower()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("dj_monaco")

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

voice_clients = {}
queues = {}
current_song = {}
song_history = {}
autoplay_flags = {}
play_locks = {}
autoplay_feedback = {}
repeat_modes = {}
manual_advance_requests = set()
idle_disconnect_tasks = {}
URL_PATTERN = re.compile(r"^https?://", re.IGNORECASE)
DATA_DIR = "data"
FEEDBACK_FILE = os.path.join(DATA_DIR, "autoplay_feedback.json")
DOWNLOAD_DIR = "downloads"
IDLE_DISCONNECT_SECONDS = 300
AUTOPLAY_BLOCKED_TERMS = (
    "cover",
    "karaoke",
    "reaction",
    "tutorial",
    "live",
    "en vivo",
)


def cookiefile_valido(path):
    if not os.path.exists(path):
        return False
    try:
        with open(path, "r", encoding="utf-8") as file:
            first_line = file.readline().strip()
    except OSError as error:
        logger.warning("No pude leer %s: %s", path, error)
        return False
    return first_line == "# Netscape HTTP Cookie File"

yt_dl_options = {
    "format": "bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio/best",
    "noplaylist": True,
    "extractaudio": True,
    "audioquality": 1,
    "outtmpl": os.path.join(DOWNLOAD_DIR, "%(id)s.%(ext)s"),
    "restrictfilenames": True,
    "quiet": True,
    "noprogress": True,
    "nocheckcertificate": True,
    "retries": 10,
    "fragment_retries": 10,
    "continuedl": True,
    "js_runtimes": {"node": {}},
    "remote_components": ["ejs:npm"],
}
if cookiefile_valido("cookies.txt"):
    yt_dl_options["cookiefile"] = "cookies.txt"
elif os.path.exists("cookies.txt"):
    logger.warning("cookies.txt existe, pero no tiene formato Netscape valido; se ignora.")

remote_ffmpeg_before_options = (
    "-nostdin "
    "-reconnect 1 "
    "-reconnect_streamed 1 "
    "-reconnect_at_eof 1 "
    "-reconnect_on_network_error 1 "
    "-reconnect_delay_max 5"
)


def limpiar_titulo(titulo):
    titulo = re.sub(r"\(.*?\)|\[.*?\]", "", titulo).lower()
    for palabra in ["letra", "karaoke", "oficial", "audio", "video", "hd", "live", "remasterizado"]:
        titulo = titulo.replace(palabra, "")
    return titulo.strip()


def extraer_artista(titulo):
    partes = titulo.split(" - ")
    return partes[0] if len(partes) > 1 else titulo


def resolver_artista(data, titulo):
    for key in ("artist", "creator", "uploader", "channel"):
        value = data.get(key)
        if value:
            return value
    return extraer_artista(titulo)


def limpiar_artista(artista):
    return limpiar_titulo(artista)


def limpiar_estado(guild_id):
    for data in (
        voice_clients,
        queues,
        current_song,
        autoplay_flags,
        song_history,
        play_locks,
        repeat_modes,
    ):
        data.pop(guild_id, None)
    manual_advance_requests.discard(guild_id)
    cancelar_desconexion_inactiva(guild_id)


def obtener_lock(guild_id):
    return play_locks.setdefault(guild_id, asyncio.Lock())


def obtener_cola(guild_id):
    return queues.setdefault(guild_id, deque())


def obtener_feedback(guild_id):
    return autoplay_feedback.setdefault(
        guild_id,
        {
            "artist_scores": Counter(),
            "rejected_titles": Counter(),
            "preferred_titles": Counter(),
        },
    )


def clonar_cancion(song):
    return dict(song)


def serializar_feedback():
    return {
        str(guild_id): {
            "artist_scores": dict(feedback["artist_scores"]),
            "rejected_titles": dict(feedback["rejected_titles"]),
            "preferred_titles": dict(feedback["preferred_titles"]),
        }
        for guild_id, feedback in autoplay_feedback.items()
    }


def guardar_feedback():
    os.makedirs(DATA_DIR, exist_ok=True)
    temp_file = f"{FEEDBACK_FILE}.tmp"
    with open(temp_file, "w", encoding="utf-8") as file:
        json.dump(serializar_feedback(), file, ensure_ascii=True, indent=2, sort_keys=True)
    os.replace(temp_file, FEEDBACK_FILE)


def cargar_feedback():
    if not os.path.exists(FEEDBACK_FILE):
        return

    try:
        with open(FEEDBACK_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)
    except (OSError, json.JSONDecodeError) as error:
        logger.warning("No pude cargar historial persistido: %s", error)
        return

    for guild_id, feedback in data.items():
        autoplay_feedback[int(guild_id)] = {
            "artist_scores": Counter(feedback.get("artist_scores", {})),
            "rejected_titles": Counter(feedback.get("rejected_titles", {})),
            "preferred_titles": Counter(feedback.get("preferred_titles", {})),
        }

    logger.info("Historial de feedback cargado para %s servidor(es).", len(autoplay_feedback))


def seleccionar_entrada(data):
    if data.get("entries"):
        return next((entry for entry in data["entries"] if entry), None)
    return data


def obtener_archivo_descargado(data):
    for download in data.get("requested_downloads") or []:
        filepath = download.get("filepath")
        if filepath and os.path.exists(filepath):
            return filepath

    for key in ("filepath", "_filename", "filename"):
        filepath = data.get(key)
        if filepath and os.path.exists(filepath):
            return filepath

    return None


def opciones_ffmpeg(song):
    before_options = "-nostdin" if song.get("is_local") else remote_ffmpeg_before_options
    return {
        "before_options": before_options,
        "options": "-vn",
    }


async def extraer_info(query, download=False):
    objetivo = query if URL_PATTERN.match(query) else f"ytsearch1:{query}"
    ytdl = yt_dlp.YoutubeDL(yt_dl_options)
    loop = asyncio.get_running_loop()
    data = await loop.run_in_executor(
        None,
        lambda: ytdl.extract_info(objetivo, download=download),
    )

    return seleccionar_entrada(data)


async def crear_cancion(query):
    download = AUDIO_MODE != "stream"
    data = await extraer_info(query, download=download)
    if not data:
        return None
    title = data.get("title", "Tema sin titulo")
    audio_file = obtener_archivo_descargado(data)
    audio_source = audio_file or data.get("url")

    if not audio_source:
        return None

    if download and not audio_file:
        logger.warning("No pude encontrar archivo descargado para %s; usando stream remoto.", title)

    return {
        "title": title,
        "url": audio_source,
        "stream_url": data["url"],
        "artist": resolver_artista(data, title),
        "video_id": data.get("id"),
        "webpage_url": data.get("webpage_url"),
        "is_local": bool(audio_file),
        "source": "manual",
    }


def puntuar_candidato(candidato, titulo_original, historial, feedback):
    candidato_original = candidato.lower()
    candidato_limpio = limpiar_titulo(candidato)
    titulo_limpio = limpiar_titulo(titulo_original)
    similitud = difflib.SequenceMatcher(None, titulo_limpio, candidato_limpio).ratio()

    if similitud > 0.8 or candidato_limpio in historial:
        return None
    if any(term in candidato_original for term in AUTOPLAY_BLOCKED_TERMS):
        return None

    score = 0
    score -= feedback["rejected_titles"][candidato_limpio] * 10
    score += feedback["preferred_titles"][candidato_limpio] * 4

    artista_candidato = limpiar_artista(extraer_artista(candidato))
    score += feedback["artist_scores"][artista_candidato] * 2
    return score


def registrar_skip_autoplay(guild_id):
    song = current_song.get(guild_id)
    if not song or song.get("source") != "autoplay":
        return

    feedback = obtener_feedback(guild_id)
    feedback["rejected_titles"][limpiar_titulo(song["title"])] += 1
    feedback["artist_scores"][limpiar_artista(song["artist"])] -= 1
    guardar_feedback()
    logger.info("Skip autoplay: %s", song["title"])


def registrar_preferencia_manual(guild_id, song):
    autoplay_song = current_song.get(guild_id)
    if not autoplay_song or autoplay_song.get("source") != "autoplay":
        return

    artista_autoplay = limpiar_artista(autoplay_song["artist"])
    artista_manual = limpiar_artista(song["artist"])
    if artista_autoplay != artista_manual:
        return

    feedback = obtener_feedback(guild_id)
    feedback["artist_scores"][artista_manual] += 2
    feedback["preferred_titles"][limpiar_titulo(song["title"])] += 1
    guardar_feedback()
    logger.info("Mismo artista preferido: %s -> %s", song["artist"], song["title"])


async def buscar_relacionada(titulo_original, artista, historial, feedback):
    query = f"{artista} canciones"
    logger.info("Buscando canciones de: %s", artista)
    try:
        resultados = YoutubeSearch(query, max_results=10).to_dict()
        historial_limpio = {limpiar_titulo(s) for s in historial}
        candidatos = []

        for resultado in resultados:
            candidato = resultado["title"]
            score = puntuar_candidato(candidato, titulo_original, historial_limpio, feedback)
            if score is None:
                continue
            candidatos.append((score, candidato, resultado["url_suffix"]))

        if candidatos:
            score, candidato, url_suffix = max(candidatos, key=lambda item: item[0])
            logger.info("Relacionada aceptada: %s (score=%s)", candidato, score)
            return f"https://www.youtube.com{url_suffix}", candidato
    except Exception as error:
        logger.exception("Error en busqueda relacionada: %s", error)

    return None, None


def iniciar_reproduccion(guild_id, voice_client, song):
    current_song[guild_id] = song
    source = discord.PCMVolumeTransformer(
        discord.FFmpegPCMAudio(song["url"], **opciones_ffmpeg(song))
    )
    origen = "archivo local" if song.get("is_local") else "stream remoto"
    logger.info("Reproduccion: %s (%s)", song["title"], origen)

    loop = asyncio.get_running_loop()

    def after_playing(error):
        if error:
            logger.error("Error al reproducir: %s", error)
        asyncio.run_coroutine_threadsafe(play_next(guild_id), loop)

    voice_client.play(source, after=after_playing)


async def play_next(guild_id):
    async with obtener_lock(guild_id):
        voice_client = voice_clients.get(guild_id)
        if not voice_client or not voice_client.is_connected():
            limpiar_estado(guild_id)
            return

        if voice_client.is_playing() or voice_client.is_paused():
            return

        current = current_song.get(guild_id)
        should_repeat = (
            current
            and repeat_modes.get(guild_id) == "song"
            and guild_id not in manual_advance_requests
        )
        manual_advance_requests.discard(guild_id)

        if should_repeat:
            iniciar_reproduccion(guild_id, voice_client, clonar_cancion(current))
            return

        if queues.get(guild_id):
            iniciar_reproduccion(guild_id, voice_client, queues[guild_id].popleft())
            return

        if current_song.get(guild_id) and autoplay_flags.get(guild_id, False):
            last_song = current_song[guild_id]
            last_title = last_song["title"]
            last_artist = last_song["artist"]
            song_history.setdefault(guild_id, []).append(last_title)
            feedback = obtener_feedback(guild_id)
            url, title = await buscar_relacionada(
                last_title,
                last_artist,
                song_history[guild_id],
                feedback,
            )

            if url:
                try:
                    song = await crear_cancion(url)
                    if song:
                        song["title"] = title
                        song["artist"] = resolver_artista(song, title)
                        song["source"] = "autoplay"
                        obtener_cola(guild_id).append(song)
                        logger.info("Autoplay agregando: %s", title)
                except Exception as error:
                    logger.exception("Error al preparar autoplay: %s", error)

            if queues.get(guild_id):
                iniciar_reproduccion(guild_id, voice_client, queues[guild_id].popleft())
                return

        await voice_client.disconnect()
        logger.info("Sesion finalizada.")
        limpiar_estado(guild_id)


def hay_usuarios_humanos(voice_client):
    return any(not member.bot for member in voice_client.channel.members)


def cancelar_desconexion_inactiva(guild_id):
    task = idle_disconnect_tasks.pop(guild_id, None)
    if task and not task.done():
        task.cancel()


def programar_desconexion_inactiva(guild_id):
    cancelar_desconexion_inactiva(guild_id)

    async def desconectar_si_sigue_vacio():
        try:
            await asyncio.sleep(IDLE_DISCONNECT_SECONDS)
            voice_client = voice_clients.get(guild_id)
            if voice_client and voice_client.is_connected() and not hay_usuarios_humanos(voice_client):
                await voice_client.disconnect()
                logger.info("Canal vacio durante %s segundos; desconectando.", IDLE_DISCONNECT_SECONDS)
                limpiar_estado(guild_id)
        except asyncio.CancelledError:
            return

    idle_disconnect_tasks[guild_id] = asyncio.create_task(desconectar_si_sigue_vacio())


@client.event
async def on_ready():
    logger.info("Bot conectado como %s", client.user)


@client.event
async def on_voice_state_update(member, before, after):
    if member.bot:
        return

    guild_id = member.guild.id
    voice_client = voice_clients.get(guild_id)
    if not voice_client or not voice_client.is_connected():
        return

    if hay_usuarios_humanos(voice_client):
        cancelar_desconexion_inactiva(guild_id)
    else:
        programar_desconexion_inactiva(guild_id)


@client.event
async def on_message(msg):
    if msg.author == client.user or not msg.guild:
        return

    gid = msg.guild.id
    content = msg.content.strip()

    if content.startswith("!play"):
        if not msg.author.voice:
            await msg.channel.send("Conectate a un canal de voz primero.")
            return

        search = content.partition(" ")[2].strip()
        if not search:
            await msg.channel.send("Decime que cancion queres.")
            return

        voice_client = voice_clients.get(gid)
        try:
            if not voice_client or not voice_client.is_connected():
                voice_client = await msg.author.voice.channel.connect(reconnect=False)
                voice_clients[gid] = voice_client
            elif voice_client.channel != msg.author.voice.channel:
                await voice_client.move_to(msg.author.voice.channel)
        except discord.errors.ConnectionClosed as error:
            limpiar_estado(gid)
            if getattr(error, "code", None) == 4017:
                await msg.channel.send(
                    "Discord rechazo la conexion de voz (4017). "
                    "La libreria actual no soporta el protocolo DAVE requerido por Discord."
                )
            else:
                await msg.channel.send("No pude conectarme al canal de voz.")
            logger.error("Error al conectar voz: %s", error)
            return

        try:
            song = await crear_cancion(search)
        except Exception as error:
            logger.exception("Error al buscar tema: %s", error)
            await msg.channel.send("No pude encontrar esa cancion.")
            return

        if not song:
            await msg.channel.send("No pude encontrar esa cancion.")
            return

        registrar_preferencia_manual(gid, song)
        obtener_cola(gid).append(song)
        await msg.channel.send(f"Agregado: {song['title']}")
        cancelar_desconexion_inactiva(gid)

        if not voice_client.is_playing() and not voice_client.is_paused():
            await play_next(gid)

    elif content.startswith("!skip"):
        if voice_clients.get(gid):
            registrar_skip_autoplay(gid)
            manual_advance_requests.add(gid)
            voice_clients[gid].stop()
            await msg.channel.send("Cancion omitida.")

    elif content.startswith("!next"):
        if voice_clients.get(gid):
            registrar_skip_autoplay(gid)
            manual_advance_requests.add(gid)
            voice_clients[gid].stop()
            await msg.channel.send("Siguiente cancion en cola.")
        else:
            await msg.channel.send("No estoy reproduciendo nada.")

    elif content.startswith("!stop"):
        if voice_clients.get(gid):
            queues[gid] = deque()
            autoplay_flags[gid] = False
            repeat_modes[gid] = "off"
            current_song.pop(gid, None)
            manual_advance_requests.add(gid)
            voice_clients[gid].stop()
            await msg.channel.send("Reproduccion detenida.")
        else:
            await msg.channel.send("No estoy reproduciendo nada.")

    elif content.startswith("!clear"):
        queue = queues.get(gid)
        if queue:
            queue.clear()
            await msg.channel.send("Cola limpiada.")
        else:
            await msg.channel.send("La cola ya esta vacia.")

    elif content.startswith("!remove"):
        queue = queues.get(gid)
        try:
            index = int(content.split()[1]) - 1
        except (IndexError, ValueError):
            await msg.channel.send("Usa !remove [numero].")
            return

        if not queue or index < 0 or index >= len(queue):
            await msg.channel.send("Ese numero no existe en la cola.")
        else:
            song = queue[index]
            del queue[index]
            await msg.channel.send(f"Quitado: {song['title']}")

    elif content.startswith("!shuffle"):
        queue = queues.get(gid)
        if queue and len(queue) > 1:
            songs = list(queue)
            random.shuffle(songs)
            queues[gid] = deque(songs)
            await msg.channel.send("Cola mezclada.")
        else:
            await msg.channel.send("No hay suficientes canciones para mezclar.")

    elif content.startswith("!loop"):
        current_mode = repeat_modes.get(gid, "off")
        repeat_modes[gid] = "off" if current_mode == "song" else "song"
        estado = "activado" if repeat_modes[gid] == "song" else "desactivado"
        await msg.channel.send(f"Loop de cancion {estado}.")

    elif content.startswith("!volume"):
        if voice_clients.get(gid):
            try:
                volume = int(content.split()[1])
                if 0 <= volume <= 100:
                    voice_clients[gid].source.volume = volume / 100
                    await msg.channel.send(f"Volumen ajustado a {volume}%")
                else:
                    await msg.channel.send("El volumen debe estar entre 0 y 100.")
            except (IndexError, ValueError):
                await msg.channel.send("Usa !volume [0-100] para ajustar el volumen.")
        else:
            await msg.channel.send("No estoy reproduciendo nada.")

    elif content.startswith("!pause"):
        if voice_clients.get(gid):
            voice_clients[gid].pause()
            await msg.channel.send("Pausado.")

    elif content.startswith("!resume"):
        if voice_clients.get(gid):
            voice_clients[gid].resume()
            await msg.channel.send("Reanudado.")

    elif content.startswith("!leave"):
        if gid in voice_clients:
            await voice_clients[gid].disconnect()
            limpiar_estado(gid)
            await msg.channel.send("Desconectado.")
        else:
            await msg.channel.send("No estoy en un canal.")

    elif content.startswith("!queue"):
        queue = queues.get(gid, [])
        actual = current_song.get(gid)
        if queue or actual:
            lineas = []
            if actual:
                lineas.append(f"Sonando ahora: {actual['title']}")
            if queue:
                lineas.append("Sigue:")
                lineas.extend(
                    f"{index + 1}. {song['title']}"
                    for index, song in enumerate(queue)
                )
            await msg.channel.send("\n".join(lineas))
        else:
            await msg.channel.send("La cola esta vacia.")

    elif content.startswith("!nowplaying"):
        song = current_song.get(gid)
        if song:
            await msg.channel.send(f"Sonando ahora: {song['title']}")
        else:
            await msg.channel.send("No estoy reproduciendo nada.")

    elif content.startswith("!feedback"):
        feedback = autoplay_feedback.get(gid)
        if not feedback:
            await msg.channel.send("Todavia no aprendi nada en este servidor.")
        else:
            top_artistas = feedback["artist_scores"].most_common(3)
            rechazadas = feedback["rejected_titles"].most_common(3)
            preferidas = feedback["preferred_titles"].most_common(3)
            lineas = ["Aprendizaje actual:"]
            if top_artistas:
                lineas.append(
                    "Artistas: " + ", ".join(f"{name} ({score})" for name, score in top_artistas)
                )
            if preferidas:
                lineas.append(
                    "Temas preferidos: " + ", ".join(f"{name} ({score})" for name, score in preferidas)
                )
            if rechazadas:
                lineas.append(
                    "Temas rechazados: " + ", ".join(f"{name} ({score})" for name, score in rechazadas)
                )
            await msg.channel.send("\n".join(lineas))

    elif content.startswith("!autoplay on"):
        autoplay_flags[gid] = True
        await msg.channel.send("Autoplay activado.")

    elif content.startswith("!autoplay off"):
        autoplay_flags[gid] = False
        await msg.channel.send("Autoplay desactivado.")

    elif content.startswith("!help"):
        await msg.channel.send(
            """
**Comandos disponibles**
- !play [nombre]: Reproduce una cancion
- !skip / !next: Omite la cancion actual
- !pause / !resume
- !queue: Ver la cola
- !nowplaying: Ver el tema actual
- !clear: Limpiar la cola pendiente
- !remove [numero]: Quitar un tema de la cola
- !shuffle: Mezclar la cola
- !loop: Repetir la cancion actual
- !feedback: Ver lo aprendido por autoplay
- !leave: Salir del canal
- !autoplay on/off
- !volume [0-100]
- !stop: Detener reproduccion
- !help: Mostrar este mensaje
"""
        )


def run_bot():
    if not TOKEN:
        raise RuntimeError("Falta DISCORD_TOKEN en las variables de entorno.")
    client.run(TOKEN, log_handler=None)


if __name__ == "__main__":
    cargar_feedback()
    run_bot()
