import discord
from discord.ext import commands

import database
from utils.embeds import error_embed


def get_name(guild, user_id):
    member = guild.get_member(user_id)
    return member.display_name if member else f"Usuario {user_id}"


def format_top(guild, data):
    if not data:
        return "Sin datos todavía."

    medals = ["🥇", "🥈", "🥉"]
    lines = []

    for index, (user_id, count) in enumerate(data, start=1):
        name = get_name(guild, user_id)
        prefix = medals[index - 1] if index <= 3 else f"**{index}.**"
        lines.append(f"{prefix} **{name}** — `{count}`")

    return "\n".join(lines)


class DashboardView(discord.ui.View):
    def __init__(self, ctx):
        super().__init__(timeout=180)
        self.ctx = ctx

    async def update(self, interaction, embed):
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message(
                embed=error_embed("Este dashboard pertenece a otra persona."),
                ephemeral=True,
            )
            return

        await interaction.response.edit_message(embed=embed, view=self)

    def general_embed(self):
        stats = database.get_dashboard_stats()
        dragons = database.get_dragon_dashboard_stats()

        embed = discord.Embed(
            title="📊 EcosBot Dashboard",
            description="Resumen general de la comunidad.",
            color=discord.Color.blue(),
        )

        embed.add_field(name="👥 Usuarios", value=f"`{stats['users_count']:,}`", inline=True)
        embed.add_field(name="⚔️ Avalonianas", value=f"`{stats['ava_count']:,}`", inline=True)
        embed.add_field(name="🐉 Dragones", value=f"`{dragons['dragon_count']:,}`", inline=True)
        embed.add_field(name="🧍 Participaciones Ava", value=f"`{stats['participations_count']:,}`", inline=True)
        embed.add_field(name="🐲 Participaciones Dragon", value=f"`{dragons['dragon_participations']:,}`", inline=True)
        embed.add_field(name="⚠️ Warnings", value=f"`{stats['warnings_count']:,}`", inline=True)
        embed.add_field(name="💰 Balance total", value=f"`{stats['total_balance']:,}`", inline=True)
        embed.add_field(name="🪙 Ecoins actuales", value=f"`{stats['total_ecoins']:,}`", inline=True)
        embed.add_field(name="🛒 Compras", value=f"`{stats['shop_purchases']:,}`", inline=True)
        embed.set_footer(text="EcosBot · Usa los botones para cambiar de sección")
        return embed

    def avas_embed(self):
        embed = discord.Embed(
            title="⚔️ Dashboard de Avalonianas",
            description="Jugadores más activos por función en los splits.",
            color=discord.Color.green(),
        )

        embed.add_field(
            name="📢 Top Callers",
            value=format_top(self.ctx.guild, database.get_top_by_ava_role("Caller", 5)),
            inline=False,
        )
        embed.add_field(
            name="🕵️ Top Scouts",
            value=format_top(self.ctx.guild, database.get_top_by_ava_role("Scout", 5)),
            inline=False,
        )
        embed.add_field(
            name="🛡️ Top Party",
            value=format_top(self.ctx.guild, database.get_top_by_ava_role("Party", 5)),
            inline=False,
        )
        embed.set_footer(text="EcosBot · Avalonianas")
        return embed

    def dragons_embed(self):
        dragon_stats = database.get_dragon_dashboard_stats()

        embed = discord.Embed(
            title="🐉 Dashboard de Dragones",
            description=(
                f"Dragones completados: **{dragon_stats['dragon_count']}**\n"
                f"Participaciones: **{dragon_stats['dragon_participations']}**"
            ),
            color=discord.Color.red(),
        )
        embed.add_field(
            name="🏆 Más Dragones",
            value=format_top(self.ctx.guild, database.get_top_dragons(10)),
            inline=False,
        )
        embed.set_footer(text="EcosBot · Dragones")
        return embed

    def warnings_embed(self):
        embed = discord.Embed(
            title="⚠️ Dashboard de Warnings",
            description="Usuarios con más warnings.",
            color=discord.Color.orange(),
        )
        embed.add_field(
            name="Top Warnings",
            value=format_top(self.ctx.guild, database.get_top_warnings(10)),
            inline=False,
        )
        embed.set_footer(text="EcosBot · Moderación")
        return embed

    def shop_embed(self):
        embed = discord.Embed(
            title="🛒 Dashboard de Tienda",
            description="Usuarios que más han comprado.",
            color=discord.Color.purple(),
        )
        embed.add_field(
            name="Top compradores",
            value=format_top(self.ctx.guild, database.get_top_shop_buyers(10)),
            inline=False,
        )
        embed.set_footer(text="EcosBot · Tienda")
        return embed

    @discord.ui.button(label="📊 General", style=discord.ButtonStyle.primary)
    async def general_button(self, interaction, button):
        await self.update(interaction, self.general_embed())

    @discord.ui.button(label="⚔️ Avas", style=discord.ButtonStyle.success)
    async def avas_button(self, interaction, button):
        await self.update(interaction, self.avas_embed())

    @discord.ui.button(label="🐉 Dragones", style=discord.ButtonStyle.danger)
    async def dragons_button(self, interaction, button):
        await self.update(interaction, self.dragons_embed())

    @discord.ui.button(label="⚠️ Warnings", style=discord.ButtonStyle.secondary)
    async def warnings_button(self, interaction, button):
        await self.update(interaction, self.warnings_embed())

    @discord.ui.button(label="🛒 Tienda", style=discord.ButtonStyle.secondary)
    async def shop_button(self, interaction, button):
        await self.update(interaction, self.shop_embed())


class Dashboard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="dashboard")
    async def dashboard(self, ctx):
        view = DashboardView(ctx)
        await ctx.send(embed=view.general_embed(), view=view)


async def setup(bot):
    await bot.add_cog(Dashboard(bot))
