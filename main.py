import discord
import yt_dlp
import asyncio
import os
import re
import difflib
from dotenv import load_dotenv
from youtube_search import YoutubeSearch

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

voice_clients = {}
queues = {}
current_song = {}
song_history = {}

autoplay_flags = {}

yt_dl_options = {
    "format": "bestaudio/best",
    "noplaylist": True,
    "extractaudio": True,
    "audioquality": 1,
    "outtmpl": "downloads/%(id)s.%(ext)s",
    "restrictfilenames": True,
    "quiet": True,
    "nocheckcertificate": True,
}

ffmpeg_options = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options": "-vn"
}

def limpiar_titulo(titulo):
    titulo = re.sub(r'\(.*?\)|\[.*?\]', '', titulo).lower()
    for palabra in ["letra", "karaoke", "oficial", "audio", "video", "hd", "live", "remasterizado"]:
        titulo = titulo.replace(palabra, "")
    return titulo.strip()

def extraer_artista(titulo):
    partes = titulo.split(" - ")
    return partes[0] if len(partes) > 1 else titulo

async def buscar_relacionada(titulo_original, historial):
    artista = extraer_artista(titulo_original)
    query = f"{artista} canciones"
    print(f"[Autoplay] Buscando canciones de: {artista}")
    try:
        resultados = YoutubeSearch(query, max_results=10).to_dict()
        titulo_limpio = limpiar_titulo(titulo_original)
        historial_limpio = set(limpiar_titulo(s) for s in historial)

        for r in resultados:
            candidato = r["title"]
            candidato_limpio = limpiar_titulo(candidato)
            similitud = difflib.SequenceMatcher(None, titulo_limpio, candidato_limpio).ratio()

            if similitud > 0.8 or candidato_limpio in historial_limpio:
                continue

            print(f"[Autoplay] Relacionada aceptada: {candidato}")
            return f"https://www.youtube.com{r['url_suffix']}", candidato

    except Exception as e:
        print(f"[Error] en búsqueda relacionada: {e}")
    return None, None

async def play_next(guild_id):
    voice_client = voice_clients.get(guild_id)

    if guild_id in queues and queues[guild_id]:
        next_song = queues[guild_id].pop(0)
        current_song[guild_id] = next_song
        source = discord.FFmpegPCMAudio(next_song["url"], **ffmpeg_options)
        print(f"[Reproducción] {next_song['title']}")

        loop = asyncio.get_running_loop()

        def after_playing(error):
            if error:
                print(f"[Error] al reproducir: {error}")
            asyncio.run_coroutine_threadsafe(play_next(guild_id), loop)

        voice_client.play(source, after=after_playing)
        return

    elif current_song.get(guild_id) and autoplay_flags.get(guild_id, True):
        last_title = current_song[guild_id]["title"]
        song_history.setdefault(guild_id, []).append(last_title)
        url, title = await buscar_relacionada(last_title, song_history[guild_id])
        if url:
            ytdl = yt_dlp.YoutubeDL(yt_dl_options)
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=False))
            if "url" in data:
                queues[guild_id] = [{"title": title, "url": data["url"]}]
                print(f"[Autoplay] Agregando: {title}")
                await play_next(guild_id)
                return

    await voice_client.disconnect()
    print("[Desconectado] Sesión finalizada.")
    for d in (voice_clients, queues, current_song):
        d.pop(guild_id, None)

@client.event
async def on_ready():
    print(f"[Inicio] Bot conectado como {client.user}")

@client.event
async def on_message(msg):
    if msg.author == client.user:
        return

    gid = msg.guild.id

    if msg.content.startswith("!play"):
        if msg.author.voice:
            if gid not in voice_clients:
                vc = await msg.author.voice.channel.connect()
                voice_clients[gid] = vc
            search = " ".join(msg.content.split()[1:])
            if not search:
                await msg.channel.send("¡Decime qué canción querés!")
                return
            ytdl = yt_dlp.YoutubeDL(yt_dl_options)
            loop = asyncio.get_event_loop()
            info = await loop.run_in_executor(None, lambda: ytdl.extract_info(f"ytsearch1:{search}", download=False))
            video = info["entries"][0]
            song = {"title": video["title"], "url": video["url"]}
            queues.setdefault(gid, []).append(song)
            await msg.channel.send(f"🎶 Añadido: {song['title']}")
            if not voice_clients[gid].is_playing():
                await play_next(gid)
        else:
            await msg.channel.send("¡Conectate a un canal de voz primero!")

    elif msg.content.startswith("!skip"):
        if voice_clients.get(gid):
            voice_clients[gid].stop()
            await msg.channel.send("⏭️ Canción omitida.")

    elif msg.content.startswith("!next"):
        if voice_clients.get(gid):
            voice_clients[gid].stop()
            await msg.channel.send("⏭️ Siguiente canción en cola.")
            await play_next(gid)
        else:
            await msg.channel.send("No estoy reproduciendo nada.")

    elif msg.content.startswith("!stop"):
        if voice_clients.get(gid):
            voice_clients[gid].stop()
            await msg.channel.send("⏹️ Reproducción detenida.")
            await play_next(gid)
        else:
            await msg.channel.send("No estoy reproduciendo nada.")

    elif msg.content.startswith("!volume"):
        if voice_clients.get(gid):
            try:
                volume = int(msg.content.split()[1])
                if 0 <= volume <= 100:
                    voice_clients[gid].source.volume = volume / 100
                    await msg.channel.send(f"🔊 Volumen ajustado a {volume}%")
                else:
                    await msg.channel.send("El volumen debe estar entre 0 y 100.")
            except (IndexError, ValueError):
                await msg.channel.send("Usá !volume [0-100] para ajustar el volumen.")
        else:
            await msg.channel.send("No estoy reproduciendo nada.")

    elif msg.content.startswith("!pause"):
        if voice_clients.get(gid):
            voice_clients[gid].pause()
            await msg.channel.send("⏸️ Pausado.")

    elif msg.content.startswith("!resume"):
        if voice_clients.get(gid):
            voice_clients[gid].resume()
            await msg.channel.send("▶️ Reanudado.")

    elif msg.content.startswith("!leave"):
        if gid in voice_clients:
            await voice_clients[gid].disconnect()
            for d in (voice_clients, queues, current_song, autoplay_flags):
                d.pop(gid, None)
            await msg.channel.send("👋 Desconectado.")
        else:
            await msg.channel.send("No estoy en un canal.")

    elif msg.content.startswith("!queue"):
        q = queues.get(gid, [])
        if q:
            lista = "\n".join([f"{i+1}. {s['title']}" for i, s in enumerate(q)])
            await msg.channel.send(f"🎧 Cola:\n{lista}")
        else:
            await msg.channel.send("La cola está vacía.")

    elif msg.content.startswith("!autoplay on"):
        autoplay_flags[gid] = True
        await msg.channel.send("🔁 Autoplay ACTIVADO")

    elif msg.content.startswith("!autoplay off"):
        autoplay_flags[gid] = False
        await msg.channel.send("⏹️ Autoplay desactivado")
    elif msg.content.startswith("!help"):
        await msg.channel.send("""
🎵 **Comandos disponibles**:
- !play [nombre]: Reproduce una canción
- !skip / !next: Omitir canción
- !pause / !resume
- !queue: Ver la cola
- !leave: Salir del canal
- !autoplay on/off: Controla reproducción automática
- !volume [0-100]: Ajustar volumen
- !stop: Detener reproducción
                            
- !help: Mostrar este mensaje
""")

client.run(TOKEN)
