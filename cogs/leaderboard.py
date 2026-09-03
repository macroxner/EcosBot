import discord
from discord.ext import commands

import database
from utils.embeds import error_embed, info_embed


PAGE_SIZE = 10


def get_member_name(ctx, user_id):
    member = ctx.guild.get_member(user_id)
    return member.display_name if member else f"Usuario {user_id}"


def get_medal(index):
    return {1: "🥇", 2: "🥈", 3: "🥉"}.get(index, f"**{index}.**")


class LeaderboardView(discord.ui.View):
    def __init__(self, ctx, users, title, value_index, color):
        super().__init__(timeout=120)
        self.ctx = ctx
        self.users = users
        self.title = title
        self.value_index = value_index
        self.color = color
        self.page = 0

    def build_embed(self):
        total_pages = max(1, (len(self.users) + PAGE_SIZE - 1) // PAGE_SIZE)
        start = self.page * PAGE_SIZE
        end = start + PAGE_SIZE
        page_users = self.users[start:end]

        lines = []
        for i, user_data in enumerate(page_users, start=start + 1):
            user_id = user_data[0]
            value = user_data[self.value_index]
            name = get_member_name(self.ctx, user_id)
            lines.append(f"{get_medal(i)} **{name}** — `{value:,}`")

        embed = discord.Embed(
            title=self.title,
            description="\n".join(lines) or "Sin datos.",
            color=self.color,
        )
        embed.set_footer(text=f"Página {self.page + 1}/{total_pages} · EcosBot")
        return embed

    async def update_message(self, interaction):
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    async def check_owner(self, interaction):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message(
                embed=error_embed("Este ranking pertenece a otra persona."),
                ephemeral=True,
            )
            return False
        return True

    @discord.ui.button(label="⬅️ Anterior", style=discord.ButtonStyle.secondary)
    async def previous(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.check_owner(interaction):
            return
        if self.page > 0:
            self.page -= 1
        await self.update_message(interaction)

    @discord.ui.button(label="➡️ Siguiente", style=discord.ButtonStyle.secondary)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.check_owner(interaction):
            return
        total_pages = max(1, (len(self.users) + PAGE_SIZE - 1) // PAGE_SIZE)
        if self.page < total_pages - 1:
            self.page += 1
        await self.update_message(interaction)


class Leaderboard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="topbal")
    async def topbal(self, ctx):
        users = sorted(database.get_all_users(), key=lambda x: x[1], reverse=True)
        if not users:
            await ctx.send(embed=info_embed("Ranking de balance", "No hay usuarios registrados."))
            return
        view = LeaderboardView(ctx, users, "🏆 Ranking de Balance", 1, discord.Color.gold())
        await ctx.send(embed=view.build_embed(), view=view)

    @commands.command(name="topecoins")
    async def topecoins(self, ctx):
        users = sorted(database.get_all_users(), key=lambda x: x[2], reverse=True)
        if not users:
            await ctx.send(embed=info_embed("Ranking de Ecoins", "No hay usuarios registrados."))
            return
        view = LeaderboardView(ctx, users, "🪙 Ranking de Ecoins", 2, discord.Color.gold())
        await ctx.send(embed=view.build_embed(), view=view)


async def setup(bot):
    await bot.add_cog(Leaderboard(bot))
