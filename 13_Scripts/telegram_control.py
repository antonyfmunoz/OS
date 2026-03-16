import subprocess
import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

load_dotenv()

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
VAULT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

async def run_command(command, update: Update):
    result = subprocess.run(["C:/Program Files/Git/bin/bash.exe", "-c", command], capture_output=True, text=True, cwd=VAULT)
    output = result.stdout.strip() or result.stderr.strip() or "Done. No output returned."
    # Telegram messages max 4096 chars
    if len(output) > 4096:
        output = output[:4090] + "\n..."
    await update.message.reply_text(output)

async def research(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Signal research started...")
    await run_command("./13_Scripts/os.sh research", update)

async def report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Market report generating...")
    await run_command("./13_Scripts/os.sh report", update)

async def content(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Content engine running...")
    await run_command("./13_Scripts/os.sh content", update)

async def outreach(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Outreach messages generating...")
    await run_command("./13_Scripts/os.sh outreach", update)

async def leads(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Lead signals generating...")
    await run_command("./13_Scripts/lead_qualifier.sh", update)

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("research", research))
app.add_handler(CommandHandler("report", report))
app.add_handler(CommandHandler("content", content))
app.add_handler(CommandHandler("outreach", outreach))
app.add_handler(CommandHandler("leads", leads))

app.run_polling()
