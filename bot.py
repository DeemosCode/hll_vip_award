import os
import discord
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv('YOUR_BOT_TOKEN') # Your Discord bot token
MONGO_CONNECTION_STRING = os.getenv('MONGO_CONNECTION_STRING') # Your MongoDB connection string
client = discord.Client()
mongo_client = MongoClient(MONGO_CONNECTION_STRING)
db = mongo_client['your_database'] # Your MongoDB database

@client.event
async def on_ready():
    print(f'We have logged in as {client.user}')

@client.event
async def on_raw_reaction_add(payload):
    # Ensure the reaction is what you expect
    if str(payload.emoji) != 'reaction_emoji': # the reaction emoji to trigger sign-up
        return

    channel = client.get_channel(payload.channel_id)
    if channel is None:
        return

    message = await channel.fetch_message(payload.message_id)
    if message is None or message.author != client.user:
        return

    event_doc = db.events.find_one({"message_id": str(payload.message_id)})
    if event_doc is None:
        return

    user_id = payload.user_id
    if user_id not in event_doc['users']:
        # Add user to the event
        db.events.update_one({"message_id": str(payload.message_id)}, {"$push": {"users": user_id}})

        # Update the message to reflect new user
        users_str = ', '.join([f'<@{user}>' for user in event_doc['users']])
        await message.edit(content=f'Users signed up for this event: {users_str}')

client.run(TOKEN)
