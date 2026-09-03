import discord
from discord.ext import commands

import database
from utils.embeds import error_embed, info_embed


class History(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="history", aliases=["historial"])
    async def history(self, ctx, currency: str = None, member: discord.Member = None):
        member = member or ctx.author
        if currency:
            currency = currency.lower()
            if currency not in {"balance", "ecoins"}:
                await ctx.send(embed=error_embed("Usa `balance` o `ecoins`."))
                return

        rows = database.get_transactions(member.id, currency, 15)
        if not rows:
            await ctx.send(embed=info_embed("Historial", f"{member.mention} no tiene movimientos todavía."))
            return

        embed = discord.Embed(
            title=f"📜 Historial de {member.display_name}",
            description=f"Moneda: **{currency or 'todas'}**",
            color=discord.Color.blue(),
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        lines = []
        for amount, row_currency, reason, created_at in rows:
            sign = "+" if amount >= 0 else ""
            icon = "🪙" if row_currency == "ecoins" else "💰"
            lines.append(f"{icon} `{created_at}` · **{sign}{amount:,}** · {reason or 'Sin motivo'}")
        embed.add_field(name="Últimos movimientos", value="\n".join(lines), inline=False)
        embed.set_footer(text="EcosBot · Historial")
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(History(bot))
