import discord
from discord.ext import commands
from dotenv import load_dotenv
import os
import database

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

database.create_tables()

bot = commands.Bot(command_prefix="?", intents=intents)

@bot.event
async def on_ready():
    print(f"Bot conectado como {bot.user}")

@bot.event
async def setup_hook():
    await bot.load_extension("cogs.balance")
    await bot.load_extension("cogs.ecoins")
    await bot.load_extension("cogs.activities")
    await bot.load_extension("cogs.loot")
    await bot.load_extension("cogs.warnings")
    await bot.load_extension("cogs.profile")
    await bot.load_extension("cogs.leaderboard")
    await bot.load_extension("cogs.stats")
    await bot.load_extension("cogs.history")
    await bot.load_extension("cogs.shop")
    await bot.load_extension("cogs.dashboard")
    await bot.load_extension("cogs.achievements")
    await bot.load_extension("cogs.albion")
    await bot.load_extension("cogs.fame")
    await bot.load_extension("cogs.ava_fame_stats")
    await bot.load_extension("cogs.audio")

bot.run(TOKEN)
