import asyncio
import discord
from discord.ext import commands
import database
import config
from utils.logger import send_log
from utils.embeds import error_embed, info_embed, success_embed

NEW = " ✦ NUEVO"
SHOP_ITEMS = {
    "mute":{"name":"🔇 Mute 2 minutos","cost":50,"description":"Mutea la voz de alguien durante 2 minutos (sin aislarlo).","type":"target"},
    "skill":{"name":"💀 Skill Issue 30 min","cost":75,"description":"Da el rol Skill Issue durante 30 minutos.","type":"target"},
    "npc":{"name":"🤖 NPC Energy 30 min","cost":40,"description":"Da el rol NPC Energy durante 30 minutos.","type":"target"},
    "braincell":{"name":"🧠 Last Braincell 30 min","cost":45,"description":"Da el rol Last Braincell durante 30 minutos.","type":"target"},
    "salty":{"name":"🧂 Salty 30 min","cost":35,"description":"Da el rol Salty durante 30 minutos.","type":"target"},
    "maincharacter":{"name":"👑 Main Character 30 min","cost":60,"description":"Da el rol Main Character durante 30 minutos.","type":"target"},
    "nickname":{"name":"📝 Cambiar nick 30 min","cost":80,"description":"Cambia el nick de alguien durante 30 minutos.","type":"nickname"},
    "quote":{"name":"💬 Frase célebre"+NEW,"cost":50,"description":"Inmortaliza una frase de la comunidad en el Museo de EcosBot.","type":"quote","new":True},
    "pet":{"name":"🐾 Mascota"+NEW,"cost":250,"description":"Elige una mascota, ponle nombre y haz que viva en tu perfil.","type":"pet","new":True},
    "badge":{"name":"🏷️ Badge"+NEW,"cost":150,"description":"Compra una insignia permanente y equípala en tu perfil.","type":"badge","new":True},
    "frame":{"name":"🖼️ Marco de perfil"+NEW,"cost":300,"description":"Desbloquea un estilo permanente para transformar tu ?profile.","type":"frame","new":True},
}
PETS={
 "frog":("🐸","Rana","Pequeña, caótica y sorprendentemente elegante."),
 "cat":("🐱","Gato","Te juzga desde tu perfil, como debe ser."),
 "dog":("🐶","Perro","Leal incluso cuando tus decisiones no lo merecen."),
 "ghost":("👻","Fantasma","Siempre conectado. Nunca responde."),
 "dragon":("🐉","Dragón","Una criatura de prestigio para perfiles con presencia."),
 "axolotl":("🦎","Ajolote","No sabe qué ocurre, pero está encantado de participar."),
}
BADGES={
 "og":("💎","OG","Para quien quiere llevar el sello de veterano."),
 "chaos":("🔥","Caos","La insignia oficial de las malas ideas excelentes."),
 "social":("💬","Social","Para la gente que mantiene vivo el Discord."),
 "collector":("🏆","Coleccionista","Porque tener cosas también es una habilidad."),
 "meme":("🤡","Meme","Una condecoración para el patrimonio cultural del servidor."),
 "heart":("💖","Corazón","Un poco de amor entre tanto caos."),
}
FRAMES={
 "royal":("👑","Real","Un perfil digno de la realeza del servidor."),
 "inferno":("🔥","Infernal","Fuego, caos y cero discreción."),
 "ocean":("🌊","Abisal","Un estilo profundo y limpio."),
 "nature":("🌿","Naturaleza","Un perfil más tranquilo... aparentemente."),
 "void":("🌌","Vacío","Oscuro, misterioso y ligeramente sospechoso."),
 "gold":("✨","Dorado","Para quien considera que normal no es suficiente."),
}

def ecoins(uid): return database.get_user(uid)[1]
def charge(uid,cost,reason): database.add_ecoins(uid,-cost,reason)

async def give_temp_role(guild,member,role_name,minutes=30):
    role=discord.utils.get(guild.roles,name=role_name) or await guild.create_role(name=role_name)
    await member.add_roles(role); await asyncio.sleep(minutes*60)
    if role in member.roles: await member.remove_roles(role)

