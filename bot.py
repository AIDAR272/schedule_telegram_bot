import json
from typing import List
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from datetime import datetime, timezone, timedelta
import os
from dotenv import load_dotenv
load_dotenv()

from greetings_list import greetings

TOKEN = os.getenv("TELEGRAM_TOKEN")


async def start(update, context):
    await update.message.reply_text("Hello my name is Kevin. How can i help you?")


async def help_command(update, context):
    await update.message.reply_text(
        f"Try asking questions like:\n"
        f"What class?\n"
        f"Which class is next?\n"
        f"Today's classes?\n"
        f"What lessons do i have for tomorrow?\n"
    )


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
    weekday = str(weekday)
    with open("schedule.json", 'r') as f:
        schedule = json.load(f)
        schedule = schedule[weekday]
        classes = [f"{day} you have: {len(schedule)} classes"]
        for key, value in schedule.items():
            classes.append(f"{value} at {key}")

        return "\n\n".join(classes)


async def cpu(update, context):
    text = update.message.text
    text = text.lower()
    if await is_greeting(text):
        await update.message.reply_text(f"What's up, Boss!\n\n")

    if await is_thanks(text):
        await update.message.reply_text(f"Sure, It's my job 😎!")
        return

    if "lesson" not in text and "class" not in text:
        await update.message.reply_text(
            f"Sorry,\n"
            f"I don't know what you mean by {text}.\n\n"
            f"Try typing: /help - to see my full potential!"
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
            await update.message.reply_text(f"You have no classes today.\n"
                                            f"Enjoy your well deserved rest, Boss")
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
                await update.message.reply_text(f"You have no other classes for today.\n"
                                                f"Enjoy your well deserved rest, Boss")
                return

            if not flag:
                text = f"Next class: {subject} in {in_what_time[0]} hours and {in_what_time[1]} minutes."
            else:
                text = f"Current class: {subject} will be over in {in_what_time[0]} hours and {in_what_time[1]} minutes."

            await update.message.reply_text(text)


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
        if word in text:
            return True

    return False


async def is_thanks(text: str) -> bool:
    if "thanks" in text or "thank you" in text:
        return True

    return False


def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, cpu))
    print("Bot is running")
    app.run_polling()

if __name__ == "__main__":
    main()