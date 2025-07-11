import discord
import yt_dlp
from youtubesearchpython import VideosSearch
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()  

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

def run_bot():
    intents = discord.Intents.default()
    intents.message_content = True
    client = discord.Client(intents=intents)

    voice_clients = {}
    queues = {}
    current_song = {}

    yt_dl_options = {
        "format": "bestaudio[ext=m4a]/bestaudio/best",
        "quiet": True,
        "noplaylist": True,
        "default_search": "auto",
        "restrictfilenames": True,
        "source_address": None,
    }

    ffmpeg_options = {
        "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
        "options": "-vn",
    }

    async def play_next_song(guild_id):
        if guild_id in queues and queues[guild_id]:
            next_song = queues[guild_id].pop(0)
            voice_client = voice_clients[guild_id]
            source = discord.FFmpegPCMAudio(next_song["url"], **ffmpeg_options)
            current_song[guild_id] = next_song

            def after_playing(error):
                if error:
                    print(f"Error al reproducir: {error}")
                asyncio.create_task(play_next_song(guild_id))

            voice_client.play(source, after=after_playing)
        else:
            if guild_id in queues:
                del queues[guild_id]
            voice_client = voice_clients.get(guild_id)
            if voice_client:
                asyncio.create_task(voice_client.disconnect())
            if guild_id in voice_clients:
                del voice_clients[guild_id]

    @client.event
    async def on_ready():
        print(f"{client.user} has connected to Discord!")

    @client.event
    async def on_message(message):
        if message.author == client.user:
            return

        if not message.content.startswith("!"):
            return

        cmd, *args = message.content[1:].split(" ", 1)
        arg = args[0] if args else ""

        guild = message.guild
        if not guild:
            await message.channel.send("Este comando solo funciona en servidores.")
            return

        queues.setdefault(guild.id, [])
        voice_clients.setdefault(guild.id, None)
        current_song.setdefault(guild.id, None)

        if cmd == "play":
            if not message.author.voice or not message.author.voice.channel:
                await message.channel.send("❌ Debes estar en un canal de voz para usar este comando.")
                return

            channel = message.author.voice.channel

            if not voice_clients[guild.id]:
                try:
                    voice_client = await channel.connect()
                    voice_clients[guild.id] = voice_client
                except Exception as e:
                    await message.channel.send(f"⚠️ No pude conectarme al canal de voz: {e}")
                    return
            else:
                voice_client = voice_clients[guild.id]
                if not voice_client.is_connected():
                    try:
                        voice_client = await channel.connect()
                        voice_clients[guild.id] = voice_client
                    except Exception as e:
                        await message.channel.send(f"⚠️ No pude reconectarme al canal de voz: {e}")
                        return

            search_query = arg.strip()
            if not search_query:
                await message.channel.send("Por favor, proporciona el nombre del artista y la canción.")
                return

            try:
                videos_search = VideosSearch(search_query, limit=1)
                results = videos_search.result()

                if not results['result']:
                    await message.channel.send("No se encontraron resultados en YouTube.")
                    return

                video_url = results['result'][0]['link']
                video_title = results['result'][0]['title']

                ytdl = yt_dlp.YoutubeDL(yt_dl_options)
                loop = asyncio.get_event_loop()
                data = await loop.run_in_executor(None, lambda: ytdl.extract_info(video_url, download=False))

                formats = data.get("formats", [])
                song_url = None
                for f in formats:
                    if f.get("acodec") != "none" and f.get("vcodec") == "none":
                        song_url = f.get("url")
                        break

                if not song_url:
                    song_url = data.get("url")

                if not song_url:
                    await message.channel.send("No se pudo obtener el enlace de audio.")
                    return

                queues[guild.id].append({"title": video_title, "url": song_url})

                await message.channel.send(f"📥 Añadido a la cola: **{video_title}**")

                if not voice_client.is_playing():
                    await play_next_song(guild.id)

            except Exception as e:
                print(f"Error al intentar reproducir: {e}")
                await message.channel.send("Ocurrió un error al intentar reproducir la música.")

        elif cmd == "pause":
            voice_client = voice_clients.get(guild.id)
            if voice_client and voice_client.is_playing():
                voice_client.pause()
                await message.channel.send("⏸️ Reproducción pausada.")
            else:
                await message.channel.send("No hay música reproduciéndose.")

        elif cmd == "resume":
            voice_client = voice_clients.get(guild.id)
            if voice_client and voice_client.is_paused():
                voice_client.resume()
                await message.channel.send("▶️ Reproducción reanudada.")
            else:
                await message.channel.send("No hay música pausada.")

        elif cmd in ["skip", "next"]:
            voice_client = voice_clients.get(guild.id)
            if voice_client and voice_client.is_playing():
                voice_client.stop()
                await message.channel.send("⏭️ Canción omitida.")
            else:
                await message.channel.send("No hay música reproduciéndose.")

        elif cmd == "leave":
            voice_client = voice_clients.get(guild.id)
            if voice_client:
                await voice_client.disconnect()
                voice_clients[guild.id] = None
                if guild.id in queues:
                    del queues[guild.id]
                if guild.id in current_song:
                    del current_song[guild.id]
                await message.channel.send("👋 Desconectado del canal de voz.")
            else:
                await message.channel.send("El bot no está conectado a un canal de voz.")

        elif cmd == "queue":
            queue = queues.get(guild.id, [])
            if queue:
                queue_list = "\n".join([f"{i+1}. {song['title']}" for i, song in enumerate(queue)])
                await message.channel.send(f"📜 Cola de reproducción:\n{queue_list}")
            else:
                await message.channel.send("🕳️ La cola está vacía.")

        elif cmd == "clearqueue":
            if guild.id in queues:
                queues[guild.id].clear()
                await message.channel.send("🧹 Cola vaciada.")
            else:
                await message.channel.send("No hay canciones en la cola.")

        elif cmd == "nowplaying":
            song = current_song.get(guild.id)
            if song:
                await message.channel.send(f"🎵 Ahora sonando: **{song['title']}**")
            else:
                await message.channel.send("No hay ninguna canción reproduciéndose.")

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
                "`!help` - Este mensaje"
            )
        else:
            await message.channel.send("❓ Comando desconocido. Usa `!help` para ver los comandos disponibles.")

    client.run(DISCORD_TOKEN)
