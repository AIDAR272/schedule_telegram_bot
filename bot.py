import json
import os
from typing import List
from telegram import Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from telegram.error import Forbidden
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from greetings_list import greetings

from db import init_db, shutdown_db, get_db_pool


load_dotenv()

TOKEN = os.getenv("TELEGRAM_TOKEN")
bot = Bot(token=TOKEN)


async def start(update, context):
    user = update.effective_user
    user_id = user.id
    first_name = user.first_name
    username = user.username if user.username else None
    db_pool = await get_db_pool()
    async with db_pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO users (user_id, first_name, username) VALUES ($1, $2, $3) ON CONFLICT DO NOTHING",
            user_id, first_name, username
        )

    await update.message.reply_text("Hello, my name is Kevin. How can i help you?")


async def help_command(update, context):
    await update.message.reply_text(
        f"I can answer questions regarding your schedule like:\n"
        f"What class?\n"
        f"Which class is next?\n"
        f"Today's classes?\n"
        f"What lessons do i have for tomorrow?\n\n"
        
        f"You can also use these commands:\n"
        f"/users - how many users are using the bot\n"
        f"/info - information about the developer"
    )


async def info(update, context):
    await update.message.reply_text(
        f"This bot was created by Aidar Nasirov.\n"
        f"Source code: https://github.com/AIDAR272/schedule_telegram_bot"
    )


async def num_users(update, context):
    db_pool = await get_db_pool()
    async with db_pool.acquire() as conn:
        cnt = await conn.fetchval("SELECT COUNT(*) FROM users")

    await update.message.reply_text(f"Currently, bot is being used by {cnt} users")


async def get_end_of_class(time:List[int], next_needed: bool):
    if next_needed:
        return time

    time[0] += 1
    if time[1] == 30:
        time[0] += 1
        time[1] = 0
    else:
        time[1] += 30

    return time


async def get_classes_for_day(weekday:int, day:str):
    if weekday == 7: weekday = 0
    weekday = str(weekday)
    if weekday == '5' or weekday == '6':
        return f"You have no classes, Boss"

    with open("schedule.json", 'r') as f:
        schedule = json.load(f)
        schedule = schedule[weekday]
        classes = [f"{day} you have: {len(schedule)} classes"]
        for key, value in schedule.items():
            classes.append(f"{value} at {key}")

        return "\n\n".join(classes)


async def is_next_class(time:List[int]) -> bool:
    now = datetime.now(timezone(timedelta(hours=6)))
    current_time = [now.hour, now.minute]
    if time[0] > current_time[0] or time[0] == current_time[0] and time[1] >= current_time[1]:
        return True
    return False


async def time_left(time: List[int]):
    now = datetime.now(timezone(timedelta(hours=6)))
    current_time = [now.hour, now.minute]
    in_what_time = []
    if time[1] < current_time[1]:
        in_what_time.append(60 + time[1] - current_time[1])
        time[0] -= 1
    else:
        in_what_time.append(time[1] - current_time[1])
    in_what_time.append(time[0] - current_time[0])

    return in_what_time[::-1]


async def is_greeting(text: str) -> bool:
    for word in greetings:
        if word == text:
            return True

    return False


async def is_thanks(text: str) -> bool:
    if "thanks" in text or "thank you" in text:
        return True

    return False


async def cpu(update, context):
    text = update.message.text
    text = text.lower()
    if await is_greeting(text):
        await update.message.reply_text(f"What's up, Boss!\n\n")
        return

    if await is_thanks(text):
        await update.message.reply_text(f"Sure, It's my job 😎!")
        return

    if "lesson" not in text and "class" not in text:
        await update.message.reply_text(
            f"I don't know what you mean by {text}.\n\n"
            f"Try typing: /help - to see what i know!"
        )
    else:
        weekday = datetime.now(timezone(timedelta(hours=6))).weekday()
        if "tomorrow" in text:
            await update.message.reply_text(await get_classes_for_day(weekday + 1, "Tomorrow"))
            return

        if "today" in text:
            await update.message.reply_text(await get_classes_for_day(weekday, "Today"))
            return


        next_needed = False
        if "next" in text:
            next_needed = True

        weekday = str(weekday)
        if weekday == '5' or weekday == '6':
            await update.message.reply_text(f"You have no classes, Boss")
            return

        with open("schedule.json", 'r') as f:
            schedule = json.load(f)
            subject = ''
            flag = 0
            for key, value in schedule[weekday].items():
                time = key.split(":")
                time = [int(x) for x in time]
                if await is_next_class(time):
                    in_what_time = await time_left(time)
                    subject = value
                    break

                else:
                    time = await get_end_of_class(time, next_needed)
                    if await is_next_class(time):
                        in_what_time = await time_left(time)
                        subject = value
                        flag = 1
                        break


            if subject == '':
                await update.message.reply_text(f"You have no other classes for today, Boss")
                return

            if not flag:
                text = f"Next class: {subject} in {in_what_time[0]} hours and {in_what_time[1]} minutes."
            else:
                text = f"Current class: {subject} will be over in {in_what_time[0]} hours and {in_what_time[1]} minutes."

            await update.message.reply_text(text)


async def notify_before_class(context):
    with open("schedule.json", 'r') as f:
        schedule = json.load(f)

    now = datetime.now(timezone(timedelta(hours=6)))
    weekday = now.weekday()
    for key, value in schedule[str(weekday)].items():
        class_hour, class_minute = map(int, key.split(":"))
        class_dt = now.replace(hour=class_hour, minute=class_minute, second=0, microsecond=0)

        diff = (class_dt - now).total_seconds()
        if 540 <= diff < 600:
            db_pool = await get_db_pool()
            async with db_pool.acquire() as conn:
                rows = await conn.fetch("SELECT user_id, first_name FROM users")
            for user in rows:
                user_id = user['user_id']
                try:
                    await context.bot.send_message(
                        chat_id=user_id,
                        text=f"Boss, you have {value} in 10 minutes"
                    )
                except Forbidden:
                    print(f"User {user['first_name']} has blocked the bot")
                except Exception as e:
                    print(f"Error sending message to {user['first_name']}: {e}")


def main():
    app = Application.builder().token(TOKEN).build()
    import asyncio
    asyncio.get_event_loop().run_until_complete(init_db(app))
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("info", info))
    app.add_handler(CommandHandler("users", num_users))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, cpu))

    app.job_queue.run_repeating(notify_before_class, interval=60, first=0)
    app.post_shutdown = shutdown_db
    print("Bot is running")
    app.run_polling()


if __name__ == "__main__":
    main()