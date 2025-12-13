from discord.ui import Container


async def error(traceback: str) -> Container:
    c = Container(color=0xFF0000)
    c.add_text("## Error\n-# Please Report This In The Support Server")
    c.add_separator()
    c.add_text(f"```\n{traceback}\n```")
    return c


async def input_error(message: str, errors: list[str]) -> Container:
    c = Container(color=0xD33033)
    c.add_text(f"## {message}")
    c.add_separator(divider=False)
    c.add_text("- " + "\n- ".join(errors))
    return c


async def fail(message: str, **kwargs) -> Container:
    c = Container(color=0xD33033)
    c.add_text("## You Can Not Do That")
    c.add_separator(divider=False)
    c.add_text(message)
    return c


async def success(message: str = None, **kwargs) -> Container:
    c = Container(color=0x00FF00)
    c.add_text("## Success!")
    c.add_separator(divider=False)
    if message:
        c.add_text(message)
    return c


async def general(message: str, title: str = None, **kwargs) -> Container:
    c = Container(color=0x30D3D0)
    if title:
        c.add_text(f"## {title}")
        c.add_separator(divider=False)
    if message:
        c.add_text(message)
    return c
