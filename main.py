import discord
import asyncio
import yt_dlp
import os
import random
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
PREFIX = "!"

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.guilds = True
intents.voice_states = True

client = discord.Client(intents=intents)

# Diccionarios por servidor
queues = {}
voice_clients = {}
now_playing = {}
autoplay_enabled = {}

YTDL_OPTIONS = {
    'format': 'bestaudio[ext=m4a]/bestaudio',
    'quiet': True,
    'default_search': 'ytsearch',
    'extract_flat': 'in_playlist',
    'noplaylist': False
}
FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

ytdl = yt_dlp.YoutubeDL(YTDL_OPTIONS)

async def join_channel(message):
    if not message.author.voice:
        await message.channel.send("❌ Debes estar en un canal de voz.")
        return None

    voice = discord.utils.get(client.voice_clients, guild=message.guild)
    if not voice or not voice.is_connected():
        try:
            voice = await message.author.voice.channel.connect()
            voice_clients[message.guild.id] = voice
            print(f"🎧 Conectado a {message.author.voice.channel}")
        except Exception as e:
            await message.channel.send("⚠️ No pude unirme al canal de voz.")
            print(f"Error al unirse: {e}")
            return None
    return voice

async def search_youtube(query):
    loop = asyncio.get_event_loop()
    try:
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(query, download=False))
        if 'entries' in data:
            return data['entries'][0]
        return data
    except Exception as e:
        print(f"Error al buscar: {e}")
        return None

async def play_next(guild):
    queue = queues.get(guild.id, [])
    if not queue:
        if autoplay_enabled.get(guild.id):
            print("🔁 Autoplay activado")
            last_song = now_playing.get(guild.id)
            if last_song:
                related = await search_youtube(f"{last_song['title']} related")
                if related and related['webpage_url'] != last_song['webpage_url']:
                    queue.append(related)
                    queues[guild.id] = queue
                else:
                    print("⚠️ No se encontraron canciones relacionadas distintas.")
            else:
                print("⚠️ No hay canción previa para autoplay.")
        else:
            await voice_clients[guild.id].disconnect()
            return

    if queue:
        song = queue.pop(0)
        queues[guild.id] = queue
        now_playing[guild.id] = song
        url = song['url']
        source = await discord.FFmpegOpusAudio.from_probe(url, **FFMPEG_OPTIONS)
        vc = voice_clients[guild.id]
        vc.play(source, after=lambda e: asyncio.run_coroutine_threadsafe(play_next(guild), client.loop))
        print(f"▶️ Reproduciendo: {song['title']}")
        channel = discord.utils.get(guild.text_channels, name="general") or guild.text_channels[0]
        await channel.send(f"🎶 Ahora suena: **{song['title']}**")

@client.event
async def on_ready():
    print(f"✅ Bot conectado como {client.user}")

@client.event
async def on_message(message):
    if message.author == client.user or not message.content.startswith(PREFIX):
        return

    cmd, *args = message.content[len(PREFIX):].strip().split(" ", 1)
    arg = args[0] if args else ""

    guild = message.guild
    queue = queues.setdefault(guild.id, [])
    autoplay_enabled.setdefault(guild.id, False)

    if cmd == "play":
        voice = await join_channel(message)
        if not voice:
            return

        search = arg if arg else "lofi hip hop"
        song = await search_youtube(search)
        if not song:
            await message.channel.send("❌ No se encontró la canción.")
            return

        url = song.get("url") or song.get("webpage_url")
        song['url'] = url
        queue.append(song)
        queues[guild.id] = queue

        if not voice.is_playing():
            await play_next(guild)
        else:
            await message.channel.send(f"📥 Añadido a la cola: **{song['title']}**")

    elif cmd == "pause":
        if voice_clients.get(guild.id) and voice_clients[guild.id].is_playing():
            voice_clients[guild.id].pause()
            await message.channel.send("⏸️ Pausado.")
    elif cmd == "resume":
        if voice_clients.get(guild.id) and voice_clients[guild.id].is_paused():
            voice_clients[guild.id].resume()
            await message.channel.send("▶️ Reanudado.")
    elif cmd in ["skip", "next"]:
        if voice_clients.get(guild.id) and voice_clients[guild.id].is_playing():
            voice_clients[guild.id].stop()
            await message.channel.send("⏭️ Saltando a la siguiente...")
    elif cmd == "leave":
        if voice_clients.get(guild.id):
            await voice_clients[guild.id].disconnect()
            voice_clients.pop(guild.id, None)
            await message.channel.send("👋 Me fui del canal.")
    elif cmd == "queue":
        if queue:
            msg = "\n".join([f"{i+1}. {s['title']}" for i, s in enumerate(queue)])
            await message.channel.send(f"📜 Cola actual:\n{msg}")
        else:
            await message.channel.send("🕳️ La cola está vacía.")
    elif cmd == "clearqueue":
        queues[guild.id] = []
        await message.channel.send("🧹 Cola vaciada.")
    elif cmd == "nowplaying":
        song = now_playing.get(guild.id)
        if song:
            await message.channel.send(f"🎵 En reproducción: **{song['title']}**")
        else:
            await message.channel.send("⚠️ Nada está sonando.")
    elif cmd == "autoplay":
        if arg.lower() == "on":
            autoplay_enabled[guild.id] = True
            await message.channel.send("🔁 Autoplay activado.")
        elif arg.lower() == "off":
            autoplay_enabled[guild.id] = False
            await message.channel.send("⛔ Autoplay desactivado.")
        else:
            await message.channel.send("Uso: `!autoplay on` o `!autoplay off`")
    elif cmd == "help":
        await message.channel.send(
            "**🎧 Comandos disponibles:**\n"
            "`!play [nombre|url]` - Reproduce una canción\n"
            "`!pause` / `!resume` - Pausar o reanudar\n"
            "`!skip` / `!next` - Siguiente canción\n"
            "`!leave` - Salir del canal\n"
            "`!queue` - Ver cola\n"
            "`!clearqueue` - Vaciar cola\n"
            "`!nowplaying` - Ver canción actual\n"
            "`!autoplay on/off` - Autoplay\n"
            "`!help` - Este mensaje"
        )
    else:
        await message.channel.send("❓ Comando desconocido. Usa `!help` para ver los comandos disponibles.")


def run_bot():
    client.run(TOKEN)
