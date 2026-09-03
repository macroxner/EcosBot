import asyncio
import discord
from discord.ext import commands
import database
import utils.Verificator as Verificator
from utils.embeds import success_embed, error_embed


AUTOROLES_CHANNEL_ID = 1544328737317720085
AUTOROLES_SETTING_KEY = "autoroles_message_id"

# Cada reacción debe ser distinta para poder saber qué rol poner/quitar.
AUTOROLES = {
    "🐉": 1540712364452610178,  # Dragones
    "🛫": 1508200249405997126,  # Grupal Dungeon
    "🔫": 1516583622503825408,  # Gank
    "💵": 1501654982972411935,  # HCE
    "💲": 1409208458397614090,  # AvaBuyer
}

ROLE_LABELS = {
    1540712364452610178: "Dragones 🐉",
    1508200249405997126: "Grupal DUNGEON",
    1516583622503825408: "Gank ☠️",
    1501654982972411935: "HCE 💲",
    1409208458397614090: "AvaBuyer 💲",
}


class AutoRoles(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._ready_lock = asyncio.Lock()

    def build_embed(self) -> discord.Embed:
        lines = [
            "**Date el rol que más te interese reaccionando a los emojis del mensaje**",
            "",
        ]

        for emoji, role_id in AUTOROLES.items():
            label = ROLE_LABELS.get(role_id, "Rol")
            lines.append(f"{emoji} = <@&{role_id}> **{label}**")

        embed = discord.Embed(
            title="¡Autoroles!",
            description="\n".join(lines),
            color=discord.Color.blue(),
        )
        embed.set_footer(text="EcosBot • Reacciona para añadir o quitar tu rol")
        return embed

    async def get_channel(self):
        channel = self.bot.get_channel(AUTOROLES_CHANNEL_ID)
        if channel is not None:
            return channel

        try:
            return await self.bot.fetch_channel(AUTOROLES_CHANNEL_ID)
        except (discord.NotFound, discord.Forbidden, discord.HTTPException) as exc:
            print(f"[AUTOROLES] No se pudo obtener el canal {AUTOROLES_CHANNEL_ID}: {exc}")
            return None

    async def get_autoroles_message(self):
        channel = await self.get_channel()
        if channel is None:
            return None

        raw_message_id = database.get_setting(AUTOROLES_SETTING_KEY)
        if not raw_message_id:
            return None

        try:
            return await channel.fetch_message(int(raw_message_id))
        except (ValueError, discord.NotFound, discord.Forbidden, discord.HTTPException):
            return None

    async def create_or_refresh_message(self):
        channel = await self.get_channel()
        if channel is None:
            raise RuntimeError(
                f"No puedo acceder al canal de autoroles ({AUTOROLES_CHANNEL_ID})."
            )

        message = await self.get_autoroles_message()
        embed = self.build_embed()

        if message is None:
            message = await channel.send(embed=embed)
            database.set_setting(AUTOROLES_SETTING_KEY, str(message.id))
        else:
            await message.edit(embed=embed)

        # Aseguramos que estén todas las reacciones aunque alguien las quite.
        existing = {str(reaction.emoji) for reaction in message.reactions}
        for emoji in AUTOROLES:
            if emoji not in existing:
                await message.add_reaction(emoji)

        return message

    @commands.Cog.listener()
    async def on_ready(self):
        async with self._ready_lock:
            try:
                await self.create_or_refresh_message()
                print("[AUTOROLES] Mensaje de autoroles preparado correctamente.")
            except Exception as exc:
                print(f"[AUTOROLES] Error preparando el mensaje: {exc}")

    async def handle_reaction(self, payload: discord.RawReactionActionEvent, adding: bool):
        if payload.guild_id is None or payload.user_id == self.bot.user.id:
            return

        stored_message_id = database.get_setting(AUTOROLES_SETTING_KEY)
        if not stored_message_id:
            return

        try:
            if payload.message_id != int(stored_message_id):
                return
        except ValueError:
            return

        emoji = str(payload.emoji)
        role_id = AUTOROLES.get(emoji)
        if role_id is None:
            return

        guild = self.bot.get_guild(payload.guild_id)
        if guild is None:
            return

        role = guild.get_role(role_id)
        if role is None:
            print(f"[AUTOROLES] No existe el rol {role_id} en el servidor.")
            return

        member = guild.get_member(payload.user_id)
        if member is None:
            try:
                member = await guild.fetch_member(payload.user_id)
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                return

        if member.bot:
            return

        try:
            if adding:
                if role not in member.roles:
                    await member.add_roles(role, reason="Autorol por reacción")
            else:
                if role in member.roles:
                    await member.remove_roles(role, reason="Autorol retirado al quitar reacción")
        except discord.Forbidden:
            print(
                f"[AUTOROLES] No tengo permisos para modificar el rol {role.name}. "
                "Pon el rol de EcosBot por encima de los roles de autoroles y dale Gestionar roles."
            )
        except discord.HTTPException as exc:
            print(f"[AUTOROLES] Error de Discord modificando {role.name}: {exc}")

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        await self.handle_reaction(payload, adding=True)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        await self.handle_reaction(payload, adding=False)

    @commands.command(aliases=["autorolesrefresh", "refreshroles"])
    @commands.check(Verificator.usuario_puede_ejecutar_comando)
    async def refreshautoroles(self, ctx: commands.Context):
        try:
            message = await self.create_or_refresh_message()
        except Exception as exc:
            await ctx.send(
                embed=error_embed(
                    f"No he podido preparar el mensaje de autoroles.\n\n`{exc}`"
                )
            )
            return

        await ctx.send(
            embed=success_embed(
                "Autoroles actualizados",
                f"El mensaje de autoroles está listo en <#{AUTOROLES_CHANNEL_ID}>.\n"
                f"[Ir al mensaje]({message.jump_url})",
            )
        )

    @refreshautoroles.error
    async def refreshautoroles_error(self, ctx: commands.Context, error):
        if isinstance(error, commands.CheckFailure):
            await ctx.send(
                embed=error_embed("No tienes permisos suficientes para usar este comando.")
            )
            return

        await ctx.send(embed=error_embed(str(error)))


async def setup(bot):
    await bot.add_cog(AutoRoles(bot))
