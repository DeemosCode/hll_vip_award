import discord
import os
from pymongo import MongoClient 
from discord.ext import commands
from dotenv import load_dotenv
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from datetime import datetime, timedelta
import schedule

load_dotenv()

deemocrat_role_id = 912034805762363473
aspiring_deemocrat_role_id = 1102000164601864304

TOKEN = os.getenv('YOUR_BOT_TOKEN') # Your Discord bot token
MONGO_CONNECTION_STRING = os.getenv('MONGO_CONNECTION_STRING') # Your MongoDB connection string
ROLE_ID = 1115617370745077800  # The ID of the role to be added.

mongo_client = MongoClient(MONGO_CONNECTION_STRING)
db = mongo_client.deemos 
vip = db.vip  # Access the 'vip' collection

intents = discord.Intents.all()  # This line enables all intents.
bot = commands.Bot(command_prefix='!', intents=intents)
jobstores = {'default': SQLAlchemyJobStore(url='sqlite:///jobs.sqlite')}
scheduler = AsyncIOScheduler(jobstores=jobstores)

@bot.command()
@commands.has_permissions(administrator=True)  # Ensure only admins can run this command
async def list_voice_now(ctx):
    guild = ctx.guild
    voice_channels = guild.voice_channels

    voice_members = []
    
    for vc in voice_channels:
        for member in vc.members:
            voice_members.append(member.name)
    
    voice_members = '\n'.join(voice_members)
    await ctx.send(f'Currently in Voice Channels:\n {voice_members}')


# @bot.event
# async def on_scheduled_event_user_add(event, user):
#     # Split the event name string into parts
#     event_parts = event.name.split(" vs ")

#     # Check if the string has been correctly split into three parts
#     if len(event_parts) == 3:
#         opponent_name = event_parts[2].lower()

#         guild = bot.get_guild(event.guild_id)

#         # Find the role that contains the opponent name as a substring
#         role = discord.utils.find(lambda r: opponent_name in r.name.lower(), guild.roles)

#         if role is not None:
#             member = guild.get_member(user.id)

#             if role not in member.roles:
#                 await member.add_roles(role)

# @bot.event
# async def on_scheduled_event_user_remove(event, user):
# # Split the event name string into parts
#     event_parts = event.name.split(" vs ")

#     # Check if the string has been correctly split into three parts
#     if len(event_parts) == 3:
#         opponent_name = event_parts[2].lower()

#         guild = bot.get_guild(event.guild_id)

#         # Find the role that contains the opponent name as a substring
#         role = discord.utils.find(lambda r: opponent_name in r.name.lower(), guild.roles)

#     member = guild.get_member(user.id)
#     if role in member.roles:
#         await member.remove_roles(role)

@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user}')
    scheduler.start()

@bot.event
async def on_command_error(ctx, error):
    await ctx.send(f"An error occurred: {str(error)}")


@bot.command()
@commands.has_permissions(administrator=True)  # Ensure only admins can run this command
async def strip(ctx):
    guild = ctx.guild  # The guild (server) from the current context

    deemocrat = discord.utils.get(guild.roles, id=aspiring_deemocrat_role_id)
    aspiring = discord.utils.get(guild.roles, id=deemocrat_role_id)

    for member in guild.members:
        print(f"{member} removed")
        if deemocrat in member.roles:
            await member.remove_roles(deemocrat)
            print("deemocrat")

        if aspiring in member.roles:
            await member.remove_roles(aspiring)
            print("aspiring deemocrat")
            
@bot.command()
@commands.has_permissions(administrator=True)  # Ensure only admins can run this command
async def list_aspiring_deemocrats(ctx):
    guild = ctx.guild
    aspiring_deemocrat_role = discord.utils.get(guild.roles, id=aspiring_deemocrat_role_id) # Get the aspiring_deemocrat role

    aspiring_deemocrats = []

    for member in guild.members:
        if aspiring_deemocrat_role in member.roles:  # Check if the member has the aspiring_deemocrat role
            aspiring_deemocrats.append(member.name)

    aspiring_deemocrats = '\n'.join(aspiring_deemocrats)
    await ctx.send(f'Aspiring Deemocrats:\n {aspiring_deemocrats}')


bot.run(TOKEN)
