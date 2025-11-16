import json
import os
from datetime import datetime, timedelta, timezone

import redis
from dotenv import load_dotenv
from telegram import Bot, KeyboardButton, ReplyKeyboardMarkup
from telegram.error import Forbidden
from telegram.ext import Application, CommandHandler, MessageHandler, filters

from db import get_db_pool, init_db, shutdown_db
from greetings_list import greetings

load_dotenv()

admin_id = os.getenv("ADMIN_ID")
TOKEN = os.getenv("TELEGRAM_TOKEN")
bot = Bot(token=TOKEN)

redis_url = os.getenv("REDIS_URL")
cache = redis.from_url(redis_url)
cache.set("flag", "False")

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

    await update.message.reply_text("Hello, my name is Kevin, I was build for testing")
    keyboard = [[KeyboardButton("CS"), KeyboardButton("CM")]]
    reply_markup = ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await update.message.reply_text("What is your major?", reply_markup=reply_markup)

async def broadcast(update, context):
    user_id = update.effective_user.id
    if str(user_id) == admin_id:
        cache.set("flag", "True")
        await bot.send_message(chat_id=admin_id, text="I am all ears, Boss")


async def help_command(update, context):
    await update.message.reply_text(
        "I can answer questions regarding your schedule like:\n"
        "What class?\n"
        "Which class is next?\n"
        "Today's classes?\n"
        "What lessons do i have for tomorrow?\n\n"
        
        "You can also use these commands:\n"
        "/users - how many users are using the bot\n"
        "/info - information about the developer"
    )


async def info(update, context):
    await update.message.reply_text(
        "This bot was created by Aidar Nasirov.\n"
        "Source code: https://github.com/AIDAR272/schedule_telegram_bot"
    )


async def num_users(update, context):
    db_pool = await get_db_pool()
    async with db_pool.acquire() as conn:
        cnt = await conn.fetchval("SELECT COUNT(*) FROM users")

    await update.message.reply_text(f"Currently, bot is being used by {cnt} users")


async def get_end_of_class(time:list[int], next_needed: bool, is_long: bool) -> list[int]:
    if next_needed:
        return time

    if is_long:
        time[0] += 3
    else:
        time[0] += 1
        time[1] += 30
        time[0] += time[1] // 60
        time[1] %= 60

    return time


async def get_classes_for_day(weekday:int, day:str, cohort: str, user_id: int) -> str:
    weekday %= 7
    weekday = str(weekday)
    if weekday == '5' or weekday == '6':
        return "You have no classes, Boss"

    with open("schedule.json") as f:
        schedule = json.load(f)
        schedule = schedule[cohort][weekday]
        classes = []
        for key, value in schedule.items():
            cached_value = cache.get("CA"+str(user_id))
            if (cohort == "CM" and
                    value[:8] == "Elective" and
                    cached_value and
                    cached_value.decode() == "False"):
                continue
            classes.append(f"{value} at {key}")

        classes.insert(0, f"{day} you have: {len(classes)} classes")
        return "\n\n".join(classes)


async def is_next_class(time:list[int]) -> bool:
    now = datetime.now(timezone(timedelta(hours=6)))
    current_time = [now.hour, now.minute]
    if time[0] > current_time[0] or time[0] == current_time[0] and time[1] >= current_time[1]:
        return True
    return False


async def time_left(time: list[int]) -> list[int]:
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


async def announcement(text: str, context) -> None:
    db_pool = await get_db_pool()
    async with db_pool.acquire() as conn:
        rows = await conn.fetch("SELECT user_id, first_name FROM users")
    for user in rows:
        user_id = user['user_id']
        cache.set(user_id, "True")
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=text
            )
        except Forbidden:
            print(f"User {user['first_name']} has blocked the bot")
        except Exception as e:
            print(f"Error sending message to {user['first_name']}: {e}")


