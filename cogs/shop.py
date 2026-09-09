import discord
from discord.ext import commands
from datetime import timedelta
import random
import database
import config
from utils.logger import send_log
from utils.embeds import error_embed, info_embed, success_embed
import asyncio


SHOP_ITEMS = {
    "mute": {
        "name": "🔇 Mute 2 minutos",
        "cost": 50,
        "description": "Mutea la voz de alguien durante 2 minutos (sin aislarlo).",
        "needs_target": True,
        "type": "target"
    },
    "skill": {
        "name": "💀 Skill Issue 30 min",
        "cost": 75,
        "description": "Da el rol Skill Issue durante 30 minutos.",
        "needs_target": True,
        "type": "target"
    },
    "npc": {
        "name": "🤖 NPC Energy 30 min",
        "cost": 40,
        "description": "Da el rol NPC Energy durante 30 minutos.",
        "needs_target": True,
        "type": "target"
    },
    "braincell": {
        "name": "🧠 Last Braincell 30 min",
        "cost": 45,
        "description": "Da el rol Last Braincell durante 30 minutos.",
        "needs_target": True,
        "type": "target"
    },
    "salty": {
        "name": "🧂 Salty 30 min",
        "cost": 35,
        "description": "Da el rol Salty durante 30 minutos.",
        "needs_target": True,
        "type": "target"
    },
    "maincharacter": {
        "name": "👑 Main Character 30 min",
        "cost": 60,
        "description": "Da el rol Main Character durante 30 minutos.",
        "needs_target": True,
        "type": "target"
    },
    "nickname": {
        "name": "📝 Cambiar nick 30 min",
        "cost": 80,
        "description": "Cambia el nick de alguien durante 30 minutos.",
        "needs_target": True,
        "type": "nickname"
    },
}


def get_user_ecoins(user_id):
    balance, ecoins = database.get_user(user_id)
    return ecoins


async def give_temp_role(guild, member, role_name, minutes=30):
    role = discord.utils.get(guild.roles, name=role_name)

    if role is None:
        role = await guild.create_role(name=role_name)

    await member.add_roles(role)

    await asyncio.sleep(minutes * 60)

    if role in member.roles:
        await member.remove_roles(role)




async def voice_mute_temporarily(member, buyer, minutes=2):
    """Mute real de voz (server mute), no timeout/aislamiento."""
    if member.voice is None or member.voice.channel is None:
        raise ValueError("El usuario debe estar conectado a un canal de voz para poder mutearlo.")

    if member.voice.mute:
        raise ValueError("Ese usuario ya está muteado por el servidor.")

    await member.edit(
        mute=True,
        reason=f"Mute de voz comprado por {buyer}"
    )

    async def unmute_later():
        await asyncio.sleep(minutes * 60)
        try:
            # El server-mute solo tiene sentido mientras existe estado de voz.
            if member.voice is not None and member.voice.mute:
                await member.edit(
                    mute=False,
                    reason="Fin del mute temporal comprado en EcoShop"
                )
        except (discord.Forbidden, discord.HTTPException):
            pass

    asyncio.create_task(unmute_later())


async def change_temp_nickname(member, new_nick, minutes=30):
    old_nick = member.nick

    await member.edit(nick=new_nick)

    await asyncio.sleep(minutes * 60)

    await member.edit(nick=old_nick)


