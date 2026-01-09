from random import choice, randint

from discord import Bot, ApplicationContext, SelectOption, slash_command, Interaction, AllowedMentions
from discord import ui, InputTextStyle

from models.goal import Goal, RepeatType
from models.incentive import Incentive
from models.user import User
from utils import component_factory as cf


GOAL_TEXT_PLACEHOLDERS = [
    "Maintain a seamless \"bread loaf\" form for at least 20 minutes.",
    "Complete five laps around the living room at top speed at 3 AM.",
    "Locate the strongest sunbeam in the house and occupy it until it moves.",
    "Ensure every single toe-bean is polished and pristine.",
    "Drink water specifically from a glass left unattended by a human.",
    "Knead the softest blanket in the house until the texture is \"just right.\"",
    "Inspect and occupy the newest delivery box within 30 seconds of arrival.",
    "Conduct a scientific experiment to see if a pen falls off the desk when nudged.",
    "Successfully corner and \"capture\" the elusive red laser dot.",
    "Reach the highest shelf in the room to survey the kingdom.",
    "Achieve a state of total liquid relaxation in a sink or basket.",
    "\"Help\" a human finish their work by sitting directly on the laptop.",
    "Trip a human by weaving through their legs the moment they walk through the door.",
    "Successfully catch the tail (even if it takes 15 tries).",
    "Secure a lap for a minimum of one hour of synchronized purring.",
]


class CreateGoal(ui.DesignerModal):
    def __init__(self):
        super().__init__(title="Create A Personal Goal")

        self.goal_text = ui.TextInput(style=InputTextStyle.long, placeholder=choice(GOAL_TEXT_PLACEHOLDERS), max_length=400)
        self.add_item(ui.Label("Goal", self.goal_text, description="Give a brief description of your goal"))

        self.repeat_select = ui.Select(options=[
                                SelectOption(label="Never", description="A one time goal", default=True, value="0"),
                                SelectOption(label="Daily", description="Repeat once a day at midnight UTC", value="1"),
                                SelectOption(label="Weekly", description="Repeat once a week on Mondays at midnight UTC", value="2"),
                                SelectOption(label="Monthly", description="Repeat once a month on the 1st at midnight UTC", value="3"),
                                SelectOption(label="Yearly",
                                             description="Repeat once a year on January 1st at midnight UTC",
                                             value="4"),
                            ])
        self.add_item(ui.Label("Repeat", self.repeat_select))

        self.crumb_count = ui.TextInput(placeholder=str(randint(2, 10)), max_length=2)
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

        await interaction.respond(view=g.display(), allowed_mentions=AllowedMentions.none())


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
    await g.complete()
    await interaction.edit(view=g.display())


async def add_incentive_button(interaction: Interaction) -> None:
    g: Goal = await Goal.fetch(interaction.message.get_component("complete_goal").id)
    if g.user == interaction.user.id:
        await interaction.respond(view=ui.DesignerView(await cf.fail("You cannot add a chocolate nibble to your own goal")),
                                  ephemeral=True)
        return

    u = await User.fetch(interaction.user.id)
    if not await u.use_share_points(1):
        await interaction.respond(
            view=ui.DesignerView(await cf.fail("You Do Not Have Any Chocolate Nibbles. Every Goal You Complete Earns You One.")),
            ephemeral=True)
        return

    incentive = Incentive(interaction.user.id, g.id)
    await incentive.create()
    g.incentives.append(incentive)
    await interaction.edit(view=g.display())

    await interaction.respond(view=await cf.general(f"You Have {u.share_points} Chocolate Nibbles Left"), ephemeral=True)


def setup(bot: Bot):
    bot.add_application_command(goal)

    bot.add_listener(on_interaction)