async def process_message(update, context) -> None:
    user_id = update.effective_user.id
    name = update.effective_user.first_name
    text = update.message.text

    if text == "CM":
        key = "cohort" + str(user_id)
        cache.set(key, "CM")
        await update.message.reply_text("Your major is CM, if you want to change it, type 'CS'")

        keyboard = [[KeyboardButton("Yes, I am taking Computer Animation")], [KeyboardButton("No, I am not taking Computer Animation")]]
        reply_markup = ReplyKeyboardMarkup(
            keyboard,
            resize_keyboard=True,
            one_time_keyboard=True
        )
        await update.message.reply_text("Are you taking Computer Animation with Nelson Max?", reply_markup=reply_markup)
        return

    if text == "CS":
        key = "cohort" + str(user_id)
        cache.set(key, "CS")
        await update.message.reply_text("Your major is CS, if you want to change it, type 'CM'")
        return

    if text == "Yes, I am taking Computer Animation":
        cache.set("CA" + str(user_id), "True")
        await update.message.reply_text("Great, Thank you for letting me know")
        return

    if text == "No, I am not taking Computer Animation":
        cache.set("CA" + str(user_id), "False")
        await update.message.reply_text("Great, Thank you for letting me know")
        return

    text = text.lower()

    if str(user_id) == admin_id and cache.get("flag").decode() == "True":
        cache.set("flag", "False")
        await announcement(text, context)
        return

    if cache.get(user_id) is not None and cache.get(user_id).decode() == "True":
        cache.set(user_id, "False")
        cache.set(name, text)
        await update.message.reply_text("Thank you, for your time")
        return

    if await is_greeting(text):
        await update.message.reply_text("What's up, Boss!")
        return

    if await is_thanks(text):
        await update.message.reply_text("Sure, It's my job 😎!")
        return

    if "lesson" not in text and "class" not in text:
        await update.message.reply_text(
            f"I don't know what you mean by {text}.\n\n"
            f"Try typing: /help - to see what i know!"
        )
    else:
        weekday = datetime.now(timezone(timedelta(hours=6))).weekday()
        cohort = cache.get("cohort" + str(user_id)).decode()

        if cohort is None:
            await update.message.reply_text("Who are you?")
            return

        if "tomorrow" in text:
            await update.message.reply_text(await get_classes_for_day(weekday + 1, "Tomorrow", cohort, user_id))
            return

        if "today" in text:
            await update.message.reply_text(await get_classes_for_day(weekday, "Today", cohort, user_id))
            return

        next_needed = False
        if "next" in text:
            next_needed = True

        weekday = str(weekday)
        if weekday == '5' or weekday == '6':
            await update.message.reply_text("You have no classes, Boss")
            return

        with (open("schedule.json") as f):
            schedule = json.load(f)
            subject = ''
            flag = 0
            for key, value in schedule[cohort][weekday].items():
                time = key.split(":")
                time = [int(x) for x in time]
                if await is_next_class(time):
                    in_what_time = await time_left(time)
                    subject = value
                    break

                else:
                    is_long = False
                    if (weekday == '1' and value == "Media Production in WHITE" or
                        weekday == '3' and value == "Creative Writing in WHITE" or
                            weekday == '4' and value == "Communication in CA in GREEN"):
                        is_long = True

                    time = await get_end_of_class(time, next_needed, is_long)
                    if await is_next_class(time):
                        in_what_time = await time_left(time)
                        subject = value
                        flag = 1
                        break

            if subject == '':
                await update.message.reply_text("You have no other classes for today, Boss")
                return

            if not flag:
                text = f"Next class: {subject} in {in_what_time[0]} hours and {in_what_time[1]} minutes."
            else:
                text = f"Current class: {subject} will be over in {in_what_time[0]} hours and {in_what_time[1]} minutes."

            await update.message.reply_text(text)


async def notify_before_class(context) -> None:
    with open("schedule.json") as f:
        schedule = json.load(f)

    now = datetime.now(timezone(timedelta(hours=6)))
    weekday = now.weekday()
    for cohort in ["CS", "CM"]:
        for key, value in schedule[cohort][str(weekday)].items():
            class_hour, class_minute = map(int, key.split(":"))
            class_dt = now.replace(hour=class_hour, minute=class_minute, second=0, microsecond=0)

            diff = (class_dt - now).total_seconds()
            if 540 <= diff < 600:
                db_pool = await get_db_pool()
                async with db_pool.acquire() as conn:
                    rows = await conn.fetch("SELECT user_id, first_name FROM users")
                for user in rows:
                    user_id = user['user_id']

                    cached_cohort = cache.get("cohort" + str(user_id))
                    if cached_cohort and cached_cohort.decode() == cohort:
                        cached_value = cache.get("CA" + str(user_id))
                        if (cohort == "CM" and
                            value[:8] == "Elective" and
                            cached_value and
                            cached_value.decode() == "False"):
                            continue
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
    app.post_init = init_db
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("info", info))
    app.add_handler(CommandHandler("users", num_users))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, process_message))

    app.job_queue.run_repeating(notify_before_class, interval=60, first=0)
    app.post_shutdown = shutdown_db
    print("Bot is running")
    app.run_polling()


if __name__ == "__main__":
    main()
    