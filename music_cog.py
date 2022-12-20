import discord
from discord_components import Select, SelectOption, Button
from discord.ext import commands
import asyncio
from asyncio import run_coroutine_threadsafe
from urllib import parse, request
import re
import json
import os
from youtube_dl import YoutubeDL


class music_cog(commands.Cog):
	def __init__(self, bot):
		self.bot = bot

		self.is_playing = {}
		self.is_paused = {}
		self.musicQueue = {}
		self.queueIndex = {}

		self.YTDL_OPTIONS = {'format': 'bestaudio', 'nonplaylist': 'True'}
		self.FFMPEG_OPTIONS = {
			'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 'options': '-vn'}

		self.embedBlue = 0x2c76dd
		self.embedRed = 0xdf1141
		self.embedGreen = 0x0eaa51

		self.vc = {}

	@commands.Cog.listener()
	async def on_ready(self):
		for guild in self.bot.guilds:
			id = int(guild.id)
			self.musicQueue[id] = []
			self.queueIndex[id] = 0
			self.vc[id] = None
			self.is_paused[id] = self.is_playing[id] = False

	@commands.Cog.listener()
	async def on_voice_state_update(self, member, before, after):
		id = int(member.guild.id)
		if member.id != self.bot.user.id and before.channel != None and after.channel != before.channel:
			remainingChannelMembers = before.channel.members
			if len(remainingChannelMembers) == 1 and remainingChannelMembers[0].id == self.bot.user.id and self.vc[id].is_connected():
				self.is_playing[id] = self.is_paused[id] = False
				self.musicQueue[id] = []
				self.queueIndex[id] = 0
				await self.vc[id].disconnect()

	def now_playing_embed(self, ctx, song):
		title = song['title']
		link = song['link']
		thumbnail = song['thumbnail']
		author = ctx.author
		avatar = author.avatar_url

		embed = discord.Embed(
			title="Estás escuchando...",
			description=f'[{title}]({link})',
			colour=self.embedBlue,
		)
		embed.set_thumbnail(url=thumbnail)
		embed.set_footer(text=f'Agregada por: {str(author)}', icon_url=avatar)
		return embed

	def added_song_embed(self, ctx, song):
		title = song['title']
		link = song['link']
		thumbnail = song['thumbnail']
		author = ctx.author
		avatar = author.avatar_url

		embed = discord.Embed(
			title="¡Canción agregada a la cola!",
			description=f'[{title}]({link})',
			colour=self.embedRed,
		)
		embed.set_thumbnail(url=thumbnail)
		embed.set_footer(text=f'Agregada por: {str(author)}', icon_url=avatar)
		return embed

	def removed_song_embed(self, ctx, song):
		title = song['title']
		link = song['link']
		thumbnail = song['thumbnail']
		author = ctx.author
		avatar = author.avatar_url

		embed = discord.Embed(
			title="¡Canción removida de la cola!",
			description=f'[{title}]({link})',
			colour=self.embedRed,
		)
		embed.set_thumbnail(url=thumbnail)
		embed.set_footer(
			text=f'Removido por: {str(author)}', icon_url=avatar)
		return embed

	async def join_VC(self, ctx, channel):
		id = int(ctx.guild.id)
		if self.vc[id] == None or not self.vc[id].is_connected():
			self.vc[id] = await channel.connect()

			if self.vc[id] == None:
				await ctx.send("No puedo conectarme a ese canal =(")
				return
		else:
			await self.vc[id].move_to(channel)

	def get_YT_title(self, videoID):
		params = {"format": "json",
				  "url": "https://www.youtube.com/watch?v=%s" % videoID}
		url = "https://www.youtube.com/oembed"
		queryString = parse.urlencode(params)
		url = url + "?" + queryString
		with request.urlopen(url) as response:
			responseText = response.read()
			data = json.loads(responseText.decode())
			return data['title']

	def search_YT(self, search):
		queryString = parse.urlencode({'search_query': search})
		htmContent = request.urlopen(
			'http://www.youtube.com/results?' + queryString)
		searchResults = re.findall(
			'/watch\?v=(.{11})', htmContent.read().decode())
		return searchResults[0:10]

	def extract_YT(self, url):
		with YoutubeDL(self.YTDL_OPTIONS) as ydl:
			try:
				info = ydl.extract_info(url, download=False)
			except:
				return False
		return {
			'link': 'https://www.youtube.com/watch?v=' + url,
			'thumbnail': 'https://i.ytimg.com/vi/' + url + '/hqdefault.jpg?sqp=-oaymwEcCOADEI4CSFXyq4qpAw4IARUAAIhCGAFwAcABBg==&rs=AOn4CLD5uL4xKN-IUfez6KIW_j5y70mlig',
			'source': info['formats'][0]['url'],
			'title': info['title']
		}

	def play_next(self, ctx):
		id = int(ctx.guild.id)
		if not self.is_playing[id]:
			return
		if self.queueIndex[id] + 1 < len(self.musicQueue[id]):
			self.is_playing[id] = True
			self.queueIndex[id] += 1

			song = self.musicQueue[id][self.queueIndex[id]][0]
			message = self.now_playing_embed(ctx, song)
			coro = ctx.send(embed=message)
			fut = run_coroutine_threadsafe(coro, self.bot.loop)
			try:
				fut.result()
			except:
				pass

			self.vc[id].play(discord.FFmpegPCMAudio(
				song['source'], **self.FFMPEG_OPTIONS), after=lambda e: self.play_next(ctx))
		else:
			self.queueIndex[id] += 1
			self.is_playing[id] = False

	async def play_music(self, ctx):
		id = int(ctx.guild.id)
		if self.queueIndex[id] < len(self.musicQueue[id]):
			self.is_playing[id] = True
			self.is_paused[id] = False

			await self.join_VC(ctx, self.musicQueue[id][self.queueIndex[id]][1])

			song = self.musicQueue[id][self.queueIndex[id]][0]
			message = self.now_playing_embed(ctx, song)
			await ctx.send(embed=message)

			self.vc[id].play(discord.FFmpegPCMAudio(
				song['source'], **self.FFMPEG_OPTIONS), after=lambda e: self.play_next(ctx))
		else:
			await ctx.send("No hay canciones agregadas para reproducir >:v")
			self.queueIndex[id] += 1
			self.is_playing[id] = False

	@ commands.command(
		name="play",
		aliases=["p"],
		help="Reproduce o reanuda un audio de Youtube."
	)
	async def play(self, ctx, *args):
		search = " ".join(args)
		id = int(ctx.guild.id)
		try:
			userChannel = ctx.author.voice.channel
		except:
			await ctx.send("Debes conectarte a un canal de voz para usarme.")
			return
		if not args:
			if len(self.musicQueue[id]) == 0:
				await ctx.send("No hay canciones agregadas para reproducir >:v")
				return
			elif not self.is_playing[id]:
				if self.musicQueue[id] == None or self.vc[id] == None:
					await self.play_music(ctx)
				else:
					self.is_paused[id] = False
					self.is_playing[id] = True
					self.vc[id].resume()
			else:
				return
		else:
			song = self.extract_YT(self.search_YT(search)[0])
			if type(song) == type(True):
				await ctx.send("No pude descargar la canción, proba con otra :v")
			else:
				self.musicQueue[id].append([song, userChannel])

				if not self.is_playing[id]:
					await self.play_music(ctx)
				else:
					message = self.added_song_embed(ctx, song)
					await ctx.send(embed=message)

	@ commands.command(
		name="agregar",
		help="Agrega el primer resultado de la búsqueda a la cola."
	)
	async def add(self, ctx, *args):
		search = " ".join(args)
		try:
			userChannel = ctx.author.voice.channel
		except:
			await ctx.send("Tenes que estar en un canal de voz para usarme :v")
			return
		if not args:
			await ctx.send("No especificaste el tema que queres agregar, mogolico")
		else:
			song = self.extract_YT(self.search_YT(search)[0])
			if type(song) == type(False):
				await ctx.send("No pude descargar la canción, proba con otra :v")
				return
			else:
				self.musicQueue[ctx.guild.id].append([song, userChannel])
				message = self.added_song_embed(ctx, song)
				await ctx.send(embed=message)

	@ commands.command(
		name="remover",
		help="Remueve la ultima canción agregada en la cola."
	)
	async def remove(self, ctx):
		id = int(ctx.guild.id)
		if self.musicQueue[id] != []:
			song = self.musicQueue[id][-1][0]
			removeSongEmbed = self.removed_song_embed(ctx, song)
			await ctx.send(embed=removeSongEmbed)
		else:
			await ctx.send("No hay ninguna canción para borrar en la cola :v")
		self.musicQueue[id] = self.musicQueue[id][:-1]
		if self.musicQueue[id] == []:
			if self.vc[id] != None and self.is_playing[id]:
				self.is_playing[id] = self.is_paused[id] = False
				await self.vc[id].disconnect()
				self.vc[id] = None
			self.queueIndex[id] = 0
		elif self.queueIndex[id] == len(self.musicQueue[id]) and self.vc[id] != None and self.vc[id]:
			self.vc[id].pause()
			self.queueIndex[id] -= 1
			await self.play_music(ctx)

	@ commands.command(
		name="buscar",
		help="Muestra una lista de resultados de la búsqueda de Youtube."
	)
	async def search(self, ctx, *args):
		search = " ".join(args)
		songNames = []
		selectionOptions = []
		embedText = ""

		if not args:
			await ctx.send("Tenes que poner lo que queres buscar virgen v:")
			return
		try:
			userChannel = ctx. author.voice.channel
		except:
			await ctx.send("CONECTATE A UN CANAL DE VOZ PRIMERO, TARADO")
			return

		await ctx.send("Buscando resultados... :v")

		songTokens = self.search_YT(search)

		for i, token in enumerate(songTokens):
			url = 'https://www.youtube.com/watch?v=' + token
			name = self.get_YT_title(token)
			songNames.append(name)
			embedText += f"{i+1} - [{name}]({url})\n"

		for i, title in enumerate(songNames):
			selectionOptions.append(SelectOption(
				label=f"{i+1} - {title[:95]}", value=i))

		searchResults = discord.Embed(
			title="Buscar resultlados",
			description=embedText,
			colour=self.embedRed
		)
		selectionComponents = [
			Select(
				placeholder="Selecciona una opción",
				options=selectionOptions
			),
			Button(
				label="Cancelar",
				custom_id="Cancel",
				style=4
			)
		]
		message = await ctx.send(embed=searchResults, components=selectionComponents)
		try:
			tasks = [
				asyncio.create_task(self.bot.wait_for(
					"button_click",
					timeout=60.0,
					check=None
				), name="button"),
				asyncio.create_task(self.bot.wait_for(
					"select_option",
					timeout=60.0,
					check=None
				), name="select")
			]
			done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
			finished = list(done)[0]

			for task in pending:
				try:
					task.cancel()
				except asyncio.CancelledError:
					pass

			if finished == None:
				searchResults.title = "Falló la búsqueda."
				searchResults.description = ""
				await message.delete()
				await ctx.send(embed=searchResults)
				return

			action = finished.get_name()

			if action == "button":
				searchResults.title = "Falló la búsqueda."
				searchResults.description = ""
				await message.delete()
				await ctx.send(embed=searchResults)
			elif action == "select":
				result = finished.result()
				chosenIndex = int(result.values[0])
				songRef = self.extract_YT(songTokens[chosenIndex])
				if type(songRef) == type(True):
					await ctx.send("No pude descargar el tema VO XD NO SE PQ PASO, proba totra cosa")
					return
				embedReponse = discord.Embed(
					title=f"Opción #{chosenIndex + 1} seleccionada",
					description=f"[{songRef['title']}]({songRef['link']}) ha sido agregado a la cola.",
					colour=self.embedRed
				)
				embedReponse.set_thumbnail(url=songRef['thumbnail'])
				await message.delete()
				await ctx.send(embed=embedReponse)
				self.musicQueue[ctx.guild.id].append([songRef, userChannel])
		except:
			searchResults.title = "La búsqueda falló."
			searchResults.description = ""
			await message.delete()
			await ctx.send(embed=searchResults)

	@ commands.command(
		name="pausar",
		help="Pausa la canción actual que se esté reproduciendo."
	)
	async def pause(self, ctx):
		id = int(ctx.guild.id)
		if not self.vc[id]:
			await ctx.send("No hay ningun audio para pausar :v")
		elif self.is_playing[id]:
			await ctx.send("¡Audio pausado!")
			self.is_playing[id] = False
			self.is_paused[id] = True
			self.vc[id].pause()

	@ commands.command(
		name="reanudar",
		help="Reanuda una canción que esté pausada."
	)
	async def resume(self, ctx):
		id = int(ctx.guild.id)
		if not self.vc[id]:
			await ctx.send("No hay ningún audio para reanudar :v")
		elif self.is_paused[id]:
			await ctx.send("¡El audio ha sido reanudado!")
			self.is_playing[id] = True
			self.is_paused[id] = False
			self.vc[id].resume()

	@ commands.command(
		name="next",
		help="Reproduce la siguiente canción de la cola."
	)
	async def previous(self, ctx):
		id = int(ctx.guild.id)
		if self.vc[id] == None:
			await ctx.send("NO ESTAS EN EL CHAT DE VOZ, VIRGEEEEEEEEEEN")
		elif self.queueIndex[id] <= 0:
			await ctx.send("Yo no veo ningún audio en la cola, no hay más :v")
			self.vc[id].pause()
			await self.play_music(ctx)
		elif self.vc[id] != None and self.vc[id]:
			self.vc[id].pause()
			self.queueIndex[id] -= 1
			await self.play_music(ctx)

	@ commands.command(
		name="skip",
		help="Salta una canción que esté en la cola."
	)
	async def skip(self, ctx):
		id = int(ctx.guild.id)
		if self.vc[id] == None:
			await ctx.send("Primero únete a un canal de voz, down.")
		elif self.queueIndex[id] >= len(self.musicQueue[id]) - 1:
			await ctx.send("Que canción queres saltear? Si no hay ninguna XDDD sos re mogolico")
			self.vc[id].pause()
			await self.play_music(ctx)
		elif self.vc[id] != None and self.vc[id]:
			self.vc[id].pause()
			self.queueIndex[id] += 1
			await self.play_music(ctx)

	@ commands.command(
		name="lista",
		help="Muestra una lista de todas las canciones en la cola."
	)
	async def queue(self, ctx):
		id = int(ctx.guild.id)
		returnValue = ""
		if self.musicQueue[id] == []:
			await ctx.send("No hay ninguna canción en la cola =(")
			return

		for i in range(self.queueIndex[id], len(self.musicQueue[id])):
			upNextSongs = len(self.musicQueue[id]) - self.queueIndex[id]
			if i > 5 + upNextSongs:
				break
			returnIndex = i - self.queueIndex[id]
			if returnIndex == 0:
				returnIndex = "Reproduciendo"
			elif returnIndex == 1:
				returnIndex = "Siguiente"
			returnValue += f"{returnIndex} - [{self.musicQueue[id][i][0]['title']}]({self.musicQueue[id][i][0]['link']})\n"

			if returnValue == "":
				await ctx.send("No hay canciones en la cola :v")
				return

		queue = discord.Embed(
			title="Lista actual",
			description=returnValue,
			colour=self.embedGreen
		)
		await ctx.send(embed=queue)

	@ commands.command(
		name="limpiar",
		help="Remueve todas las canciones que estén en la cola."
	)
	async def clear(self, ctx):
		id = int(ctx.guild.id)
		if self.vc[id] != None and self.is_playing[id]:
			self.is_playing = self.is_paused = False
			self.vc[id].stop()
		if self.musicQueue[id] != []:
			await ctx.send("La cola de música se ha borreado NOOOOO D:")
			self.musicQueue[id] = []
		self.queueIndex = 0

	@ commands.command(
		name="papu",
		help="Conecta a elpapu al canal de voz :v"
	)
	async def join(self, ctx):
		if ctx.author.voice:
			userChannel = ctx.author.voice.channel
			await self.join_VC(ctx, userChannel)
			await ctx.send(f'elpapu se ha unido a {userChannel}')
		else:
			await ctx.send("Primero únete al canal de voz para usar esto :v")

	@ commands.command(
		name="salir",
		help="Remueve al papu del canal del voz y la cola de canciones :v"
	)
	async def leave(self, ctx):
		id = int(ctx.guild.id)
		self.is_playing[id] = self.is_paused[id] = False
		self.musicQueue[id] = []
		self.queueIndex[id] = 0
		if self.vc[id] != None:
			await ctx.send("elpapu ha salido del chat :'v")
			await self.vc[id].disconnect()
			self.vc[id] = None