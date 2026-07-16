import aiohttp
import discord
from discord.ext import commands, tasks
import config
import database
from utils.logger import send_log


async def fetch_json(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url, timeout=15) as response:
            if response.status != 200:
                return None
            return await response.json()


async def find_player_by_name(name):
    search_url = f"{config.ALBION_API_BASE}/search?q={name}"
    data = await fetch_json(search_url)

    if not data or "players" not in data:
        return None

    players = data["players"]

    exact = None
    for player in players:
        if player.get("Name", "").lower() == name.lower():
            exact = player
            break

    if exact is None and players:
        exact = players[0]

    if exact is None:
        return None

    player_id = exact.get("Id")
    player_url = f"{config.ALBION_API_BASE}/players/{player_id}"

    return await fetch_json(player_url)


def parse_player_data(data):
    return {
        "albion_id": data.get("Id"),
        "albion_name": data.get("Name"),
        "guild_id": data.get("GuildId"),
        "guild_name": data.get("GuildName") or "Sin gremio",
        "alliance_id": data.get("AllianceId"),
        "alliance_name": data.get("AllianceName") or "Sin alianza",
    }

class RegisteredView(discord.ui.View):
    def __init__(self, ctx, registered_members, unregistered_members):
        super().__init__(timeout=180)
        self.ctx = ctx
        self.registered_members = registered_members
        self.unregistered_members = unregistered_members
        self.mode = "registered"
        self.page = 0
        self.page_size = 10

    def current_items(self):
        if self.mode == "registered":
            return self.registered_members

        return self.unregistered_members

    def total_pages(self):
        items = self.current_items()
        return max(1, (len(items) + self.page_size - 1) // self.page_size)

    def build_embed(self):
        items = self.current_items()
        total_pages = self.total_pages()

        if self.page >= total_pages:
            self.page = total_pages - 1

        start = self.page * self.page_size
        end = start + self.page_size

        embed = discord.Embed(
            title="📋 Registro de jugadores",
            description=(
                f"Registrados: **{len(self.registered_members)}**\n"
                f"Por registrar: **{len(self.unregistered_members)}**\n\n"
                f"Vista: **{'Registrados' if self.mode == 'registered' else 'Por registrar'}**\n"
                f"Página **{self.page + 1}/{total_pages}**"
            ),
            color=(
                discord.Color.green()
                if self.mode == "registered"
                else discord.Color.orange()
            )
        )

        if not items:
            embed.add_field(
                name="Sin resultados",
                value=(
                    "No hay usuarios registrados."
                    if self.mode == "registered"
                    else "🎉 Todos los miembros están registrados."
                ),
                inline=False
            )
            return embed

        lines = []

        if self.mode == "registered":
            for discord_name, albion_name, guild_name in items[start:end]:
                lines.append(
                    f"✅ **{discord_name}**\n"
                    f"└ Albion: `{albion_name}` | Gremio: **{guild_name}**"
                )
        else:
            for discord_name in items[start:end]:
                lines.append(f"❌ **{discord_name}**")

        embed.add_field(
            name=(
                f"✅ Registrados ({len(items)})"
                if self.mode == "registered"
                else f"❌ Por registrar ({len(items)})"
            ),
            value="\n".join(lines),
            inline=False
        )

        return embed

    async def check_user(self, interaction):
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message(
                "❌ Este panel no es tuyo.",
                ephemeral=True
            )
            return False

        return True

    @discord.ui.button(
        label="✅ Registrados",
        style=discord.ButtonStyle.success
    )
    async def show_registered(self, interaction, button):
        if not await self.check_user(interaction):
            return

        self.mode = "registered"
        self.page = 0

        await interaction.response.edit_message(
            embed=self.build_embed(),
            view=self
        )

    @discord.ui.button(
        label="❌ Por registrar",
        style=discord.ButtonStyle.danger
    )
    async def show_unregistered(self, interaction, button):
        if not await self.check_user(interaction):
            return

        self.mode = "unregistered"
        self.page = 0

        await interaction.response.edit_message(
            embed=self.build_embed(),
            view=self
        )

    @discord.ui.button(
        label="⬅️",
        style=discord.ButtonStyle.secondary
    )
    async def previous_page(self, interaction, button):
        if not await self.check_user(interaction):
            return

        if self.page > 0:
            self.page -= 1

        await interaction.response.edit_message(
            embed=self.build_embed(),
            view=self
        )

    @discord.ui.button(
        label="➡️",
        style=discord.ButtonStyle.secondary
    )
    async def next_page(self, interaction, button):
        if not await self.check_user(interaction):
            return

        if self.page < self.total_pages() - 1:
            self.page += 1

        await interaction.response.edit_message(
            embed=self.build_embed(),
            view=self
        )

class Albion(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.guild_sync_loop.start()

    def cog_unload(self):
        self.guild_sync_loop.cancel()

    @commands.command(name="register")
    async def register(self, ctx, *args):
        if not args:
            await ctx.send("Uso: `!register NombreAlbion` o `!register @usuario NombreAlbion`")
            return

        target = ctx.author

        if ctx.message.mentions:
            if not ctx.author.guild_permissions.manage_guild:
                await ctx.send("❌ No tienes permisos para registrar a otra persona.")
                return

            target = ctx.message.mentions[0]
            albion_name = " ".join(args[1:])
        else:
            albion_name = " ".join(args)

        if not albion_name:
            await ctx.send("❌ Falta el nombre de Albion.")
            return

        data = await find_player_by_name(albion_name)

        if data is None:
            await ctx.send(f"❌ No he encontrado el jugador `{albion_name}`.")
            return

        player = parse_player_data(data)

        database.upsert_registered_player(
            target.id,
            player["albion_id"],
            player["albion_name"],
            player["guild_id"],
            player["guild_name"],
            player["alliance_id"],
            player["alliance_name"]
        )

        await ctx.send(
            f"✅ **Registrado correctamente**\n"
            f"Discord: **{target.display_name}**\n"
            f"Albion: **{player['albion_name']}**\n"
            f"Gremio: **{player['guild_name']}**\n"
            f"Alianza: **{player['alliance_name']}**"
        )

    @commands.command(name="albion")
    async def albion(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        data = database.get_registered_player(member.id)

        if not data:
            await ctx.send(f"❌ {member.display_name} no está registrado.")
            return

        discord_id, albion_id, albion_name, guild_id, guild_name, alliance_id, alliance_name = data

        await ctx.send(
            f"👤 **Perfil Albion de {member.display_name}**\n\n"
            f"Albion: **{albion_name}**\n"
            f"Gremio: **{guild_name}**\n"
            f"Alianza: **{alliance_name}**"
        )

    @commands.command(name="guilds")
    async def guilds(self, ctx):
        players = database.get_registered_players()

        if not players:
            await ctx.send("No hay jugadores registrados.")
            return

        guild_map = {}

        for discord_id, albion_id, albion_name, guild_id, guild_name, alliance_id, alliance_name in players:
            guild_map.setdefault(guild_name or "Sin gremio", []).append((discord_id, albion_name))

        lines = ["🏰 **Gremios registrados**", ""]

        for guild_name, members in sorted(guild_map.items(), key=lambda x: len(x[1]), reverse=True):
            names = []

            for discord_id, albion_name in members:
                member = ctx.guild.get_member(discord_id)
                discord_name = member.display_name if member else f"Usuario {discord_id}"
                names.append(f"{discord_name} / {albion_name}")

            lines.append(f"**{guild_name}** — `{len(members)}`")
            lines.append(", ".join(names[:15]))

            if len(names) > 15:
                lines.append(f"... y {len(names) - 15} más")

            lines.append("")

        await ctx.send("\n".join(lines[:80]))

    @commands.command(name="registered")
    async def registered(self, ctx):
        registered_players = database.get_registered_players()

        registered_by_discord_id = {
            discord_id: {
                "albion_name": albion_name,
                "guild_name": guild_name or "Sin gremio"
            }
            for (
                discord_id,
                albion_id,
                albion_name,
                guild_id,
                guild_name,
                alliance_id,
                alliance_name
            ) in registered_players
        }

        guild_members = [
            member
            for member in ctx.guild.members
            if not member.bot
        ]

        registered_members = []
        unregistered_members = []

        for member in guild_members:
            player = registered_by_discord_id.get(member.id)

            if player:
                registered_members.append(
                    (
                        member.display_name,
                        player["albion_name"],
                        player["guild_name"]
                    )
                )
            else:
                unregistered_members.append(member.display_name)

        registered_members.sort(key=lambda item: item[0].lower())
        unregistered_members.sort(key=str.lower)

        view = RegisteredView(
            ctx,
            registered_members,
            unregistered_members
        )

        await ctx.send(
            embed=view.build_embed(),
            view=view
        )

    @tasks.loop(minutes=10)
    async def guild_sync_loop(self):
        players = database.get_registered_players()

        for discord_id, albion_id, old_name, old_guild_id, old_guild_name, old_alliance_id, old_alliance_name in players:
            url = f"{config.ALBION_API_BASE}/players/{albion_id}"
            data = await fetch_json(url)

            if data is None:
                continue

            player = parse_player_data(data)

            database.upsert_registered_player(
                discord_id,
                player["albion_id"],
                player["albion_name"],
                player["guild_id"],
                player["guild_name"],
                player["alliance_id"],
                player["alliance_name"]
            )

            if old_guild_name != player["guild_name"]:
                await send_log(
                    self.bot,
                    "🏰 Cambio de gremio detectado",
                    f"Jugador: **{player['albion_name']}**\n"
                    f"Antes: **{old_guild_name}**\n"
                    f"Ahora: **{player['guild_name']}**",
                    discord.Color.orange()
                )

    @guild_sync_loop.before_loop
    async def before_guild_sync(self):
        await self.bot.wait_until_ready()


async def setup(bot):
    await bot.add_cog(Albion(bot))