async def voice_mute_temporarily(member,buyer,minutes=2):
    if member.voice is None or member.voice.channel is None: raise ValueError("El usuario debe estar conectado a un canal de voz para poder mutearlo.")
    if member.voice.mute: raise ValueError("Ese usuario ya está muteado por el servidor.")
    await member.edit(mute=True,reason=f"Mute comprado por {buyer}")
    async def later():
        await asyncio.sleep(minutes*60)
        try:
            if member.voice is not None and member.voice.mute: await member.edit(mute=False,reason="Fin del mute temporal de EcoShop")
        except (discord.Forbidden,discord.HTTPException): pass
    asyncio.create_task(later())

async def change_temp_nickname(member,new_nick,minutes=30):
    old=member.nick; await member.edit(nick=new_nick); await asyncio.sleep(minutes*60)
    try: await member.edit(nick=old)
    except (discord.Forbidden,discord.HTTPException): pass

class QuoteModal(discord.ui.Modal,title="💬 Nueva frase célebre"):
    author=discord.ui.TextInput(label="¿Quién lo dijo?",placeholder="Nombre, apodo o @usuario",max_length=80)
    quote=discord.ui.TextInput(label="¿Qué dijo?",placeholder="Escribe la frase exactamente como quieres guardarla",style=discord.TextStyle.paragraph,max_length=500)
    def __init__(self,buyer): super().__init__(); self.buyer=buyer
    async def on_submit(self,i):
        cost=SHOP_ITEMS['quote']['cost']
        if ecoins(self.buyer.id)<cost: await i.response.send_message(embed=error_embed("Ya no tienes Ecoins suficientes."),ephemeral=True); return
        charge(self.buyer.id,cost,"Compra tienda: Frase célebre")
        qid=database.add_community_quote(self.buyer.id,self.author.value.strip(),self.quote.value.strip())
        database.add_shop_purchase(self.buyer.id,None,'quote',cost)
        e=success_embed("Frase inmortalizada",f"> “{self.quote.value.strip()}”\n\n— **{self.author.value.strip()}**\n\n🏛️ Guardada permanentemente en el **Museo de frases** como `#{qid}`.\nUsa `?quotes` para verlo o `?quote` para sacar una al azar.")
        await i.response.send_message(embed=e)

class NicknameModal(discord.ui.Modal,title="Cambiar nick temporal"):
    new_nick=discord.ui.TextInput(label="Nuevo nick",max_length=32)
    def __init__(self,buyer,target): super().__init__(); self.buyer=buyer; self.target=target
    async def on_submit(self,i):
        cost=SHOP_ITEMS['nickname']['cost']
        if ecoins(self.buyer.id)<cost: await i.response.send_message(embed=error_embed("No tienes suficientes Ecoins."),ephemeral=True); return
        try: await self.target.edit(nick=self.new_nick.value)
        except discord.Forbidden: await i.response.send_message(embed=error_embed("No puedo cambiar el nick de ese usuario."),ephemeral=True); return
        charge(self.buyer.id,cost,"Compra tienda: Cambiar nick"); database.add_shop_purchase(self.buyer.id,self.target.id,'nickname',cost)
        await i.response.send_message(embed=success_embed("Nick temporal aplicado",f"📝 {self.target.mention} será **{self.new_nick.value}** durante **30 minutos**."))
        async def restore():
            await asyncio.sleep(1800)
            try: await self.target.edit(nick=None)
            except: pass
        asyncio.create_task(restore())

class PetNameModal(discord.ui.Modal,title="🐾 Ponle nombre a tu mascota"):
    pet_name=discord.ui.TextInput(label="Nombre de la mascota",placeholder="Ejemplo: Manolo",max_length=24)
    def __init__(self,buyer,key): super().__init__(); self.buyer=buyer; self.key=key
    async def on_submit(self,i):
        cost=SHOP_ITEMS['pet']['cost']
        if ecoins(self.buyer.id)<cost: await i.response.send_message(embed=error_embed("Ya no tienes Ecoins suficientes."),ephemeral=True); return
        emoji,name,desc=PETS[self.key]; charge(self.buyer.id,cost,f"Mascota: {name}"); database.set_user_pet(self.buyer.id,self.key,self.pet_name.value.strip()); database.add_shop_purchase(self.buyer.id,None,'pet:'+self.key,cost)
        await i.response.send_message(embed=success_embed("¡Nueva compañera!",f"{emoji} **{self.pet_name.value.strip()}** ({name}) ya vive en tu perfil.\n\n*{desc}*\n\nMírala con `?profile`."))

