from discord import Bot, ApplicationContext, slash_command, Interaction, Option, SlashCommand, ui

from models.goal import Goal
from utils import component_factory as cf


@slash_command(description="Create A New Personal Goal")
async def goal_list(ctx: ApplicationContext, completed: Option(bool, description="List Completed Goals", default=False)):
    goals = await Goal.fetch_user_goals(ctx.author.id, completed)

    if len(goals) == 0:
        if completed:
            await ctx.respond(await cf.fail(f"You have not made any goals! Use {ctx.bot.get_command("goal", None, SlashCommand).mention} to get started."), ephemeral=True)
            return
        else:
            await ctx.respond(await cf.fail(f"You dont have any uncompleted goals. Use {ctx.bot.get_command("goal", None, SlashCommand).mention} to get another."), ephemeral=True)
            return

    c = ui.Container(ui.TextDisplay(f"## {ctx.author.display_name}'s Goals"), color=0x5865F2)
    # TODO: Paginate This
    for goal in goals[:5]:
        c.add_separator()
        c.add_item(goal.short_display())
    await ctx.respond(view=ui.DesignerView(c))


# Handle Interactions Manually Instead Of Using View Callbacks
async def on_interaction(interaction: Interaction):
    if interaction.custom_id and interaction.custom_id.startswith("view_goal::"):
        await view_goal_button(interaction)


async def view_goal_button(interaction: Interaction) -> None:
    g = await Goal.fetch(interaction.message.get_component(interaction.custom_id).id)
    await interaction.respond(view=g.display())


def setup(bot: Bot):
    bot.add_application_command(goal_list)

    bot.add_listener(on_interaction)