class NicknameModal(discord.ui.Modal, title="Cambiar nick temporal"):
    new_nick = discord.ui.TextInput(
        label="Nuevo nick",
        placeholder="Ejemplo: Skill Issue Man",
        max_length=32
    )

    def __init__(self, bot, buyer, target, item_key):
        super().__init__()
        self.bot = bot
        self.buyer = buyer
        self.target = target
        self.item_key = item_key

    async def on_submit(self, interaction: discord.Interaction):
        item = SHOP_ITEMS[self.item_key]
        cost = item["cost"]

        balance, ecoins = database.get_user(self.buyer.id)

        if ecoins < cost:
            await interaction.response.send_message(
                embed=error_embed(f"No tienes suficientes Ecoins. Necesitas **{cost}**."),
                ephemeral=True
            )
            return

        database.add_ecoins(self.buyer.id, -cost, f"Compra tienda: {item['name']}")
        database.add_shop_purchase(self.buyer.id, self.target.id, self.item_key, cost)

        await interaction.response.send_message(
            embed=success_embed(
                "Nick temporal aplicado",
                f"📝 {self.buyer.mention} ha cambiado el nick de {self.target.mention} "
                f"a **{self.new_nick.value}** durante **30 minutos**."
            )
        )

        asyncio.create_task(change_temp_nickname(self.target, self.new_nick.value, 30))

class TargetSelect(discord.ui.UserSelect):
    def __init__(self, bot, buyer, item_key):
        super().__init__(
            placeholder="Elige a la víctima...",
            min_values=1,
            max_values=1
        )
        self.bot = bot
        self.buyer = buyer
        self.item_key = item_key

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.buyer.id:
            await interaction.response.send_message(
                embed=error_embed("Esta compra pertenece a otra persona."),
                ephemeral=True
            )
            return

        target = self.values[0]

        if target.bot:
            await interaction.response.send_message(
                embed=error_embed("No puedes elegir bots."),
                ephemeral=True
            )
            return

        if target.id == self.buyer.id:
            await interaction.response.send_message(
                embed=error_embed("No puedes elegirte a ti mismo."),
                ephemeral=True
            )
            return

        member = interaction.guild.get_member(target.id)

        if member is None:
            await interaction.response.send_message(
                embed=error_embed("No encuentro a ese usuario en el servidor."),
                ephemeral=True
            )
            return

        item = SHOP_ITEMS[self.item_key]

        if item.get("type") == "nickname":
            await interaction.response.send_modal(
                NicknameModal(self.bot, self.buyer, member, self.item_key)
            )
            return

        cost = item["cost"]

        ecoins = get_user_ecoins(self.buyer.id)

        if ecoins < cost:
            await interaction.response.send_message(
                embed=error_embed(f"No tienes suficientes Ecoins. Necesitas **{cost}**."),
                ephemeral=True
            )
            return

        # El mute es un server-mute REAL de voz. No usamos timeout, que aísla al usuario.
        # Se aplica antes de cobrar para que nadie pierda Ecoins si Discord rechaza el mute.
        if self.item_key == "mute":
            try:
                await voice_mute_temporarily(member, self.buyer, 2)
            except ValueError as exc:
                await interaction.response.send_message(
                    embed=error_embed(str(exc)),
                    ephemeral=True
                )
                return
            except discord.Forbidden:
                await interaction.response.send_message(
                    embed=error_embed(
                        "No puedo mutear a ese usuario. Comprueba que EcosBot tenga **Silenciar miembros** "
                        "y que su rol esté por encima del rol del objetivo."
                    ),
                    ephemeral=True
                )
                return
            except discord.HTTPException as exc:
                await interaction.response.send_message(
                    embed=error_embed(f"Discord no ha permitido aplicar el mute: `{exc}`"),
                    ephemeral=True
                )
                return

            database.add_ecoins(self.buyer.id, -cost, f"Compra tienda: {item['name']}")
            database.add_shop_purchase(self.buyer.id, member.id, self.item_key, cost)
            msg = (
                f"🔇 {self.buyer.mention} ha comprado un **mute de voz de 2 minutos** "
                f"para {member.mention}."
            )
        else:
            database.add_ecoins(self.buyer.id, -cost, f"Compra tienda: {item['name']}")
            database.add_shop_purchase(self.buyer.id, member.id, self.item_key, cost)

            msg = await apply_shop_effect(
                interaction,
                self.bot,
                self.buyer,
                member,
                self.item_key
            )

        await interaction.response.send_message(
            embed=success_embed("Compra aplicada", msg)
        )

        await send_log(
            self.bot,
            "🛒 Compra de tienda",
            f"Comprador: {self.buyer.mention}\n"
            f"Objetivo: {member.mention}\n"
            f"Producto: {item['name']}\n"
            f"Coste: {cost} Ecoins",
            discord.Color.purple()
        )


