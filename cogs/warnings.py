import discord
from discord.ext import commands

import config
import database
from utils.embeds import error_embed, info_embed, success_embed, warning_embed
from utils.logger import send_log


def get_warning_type(text):
    text = text.lower()
    for warning_name, data in config.WARNING_TYPES.items():
        for alias in data["aliases"]:
            if alias in text:
                return warning_name
    return None


def calculate_fine(user_id, warning_type):
    data = config.WARNING_TYPES[warning_type]
    if data.get("escalate"):
        current_warnings = database.get_warning_count(user_id)
        fines = data["fines"]
        return fines[min(current_warnings, len(fines) - 1)]
    return data["fine"]


class Warnings(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or message.channel.id != config.WARNING_CHANNEL:
            return
        if not message.mentions:
            return

        member = message.mentions[0]
        warning_type = get_warning_type(message.content)
        if warning_type is None:
            return

        fine = calculate_fine(member.id, warning_type)
        database.add_warning(member.id, message.author.id, warning_type, fine)
        database.add_balance(member.id, -fine, reason=f"Warning {warning_type}")
        total_warnings = database.get_warning_count(member.id)

        await message.add_reaction("✅")
        embed = warning_embed(
            "Warning procesado",
            (
                f"👤 **Usuario:** {member.mention}\n"
                f"🛡️ **Moderador:** {message.author.mention}\n"
                f"📌 **Tipo:** `{warning_type}`\n"
                f"⚠️ **Warning nº:** `{total_warnings}`\n"
                f"💸 **Multa:** `{fine:,}`\n"
                f"💰 **Balance aplicado:** `-{fine:,}`"
            ),
        )
        await message.reply(embed=embed, mention_author=False)

        await send_log(
            self.bot,
            "⚠️ Warning procesado",
            (
                f"Usuario: {member.mention}\n"
                f"Moderador: {message.author.mention}\n"
                f"Tipo: {warning_type}\n"
                f"Warning nº: {total_warnings}\n"
                f"Multa: {fine:,}"
            ),
            discord.Color.orange(),
        )

    @commands.command(name="warnings")
    async def warnings(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        rows = database.get_warnings(member.id)

        if not rows:
            await ctx.send(embed=success_embed("Sin warnings", f"{member.mention} no tiene warnings."))
            return

        total_fines = sum(row[2] for row in rows)
        embed = discord.Embed(
            title=f"⚠️ Warnings de {member.display_name}",
            description=f"Total: **{len(rows)}** · Multas acumuladas: **{total_fines:,}**",
            color=discord.Color.orange(),
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(
            name="📜 Últimos warnings",
            value="\n".join(
                f"`#{warning_id}` · **{fine:,}** · `{reason}` · {created_at}"
                for warning_id, reason, fine, created_at in rows[:10]
            ),
            inline=False,
        )
        embed.set_footer(text="EcosBot · Warnings")
        await ctx.send(embed=embed)

    @commands.command(name="removewarning")
    @commands.has_permissions(administrator=True)
    async def removewarning(self, ctx, member: discord.Member):
        fine = database.remove_last_warning(member.id)
        if fine is None:
            await ctx.send(embed=error_embed(f"{member.mention} no tiene warnings."))
            return

        database.add_balance(member.id, fine, reason=f"Warning eliminado por {ctx.author}")
        await ctx.send(embed=success_embed(
            "Warning eliminado",
            f"👤 {member.mention}\n💰 Balance devuelto: **{fine:,}**"
        ))

        await send_log(
            self.bot,
            "✅ Warning eliminado",
            f"Usuario: {member.mention}\nEliminado por: {ctx.author.mention}\nBalance devuelto: {fine:,}",
            discord.Color.green(),
        )


async def setup(bot):
    await bot.add_cog(Warnings(bot))
