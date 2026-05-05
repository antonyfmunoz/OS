import asyncio
import discord
import os
from dotenv import load_dotenv

load_dotenv('/opt/OS/services/.env')

DISCORD_TOKEN = os.getenv('DISCORD_BOT_TOKEN')

CLEAR_CHANNELS = {
    'general':       1486289444830056540,
    'morning-brief': 1485765524766982234,
}

async def clear_channels():
    intents = discord.Intents.default()
    intents.message_content = True
    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        for name, channel_id in CLEAR_CHANNELS.items():
            channel = client.get_channel(channel_id)
            if channel:
                deleted = await channel.purge(limit=1000)
                print(f'[DailyClear] #{name}: cleared {len(deleted)} messages')
            else:
                print(f'[DailyClear] #{name}: channel not found')
        await client.close()

    await client.start(DISCORD_TOKEN)

if __name__ == '__main__':
    asyncio.run(clear_channels())
