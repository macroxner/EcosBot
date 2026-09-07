import discord
from discord.ext import commands
from datetime import timedelta

import database
import utils.Verificator as Verificator
from utils.embeds import economy_embed, error_embed, success_embed


class Ecoins(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.check(Verificator.usuario_puede_ejecutar_comando)
    async def addecoins(self, ctx, member: discord.Member, amount: int):
        database.add_ecoins(member.id, amount, reason=f"Añadido por {ctx.author}")
        _, ecoins = database.get_user(member.id)
        await ctx.send(embed=economy_embed(
            "Ecoins añadidos",
            f"👤 {member.mention}\n➕ **{amount:,} Ecoins**\n🪙 Total: **{ecoins:,}**"
        ))

    @commands.command()
    @commands.check(Verificator.usuario_puede_ejecutar_comando)
    async def removeecoins(self, ctx, member: discord.Member, amount: int):
        database.add_ecoins(member.id, -amount, reason=f"Retirado por {ctx.author}")
        _, ecoins = database.get_user(member.id)
        await ctx.send(embed=economy_embed(
            "Ecoins retirados",
            f"👤 {member.mention}\n➖ **{amount:,} Ecoins**\n🪙 Total: **{ecoins:,}**"
        ))

    @commands.command()
    async def buymute(self, ctx, member: discord.Member):
        cost = 50
        if member == ctx.author:
            await ctx.send(embed=error_embed("No puedes mutearte a ti mismo."))
            return
        if member.bot:
            await ctx.send(embed=error_embed("No puedes mutear bots."))
            return

        _, ecoins = database.get_user(ctx.author.id)
        if ecoins < cost:
            await ctx.send(embed=error_embed(f"Necesitas **{cost} Ecoins** y tienes **{ecoins}**."))
            return

        database.add_ecoins(ctx.author.id, -cost, reason=f"Mute comprado sobre {member}")
        await member.timeout(
            discord.utils.utcnow() + timedelta(minutes=2),
            reason=f"Mute comprado por {ctx.author}"
        )
        await ctx.send(embed=success_embed(
            "Mute comprado",
            f"🔇 {ctx.author.mention} ha gastado **{cost} Ecoins** para mutear a {member.mention} durante **2 minutos**."
        ))


async def setup(bot):
    await bot.add_cog(Ecoins(bot))
