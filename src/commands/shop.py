from discord import Bot, ApplicationContext, SelectOption, slash_command, Interaction
from discord import ui

from models.reward import Reward
from models.user import User
from utils import component_factory as cf


class CreateShopItem(ui.DesignerModal):
    def __init__(self):
        super().__init__(title="Create A Reward Item")

        self.reward_text = ui.InputText(placeholder="Eat A Cookie")
        self.add_item(ui.Label("Reward", self.reward_text,
                               description="Something that helps motivate you to complete your goals"))
        self.cost_text = ui.InputText(placeholder="10", max_length=6)
        self.add_item(ui.Label("Crumb Cost", self.cost_text,
                               description="How many crumbs do you want to spend to redeem this reward? Bigger rewards should have higher costs."),)
        self.renewable_select = ui.Select(options=[
            SelectOption(label="Forever", description="Rewards That You Can Redeem As Many Times As You Want.", default=True, value="forever"),
            SelectOption(label="Once", description="Once You Redeem This Reward It Will Be Removed From The Shop", value="once"),
        ])
        self.add_item(ui.Label("Redeemable", self.renewable_select))

    async def callback(self, interaction: Interaction):
        try:
            cost = int(self.cost_text.value)
        except ValueError:
            cost_error = True
        else:
            cost_error = cost <= 0

        if cost_error:
            await interaction.respond(view=ui.DesignerView(await cf.input_error(
                "Failed To Process Input", ["The cost of the reward must be a positive integer"]
            )), ephemeral=True)
            return

        if self.renewable_select.values[0] == "forever":
            renewable = True
        else:
            renewable = False

        r = Reward(interaction.user.id, self.reward_text.value, cost, renewable)
        await r.create()

        await interaction.respond(view=ui.DesignerView(await cf.success(f"Your Reward For **{r.text}** Was Created")), ephemeral=True)


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


class RewardListPaginator(ui.DesignerView):
    def __init__(self, rewards: list[Reward], display_name: str, crumbs: float, interaction: Interaction):
        self.chunks = [rewards[i:min(i + 5, len(rewards))] for i in range(0, len(rewards), 5)]
        if len(self.chunks) > 1:
            super().__init__(timeout=300)
        else:
            super().__init__(store=False)
        self.index = 0
        self.interaction = interaction
        self.user_id = interaction.user.id

        c = ui.Container(ui.TextDisplay(f"## {display_name}'s Shop\nYou Have **{crumbs:.2f}** to spend"), color=0xfcba03, id=1)

        for reward in self.chunks[self.index]:
            c.add_separator()
            c.add_item(reward.short_display())

        self.add_item(c)

        if len(self.chunks) > 1:
            self.back = NavButton(forward=False)
            self.back.disabled = True
            self.page_display = ui.Button(label=f"1/{len(self.chunks)}", disabled=True)
            self.forward = NavButton(forward=True)
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
        self.back.parent.add_item(ui.Button(label="Refresh", emoji="🔁", custom_id=f"reward_list_refresh::{self.user_id}"))
        await self.interaction.edit(view=self)


@slash_command(description="Spend Your Crumbs On Rewards")
async def shop(ctx: ApplicationContext):
    rewards = await Reward.fetch_user_rewards(ctx.user.id)

    if len(rewards) == 0:
        await ctx.respond(view=ui.DesignerView(
            await cf.fail("You Have Not Made Any Rewards. Use </create_reward:1457079554295464170> To Make One")
        ), ephemeral=True)
        return

    u = await User.fetch(ctx.user.id)

    await ctx.respond(view=RewardListPaginator(rewards, ctx.user.display_name, u.points, ctx.interaction))


@slash_command(description="Create A New Reward In The Shop")
async def create_reward(ctx: ApplicationContext):
    await ctx.send_modal(CreateShopItem())


# Handle Interactions Manually Instead Of Using View Callbacks
async def on_interaction(interaction: Interaction):
    if interaction.custom_id is None:
        return
    if interaction.custom_id.startswith("shop_reward::"):
        await shop_reward_button(interaction)
    elif interaction.custom_id.startswith("reward_list_refresh::"):
        await reward_list_refresh(interaction)


async def shop_reward_button(interaction: Interaction):
    reward_id = int(interaction.custom_id.split("::", maxsplit=1)[1])
    reward = await Reward.fetch(reward_id)
    if reward is None:
        await interaction.respond(view=ui.DesignerView(await cf.fail("Uh Oh! This reward was already claimed!")), ephemeral=True)
        return

    u = await User.fetch(interaction.user.id)
    if not await u.use_points(reward.cost):
        await interaction.respond(view=ui.DesignerView(await cf.fail("You Do Not Have Enough Crumbs. Complete Goals To Earn More Crumbs")), ephemeral=True)
        return

    if not reward.renewable:
        await reward.delete()
        v = ui.DesignerView.from_message(interaction.message)
        button = v.get_item(interaction.custom_id)
        button.disabled = True
        await interaction.edit(view=v)

    await interaction.respond(
        view=ui.DesignerView(await cf.success(f"You redeemed **{reward.text}** for {reward.cost} Crumbs.")),
        ephemeral=True)


async def reward_list_refresh(interaction: Interaction):
    user_id = int(interaction.custom_id.split("::", maxsplit=1)[1])

    rewards = await Reward.fetch_user_rewards(user_id)

    if len(rewards) == 0:
        await interaction.respond(view=ui.DesignerView(
            await cf.fail("You Have Not Made Any Rewards. Use </create_reward:1457079554295464170> To Make One")
        ), ephemeral=True)
        return

    u = await User.fetch(user_id)

    await interaction.edit(view=RewardListPaginator(rewards, interaction.user.display_name, u.points, interaction))


def setup(bot: Bot):
    bot.add_application_command(shop)
    bot.add_application_command(create_reward)

    bot.add_listener(on_interaction)
