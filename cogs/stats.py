import discord
from discord.ext import commands

import database


class Stats(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="stats")
    async def stats(self, ctx, member: discord.Member = None):
        member = member or ctx.author

        balance, ecoins = database.get_user(member.id)
        ava_stats = database.get_user_ava_stats(member.id)
        ava_history = database.get_user_ava_history(member.id, 5)
        dragon_total, dragon_roles = database.get_user_dragon_stats(member.id)

        total_avas = ava_stats[0] or 0
        caller_count = ava_stats[1] or 0
        scout_count = ava_stats[2] or 0
        party_count = ava_stats[3] or 0
        ecoins_from_avas = ava_stats[4] or 0

        embed = discord.Embed(
            title=f"📊 Stats de {member.display_name}",
            color=discord.Color.blue(),
        )
        embed.set_thumbnail(url=member.display_avatar.url)

        embed.add_field(
            name="💰 Economía",
            value=(
                f"Balance: **{balance:,}**\n"
                f"Ecoins: **{ecoins:,}**\n"
                f"Ecoins por Avas: **{ecoins_from_avas:,}**"
            ),
            inline=False,
        )

        embed.add_field(
            name="⚔️ Avalonianas",
            value=(
                f"Total: **{total_avas}**\n"
                f"Caller: **{caller_count}** · Scout: **{scout_count}** · Party: **{party_count}**"
            ),
            inline=False,
        )

        if ava_history:
            embed.add_field(
                name="📜 Últimas Avas",
                value="\n".join(
                    f"`{created_at}` · **{role}** · +{ecoins_given} Ecoins"
                    for role, ecoins_given, created_at in ava_history
                ),
                inline=False,
            )

        dragon_text = f"Total completados: **{dragon_total}**"
        if dragon_roles:
            dragon_text += "\n" + "\n".join(
                f"**{role}:** `{count}`" for role, count in dragon_roles[:5]
            )

        embed.add_field(
            name="🐉 Dragones",
            value=dragon_text,
            inline=False,
        )
        embed.set_footer(text="EcosBot · Estadísticas")

        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Stats(bot))
