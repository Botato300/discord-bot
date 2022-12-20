from discord_components import ComponentsBot

from music_cog import music_cog
from help_cog import help_cog

bot = ComponentsBot(command_prefix='.')

bot.remove_command('help')

bot.add_cog(music_cog(bot))
bot.add_cog(help_cog(bot))

bot.run('ODU5OTk3OTg0NTA1NDYyNzk4.G569RW.8HKkEblmrLgXCEZwtQa0msowhH-EDMLQ0xBflQ')