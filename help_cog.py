import discord
from discord.ext import commands

class help_cog(commands.Cog):
	def __init__(self, bot):
		self.bot = bot
		self.embedOrange = 0xeab148

	@commands.Cog.listener()
	async def on_ready(self):
		print("Bot iniciado correctamente.")

	@commands.command(
		name="ayuda",
		help="Muestre la descripción de todos los comandos."
	)
	async def help(self, ctx):
		helpCog = self.bot.get_cog('help_cog')
		musicCog = self.bot.get_cog('music_cog')
		commands = helpCog.get_commands() + musicCog.get_commands()
		commandDescription = ""

		for c in commands:
			commandDescription += f"**`.{c.name}`** {c.help}\n"
		commandsEmbed = discord.Embed(
			title="Lista de comandos",
			description=commandDescription,
			colour=self.embedOrange
		)

		await ctx.send(embed=commandsEmbed)