class ChoiceSelect(discord.ui.Select):
    def __init__(self,buyer,kind):
        self.buyer=buyer; self.kind=kind; data=PETS if kind=='pet' else BADGES if kind=='badge' else FRAMES
        opts=[discord.SelectOption(label=v[1],emoji=v[0],description=v[2][:100],value=k) for k,v in data.items()]
        super().__init__(placeholder={"pet":"Elige tu mascota...","badge":"Elige tu badge...","frame":"Elige tu marco..."}[kind],options=opts)
    async def callback(self,i):
        if i.user.id!=self.buyer.id: await i.response.send_message(embed=error_embed("Este menú pertenece a otra persona."),ephemeral=True); return
        key=self.values[0]
        if self.kind=='pet': await i.response.send_modal(PetNameModal(self.buyer,key)); return
        data=BADGES if self.kind=='badge' else FRAMES; emoji,name,desc=data[key]; item=SHOP_ITEMS[self.kind]; cost=item['cost']
        owned=database.has_user_badge(self.buyer.id,key) if self.kind=='badge' else database.has_user_frame(self.buyer.id,key)
        if owned:
            if self.kind=='badge': database.equip_user_badge(self.buyer.id,key)
            else: database.equip_user_frame(self.buyer.id,key)
            await i.response.send_message(embed=success_embed(f"{emoji} {name} equipado",f"Ya lo tenías comprado, así que **no se te ha cobrado nada**.\n\n{desc}\n\nMíralo con `?profile`."),ephemeral=True); return
        if ecoins(self.buyer.id)<cost: await i.response.send_message(embed=error_embed("Ya no tienes Ecoins suficientes."),ephemeral=True); return
        charge(self.buyer.id,cost,f"{self.kind}: {name}"); database.add_shop_purchase(self.buyer.id,None,self.kind+':'+key,cost)
        if self.kind=='badge': database.add_user_badge(self.buyer.id,key); database.equip_user_badge(self.buyer.id,key)
        else: database.add_user_frame(self.buyer.id,key); database.equip_user_frame(self.buyer.id,key)
        await i.response.send_message(embed=success_embed(f"{emoji} {name} desbloqueado",f"{desc}\n\n✨ Se ha **equipado automáticamente** y ya aparece en `?profile`."))

class ChoiceView(discord.ui.View):
    def __init__(self,buyer,kind): super().__init__(timeout=90); self.add_item(ChoiceSelect(buyer,kind))

class TargetSelect(discord.ui.UserSelect):
    def __init__(self,buyer,key): super().__init__(placeholder="Elige a la víctima...",min_values=1,max_values=1); self.buyer=buyer; self.key=key
    async def callback(self,i):
        if i.user.id!=self.buyer.id: await i.response.send_message(embed=error_embed("Esta compra pertenece a otra persona."),ephemeral=True); return
        target=i.guild.get_member(self.values[0].id)
        if not target or target.bot or target.id==self.buyer.id: await i.response.send_message(embed=error_embed("Elige otro miembro válido del servidor."),ephemeral=True); return
        if self.key=='nickname': await i.response.send_modal(NicknameModal(self.buyer,target)); return
        item=SHOP_ITEMS[self.key]; cost=item['cost']
        if ecoins(self.buyer.id)<cost: await i.response.send_message(embed=error_embed("No tienes suficientes Ecoins."),ephemeral=True); return
        try:
            if self.key=='mute': await voice_mute_temporarily(target,self.buyer,2); msg=f"🔇 {target.mention} ha sido muteado de voz durante **2 minutos**."
            else:
                names={'skill':'Skill Issue','npc':'NPC Energy','braincell':'Last Braincell','salty':'Salty','maincharacter':'Main Character'}
                asyncio.create_task(give_temp_role(i.guild,target,names[self.key],30)); msg=f"{target.mention} recibe **{names[self.key]}** durante **30 minutos**."
        except (ValueError,discord.Forbidden,discord.HTTPException) as e: await i.response.send_message(embed=error_embed(str(e)),ephemeral=True); return
        charge(self.buyer.id,cost,f"Compra tienda: {item['name']}"); database.add_shop_purchase(self.buyer.id,target.id,self.key,cost)
        await i.response.send_message(embed=success_embed("Compra aplicada",msg))

