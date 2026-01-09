from os import environ

import discord as pycord
from discord import ApplicationContext
from dotenv import load_dotenv


load_dotenv()

bot = pycord.Bot()


@bot.event
async def on_ready():
    print(f"{bot.user.name} is ready!")
    print("Loaded Commands:")
    for cmd in bot.walk_application_commands():
        tabs = ""
        if cmd.parent is not None:
            if cmd.parent.parent is not None:
                tabs += "\t"
            tabs += "\t"
        print(tabs + cmd.name)


@pycord.slash_command()
async def ping(ctx: ApplicationContext):
    v = pycord.ui.DesignerView()
    v.add_item(
        pycord.ui.Container(
            pycord.ui.TextDisplay(f"**🏓 Pong**\n{bot.user.name}'s Latency To The Discord API Is {bot.latency}")
        )
    )
    await ctx.respond(view=v)

# Add commands to the bot
bot.add_application_command(ping)

# Add extensions to the bot
bot.load_extension("commands.create_goal")
bot.load_extension("commands.view_goals")
bot.load_extension("commands.shop")
bot.load_extension("commands.goal_repeat")

bot.run(environ["DISCORD_BOT_TOKEN"])
