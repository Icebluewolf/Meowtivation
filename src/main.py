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

bot.add_application_command(ping)

bot.run(environ["DISCORD_BOT_TOKEN"])
