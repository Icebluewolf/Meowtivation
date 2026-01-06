from textwrap import dedent
from typing import Self

from asyncpg import ForeignKeyViolationError, Record
from discord import ui, ButtonStyle

from utils.database import database as db


class Reward:
    _cache: dict[int, Self] = {}

    def __init__(self, user: int, text: str, cost: int, renewable: bool):
        self.user = user
        self.text = text
        self.cost = cost
        self.renewable = renewable

        self.id = None
        self.deleted = False

    def display(self) -> ui.DesignerView:
        assert NotImplementedError()

    def short_display(self) -> ui.Section:
        output = dedent(f"""\
            ### {self.text}
            {"Redeemable Once" if not self.renewable else ""}
        """)

        s = ui.Section(
            ui.TextDisplay(output),
            accessory=ui.Button(
                emoji="<:cookie_star:1449975179659968626>",
                label=f"{self.cost:.2f} Crumbs",
                style=ButtonStyle.primary,
                custom_id="shop_reward::" + str(self.id),
                disabled=self.deleted,
            )
        )
        return s

    async def create(self) -> None:
        sql = ("INSERT INTO reward (discord_user, text, cost, renewable) "
               "VALUES ($1, $2, $3, $4) RETURNING id;")
        sql_vars = (self.user, self.text, self.cost, self.renewable)
        try:
            self.id = await db.fetchval(sql, *sql_vars)
        except ForeignKeyViolationError:
            # Insert the user if they do not exist
            await db.execute("INSERT INTO discord_user (id, points, share_points) VALUES ($1, 0, 0);", self.user)
            self.id = await db.fetchval(sql, *sql_vars)

        Reward._cache[self.id] = self

    async def edit(self, *, temp) -> None:
        assert NotImplementedError()

    async def delete(self) -> None:
        try:
            Reward._cache.pop(self.id)
        except KeyError:
            pass
        await db.execute("DELETE FROM reward WHERE id=$1;", self.id)
        self.deleted = True

    @staticmethod
    async def fetch(id: int) -> Self:
        r = Reward._cache.get(id)
        if r is None:
            sql = "SELECT id, discord_user, text, cost, renewable FROM reward WHERE id=$1;"
            r = await Reward.from_db(await db.fetch_one(sql, id))

        return r

    @staticmethod
    async def fetch_user_rewards(user_id: int) -> list[Self]:
        sql = "SELECT id, discord_user, text, cost, renewable FROM reward WHERE discord_user=$1 ORDER BY created;"
        rows = await db.fetch(sql, user_id)
        return [await Reward.from_db(r) for r in rows]

    @classmethod
    async def from_db(cls, row: Record) -> Self:
        g = cls(row["discord_user"], row["text"], row["cost"], row["renewable"])
        g.id = row["id"]

        Reward._cache[g.id] = g

        return g



