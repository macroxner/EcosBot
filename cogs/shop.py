import discord
from discord.ext import commands
from datetime import timedelta
import random
import database
import config
from utils.logger import send_log
import asyncio


SHOP_ITEMS = {
    "mute": {
        "name": "🔇 Mute 1 minuto",
        "cost": 50,
        "description": "Mutea a alguien durante 1 minuto.",
        "needs_target": True,
        "type": "target",
        
    },
    "skill": {
        "name": "💀 Skill Issue 20 min",
        "cost": 75,
        "description": "Da el rol Skill Issue durante 20 minutos.",
        "needs_target": True,
        "type": "target",
        "id_rol": 1535231201193893998
        # PRUEBAS "id_rol":1535233450632814663
    },
    "npc": {
        "name": "🤖 NPC Energy 20 min",
        "cost": 40,
        "description": "Da el rol NPC Energy durante 20 minutos.",
        "needs_target": True,
        "type": "target",
        "id_rol": 1529106389312602183
    },
    "braincell": {
        "name": "🧠 Last Braincell 20 min",
        "cost": 45,
        "description": "Da el rol Last Braincell durante 20 minutos.",
        "needs_target": True,
        "type": "target",
        "id_rol": 1528791663030440058
    },
    "salty": {
        "name": "🧂 Salty 20 min",
        "cost": 35,
        "description": "Da el rol Salty durante 20 minutos.",
        "needs_target": True,
        "type": "target",
        "id_rol": 1535230451071852656
    },
    "maincharacter": {
        "name": "👑 Main Character 20 min",
        "cost": 60,
        "description": "Da el rol Main Character durante 20 minutos.",
        "needs_target": True,
        "type": "target",
        "id_rol": 1535230938185994250
    },
    "nickname": {
        "name": "📝 Cambiar nick 20 min",
        "cost": 80,
        "description": "Cambia el nick de alguien durante 20 minutos.",
        "needs_target": True,
        "type": "nickname",
    },
}


def get_user_ecoins(user_id):
    balance, ecoins = database.get_user(user_id)
    return ecoins


async def give_temp_role(guild, member, role_id, minutes=20):
    role = discord.utils.get(guild.roles, id=role_id)

    #if role is None:
    #    role = await guild.create_role(name=role_name)

    await member.add_roles(role)

    await asyncio.sleep(minutes * 60)

    if role in member.roles:
        await member.remove_roles(role)


async def change_temp_nickname(member, new_nick, minutes=20):
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
                f"❌ No tienes suficientes Ecoins. Necesitas **{cost}**.",
                ephemeral=True
            )
            return

        database.add_ecoins(self.buyer.id, -cost, f"Compra tienda: {item['name']}")
        database.add_shop_purchase(self.buyer.id, self.target.id, self.item_key, cost)

        await interaction.response.send_message(
            f"📝 {self.buyer.mention} ha cambiado el nick de {self.target.mention} "
            f"a **{self.new_nick.value}** durante **20 minutos**."
        )

        asyncio.create_task(change_temp_nickname(self.target, self.new_nick.value, 20))

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
                "❌ Esta compra no es tuya.",
                ephemeral=True
            )
            return

        target = self.values[0]

        if target.bot:
            await interaction.response.send_message(
                "❌ No puedes elegir bots.",
                ephemeral=True
            )
            return

        if target.id == self.buyer.id:
            await interaction.response.send_message(
                "❌ No puedes elegirte a ti mismo.",
                ephemeral=True
            )
            return

        member = interaction.guild.get_member(target.id)

        if member is None:
            await interaction.response.send_message(
                "❌ No encuentro a ese usuario en el servidor.",
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
                f"❌ No tienes suficientes Ecoins. Necesitas **{cost}**.",
                ephemeral=True
            )
            return

        database.add_ecoins(self.buyer.id, -cost, f"Compra tienda: {item['name']}")
        
        msg = await apply_shop_effect(
            interaction,
            self.bot,
            self.buyer,
            member,
            self.item_key
        )

        if(msg[1]):
            database.add_shop_purchase(self.buyer.id, member.id, self.item_key, cost)
            await interaction.response.send_message(msg[0])
        else:
            # Comando erroneo por algun motivo
            await interaction.response.send_message(msg[0])
            database.add_ecoins(self.buyer.id, cost, f"Compra reembolsada tienda por {msg[0]}: {item['name']}")

        if(msg[1]):
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
                "❌ La tienda solo se puede usar en el canal de tienda.",
                ephemeral=True
            )
            return

        item_key = self.values[0]
        item = SHOP_ITEMS[item_key]
        cost = item["cost"]

        ecoins = get_user_ecoins(interaction.user.id)

        if ecoins < cost:
            await interaction.response.send_message(
                f"❌ No tienes suficientes Ecoins. Tienes **{ecoins}**, necesitas **{cost}**.",
                ephemeral=True
            )
            return

        if item["needs_target"]:
            await interaction.response.send_message(
                f"Has elegido **{item['name']}**.\nAhora elige a la víctima:",
                view=TargetView(self.bot, interaction.user, item_key),
                ephemeral=True
            )

async def mute_member_async(member):
    await member.edit(mute = True)
            
    await asyncio.sleep(60);
    
    await member.edit(mute = False)
class ShopView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=180)
        self.add_item(ShopSelect(bot))


async def apply_shop_effect(interaction, bot, buyer, member, item_key):
    guild = interaction.guild

    if item_key == "mute":
        member_data = await member.fetch_voice()
        if(member_data.mute):
            return [f"{member.mention} ya está silenciado, compra reembolsada.", False]
        
        asyncio.create_task(mute_member_async(member=member))
        return [f"🔇 {buyer.mention} ha comprado un **mute de 1 minuto** para {member.mention}.", True]
    

    if item_key == "skill":
        asyncio.create_task(give_temp_role(guild, member, SHOP_ITEMS["skill"]["id_rol"], 20))
        return [f"💀 {buyer.mention} ha dado **Skill Issue** a {member.mention} durante **20 minutos**.", True]

    if item_key == "npc":
        asyncio.create_task(give_temp_role(guild, member, SHOP_ITEMS["npc"]["id_rol"], 20))
        return [f"🤖 {buyer.mention} ha dado **NPC Energy** a {member.mention} durante **20 minutos**.", True]

    if item_key == "braincell":
        asyncio.create_task(give_temp_role(guild, member, SHOP_ITEMS["braincell"]["id_rol"], 20))
        return [f"🧠 {buyer.mention} ha dado **Last Braincell** a {member.mention} durante **20 minutos**.", True]

    if item_key == "salty":
        asyncio.create_task(give_temp_role(guild, member, SHOP_ITEMS["salty"]["id_rol"], 20))
        return [f"🧂 {buyer.mention} ha dado **Salty** a {member.mention} durante **20 minutos**.", True]

    if item_key == "maincharacter":
        asyncio.create_task(give_temp_role(guild, member, SHOP_ITEMS["maincharacter"]["id_rol"], 20))
        return [f"👑 {buyer.mention} ha convertido a {member.mention} en **Main Character** durante **20 minutos**.", True]

    return "Compra realizada."


class Shop(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="shop")
    async def shop(self, ctx):
        if ctx.channel.id != config.SHOP_CHANNEL:
            await ctx.send("❌ La tienda solo se puede usar en el canal de tienda.")
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

        await ctx.send(embed=embed, view=ShopView(self.bot))


async def setup(bot):
    await bot.add_cog(Shop(bot))