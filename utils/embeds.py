import discord


def success_embed(
    title: str,
    description: str,
) -> discord.Embed:
    embed = discord.Embed(
        title=f"✅ {title}",
        description=description,
        color=discord.Color.green(),
    )
    embed.set_footer(text="EcosBot")
    return embed


def error_embed(
    description: str,
    title: str = "Error",
) -> discord.Embed:
    embed = discord.Embed(
        title=f"❌ {title}",
        description=description,
        color=discord.Color.red(),
    )
    embed.set_footer(text="EcosBot")
    return embed


def warning_embed(
    title: str,
    description: str,
) -> discord.Embed:
    embed = discord.Embed(
        title=f"⚠️ {title}",
        description=description,
        color=discord.Color.orange(),
    )
    embed.set_footer(text="EcosBot")
    return embed


def info_embed(
    title: str,
    description: str,
) -> discord.Embed:
    embed = discord.Embed(
        title=f"ℹ️ {title}",
        description=description,
        color=discord.Color.blue(),
    )
    embed.set_footer(text="EcosBot")
    return embed


def economy_embed(
    title: str,
    description: str,
) -> discord.Embed:
    embed = discord.Embed(
        title=f"🪙 {title}",
        description=description,
        color=discord.Color.gold(),
    )
    embed.set_footer(text="EcosBot")
    return embed