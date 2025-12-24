from discord import Bot, ApplicationContext, slash_command, Interaction, Option, SlashCommand, ui, AllowedMentions

from models.goal import Goal
from utils import component_factory as cf


class NavButton(ui.Button):
    def __init__(self, forward: bool):
        super().__init__(emoji=("▶️" if forward else "◀️"))
        self.forward = forward

    async def callback(self, interaction: Interaction):
        if interaction.user.id != self.parent.parent.user_id:
            await interaction.respond(view=ui.DesignerView(await cf.fail("You cannot change the page")),
                                      ephemeral=True)
            return
        await self.parent.parent.nav(interaction, self.forward)


class GoalListPaginator(ui.DesignerView):
    def __init__(self, goals: list[Goal], display_name: str, interaction: Interaction):
        self.chunks = [goals[i:min(i + 5, len(goals))] for i in range(0, len(goals), 5)]
        if len(self.chunks) > 1:
            super().__init__(timeout=300)
        else:
            super().__init__(store=False)
        self.index = 0
        self.interaction = interaction
        self.user_id = interaction.user.id

        c = ui.Container(ui.TextDisplay(f"## {display_name}'s Goals"), color=0x5865F2, id=1)

        for goal in self.chunks[self.index]:
            c.add_separator()
            c.add_item(goal.short_display())

        if len(self.chunks) > 1:
            self.back = NavButton(forward=False)
            self.back.disabled = True
            self.page_display = ui.Button(label=f"1/{len(self.chunks)}", disabled=True)
            self.forward = NavButton(forward=True)

        self.add_item(c)
        self.add_item(ui.ActionRow(self.back, self.page_display, self.forward))

    async def nav(self, interaction: Interaction, forward: bool):
        self.interaction = interaction
        if forward:
            self.index += 1
        else:
            self.index -= 1

        self.back.disabled = self.index == 0
        self.page_display.label = f"{self.index + 1}/{len(self.chunks)}"
        self.forward.disabled = self.index == len(self.chunks) - 1

        c: ui.Container = self.get_item(1)
        c.items = c.items[:1]
        for goal in self.chunks[self.index]:
            c.add_separator()
            c.add_item(goal.short_display())

        await interaction.edit(view=self)

    async def on_timeout(self) -> None:
        self.back.parent.children = []
        self.back.parent.add_item(ui.Button(label="Refresh", emoji="🔁", custom_id=f"goal_list_refresh::{self.user_id}"))
        await self.interaction.edit(view=self)



@slash_command(description="List All Of Your Goals")
async def goal_list(ctx: ApplicationContext, completed: Option(bool, description="Include Completed Goals", default=False)):
    goals = await Goal.fetch_user_goals(ctx.author.id, completed)

    if len(goals) == 0:
        if completed:
            await ctx.respond(await cf.fail(f"You have not made any goals! Use {ctx.bot.get_command("goal", None, SlashCommand).mention} to get started."), ephemeral=True)
            return
        else:
            await ctx.respond(await cf.fail(f"You dont have any uncompleted goals. Use {ctx.bot.get_command("goal", None, SlashCommand).mention} to get another."), ephemeral=True)
            return

    await ctx.respond(view=GoalListPaginator(goals, ctx.author.display_name, ctx.interaction))


# Handle Interactions Manually Instead Of Using View Callbacks
async def on_interaction(interaction: Interaction):
    if interaction.custom_id is None:
        return
    if interaction.custom_id.startswith("view_goal::"):
        await view_goal_button(interaction)
    elif interaction.custom_id.startswith("goal_list_refresh::"):
        await view_goal_list_refresh_button(interaction)


async def view_goal_button(interaction: Interaction) -> None:
    g = await Goal.fetch(interaction.message.get_component(interaction.custom_id).id)
    await interaction.respond(view=g.display(), allowed_mentions=AllowedMentions.none())


async def view_goal_list_refresh_button(interaction: Interaction) -> None:
    user_id = int(interaction.custom_id.split("::")[1])
    if user_id != interaction.user.id:
        await interaction.respond(view=ui.DesignerView(await cf.fail("You cannot refresh someone else's goal list")),
                                  ephemeral=True)
        return
    goals = await Goal.fetch_user_goals(interaction.user.id, False)
    await interaction.edit(view=GoalListPaginator(goals, interaction.user.display_name, interaction))


def setup(bot: Bot):
    bot.add_application_command(goal_list)

    bot.add_listener(on_interaction)
