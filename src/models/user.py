import decimal
from typing import Self

from asyncpg import Record

from utils.database import database as db


class User:
    _cache: dict[int, Self] = {}

    def __init__(self, user_id: int):
        self.user_id = user_id
        self.points = 0
        self.share_points = 0

        User._cache[self.user_id] = self

    async def create(self) -> None:
        await db.execute("INSERT INTO discord_user (id, points, share_points) VALUES ($1, 0, 0);", self.user_id)

    async def use_points(self, num: int) -> bool:
        """:returns True if the user had enough points, otherwise False"""
        if self.points < num:
            return False

        self.points -= num
        await db.execute("UPDATE discord_user SET points=$1 WHERE id=$2;", self.points, self.user_id)
        return True

    async def use_share_points(self, num: int) -> bool:
        """:returns True if the user had enough share points, otherwise False"""
        if self.share_points < num:
            return False

        self.share_points -= num
        await db.execute("UPDATE discord_user SET share_points=$1 WHERE id=$2;", self.share_points, self.user_id)
        return True

    async def add_points(self, points: float = 0, share_points: int = 0) -> None:
        self.points += points
        self.share_points += share_points
        await db.execute("UPDATE discord_user SET points=$1, share_points=$2 WHERE id=$3;", self.points, self.share_points, self.user_id)

    @classmethod
    async def fetch(cls, id: int) -> Self:
        r = cls._cache.get(id)
        if r is None:
            sql = "SELECT id, points, share_points FROM discord_user WHERE id=$1;"
            r = await cls.from_db(await db.fetch_one(sql, id))
            if r is None:
                r = cls(id)
                await r.create()
            cls._cache[id] = r

        return r

    @classmethod
    async def from_db(cls, row: Record) -> Self | None:
        if row is None:
            return None
        u = cls(row["id"])
        u.points = row["points"]
        u.share_points = row["share_points"]

        return u
