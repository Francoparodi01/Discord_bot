import discord
import yt_dlp
from youtube_search import YoutubeSearch  
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
    autoplay_flags = {}  # Control por servidor

    yt_dl_options = {
        "format": "bestaudio/best",
        "noplaylist": True,
        "extractaudio": True,
        "audioquality": 1,
        "outtmpl": "downloads/%(id)s.%(ext)s",
        "restrictfilenames": True,
    }

    ffmpeg_options = {
        "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
        "options": "-vn",
    }

    def buscar_relacionada(titulo_original):
        try:
            print(f"[Autoplay] Buscando canción relacionada con: {titulo_original}")
            resultados = YoutubeSearch(titulo_original + " música", max_results=5).to_dict()
            for r in resultados:
                if r["title"].lower() != titulo_original.lower():
                    print(f"[Autoplay] Relacionada encontrada: {r['title']}")
                    return f"https://www.youtube.com{r['url_suffix']}", r["title"]
        except Exception as e:
            print(f"[Error] Falló búsqueda relacionada: {e}")
        return None, None

    @client.event
    async def on_ready():
        print(f"[Inicio] {client.user} conectado a Discord.")

    async def play_next_song(guild_id):
        if guild_id in queues and queues[guild_id]:
            next_song = queues[guild_id].pop(0)
            voice_client = voice_clients[guild_id]
            source = discord.FFmpegPCMAudio(next_song["url"], **ffmpeg_options)
            current_song[guild_id] = next_song
            print(f"[Reproducción] Reproduciendo: {next_song['title']}")

            loop = asyncio.get_event_loop()

            def after_playing(error):
                if error:
                    print(f"[Error] al reproducir: {error}")
                loop.call_soon_threadsafe(asyncio.create_task, play_next_song(guild_id))

            voice_client.play(source, after=after_playing)

        else:
            if guild_id in current_song and autoplay_flags.get(guild_id, True):
                original_title = current_song[guild_id]['title']
                video_url, video_title = buscar_relacionada(original_title)

                if video_url:
                    ytdl = yt_dlp.YoutubeDL(yt_dl_options)
                    loop = asyncio.get_event_loop()
                    data = await loop.run_in_executor(None, lambda: ytdl.extract_info(video_url, download=False))

                    if "url" in data:
                        autoplay_song = {"title": video_title, "url": data["url"]}
                        queues[guild_id] = [autoplay_song]
                        print(f"[Autoplay] Agregando canción sugerida: {video_title}")
                        await play_next_song(guild_id)
                        return

            voice_client = voice_clients.get(guild_id)
            if voice_client:
                await voice_client.disconnect()
            voice_clients.pop(guild_id, None)
            queues.pop(guild_id, None)
            current_song.pop(guild_id, None)
            print(f"[Desconectado] Finalizó la sesión de música en el servidor {guild_id}.")

    @client.event
    async def on_message(message):
        if message.author == client.user:
            return

        if message.content.startswith("!play"):
            if message.author.voice:
                channel = message.author.voice.channel
                if message.guild.id not in voice_clients:
                    try:
                        voice_client = await channel.connect()
                        voice_clients[message.guild.id] = voice_client
                        print(f"[Conectado] A canal de voz: {channel.name}")
                    except Exception as e:
                        await message.channel.send(f"No pude conectarme al canal de voz: {e}")
                        return

                try:
                    search_query = " ".join(message.content.split()[1:])
                    if not search_query:
                        await message.channel.send("Por favor, proporciona el nombre del artista y la canción.")
                        return

                    print(f"[Búsqueda] Usuario pidió: {search_query}")
                    results = YoutubeSearch(search_query, max_results=1).to_dict()
                    if not results:
                        await message.channel.send("No se encontraron resultados en YouTube.")
                        return

                    video_url = f"https://www.youtube.com{results[0]['url_suffix']}"
                    video_title = results[0]['title']

                    ytdl = yt_dlp.YoutubeDL(yt_dl_options)
                    loop = asyncio.get_event_loop()
                    data = await loop.run_in_executor(None, lambda: ytdl.extract_info(video_url, download=False))

                    if "url" not in data:
                        await message.channel.send("No se pudo obtener el enlace de audio.")
                        return

                    song_url = data["url"]
                    await message.channel.send(f"Añadido a la cola: {video_title}")
                    print(f"[Cola] Añadido: {video_title}")

                    if message.guild.id not in queues:
                        queues[message.guild.id] = []

                    queues[message.guild.id].append({"title": video_title, "url": song_url})

                    if not voice_clients[message.guild.id].is_playing():
                        await play_next_song(message.guild.id)
                except Exception as e:
                    print(f"[Error] Al reproducir: {e}")
                    await message.channel.send("Ocurrió un error al intentar reproducir la música.")
            else:
                await message.channel.send("¡Necesitas estar en un canal de voz!")

        elif message.content.startswith("!resume"):
            if message.guild.id in voice_clients:
                voice_clients[message.guild.id].resume()
                await message.channel.send("Reproducción reanudada.")
                print("[Control] Reanudado.")
            else:
                await message.channel.send("No hay música reproduciéndose.")

        elif message.content.startswith("!pause"):
            if message.guild.id in voice_clients:
                voice_clients[message.guild.id].pause()
                await message.channel.send("Reproducción pausada.")
                print("[Control] Pausado.")
            else:
                await message.channel.send("No hay música reproduciéndose.")

        elif message.content.startswith("!leave"):
            if message.guild.id in voice_clients:
                await voice_clients[message.guild.id].disconnect()
                queues.pop(message.guild.id, None)
                await message.channel.send("Desconectado del canal de voz.")
                print("[Control] Desconectado por comando.")
            else:
                await message.channel.send("El bot no está conectado a un canal de voz.")

        elif message.content.startswith("!skip") or message.content.startswith("!next"):
            if message.guild.id in voice_clients:
                voice_client = voice_clients[message.guild.id]
                if voice_client.is_playing():
                    voice_client.stop()
                    await message.channel.send("Canción omitida.")
                    print("[Control] Canción omitida.")
                else:
                    await message.channel.send("No hay música reproduciéndose.")
            else:
                await message.channel.send("No hay música reproduciéndose.")

        elif message.content.startswith("!queue"):
            if message.guild.id in queues and queues[message.guild.id]:
                queue_list = "\n".join([f"{i+1}. {song['title']}" for i, song in enumerate(queues[message.guild.id])])
                await message.channel.send(f"Cola de reproducción:\n{queue_list}")
            else:
                await message.channel.send("La cola está vacía.")

        elif message.content.startswith("!clearqueue"):
            if message.guild.id in queues:
                queues[message.guild.id].clear()
                await message.channel.send("La cola ha sido vaciada.")
                print("[Cola] Vaciada por comando.")
            else:
                await message.channel.send("No hay canciones en la cola.")

        elif message.content.startswith("!nowplaying"):
            if message.guild.id in current_song and current_song[message.guild.id]:
                now_playing = current_song[message.guild.id]
                await message.channel.send(f"Ahora sonando: {now_playing['title']}")
            else:
                await message.channel.send("No hay ninguna canción reproduciéndose.")

        elif message.content.startswith("!autoplay on"):
            autoplay_flags[message.guild.id] = True
            await message.channel.send("Autoplay activado.")
            print(f"[Autoplay] Activado en servidor {message.guild.id}.")

        elif message.content.startswith("!autoplay off"):
            autoplay_flags[message.guild.id] = False
            await message.channel.send("Autoplay desactivado.")
            print(f"[Autoplay] Desactivado en servidor {message.guild.id}.")

        elif message.content.startswith("!help"):
            help_message = """
            Comandos:
            - !play [nombre de la canción]: Reproduce una canción desde YouTube.
            - !resume: Reanuda la reproducción de la canción actual.
            - !pause: Pausa la reproducción de la canción actual.
            - !skip o !next: Omitir la canción actual y reproducir la siguiente.
            - !queue: Muestra la cola de reproducción.
            - !clearqueue: Elimina todas las canciones de la cola.
            - !nowplaying: Muestra la canción que se está reproduciendo actualmente.
            - !leave: Desconecta al bot del canal de voz.
            - !autoplay on/off: Activa o desactiva autoplay.
            - !help: Muestra este mensaje de ayuda.
            """
            await message.channel.send(help_message)

    client.run(DISCORD_TOKEN)
