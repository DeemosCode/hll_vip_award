import discord
from discord.ext import commands

intents = discord.Intents.default()
intents.members = True
intents.voice_states = True

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.command()
async def list_voice_members(ctx):
    guild = ctx.guild
    voice_channels = guild.voice_channels

    voice_members = []
    
    for vc in voice_channels:
        for member in vc.members:
            voice_members.append(member.name)
    
    voice_members = ', '.join(voice_members)
    await ctx.send(f'Currently in Voice Channels: {voice_members}')

bot.run('OTE5OTE3NTc5ODQ0MzQ5OTUy.GNBNf7.qikHXJcbUXaio91pZJOrNBpeKtq66ba7oAUlYY')
