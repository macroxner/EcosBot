import discord
from discord.ext import commands

from utils.embeds import economy_embed, error_embed
import database


PAGE_SIZE = 10


def get_member_name(ctx, user_id):
    member = ctx.guild.get_member(user_id)
    return member.display_name if member else f"Usuario {user_id}"


def get_medal(index):
    return {
        1: "🥇",
        2: "🥈",
        3: "🥉"
    }.get(index, f"`#{index}`")


class LeaderboardView(discord.ui.View):
    def __init__(self, ctx, users, title, value_index):
        super().__init__(timeout=120)

        self.ctx = ctx
        self.users = users
        self.title = title
        self.value_index = value_index
        self.page = 0

    def build_embed(self):
        total_pages = max(
            1,
            (len(self.users) + PAGE_SIZE - 1) // PAGE_SIZE
        )

        start = self.page * PAGE_SIZE
        end = start + PAGE_SIZE

        page_users = self.users[start:end]

        lines = []

        for i, user_data in enumerate(
            page_users,
            start=start + 1
        ):
            user_id = user_data[0]
            value = user_data[self.value_index] or 0

            name = get_member_name(
                self.ctx,
                user_id
            )

            medal = get_medal(i)

            if self.value_index == 1:
                icon = "💰"
                unit = "plata"
            else:
                icon = "🪙"
                unit = "Ecoins"

            lines.append(
                f"{medal} **{name}**\n"
                f"└ {icon} `{value:,}` {unit}"
            )

        if not lines:
            description = "No hay datos para mostrar."
        else:
            description = "\n\n".join(lines)

        embed = economy_embed(
            self.title,
            description
        )

        embed.set_footer(
            text=(
                f"EcosBot · Página "
                f"{self.page + 1}/{total_pages}"
            )
        )

        return embed

    async def update_message(
        self,
        interaction: discord.Interaction
    ):
        await interaction.response.edit_message(
            content=None,
            embed=self.build_embed(),
            view=self
        )

    @discord.ui.button(
        label="⬅️ Anterior",
        style=discord.ButtonStyle.secondary
    )
    async def previous(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message(
                "❌ Este ranking no es tuyo.",
                ephemeral=True
            )
            return

        if self.page > 0:
            self.page -= 1

        await self.update_message(
            interaction
        )

    @discord.ui.button(
        label="➡️ Siguiente",
        style=discord.ButtonStyle.secondary
    )
    async def next(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message(
                "❌ Este ranking no es tuyo.",
                ephemeral=True
            )
            return

        total_pages = max(
            1,
            (len(self.users) + PAGE_SIZE - 1)
            // PAGE_SIZE
        )

        if self.page < total_pages - 1:
            self.page += 1

        await self.update_message(
            interaction
        )


class Leaderboard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="topbal")
    async def topbal(self, ctx):
        users = database.get_all_users()

        users = sorted(
            users,
            key=lambda x: x[1],
            reverse=True
        )

        if not users:
            await ctx.send(
                embed=error_embed(
                    "No hay usuarios registrados."
                )
            )
            return

        view = LeaderboardView(
            ctx,
            users,
            "Ranking de Balance",
            1
        )

        await ctx.send(
            embed=view.build_embed(),
            view=view
        )

    @commands.command(name="topecoins")
    async def topecoins(self, ctx):
        users = database.get_all_users()

        users = sorted(
            users,
            key=lambda x: x[2],
            reverse=True
        )

        if not users:
            await ctx.send(
                embed=error_embed(
                    "No hay usuarios registrados."
                )
            )
            return

        view = LeaderboardView(
            ctx,
            users,
            "Ranking de Ecoins",
            2
        )

        await ctx.send(
            embed=view.build_embed(),
            view=view
        )


async def setup(bot):
    await bot.add_cog(
        Leaderboard(bot)
    )