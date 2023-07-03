import os
import random
import logging
import traceback
from dotenv import load_dotenv

import discord
from discord.ext import commands

from logger import setup_logger
from agents.async_shelby_agent import ShelbyAgent

logger = setup_logger('discord_bot', 'discord_bot.log', level=logging.DEBUG)

load_dotenv()

# Use this for local testing
# bot_token = os.getenv('SHELBY_SPRITE_DISCORD_TOKEN')
# channel_id = int(os.environ['SHELBY_SPRITE_DISCORD_CHANNEL_ID'])

# Use this for container deployments 
bot_token = os.getenv('DISCORD_TOKEN')
channel_id = int(os.environ['DISCORD_CHANNEL_ID'])

message_start = "Running query. Relax, chill, and vibe a minute."


def create_bot():
    intents = discord.Intents.default()
    bot = commands.Bot(command_prefix=commands.when_mentioned_or("!"), intents=intents)
    return bot

bot = create_bot()

async def get_random_animal():
    animals_txt_path = os.path.join('data', 'animals.txt')
    with open(animals_txt_path, 'r') as file:
        animals = file.readlines()
    return random.choice(animals).strip().lower()

@bot.event
async def on_ready():
    logger.info(f'Bot has logged in as {bot.user.name} (ID: {bot.user.id})')
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    print('------')
    channel = bot.get_channel(channel_id)
    if channel:
        random_animal = await get_random_animal()
        lower_animal = random_animal.lower()
        await channel.send(f'ima tell you about the {lower_animal}.')
    else:
        print(f'No channel with id {channel_id} found.')

@bot.event
async def on_message(message):
    print(message)
    print(message.content)
    if bot.user.mentioned_in(message):
        # don't respond to ourselves
        if message.author == bot.user.id:
            return
        if "rabbit" in message.content.lower():
            await message.channel.send(f'No, I will not tell you about the rabbits, {message.author.name}.')
            return
        # Must be in the correct channel
        if message.channel.id != channel_id:
            return
        
        query = message.content.replace(f'<@{bot.user.id}>', '').strip()
        
        # If question is too short
        if len(query.split()) < 4:
            logger.info('Message too short.')
            await message.channel.send("Ask a longer question please.")
            return
        logger.info(f'Message received: {message.content} (From: {message.author.name})')
        # Create thread
        random_animal = await get_random_animal()
        thread = await message.create_thread(name=f"{random_animal} by {message.author.name}", auto_archive_duration=60)
        await thread.send(message_start)
        
        try:
            query_response = await agent.run_query(query)
        except Exception as e:
            tb = traceback.format_exc()
            logger.error(f"An error occurred: {str(e)}. Traceback: {tb}")
            await thread.send(f"An error occurred: {str(e)}. Traceback: {tb}")
            return  # or any other appropriate handling

        # Parse for discord and then respond
        parsed_reponse = parse_discord_markdown(query_response)
        logger.info(f'Parsed output: {parsed_reponse})')
        await thread.send(parsed_reponse)

def parse_discord_markdown(answer_obj):
    # Start with the answer text
    markdown_string = f"{answer_obj['answer_text']}\n\n"

    # Add the sources header if there are any documents
    if answer_obj['documents']:
        markdown_string += "**Sources:**\n"

        # For each document, add a numbered list item with the title and URL
        for doc in answer_obj['documents']:
            markdown_string += f"[{doc['doc_num']}] **{doc['title']}**: <{doc['url']}>\n"
    else:
        markdown_string += "No related documents found.\n"
    markdown_string += "\n Generated with: " + answer_obj['llm']
    markdown_string += "\n Memory not enabled. Will not respond with knowledge of past or current query."
    markdown_string += "\n For code see https://github.com/ShelbyJenkins/shelby-as-a-sprite."
    return markdown_string

if __name__ == "__main__":
    agent = ShelbyAgent()
    # Runs the bot through the asyncio.run() function built into the library
    bot.run(bot_token)



