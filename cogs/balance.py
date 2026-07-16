import discord
from discord.ext import commands

import database
import utils.Verificator as Verificator


class Balance(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @staticmethod
    def parse_money(value: str | int) -> int:
        """
        Acepta cantidades como:
        293543345
        293,543,345
        293_543_345

        Y devuelve:
        293543345
        """
        if isinstance(value, int):
            return value

        cleaned = (
            str(value)
            .strip()
            .replace(",", "")
            .replace(" ", "")
            .replace("_", "")
        )

        if not cleaned:
            raise ValueError("La cantidad está vacía.")

        if cleaned.startswith("-"):
            number_part = cleaned[1:]

            if not number_part.isdigit():
                raise ValueError("La cantidad no es válida.")

            return -int(number_part)

        if not cleaned.isdigit():
            raise ValueError("La cantidad no es válida.")

        return int(cleaned)

    @staticmethod
    def format_money(value: int | None) -> str:
        """
        Convierte:
        293543345

        En:
        293,543,345
        """
        return f"{int(value or 0):,}"

    @commands.command()
    async def bal(
        self,
        ctx,
        member: discord.Member = None
    ):
        member = member or ctx.author
        balance, ecoins = database.get_user(member.id)

        await ctx.send(
            f"💰 Balance de {member.mention}\n"
            f"Balance: **{self.format_money(balance)}**\n"
            f"Ecoins: **{self.format_money(ecoins)}**"
        )

    @commands.command()
    @commands.check(Verificator.usuario_puede_ejecutar_comando)
    async def addbal(
        self,
        ctx,
        member: discord.Member,
        amount: str
    ):
        try:
            parsed_amount = self.parse_money(amount)
        except ValueError:
            await ctx.send(
                "❌ Cantidad no válida.\n"
                "Ejemplos: `25000000` o `25,000,000`."
            )
            return

        if parsed_amount <= 0:
            await ctx.send(
                "❌ La cantidad debe ser mayor que cero."
            )
            return

        database.add_balance(
            member.id,
            parsed_amount
        )

        balance, _ = database.get_user(member.id)

        await ctx.send(
            f"✅ Sumados **{self.format_money(parsed_amount)}** "
            f"al balance de {member.mention}.\n"
            f"Nuevo balance: **{self.format_money(balance)}**"
        )

    @commands.command()
    @commands.check(Verificator.usuario_puede_ejecutar_comando)
    async def removebal(
        self,
        ctx,
        member: discord.Member,
        amount: str
    ):
        try:
            parsed_amount = self.parse_money(amount)
        except ValueError:
            await ctx.send(
                "❌ Cantidad no válida.\n"
                "Ejemplos: `25000000` o `25,000,000`."
            )
            return

        if parsed_amount <= 0:
            await ctx.send(
                "❌ Escribe una cantidad positiva. "
                "El comando ya se encarga de restarla."
            )
            return

        database.add_balance(
            member.id,
            -parsed_amount
        )

        balance, _ = database.get_user(member.id)

        await ctx.send(
            f"❌ Restados **{self.format_money(parsed_amount)}** "
            f"del balance de {member.mention}.\n"
            f"Nuevo balance: **{self.format_money(balance)}**"
        )

    @commands.command()
    @commands.check(Verificator.usuario_puede_ejecutar_comando)
    async def resetbal(
        self,
        ctx,
        member: discord.Member
    ):
        database.reset_balance(member.id)

        await ctx.send(
            f"🧹 Balance de {member.mention} reiniciado a **0**."
        )

    @commands.command()
    @commands.check(Verificator.usuario_puede_ejecutar_comando)
    async def addrolebal(
        self,
        ctx,
        role: discord.Role,
        amount: str
    ):
        try:
            parsed_amount = self.parse_money(amount)
        except ValueError:
            await ctx.send(
                "❌ Cantidad no válida.\n"
                "Ejemplos: `25000000` o `25,000,000`."
            )
            return

        if parsed_amount <= 0:
            await ctx.send(
                "❌ La cantidad debe ser mayor que cero."
            )
            return

        count = 0

        for member in role.members:
            if member.bot:
                continue

            database.add_balance(
                member.id,
                parsed_amount
            )
            count += 1

        await ctx.send(
            f"✅ Sumados **{self.format_money(parsed_amount)}** "
            f"de balance a **{count}** miembros "
            f"con el rol **{role.name}**."
        )

    @addrolebal.error
    @resetbal.error
    @removebal.error
    @addbal.error
    async def error_permisos(
        self,
        contexto: commands.Context,
        error
    ):
        if isinstance(error, commands.MissingRequiredArgument):
            await contexto.send(
                "❌ Faltan argumentos en el comando."
            )
            return

        if isinstance(error, commands.MemberNotFound):
            await contexto.send(
                "❌ No he encontrado a ese usuario."
            )
            return

        if isinstance(error, commands.RoleNotFound):
            await contexto.send(
                "❌ No he encontrado ese rol."
            )
            return

        await contexto.send(f"❌ {error}")


async def setup(bot):
    await bot.add_cog(Balance(bot))