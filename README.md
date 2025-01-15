
# Discord Music Bot 🎵🎶


Este es un bot de música para Discord que te permite escuchar música directamente desde YouTube en un canal de voz. Usando comandos sencillos para gestionar la cola de reproducción, pausar, reanudar, omitir canciones y algunas funcionalidades más.

Librerías utilizadas: discord.py, yt-dlp, youtube-search, python-dotenv

Comenzando 🚀

Para crear un bot personalizado y propio, seguí estos pasos:

Ingresá a la sección de developers en https://discord.com/developers/docs/intro
Luego en applications y creas una nueva aplicación.
Una vez creado el bot, en OAuth2 copiamos la clave secreta y seleccionamos la casilla de bot con el rol de administrador para invitar el bot a nuestro canal.


Requisitos 📋
Python 3.x
Librerías necesarias: discord.py, yt-dlp, youtube-search, python-dotenv.
Una vez completados los pasos anteriores, clona el repositorio e instala las dependencias con el siguiente comando:

"pip install -r requirements.txt"


Comandos del Bot ⚙️

1. !play [nombre de la canción] 🎧
Este comando permite buscar y reproducir música directamente desde YouTube.

[!playvideo](https://github.com/user-attachments/assets/3aa24a11-529d-441a-a38b-afecc17eb607)

2. !pause & !resume ⏸️▶️
Pausa y reanuda la canción que se está reproduciendo actualmente.

[!pause_!resume](https://github.com/user-attachments/assets/be94ce71-1045-489f-92aa-175abdfc900a)


4. !skip o !next ⏭️
Omitir la canción actual y pasar a la siguiente en la cola.

[!next](https://github.com/user-attachments/assets/a911e7e8-a729-4d8c-93f0-6f2920e67381)

5. !queue 📜
Muestra la lista de canciones que están en la cola de reproducción.

[!queue](https://github.com/user-attachments/assets/427ebbda-177e-4389-9ba2-ebb57fa96ca6)

6. !nowplaying 🎶
Muestra el título de la canción que está sonando actualmente.

[!nowplaying](https://github.com/user-attachments/assets/23a6aae3-8f0e-40b4-a816-b0de6383c8e8)

7. !leave 👋
Desconecta el bot del canal de voz.

![!leave](https://github.com/user-attachments/assets/d37b3e7a-e053-4bbe-bb91-9fb50bf495e9)

8. !help ❓
Muestra una lista de todos los comandos disponibles y cómo usarlos.

Contribuir 🤝

Si tienes ideas para mejorar este bot, no dudes en hacer un fork y crear un pull request.




