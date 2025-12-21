from typing import Self

from asyncpg import Record

from utils.database import database as db


class Incentive:
    # Key: (Goal ID, Sender ID)
    _cache: dict[tuple[int, int], Self] = {}

    def __init__(self, sender: int, goal: int):
        self.sender: int = sender
        self.goal: int = goal

    async def create(self):
        sql = "INSERT INTO incentive (sender, goal) VALUES ($1, $2)"
        await db.execute(sql, self.sender, self.goal)

    @staticmethod
    async def fetch(sender: int, goal: int) -> Self:
        r = Incentive._cache.get((goal, sender))
        if r is None:
            sql = "SELECT goal, sender FROM incentive WHERE goal=$1 AND sender=$2;"
            r = await Incentive.from_db(await db.fetch_one(sql, goal, sender))

        return r

    @staticmethod
    async def fetch_all_goal(goal: int) -> list[Self]:
        sql = "SELECT goal, sender FROM incentive WHERE goal=$1;"
        rows = await db.fetch(sql, goal)
        return [await Incentive.from_db(r) for r in rows]

    @classmethod
    async def from_db(cls, row: Record) -> Self:
        g = cls(row["sender"], row["goal"])

        return g

