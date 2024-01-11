# Import necessary libraries
from flask import Flask
from threading import Thread
import discord
from discord.ext import commands, tasks
import pytesseract
from PIL import Image
import requests
from io import BytesIO
from datetime import datetime, timedelta
import pytz
import os

# Initialize Intents and Discord Bot
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True

bot = commands.Bot(command_prefix="/", intents=intents)

# Initialize Flask App for the Web Server
app = Flask('')

@app.route('/')
def home():
    return "Hello. I am alive!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    server = Thread(target=run)
    server.start()

# Bot's code
# OCR function to process images
def process_image(url):
    response = requests.get(url)
    img = Image.open(BytesIO(response.content))
    text = pytesseract.image_to_string(img)
    return text

# Check if all tasks are claimed
def all_tasks_claimed(text):
    return "Claimed" in text

# Leaderboard data
daily_leaderboard = {}
weekly_leaderboard = {}
monthly_leaderboard = {}

# Reset function for leaderboards
def reset_leaderboard(leaderboard):
    for key in list(leaderboard.keys()):
        leaderboard[key] = 0

# Update leaderboards
def update_leaderboards(user):
    for board in [daily_leaderboard, weekly_leaderboard, monthly_leaderboard]:
        board[user] = board.get(user, 0) + 1

# Show leaderboard
def format_leaderboard(leaderboard):
    return "\n".join([f"{user}: {score}" for user, score in leaderboard.items()])

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    reset_daily_leaderboard.start()
    reset_weekly_leaderboard.start()
    reset_monthly_leaderboard.start()

@bot.command()
async def leaderboard(ctx, leaderboard_type):
    if leaderboard_type == "daily":
        await ctx.send(f"Daily Leaderboard:\n{format_leaderboard(daily_leaderboard)}")
    elif leaderboard_type == "weekly":
        await ctx.send(f"Weekly Leaderboard:\n{format_leaderboard(weekly_leaderboard)}")
    elif leaderboard_type == "monthly":
        await ctx.send(f"Monthly Leaderboard:\n{format_leaderboard(monthly_leaderboard)}")
    else:
        await ctx.send("Invalid leaderboard type. Use daily, weekly, or monthly.")

@bot.command()
async def submit(ctx, in_game_username: str):
    for attachment in ctx.message.attachments:
        if attachment.filename.endswith(('.png', '.jpg', '.jpeg')):
            text = process_image(attachment.url)
            if all_tasks_claimed(text):
                update_leaderboards(in_game_username)
                await ctx.send(f"Task completed by {in_game_username}.")
            else:
                await ctx.send("No claimed tasks found in the submitted image.")
        else:
            await ctx.send("Please attach an image with your command.")

@bot.event
async def on_message(message):
    if message.author == bot.user or not message.guild:
        return

    if message.channel.name == 'power-level-submissions':
        if message.content.startswith('/submit'):
            await bot.process_commands(message)
        else:
            await message.delete()

# Reset the daily leaderboard every day at 0 UTC
@tasks.loop(hours=24)
async def reset_daily_leaderboard():
    reset_leaderboard(daily_leaderboard)

@reset_daily_leaderboard.before_loop
async def before_reset_daily_leaderboard():
    await bot.wait_until_ready()
    now = datetime.now(pytz.utc)
    next_run = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    await discord.utils.sleep_until(next_run)

# Reset the weekly leaderboard every week
@tasks.loop(hours=168)  # 168 hours = 7 days
async def reset_weekly_leaderboard():
    reset_leaderboard(weekly_leaderboard)

# Reset the monthly leaderboard every month
@tasks.loop(hours=730)  # Approximate number of hours in a month
async def reset_monthly_leaderboard():
    reset_leaderboard(monthly_leaderboard)

# Start the web server and the bot
keep_alive()
bot.run(os.getenv('DISCORD_TOKEN'))
