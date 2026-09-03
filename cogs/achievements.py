import discord
from discord.ext import commands

import database
from utils.logger import send_log


ACHIEVEMENTS = [
    {
        "key": "avas_10",
        "name": "10 Avalonianas",
        "role": "🏅 Ava Novice",
        "type": "total_avas",
        "required": 10,
        "category": "ava",
    },
    {
        "key": "avas_50",
        "name": "50 Avalonianas",
        "role": "⚔️ Ava Veteran",
        "type": "total_avas",
        "required": 50,
        "category": "ava",
    },
    {
        "key": "avas_100",
        "name": "100 Avalonianas",
        "role": "👑 Ava Legend",
        "type": "total_avas",
        "required": 100,
        "category": "ava",
    },
    {
        "key": "caller_20",
        "name": "20 Callers",
        "role": "📢 Caller Veteran",
        "type": "caller_count",
        "required": 20,
        "category": "ava",
    },
    {
        "key": "scout_20",
        "name": "20 Scouts",
        "role": "🕵️ Scout Veteran",
        "type": "scout_count",
        "required": 20,
        "category": "ava",
    },
    {
        "key": "dragons_10",
        "name": "10 Dragones",
        "role": "🐉 Dragon Novice",
        "type": "total_dragons",
        "required": 10,
        "category": "dragon",
    },
    {
        "key": "dragons_50",
        "name": "50 Dragones",
        "role": "🐲 Dragon Veteran",
        "type": "total_dragons",
        "required": 50,
        "category": "dragon",
    },
    {
        "key": "dragons_100",
        "name": "100 Dragones",
        "role": "👑 Dragon Legend",
        "type": "total_dragons",
        "required": 100,
        "category": "dragon",
    },
]


async def get_or_create_role(guild, role_name):
    role = discord.utils.get(guild.roles, name=role_name)
    if role is None:
        role = await guild.create_role(name=role_name, reason="Logro de EcosBot")
    return role


def get_values(user_id):
    ava_stats = database.get_user_ava_stats(user_id)
    dragon_total, _ = database.get_user_dragon_stats(user_id)

    return {
        "total_avas": ava_stats[0] or 0,
        "caller_count": ava_stats[1] or 0,
        "scout_count": ava_stats[2] or 0,
        "party_count": ava_stats[3] or 0,
        "total_dragons": dragon_total or 0,
    }


class Achievements(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def check_user_achievements(self, guild, user_id):
        member = guild.get_member(user_id)
        if member is None:
            return

        values = get_values(user_id)

        for achievement in ACHIEVEMENTS:
            current_value = values[achievement["type"]]

            if current_value < achievement["required"]:
                continue

            if database.has_achievement(user_id, achievement["key"]):
                continue

            try:
                role = await get_or_create_role(guild, achievement["role"])
                await member.add_roles(role, reason="Logro desbloqueado en EcosBot")
            except discord.Forbidden:
                # Guardamos el logro solo si Discord nos deja aplicar el rol.
                continue

            database.add_achievement(user_id, achievement["key"])

            await send_log(
                self.bot,
                "🏆 Logro desbloqueado",
                (
                    f"Usuario: {member.mention}\n"
                    f"Logro: **{achievement['name']}**\n"
                    f"Rol otorgado: **{achievement['role']}**"
                ),
                discord.Color.gold(),
            )

    @commands.command(name="achievements", aliases=["logros"])
    async def achievements(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        values = get_values(member.id)

        embed = discord.Embed(
            title=f"🏆 Logros de {member.display_name}",
            description=(
                f"⚔️ Avalonianas: **{values['total_avas']}**\n"
                f"📢 Caller: **{values['caller_count']}** · "
                f"🕵️ Scout: **{values['scout_count']}** · "
                f"🛡️ Party: **{values['party_count']}**\n"
                f"🐉 Dragones: **{values['total_dragons']}**"
            ),
            color=discord.Color.gold(),
        )
        embed.set_thumbnail(url=member.display_avatar.url)

        ava_lines = []
        dragon_lines = []

        for achievement in ACHIEVEMENTS:
            value = values[achievement["type"]]
            unlocked = database.has_achievement(member.id, achievement["key"])
            status = "✅" if unlocked or value >= achievement["required"] else "⬜"
            line = (
                f"{status} **{achievement['name']}** "
                f"— `{min(value, achievement['required'])}/{achievement['required']}`\n"
                f"└ Rol: {achievement['role']}"
            )

            if achievement["category"] == "dragon":
                dragon_lines.append(line)
            else:
                ava_lines.append(line)

        embed.add_field(
            name="⚔️ Avalonianas",
            value="\n".join(ava_lines) or "Sin logros.",
            inline=False,
        )
        embed.add_field(
            name="🐉 Dragones",
            value="\n".join(dragon_lines) or "Sin logros.",
            inline=False,
        )
        embed.set_footer(text="EcosBot · Los roles se entregan automáticamente")

        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Achievements(bot))
