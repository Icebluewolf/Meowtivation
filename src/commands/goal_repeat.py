from datetime import time, UTC, datetime
from discord.ext import tasks

from models.goal import RepeatType
from utils.database import database as db


@tasks.loop(time=time(tzinfo=UTC))
async def uncomplete():
    dt = datetime.now(UTC)

    sql = "UPDATE goal SET completed=FALSE WHERE repeat=$1;"

    await db.execute(sql, RepeatType.DAILY)

    if dt.weekday() == 0:
        await db.execute(sql, RepeatType.WEEKLY)
    if dt.day == 1:
        await db.execute(sql, RepeatType.MONTHLY)
    if dt.day == 1 and dt.month == 1:
        await db.execute(sql, RepeatType.YEARLY)


def setup(bot):
    uncomplete.start()
