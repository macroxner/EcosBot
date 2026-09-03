import discord
from discord.ext import commands

import database


class Profile(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="profile", aliases=["perfil"])
    async def profile(self, ctx, member: discord.Member = None):
        member = member or ctx.author

        balance, ecoins = database.get_user(member.id)
        warnings = database.get_warnings(member.id)
        warning_count = len(warnings)
        total_fines = sum(row[2] for row in warnings)
        ava_stats = database.get_user_ava_stats(member.id)
        dragon_total, _ = database.get_user_dragon_stats(member.id)
        albion = database.get_registered_player(member.id)

        embed = discord.Embed(
            title=f"📋 Perfil de {member.display_name}",
            color=discord.Color.blurple(),
        )
        embed.set_thumbnail(url=member.display_avatar.url)

        if albion:
            _, _, albion_name, _, guild_name, _, alliance_name = albion
            embed.add_field(
                name="🎮 Albion",
                value=(
                    f"Personaje: **{albion_name}**\n"
                    f"Gremio: **{guild_name or 'Sin gremio'}**\n"
                    f"Alianza: **{alliance_name or 'Sin alianza'}**"
                ),
                inline=False,
            )

        embed.add_field(name="💰 Balance", value=f"`{balance:,}`", inline=True)
        embed.add_field(name="🪙 Ecoins", value=f"`{ecoins:,}`", inline=True)
        embed.add_field(name="⚠️ Warnings", value=f"`{warning_count}`", inline=True)
        embed.add_field(name="💸 Multas", value=f"`{total_fines:,}`", inline=True)
        embed.add_field(name="⚔️ Avas", value=f"`{ava_stats[0] or 0}`", inline=True)
        embed.add_field(name="🐉 Dragones", value=f"`{dragon_total}`", inline=True)
        embed.set_footer(text="EcosBot · Perfil")

        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Profile(bot))