class TargetView(discord.ui.View):
    def __init__(self,buyer,key): super().__init__(timeout=60); self.add_item(TargetSelect(buyer,key))

class ConfirmView(discord.ui.View):
    def __init__(self,buyer,key): super().__init__(timeout=60); self.buyer=buyer; self.key=key
    @discord.ui.button(label="Continuar",style=discord.ButtonStyle.success,emoji="✨")
    async def cont(self,i,b):
        if i.user.id!=self.buyer.id: await i.response.send_message(embed=error_embed("Esta selección pertenece a otra persona."),ephemeral=True); return
        typ=SHOP_ITEMS[self.key]['type']
        if typ=='quote': await i.response.send_modal(QuoteModal(self.buyer)); return
        if typ in ('pet','badge','frame'):
            await i.response.send_message(embed=info_embed("Elige una opción","Cada opción tiene su propia personalidad. Al seleccionarla verás el resultado inmediatamente."),view=ChoiceView(self.buyer,typ),ephemeral=True); return
        await i.response.send_message(embed=info_embed("Elige objetivo","Ahora selecciona a la persona a la que quieres aplicar la compra."),view=TargetView(self.buyer,self.key),ephemeral=True)

class ShopSelect(discord.ui.Select):
    def __init__(self):
        opts=[discord.SelectOption(label=v['name'][:100],description=f"{v['cost']} Ecoins · {v['description']}"[:100],value=k) for k,v in SHOP_ITEMS.items()]
        super().__init__(placeholder="Elige qué quieres descubrir o comprar...",options=opts)
    async def callback(self,i):
        if i.channel.id!=config.SHOP_CHANNEL: await i.response.send_message(embed=error_embed("La tienda solo se puede usar en el canal de tienda."),ephemeral=True); return
        key=self.values[0]; item=SHOP_ITEMS[key]
        e=discord.Embed(title=item['name'],description=item['description'],color=discord.Color.gold())
        e.add_field(name="💰 Precio",value=f"**{item['cost']} Ecoins**",inline=True)
        if item.get('new'): e.add_field(name="✨ Novedad",value="Recién llegado a EcoShop",inline=True)
        notes={'quote':'Quedará guardada **permanentemente en SQLite** y toda la comunidad podrá verla con `?quotes` o sacar una al azar con `?quote`.','pet':'Podrás elegir especie y **ponerle tu propio nombre**. Aparecerá en `?profile`.','badge':'Es **permanente**. Si vuelves a elegir uno que ya tienes, simplemente se equipa sin cobrarte otra vez.','frame':'Es **permanente** y cambia el estilo visual de tu `?profile`. Puedes coleccionar varios.'}
        if key in notes: e.add_field(name="ℹ️ ¿Cómo funciona?",value=notes[key],inline=False)
        e.set_footer(text="Pulsa Continuar si quieres seguir con la compra")
        await i.response.send_message(embed=e,view=ConfirmView(i.user,key),ephemeral=True)

class ShopView(discord.ui.View):
    def __init__(self): super().__init__(timeout=180); self.add_item(ShopSelect())

class Shop(commands.Cog):
    def __init__(self,bot): self.bot=bot
    @commands.command(name='shop')
    async def shop(self,ctx):
        if ctx.channel.id!=config.SHOP_CHANNEL: await ctx.send(embed=error_embed("La tienda solo se puede usar en el canal de tienda.")); return
        e=discord.Embed(title="🛒 EcoShop",description="Objetos sociales, coleccionables y pequeñas dosis de caos para la comunidad.\n\n✨ Los artículos marcados como **✦ NUEVO** acaban de llegar.",color=discord.Color.gold())
        for item in SHOP_ITEMS.values(): e.add_field(name=f"{item['name']} — {item['cost']} Ecoins",value=item['description'],inline=False)
        e.set_footer(text="EcosBot · Elige un artículo para ver sus detalles antes de comprar")
        await ctx.send(embed=e,view=ShopView())

async def setup(bot): await bot.add_cog(Shop(bot))
