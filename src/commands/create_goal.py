from discord import Bot, ApplicationContext, SelectOption, slash_command, Interaction
from discord import ui

from models.goal import Goal, RepeatType
from models.incentive import Incentive
from utils import component_factory as cf


class CreateGoal(ui.DesignerModal):
    def __init__(self):
        super().__init__(title="Create A Personal Goal")

        self.goal_text = ui.TextInput(placeholder="Chase a laser pointer for 15 minutes", max_length=400)
        self.add_item(ui.Label("Goal", self.goal_text, description="Give a brief description of your goal"))

        self.repeat_select = ui.Select(options=[
                                SelectOption(label="Never", description="A one time goal", default=True, value="0"),
                                SelectOption(label="Daily", description="Repeat once a day", value="1"),
                                SelectOption(label="Weekly", description="Repeat once a week on this day", value="2"),
                                SelectOption(label="Monthly", description="Repeat once a month on this day", value="3"),
                                SelectOption(label="Custom (Set After Submitting)",
                                             description="More fine grained control in a separate panel",
                                             value="4"),
                            ])
        self.add_item(ui.Label("Repeat", self.repeat_select))

        self.crumb_count = ui.TextInput(placeholder="5", max_length=2)
        self.add_item(ui.Label("Cookie Crumb Reward", self.crumb_count,
                            description="How much of a reward does this task deserve? We recommend 10 Crumbs should "
                                        "equal one small reward."))

    async def callback(self, interaction: Interaction):
        try:
            crumbs = int(self.crumb_count.value)
        except ValueError:
            crumb_error = True
        else:
            crumb_error = crumbs <= 0

        if crumb_error:
            await interaction.respond(view=ui.DesignerView(await cf.input_error(
                "Failed To Process Input", ["Cookie Crumb Reward must be a positive integer"]
            )), ephemeral=True)
            return

        g = Goal(interaction.user.id, self.goal_text.value, RepeatType(int(self.repeat_select.values[0])), crumbs)
        await g.create()

        await interaction.respond(view=g.display(), allowed_mentions=None)


@slash_command(description="Create A New Personal Goal")
async def goal(ctx: ApplicationContext):
    await ctx.send_modal(CreateGoal())


# Handle Interactions Manually Instead Of Using View Callbacks
async def on_interaction(interaction: Interaction):
    if interaction.custom_id == "complete_goal":
        await complete_goal_button(interaction)
    elif interaction.custom_id == "add_incentive":
        await add_incentive_button(interaction)


async def complete_goal_button(interaction: Interaction) -> None:
    g = await Goal.fetch(interaction.message.get_component("complete_goal").id)
    if g.user != interaction.user.id:
        await interaction.respond(view=ui.DesignerView(await cf.fail("You cannot complete other users goals")), ephemeral=True)
        return
    await g.edit(completed=True)
    await interaction.edit(view=g.display())


async def add_incentive_button(interaction: Interaction) -> None:
    g: Goal = await Goal.fetch(interaction.message.get_component("complete_goal").id)
    if g.user == interaction.user.id:
        await interaction.respond(view=ui.DesignerView(await cf.fail("You cannot add a chocolate nibble to your own goal")),
                                  ephemeral=True)
        return

    incentive = Incentive(interaction.user.id, g.id)
    await incentive.create()
    g.incentives.append(incentive)
    await interaction.edit(view=g.display())


def setup(bot: Bot):
    bot.add_application_command(goal)

    bot.add_listener(on_interaction)
