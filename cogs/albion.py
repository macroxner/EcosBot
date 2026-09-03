import aiohttp
import discord
from discord.ext import commands, tasks

import config
import database
from utils.embeds import error_embed, info_embed, success_embed
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
    exact = next((p for p in players if p.get("Name", "").lower() == name.lower()), None)
    if exact is None and players:
        exact = players[0]
    if exact is None:
        return None

    return await fetch_json(f"{config.ALBION_API_BASE}/players/{exact.get('Id')}")


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
        return self.registered_members if self.mode == "registered" else self.unregistered_members

    def total_pages(self):
        return max(1, (len(self.current_items()) + self.page_size - 1) // self.page_size)

    def build_embed(self):
        items = self.current_items()
        total_pages = self.total_pages()
        self.page = min(self.page, total_pages - 1)
        start = self.page * self.page_size
        end = start + self.page_size

        embed = discord.Embed(
            title="📋 Registro de jugadores",
            description=(
                f"✅ Registrados: **{len(self.registered_members)}**\n"
                f"❌ Por registrar: **{len(self.unregistered_members)}**"
            ),
            color=discord.Color.green() if self.mode == "registered" else discord.Color.orange(),
        )

        if not items:
            embed.add_field(
                name="Sin resultados",
                value="No hay usuarios registrados." if self.mode == "registered" else "🎉 Todos los miembros están registrados.",
                inline=False,
            )
        elif self.mode == "registered":
            embed.add_field(
                name=f"✅ Registrados ({len(items)})",
                value="\n".join(
                    f"**{discord_name}** → `{albion_name}` · **{guild_name}**"
                    for discord_name, albion_name, guild_name in items[start:end]
                ),
                inline=False,
            )
        else:
            embed.add_field(
                name=f"❌ Por registrar ({len(items)})",
                value="\n".join(f"• **{name}**" for name in items[start:end]),
                inline=False,
            )

        embed.set_footer(text=f"Página {self.page + 1}/{total_pages} · EcosBot")
        return embed

    async def check_user(self, interaction):
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message(embed=error_embed("Este panel pertenece a otra persona."), ephemeral=True)
            return False
        return True

    @discord.ui.button(label="✅ Registrados", style=discord.ButtonStyle.success)
    async def show_registered(self, interaction, button):
        if not await self.check_user(interaction):
            return
        self.mode = "registered"
        self.page = 0
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    @discord.ui.button(label="❌ Por registrar", style=discord.ButtonStyle.danger)
    async def show_unregistered(self, interaction, button):
        if not await self.check_user(interaction):
            return
        self.mode = "unregistered"
        self.page = 0
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    @discord.ui.button(label="⬅️", style=discord.ButtonStyle.secondary)
    async def previous_page(self, interaction, button):
        if not await self.check_user(interaction):
            return
        if self.page > 0:
            self.page -= 1
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    @discord.ui.button(label="➡️", style=discord.ButtonStyle.secondary)
    async def next_page(self, interaction, button):
        if not await self.check_user(interaction):
            return
        if self.page < self.total_pages() - 1:
            self.page += 1
        await interaction.response.edit_message(embed=self.build_embed(), view=self)


class Albion(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.guild_sync_loop.start()

    def cog_unload(self):
        self.guild_sync_loop.cancel()

    @commands.command(name="register")
    async def register(self, ctx, *args):
        if not args:
            await ctx.send(embed=info_embed("Registro Albion", "Uso: `?register NombreAlbion` o `?register @usuario NombreAlbion`."))
            return

        target = ctx.author
        if ctx.message.mentions:
            if not ctx.author.guild_permissions.manage_guild:
                await ctx.send(embed=error_embed("No tienes permisos para registrar a otra persona."))
                return
            target = ctx.message.mentions[0]
            albion_name = " ".join(args[1:])
        else:
            albion_name = " ".join(args)

        if not albion_name:
            await ctx.send(embed=error_embed("Falta el nombre de Albion."))
            return

        data = await find_player_by_name(albion_name)
        if data is None:
            await ctx.send(embed=error_embed(f"No he encontrado el jugador `{albion_name}`."))
            return

        player = parse_player_data(data)
        database.upsert_registered_player(
            target.id,
            player["albion_id"],
            player["albion_name"],
            player["guild_id"],
            player["guild_name"],
            player["alliance_id"],
            player["alliance_name"],
        )

        embed = success_embed(
            "Registrado correctamente",
            (
                f"👤 **Discord:** {target.mention}\n"
                f"🎮 **Albion:** `{player['albion_name']}`\n"
                f"🏰 **Gremio:** {player['guild_name']}\n"
                f"🤝 **Alianza:** {player['alliance_name']}"
            ),
        )
        embed.set_thumbnail(url=target.display_avatar.url)
        await ctx.send(embed=embed)

    @commands.command(name="albion")
    async def albion(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        data = database.get_registered_player(member.id)
        if not data:
            await ctx.send(embed=error_embed(f"{member.mention} no está registrado."))
            return

        _, _, albion_name, _, guild_name, _, alliance_name = data
        embed = discord.Embed(
            title=f"🎮 Perfil Albion de {member.display_name}",
            color=discord.Color.blurple(),
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="Personaje", value=f"`{albion_name}`", inline=False)
        embed.add_field(name="🏰 Gremio", value=guild_name or "Sin gremio", inline=True)
        embed.add_field(name="🤝 Alianza", value=alliance_name or "Sin alianza", inline=True)
        embed.set_footer(text="EcosBot · Albion")
        await ctx.send(embed=embed)

    @commands.command(name="guilds")
    async def guilds(self, ctx):
        players = database.get_registered_players()
        if not players:
            await ctx.send(embed=info_embed("Gremios", "No hay jugadores registrados."))
            return

        guild_map = {}
        for discord_id, _, albion_name, _, guild_name, _, _ in players:
            guild_map.setdefault(guild_name or "Sin gremio", []).append((discord_id, albion_name))

        embed = discord.Embed(title="🏰 Gremios registrados", color=discord.Color.blurple())
        for guild_name, members in sorted(guild_map.items(), key=lambda x: len(x[1]), reverse=True)[:20]:
            names = []
            for discord_id, albion_name in members[:12]:
                member = ctx.guild.get_member(discord_id)
                discord_name = member.display_name if member else f"Usuario {discord_id}"
                names.append(f"**{discord_name}** / `{albion_name}`")
            if len(members) > 12:
                names.append(f"… y **{len(members) - 12}** más")
            embed.add_field(name=f"{guild_name} · {len(members)}", value="\n".join(names), inline=False)
        embed.set_footer(text="EcosBot · Gremios")
        await ctx.send(embed=embed)

    @commands.command(name="registered")
    async def registered(self, ctx):
        registered_players = database.get_registered_players()
        registered_by_id = {
            discord_id: {"albion_name": albion_name, "guild_name": guild_name or "Sin gremio"}
            for discord_id, _, albion_name, _, guild_name, _, _ in registered_players
        }

        guild_members = [member for member in ctx.guild.members if not member.bot]
        registered_members = []
        unregistered_members = []

        for member in guild_members:
            player = registered_by_id.get(member.id)
            if player:
                registered_members.append((member.display_name, player["albion_name"], player["guild_name"]))
            else:
                unregistered_members.append(member.display_name)

        registered_members.sort(key=lambda item: item[0].lower())
        unregistered_members.sort(key=str.lower)
        view = RegisteredView(ctx, registered_members, unregistered_members)
        await ctx.send(embed=view.build_embed(), view=view)

    @tasks.loop(minutes=10)
    async def guild_sync_loop(self):
        for discord_id, albion_id, old_name, old_guild_id, old_guild_name, old_alliance_id, old_alliance_name in database.get_registered_players():
            data = await fetch_json(f"{config.ALBION_API_BASE}/players/{albion_id}")
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
                player["alliance_name"],
            )
            if old_guild_name != player["guild_name"]:
                await send_log(
                    self.bot,
                    "🏰 Cambio de gremio detectado",
                    f"Jugador: **{player['albion_name']}**\nAntes: **{old_guild_name}**\nAhora: **{player['guild_name']}**",
                    discord.Color.orange(),
                )

    @guild_sync_loop.before_loop
    async def before_guild_sync(self):
        await self.bot.wait_until_ready()


async def setup(bot):
    await bot.add_cog(Albion(bot))