class TargetView(discord.ui.View):
    def __init__(self, bot, buyer, item_key):
        super().__init__(timeout=60)
        self.add_item(TargetSelect(bot, buyer, item_key))


class ShopSelect(discord.ui.Select):
    def __init__(self, bot):
        self.bot = bot

        options = []

        for key, item in SHOP_ITEMS.items():
            options.append(
                discord.SelectOption(
                    label=item["name"],
                    description=f"{item['cost']} Ecoins - {item['description']}",
                    value=key
                )
            )

        super().__init__(
            placeholder="Elige qué quieres comprar...",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        if interaction.channel.id != config.SHOP_CHANNEL:
            await interaction.response.send_message(
                embed=error_embed("La tienda solo se puede usar en el canal de tienda."),
                ephemeral=True
            )
            return

        item_key = self.values[0]
        item = SHOP_ITEMS[item_key]
        cost = item["cost"]

        ecoins = get_user_ecoins(interaction.user.id)

        if ecoins < cost:
            await interaction.response.send_message(
                embed=error_embed(
                    f"No tienes suficientes Ecoins. Tienes **{ecoins}** y necesitas **{cost}**."
                ),
                ephemeral=True
            )
            return

        if item["needs_target"]:
            await interaction.response.send_message(
                embed=info_embed(
                    "Elige objetivo",
                    f"Has elegido **{item['name']}**. Ahora selecciona a la víctima."
                ),
                view=TargetView(self.bot, interaction.user, item_key),
                ephemeral=True
            )


class ShopView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=180)
        self.add_item(ShopSelect(bot))


async def apply_shop_effect(interaction, bot, buyer, member, item_key):
    guild = interaction.guild

    if item_key == "mute":
        await voice_mute_temporarily(member, buyer, 2)
        return f"🔇 {buyer.mention} ha comprado un **mute de voz de 2 minutos** para {member.mention}."

    if item_key == "skill":
        asyncio.create_task(give_temp_role(guild, member, "Skill Issue", 30))
        return f"💀 {buyer.mention} ha dado **Skill Issue** a {member.mention} durante **30 minutos**."

    if item_key == "npc":
        asyncio.create_task(give_temp_role(guild, member, "NPC Energy", 30))
        return f"🤖 {buyer.mention} ha dado **NPC Energy** a {member.mention} durante **30 minutos**."

    if item_key == "braincell":
        asyncio.create_task(give_temp_role(guild, member, "Last Braincell", 30))
        return f"🧠 {buyer.mention} ha dado **Last Braincell** a {member.mention} durante **30 minutos**."

    if item_key == "salty":
        asyncio.create_task(give_temp_role(guild, member, "Salty", 30))
        return f"🧂 {buyer.mention} ha dado **Salty** a {member.mention} durante **30 minutos**."

    if item_key == "maincharacter":
        asyncio.create_task(give_temp_role(guild, member, "Main Character", 30))
        return f"👑 {buyer.mention} ha convertido a {member.mention} en **Main Character** durante **30 minutos**."

    return "Compra realizada."


class Shop(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="shop")
    async def shop(self, ctx):
        if ctx.channel.id != config.SHOP_CHANNEL:
            await ctx.send(embed=error_embed("La tienda solo se puede usar en el canal de tienda."))
            return

        embed = discord.Embed(
            title="🛒 EcoShop",
            description="Compra recompensas meme usando tus Ecoins.",
            color=discord.Color.gold()
        )

        for item in SHOP_ITEMS.values():
            embed.add_field(
                name=f"{item['name']} — {item['cost']} Ecoins",
                value=item["description"],
                inline=False
            )

        embed.set_footer(text="EcosBot · EcoShop")
        await ctx.send(embed=embed, view=ShopView(self.bot))


async def setup(bot):
    await bot.add_cog(Shop(bot))