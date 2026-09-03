import re
import discord
from discord.ext import commands
import database
import config
from utils.logger import send_log
from utils.embeds import error_embed, economy_embed


ECOINS_CALLER = 10
ECOINS_PARTY = 10
ECOINS_SCOUT = 15


def parse_money(value):
    return int(value.replace(",", "").replace(".", "").strip())


def extract_mentions_from_line(line):
    return re.findall(r"<@!?\d+>|<@&\d+>", line)


def extract_user_ids_from_mentions(mentions):
    ids = []

    for mention in mentions:
        if mention.startswith("<@&"):
            continue

        user_id = mention.replace("<@", "").replace("!", "").replace(">", "")
        ids.append(int(user_id))

    return ids


def parse_split_message(text):
    lines = text.splitlines()

    users = {
        "Caller": [],
        "Party": [],
        "Scout": []
    }

    payments = {
        "Caller": None,
        "Party": None,
        "Scout": None
    }

    for line in lines:
        clean = line.strip()

        if not clean:
            continue

        if clean.lower().startswith("bolsas"):
            break

        if clean.lower().startswith("caller") and "@" in clean:
            mentions = extract_mentions_from_line(clean)
            users["Caller"] = extract_user_ids_from_mentions(mentions)

        elif clean.lower().startswith("party") and "@" in clean:
            mentions = extract_mentions_from_line(clean)
            users["Party"] = extract_user_ids_from_mentions(mentions)

        elif clean.lower().startswith("scout") and "@" in clean:
            mentions = extract_mentions_from_line(clean)
            users["Scout"] = extract_user_ids_from_mentions(mentions)

        money_match = re.match(r"^(Caller|Party|Scout)\s*:?\s*([\d,\.]+)", clean, re.IGNORECASE)

        if money_match:
            role = money_match.group(1).capitalize()
            amount = parse_money(money_match.group(2))
            payments[role] = amount

    return users, payments


def looks_like_split(text):
    lower = text.lower()

    return (
        "caller" in lower
        and "party" in lower
        and "scout" in lower
        and "bolsas" in lower
    )


def get_parent_channel_id(channel):
    if isinstance(channel, discord.Thread):
        return channel.parent_id

    return channel.id


def add_split_ecoins(message_id, users):
    result_lines = []
    total_ecoins = 0

    for user_id in users["Caller"]:
        database.add_ecoins(user_id, ECOINS_CALLER)
        database.add_ava_participation(message_id, user_id, "Caller", ECOINS_CALLER)
        total_ecoins += ECOINS_CALLER
        result_lines.append(f"Caller: <@{user_id}> +{ECOINS_CALLER} Ecoins")

    for user_id in users["Party"]:
        database.add_ecoins(user_id, ECOINS_PARTY)
        database.add_ava_participation(message_id, user_id, "Party", ECOINS_PARTY)
        total_ecoins += ECOINS_PARTY
        result_lines.append(f"Party: <@{user_id}> +{ECOINS_PARTY} Ecoins")

    for user_id in users["Scout"]:
        database.add_ecoins(user_id, ECOINS_SCOUT)
        database.add_ava_participation(message_id, user_id, "Scout", ECOINS_SCOUT)
        total_ecoins += ECOINS_SCOUT
        result_lines.append(f"Scout: <@{user_id}> +{ECOINS_SCOUT} Ecoins")

    return result_lines, total_ecoins


class Loot(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        parent_channel_id = get_parent_channel_id(message.channel)

        if parent_channel_id != config.SPLIT_CHANNEL:
            return

        if database.is_split_processed(message.id):
            return

        if not looks_like_split(message.content):
            return

        users, payments = parse_split_message(message.content)

        total_users = (
            len(users["Caller"])
            + len(users["Party"])
            + len(users["Scout"])
        )

        if total_users == 0:
            return

        result_lines, total_ecoins = add_split_ecoins(message.id, users)

        achievements_cog = self.bot.get_cog("Achievements")

        if achievements_cog:
            all_users = users["Caller"] + users["Party"] + users["Scout"]

            for user_id in all_users:
                await achievements_cog.check_user_achievements(message.guild, user_id)

        database.mark_split_processed(message.id)

        await send_log(
            self.bot,
            "🪙 Ecoins de split procesados",
            f"Mensaje: {message.jump_url}\n"
            f"Canal/Hilo: {message.channel.mention}\n"
            f"Procesado por mensaje de: {message.author.mention}\n\n"
            + "\n".join(result_lines)
            + f"\n\nTotal Ecoins repartidos: **{total_ecoins}**",
            discord.Color.green()
        )

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def loot(self, ctx, *, text):
        users, payments = parse_split_message(text)

        total_added = 0
        result_lines = []

        for role in ["Caller", "Party", "Scout"]:
            amount = payments.get(role)

            if amount is None:
                continue

            for user_id in users[role]:
                database.add_balance(user_id, amount)
                total_added += amount
                result_lines.append(f"✅ <@{user_id}> +{amount:,} balance ({role})")

        if not result_lines:
            await ctx.send(embed=error_embed("No he encontrado pagos válidos."))
            return

        embed = economy_embed(
            "Loot procesado correctamente",
            "\n".join(result_lines) + f"\n\n💰 **Total añadido:** `{total_added:,}`"
        )
        await ctx.send(embed=embed)

        await send_log(
            self.bot,
            "💰 Loot procesado",
            f"Procesado por: {ctx.author.mention}\n"
            f"Total añadido: {total_added:,}",
            discord.Color.gold()
        )


async def setup(bot):
    await bot.add_cog(Loot(bot))