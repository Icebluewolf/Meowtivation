from enum import Enum
from typing import Self
from textwrap import dedent

from asyncpg import ForeignKeyViolationError, Record
from discord import ui, ButtonStyle

from models.user import User
from utils.database import database as db
from models.incentive import Incentive


class RepeatType(Enum):
    NEVER = 0
    DAILY = 1
    WEEKLY = 2
    MONTHLY = 3
    YEARLY = 4

    def display(self):
        if self == RepeatType.NEVER:
            return "Never"
        elif self == RepeatType.DAILY:
            return "Daily At Midnight UTC"
        elif self == RepeatType.WEEKLY:
            return "Weekly On Mondays At Midnight UTC"
        elif self == RepeatType.MONTHLY:
            return "Monthly On The 1st At Midnight UTC"
        elif self == RepeatType.YEARLY:
            return "Yearly On January 1st At Midnight UTC"


class Goal:
    _cache: dict[int, Self] = {}

    def __init__(self, user: int, text: str, repeat: RepeatType, reward: int):
        self.user = user
        self.text = text
        self.repeat = repeat
        self.reward = reward

        self.completed = False
        self.reset_at = None
        self.id = None
        self.created = None

        self.incentives: list[Incentive] = []

    def display(self) -> ui.DesignerView:
        output = dedent(f"""\
            ## {"You Did It" if self.completed else "You Got This"} <@{self.user}>!
            **Goal:** {self.text}
            **Repeat:** {self.repeat.display()}
            **Reward:** {self.reward} {f"(+{0.1 * self.reward * len(self.incentives):.2f})" if len(self.incentives) > 0 else ""} Crumbs
        """)

        v = ui.DesignerView(
            ui.Container(
                ui.TextDisplay(output),
                ui.ActionRow(
                    ui.Button(label="Complete", style=ButtonStyle.success, custom_id="complete_goal", id=self.id,
                              disabled=self.completed),
                    ui.Button(emoji="<:chip:1450994486275735562>", label="Add Chocolate Nibble", style=ButtonStyle.secondary, custom_id="add_incentive"),
                )
            ),
        )

        if len(self.incentives) > 0:
            c = ui.Container(
                ui.TextDisplay(f"These users gave a little boost because they want to see <@{self.user}> succeed!\n" + "\n".join(["<@"+str(i.sender)+"> Added a chocolate nibble to the reward" for i in self.incentives]))
            )
            v.add_item(c)
        return v

    def short_display(self) -> ui.Section:
        output = dedent(f"""\
            ### {"<:cookie_star:1449975179659968626> Completed: " if self.completed else ""} {self.text}
            {"**Repeat:** " + self.repeat.display() if self.repeat != RepeatType.NEVER else ""}
            *Gives {self.reward} <:cookie_star:1449975179659968626> when completed*
        """)

        s = ui.Section(
            ui.TextDisplay(output),
            accessory=ui.Button(label="View", style=ButtonStyle.primary, custom_id="view_goal::" + str(self.id), id=self.id)
        )
        return s

    async def create(self) -> None:
        sql = ("INSERT INTO goal (discord_user, text, reward, completed, repeat, reset_at) "
               "VALUES ($1, $2, $3, $4, $5, $6) RETURNING id;")
        sql_vars = (self.user, self.text, self.reward, False, self.repeat.value, None)
        try:
            self.id = await db.fetchval(sql, *sql_vars)
        except ForeignKeyViolationError:
            # Insert the user if they do not exist
            await db.execute("INSERT INTO discord_user (id, points, share_points) VALUES ($1, 0, 0);", self.user)
            self.id = await db.fetchval(sql, *sql_vars)

        Goal._cache[self.id] = self

    async def edit(self, *, completed: bool = None, text: str = None, reward: int = None,
                   repeat: RepeatType = None) -> None:
        if completed is not None:
            self.completed = completed
        if text is not None:
            self.text = text
        if reward is not None:
            self.reward = reward
        if repeat is not None:
            self.repeat = repeat

        sql = "UPDATE goal SET completed=$2, text=$3, reward=$4, repeat=$5 WHERE id=$1;"
        await db.execute(
            sql,
            self.id,
            self.completed,
            self.text,
            self.reward,
            self.repeat.value,
        )

    async def complete(self) -> None:
        await self.edit(completed=True)
        u = await User.fetch(self.user)
        await u.add_points(self.reward + self.reward * 0.1 * len(self.incentives), 1)

    @staticmethod
    async def fetch(id: int) -> Self:
        r = Goal._cache.get(id)
        if r is None:
            sql = "SELECT id, discord_user, text, reward, completed, repeat, reset_at, created FROM goal WHERE id=$1"
            r = await Goal.from_db(await db.fetch_one(sql, id))
            r.incentives = await Incentive.fetch_all_goal(id)

        return r

    @staticmethod
    async def fetch_user_goals(user_id: int, completed: bool) -> list[Self]:
        if completed:
            sql = "SELECT id, discord_user, text, reward, completed, repeat, reset_at, created FROM goal WHERE discord_user=$1 ORDER BY created;"
        else:
            sql = "SELECT id, discord_user, text, reward, completed, repeat, reset_at, created FROM goal WHERE discord_user=$1 AND completed=false ORDER BY created;"
        rows = await db.fetch(sql, user_id)
        return [await Goal.from_db(r) for r in rows]

    @classmethod
    async def from_db(cls, row: Record) -> Self:
        g = cls(row["discord_user"], row["text"], RepeatType(row["repeat"]), row["reward"])
        g.completed = row["completed"]
        g.reset_at = row["reset_at"]
        g.id = row["id"]
        g.created = row["created"]

        return g



