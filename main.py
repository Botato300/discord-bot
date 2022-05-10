import discord
from discord.ext import commands
import youtube_dl
import os

client = commands.Bot(command_prefix=".", help_command=None)
token = "TOKEN" #Debes poner tu token aqui

# Eventos
@client.event
async def on_connect():
    print("Bot conectado.")

@client.event
async def on_ready():
    print("Bot preparado.")

@client.event
async def on_command_error(ctx, error):
    errorEmbed = discord.Embed(title="Ha ocurrido un error...", description=f"Se produjo un error al procesar el comando ingresado.\nERROR: {error}", color=discord.Colour.red())
    await ctx.send(embed=errorEmbed)

# Comandos
@client.command(name="p")
async def play(ctx, url : str):
    song_there = os.path.isfile("song.mp3")
    try:
        if song_there:
            os.remove("song.mp3")
    except PermissionError:
        await ctx.send("La canción actual debe terminar para que puedas poner otra canción.")
        return
    voiceChannel = discord.utils.get(ctx.guild.voice_channels, name="chat-de-voz")
    voice = discord.utils.get(client.voice_clients, guild=ctx.guild)

    if voice and voice.is_connected:
        await voice.move_to(voiceChannel)
    else:
        voice = await voiceChannel.connect()

    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors':
        [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
    }

    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    for file in os.listdir("./"):
        if file.endswith(".mp3"):
            os.rename(file, "song.mp3")
    voice.play(discord.FFmpegPCMAudio("song.mp3"))
    await client.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="música"))

@client.command(name="ping")
async def asd(ctx):
    await ctx.send(f"{round(client.latency * 1000)}ms")

client.run(token)
