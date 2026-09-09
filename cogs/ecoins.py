import discord
from discord.ext import commands
import asyncio

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

        if member.voice is None or member.voice.channel is None:
            await ctx.send(embed=error_embed(
                "Ese usuario debe estar conectado a un canal de voz para poder mutearlo."
            ))
            return

        if member.voice.mute:
            await ctx.send(embed=error_embed(
                "Ese usuario ya está muteado por el servidor."
            ))
            return

        try:
            # Server mute real de voz. No usamos timeout porque eso aísla al usuario.
            await member.edit(
                mute=True,
                reason=f"Mute de voz comprado por {ctx.author}"
            )
        except discord.Forbidden:
            await ctx.send(embed=error_embed(
                "No puedo mutear a ese usuario. Comprueba que EcosBot tenga **Silenciar miembros** "
                "y que su rol esté por encima del rol del objetivo."
            ))
            return
        except discord.HTTPException as exc:
            await ctx.send(embed=error_embed(
                f"Discord no ha permitido aplicar el mute: `{exc}`"
            ))
            return

        # Solo cobramos cuando el mute se ha aplicado correctamente.
        database.add_ecoins(ctx.author.id, -cost, reason=f"Mute comprado sobre {member}")

        async def unmute_later():
            await asyncio.sleep(120)
            try:
                if member.voice is not None and member.voice.mute:
                    await member.edit(
                        mute=False,
                        reason="Fin del mute temporal comprado con Ecoins"
                    )
            except (discord.Forbidden, discord.HTTPException):
                pass

        asyncio.create_task(unmute_later())

        await ctx.send(embed=success_embed(
            "Mute comprado",
            f"🔇 {ctx.author.mention} ha gastado **{cost} Ecoins** para mutear la voz de "
            f"{member.mention} durante **2 minutos**."
        ))


async def setup(bot):
    await bot.add_cog(Ecoins(bot))
