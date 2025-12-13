from asyncpg.exceptions import ForeignKeyViolationError
from discord import Bot, ApplicationContext, SelectOption, slash_command, Interaction
from discord.ui import DesignerModal, TextInput, Select, Label, DesignerView

from utils import component_factory as cf
from utils.database import database as db


class CreateGoal(DesignerModal):
    def __init__(self):
        super().__init__(title="Create A Personal Goal")

        self.goal_text = TextInput(placeholder="Chase a laser pointer for 15 minutes", max_length=400)
        self.add_item(Label("Goal", self.goal_text, description="Give a brief description of your goal"))

        self.repeat_select = Select(options=[
                                SelectOption(label="Never", description="A one time goal", default=True),
                                SelectOption(label="Daily", description="Repeat once a day"),
                                SelectOption(label="Weekly", description="Repeat once a week on this day"),
                                SelectOption(label="Monthly", description="Repeat once a month on this day"),
                                SelectOption(label="Custom (Set After Submitting)",
                                             description="More fine grained control in a separate panel"),
                            ])
        self.add_item(Label("Repeat", self.repeat_select))

        self.crumb_count = TextInput(placeholder="5", max_length=2)
        self.add_item(Label("Cookie Crumb Reward", self.crumb_count,
                            description="How much of a reward does this task deserve? We recommend 10 Crumbs should "
                                        "equal one small reward."))

    async def callback(self, interaction: Interaction):
        crumb_error = False
        try:
            crumbs = int(self.crumb_count.value)
        except ValueError:
            crumb_error = True
        else:
            crumb_error = crumbs <= 0

        if crumb_error:
            await interaction.respond(view=DesignerView(await cf.input_error(
                "Failed To Process Input", ["Cookie Crumb Reward must be a positive integer"]
            )), ephemeral=True)
            return

        sql = "INSERT INTO goal (discord_user, text, reward, completed, repeat, reset_at) VALUES ($1, $2, $3, $4, $5, $6) RETURNING id;"
        vars = (interaction.user.id, self.goal_text.value, crumbs, False, 0, None)
        try:
            gid = await db.fetchval(sql, *vars)
        except ForeignKeyViolationError:
            await db.execute("INSERT INTO discord_user (id, points, share_points) VALUES ($1, 0, 0)", interaction.user.id)
            gid = await db.fetchval(sql, *vars)
        await interaction.respond(str(gid))


@slash_command(description="Create A New Personal Goal")
async def goal(ctx: ApplicationContext):
    await ctx.send_modal(CreateGoal())


def setup(bot: Bot):
    bot.add_application_command(goal)
