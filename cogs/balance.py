import discord
from discord.ext import commands
import database
import utils.Verificator as Verificator
from discord import app_commands
from utils.embeds import economy_embed, error_embed


class Balance(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @staticmethod
    def parse_money(value: str | int) -> int:
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
        return f"{int(value or 0):,}"

    async def resolve_user(self, ctx, user_input: str):
        """
        Acepta:
        @usuario
        123456789012345678

        Devuelve:
        (user_id, member)

        member será None si el usuario ya no está en el servidor.
        """

        raw = user_input.strip()

        # Si llega como mención: <@123> o <@!123>
        if raw.startswith("<@") and raw.endswith(">"):
            raw = raw[2:-1]

            if raw.startswith("!"):
                raw = raw[1:]

        if not raw.isdigit():
            return None, None

        user_id = int(raw)

        member = ctx.guild.get_member(user_id)

        if member is None:
            try:
                member = await ctx.guild.fetch_member(user_id)
            except (
                discord.NotFound,
                discord.Forbidden,
                discord.HTTPException
            ):
                member = None

        return user_id, member

    def display_user(self, user_id, member):
        if member:
            return member.mention

        return f"`{user_id}`"

    # =========================
    # SLASH COMMANDS
    # =========================

    @app_commands.command(
        name="addbal",
        description="Añade balance a un usuario"
    )
    @app_commands.describe(
        usuario="Usuario al que quieres añadir balance",
        cantidad="Cantidad a añadir, por ejemplo 25,000,000"
    )
    async def slash_addbal(
        self,
        interaction: discord.Interaction,
        usuario: discord.Member,
        cantidad: str
    ):
        try:
            amount = self.parse_money(cantidad)
        except ValueError:
            await interaction.response.send_message(
                embed=error_embed(
                    "Cantidad no válida.\n\n"
                    "Ejemplos:\n"
                    "`25000000`\n"
                    "`25,000,000`"
                ),
                ephemeral=True
            )
            return

        if amount <= 0:
            await interaction.response.send_message(
                embed=error_embed(
                    "La cantidad debe ser mayor que cero."
                ),
                ephemeral=True
            )
            return

        database.add_balance(
            usuario.id,
            amount,
            reason=f"Añadido por {interaction.user}"
        )

        balance, _ = database.get_user(usuario.id)

        embed = economy_embed(
            "Balance añadido",
            (
                f"👤 **Usuario:** {usuario.mention}\n\n"
                f"➕ **Añadido:** `{self.format_money(amount)}`\n"
                f"💰 **Nuevo balance:** `{self.format_money(balance)}`"
            )
        )

        embed.set_thumbnail(
            url=usuario.display_avatar.url
        )

        await interaction.response.send_message(
            embed=embed
        )

    @app_commands.command(
        name="removebal",
        description="Resta balance a un usuario"
    )
    @app_commands.describe(
        usuario="Usuario al que quieres quitar balance",
        cantidad="Cantidad a retirar, por ejemplo 25,000,000"
    )
    async def slash_removebal(
        self,
        interaction: discord.Interaction,
        usuario: discord.Member,
        cantidad: str
    ):
        try:
            amount = self.parse_money(cantidad)
        except ValueError:
            await interaction.response.send_message(
                embed=error_embed(
                    "Cantidad no válida.\n\n"
                    "Ejemplos:\n"
                    "`25000000`\n"
                    "`25,000,000`"
                ),
                ephemeral=True
            )
            return

        if amount <= 0:
            await interaction.response.send_message(
                embed=error_embed(
                    "La cantidad debe ser mayor que cero."
                ),
                ephemeral=True
            )
            return

        database.add_balance(
            usuario.id,
            -amount,
            reason=f"Retirado por {interaction.user}"
        )

        balance, _ = database.get_user(usuario.id)

        embed = economy_embed(
            "Balance retirado",
            (
                f"👤 **Usuario:** {usuario.mention}\n\n"
                f"➖ **Retirado:** `{self.format_money(amount)}`\n"
                f"💰 **Nuevo balance:** `{self.format_money(balance)}`"
            )
        )

        embed.set_thumbnail(
            url=usuario.display_avatar.url
        )

        await interaction.response.send_message(
            embed=embed
        )

    # =========================
    # PREFIX COMMANDS
    # =========================

    @commands.command()
    async def bal(
        self,
        ctx,
        user_input: str = None
    ):
        if user_input is None:
            user_id = ctx.author.id
            member = ctx.author
        else:
            user_id, member = await self.resolve_user(
                ctx,
                user_input
            )

            if user_id is None:
                await ctx.send(
                    embed=error_embed(
                        "Debes indicar una mención o un ID válido."
                    )
                )
                return

        balance, ecoins = database.get_user(user_id)

        if member:
            title = f"Balance de {member.display_name}"
        else:
            title = f"Balance de {user_id}"

        embed = economy_embed(
            title,
            (
                f"👤 **Usuario:** {self.display_user(user_id, member)}\n\n"
                f"💰 **Balance**\n"
                f"`{self.format_money(balance)}` plata\n\n"
                f"🪙 **Ecoins**\n"
                f"`{self.format_money(ecoins)}`"
            )
        )

        if member:
            embed.set_thumbnail(
                url=member.display_avatar.url
            )

        await ctx.send(embed=embed)

    @commands.command()
    @commands.check(Verificator.usuario_puede_ejecutar_comando)
    async def addbal(
        self,
        ctx,
        user_input: str,
        amount: str
    ):
        user_id, member = await self.resolve_user(
            ctx,
            user_input
        )

        if user_id is None:
            await ctx.send(
                embed=error_embed(
                    "No he podido interpretar ese usuario.\n\n"
                    "Puedes usar:\n"
                    "`?addbal @usuario 25000000`\n"
                    "`?addbal 123456789012345678 25000000`"
                )
            )
            return

        try:
            parsed_amount = self.parse_money(amount)
        except ValueError:
            await ctx.send(
                embed=error_embed(
                    "Cantidad no válida.\n\n"
                    "Ejemplos:\n"
                    "`25000000`\n"
                    "`25,000,000`"
                )
            )
            return

        if parsed_amount <= 0:
            await ctx.send(
                embed=error_embed(
                    "La cantidad debe ser mayor que cero."
                )
            )
            return

        database.add_balance(
            user_id,
            parsed_amount,
            reason=f"Añadido por {ctx.author}"
        )

        balance, _ = database.get_user(user_id)

        embed = economy_embed(
            "Balance añadido",
            (
                f"👤 **Usuario:** {self.display_user(user_id, member)}\n\n"
                f"➕ **Añadido:** `{self.format_money(parsed_amount)}`\n"
                f"💰 **Nuevo balance:** `{self.format_money(balance)}`"
            )
        )

        if member:
            embed.set_thumbnail(
                url=member.display_avatar.url
            )

        await ctx.send(embed=embed)

    @commands.command()
    @commands.check(Verificator.usuario_puede_ejecutar_comando)
    async def removebal(
        self,
        ctx,
        user_input: str,
        amount: str
    ):
        user_id, member = await self.resolve_user(
            ctx,
            user_input
        )

        if user_id is None:
            await ctx.send(
                embed=error_embed(
                    "No he podido interpretar ese usuario.\n\n"
                    "Puedes usar:\n"
                    "`?removebal @usuario 25000000`\n"
                    "`?removebal 123456789012345678 25000000`"
                )
            )
            return

        try:
            parsed_amount = self.parse_money(amount)
        except ValueError:
            await ctx.send(
                embed=error_embed(
                    "Cantidad no válida."
                )
            )
            return

        if parsed_amount <= 0:
            await ctx.send(
                embed=error_embed(
                    "Escribe una cantidad positiva. "
                    "El comando ya se encarga de restarla."
                )
            )
            return

        database.add_balance(
            user_id,
            -parsed_amount,
            reason=f"Retirado por {ctx.author}"
        )

        balance, _ = database.get_user(user_id)

        embed = economy_embed(
            "Balance retirado",
            (
                f"👤 **Usuario:** {self.display_user(user_id, member)}\n\n"
                f"➖ **Retirado:** `{self.format_money(parsed_amount)}`\n"
                f"💰 **Nuevo balance:** `{self.format_money(balance)}`"
            )
        )

        if member:
            embed.set_thumbnail(
                url=member.display_avatar.url
            )

        await ctx.send(embed=embed)

    @commands.command()
    @commands.check(Verificator.usuario_puede_ejecutar_comando)
    async def resetbal(
        self,
        ctx,
        user_input: str
    ):
        user_id, member = await self.resolve_user(
            ctx,
            user_input
        )

        if user_id is None:
            await ctx.send(
                embed=error_embed(
                    "No he podido interpretar ese usuario.\n\n"
                    "Puedes usar:\n"
                    "`?resetbal @usuario`\n"
                    "`?resetbal 123456789012345678`"
                )
            )
            return

        balance_before, _ = database.get_user(user_id)

        database.reset_balance(user_id)

        embed = economy_embed(
            "Balance reiniciado",
            (
                f"👤 **Usuario:** {self.display_user(user_id, member)}\n\n"
                f"💰 **Balance anterior:** "
                f"`{self.format_money(balance_before)}`\n"
                f"🧹 **Balance actual:** `0`"
            )
        )

        if member:
            embed.set_thumbnail(
                url=member.display_avatar.url
            )

        await ctx.send(embed=embed)

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
                embed=error_embed(
                    "Cantidad no válida.\n\n"
                    "Ejemplos:\n"
                    "`25000000`\n"
                    "`25,000,000`"
                )
            )
            return

        if parsed_amount <= 0:
            await ctx.send(
                embed=error_embed(
                    "La cantidad debe ser mayor que cero."
                )
            )
            return

        count = 0

        for member in role.members:
            if member.bot:
                continue

            database.add_balance(
                member.id,
                parsed_amount,
                reason=f"Añadido por rol {role.name} por {ctx.author}"
            )

            count += 1

        embed = economy_embed(
            "Balance añadido por rol",
            (
                f"🎭 **Rol:** {role.mention}\n"
                f"👥 **Miembros afectados:** `{count}`\n\n"
                f"➕ **Añadido por usuario:** "
                f"`{self.format_money(parsed_amount)}`"
            )
        )

        await ctx.send(embed=embed)

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
                embed=error_embed(
                    "Faltan argumentos en el comando."
                )
            )
            return

        if isinstance(error, commands.RoleNotFound):
            await contexto.send(
                embed=error_embed(
                    "No he encontrado ese rol."
                )
            )
            return

        if isinstance(error, commands.CheckFailure):
            await contexto.send(
                embed=error_embed(
                    "No tienes permisos suficientes para hacer esto."
                )
            )
            return

        await contexto.send(
            embed=error_embed(
                str(error)
            )
        )


async def setup(bot):
    await bot.add_cog(Balance(bot))