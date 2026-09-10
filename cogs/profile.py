import discord
from discord.ext import commands
import database
from cogs.community import PETS, BADGES, FRAMES

FRAME_STYLES={
 "royal":(discord.Color.purple(),"👑 ══ PERFIL REAL ══ 👑","👑 ✦ EcosBot · Perfil Real ✦ 👑"),
 "inferno":(discord.Color.red(),"🔥 ━━ PERFIL INFERNAL ━━ 🔥","🔥 EcosBot · Que arda el perfil 🔥"),
 "ocean":(discord.Color.blue(),"🌊 ～～ PERFIL ABISAL ～～ 🌊","🌊 EcosBot · Desde las profundidades 🌊"),
 "nature":(discord.Color.green(),"🌿 ❧ PERFIL NATURALEZA ❧ 🌿","🌿 EcosBot · Perfil Naturaleza 🌿"),
 "void":(discord.Color.dark_purple(),"🌌 ◈ PERFIL DEL VACÍO ◈ 🌌","🌌 EcosBot · El Vacío observa 🌌"),
 "gold":(discord.Color.gold(),"✨ ══ PERFIL DORADO ══ ✨","✨ EcosBot · Edición Dorada ✨"),
}

class Profile(commands.Cog):
    def __init__(self,bot): self.bot=bot
    @commands.command(name='profile',aliases=['perfil'])
    async def profile(self,ctx,member:discord.Member=None):
        member=member or ctx.author
        balance,ecoins=database.get_user(member.id); warnings=database.get_warnings(member.id); total_fines=sum(r[2] for r in warnings)
        ava=database.get_user_ava_stats(member.id); dragon_total,_=database.get_user_dragon_stats(member.id); albion=database.get_registered_player(member.id)
        pet=database.get_user_pet(member.id); badge_key=database.get_equipped_badge(member.id); frame_key=database.get_equipped_frame(member.id)
        color,title_prefix,footer=(discord.Color.blurple(),"📋 PERFIL","EcosBot · Perfil")
        if frame_key in FRAME_STYLES: color,title_prefix,footer=FRAME_STYLES[frame_key]
        badge=""
        if badge_key in BADGES:
            em,nm,_=BADGES[badge_key]; badge=f" · {em} **{nm}**"
        embed=discord.Embed(title=f"{title_prefix}\n{member.display_name}{badge}",color=color)
        embed.set_thumbnail(url=member.display_avatar.url)
        if pet and pet[0] in PETS:
            em,species,desc=PETS[pet[0]]; embed.description=f"{em} **{pet[1]}** · {species}\n*{desc}*"
        if albion:
            _,_,name,_,guild,_,alliance=albion; embed.add_field(name='🎮 Albion',value=f"Personaje: **{name}**\nGremio: **{guild or 'Sin gremio'}**\nAlianza: **{alliance or 'Sin alianza'}**",inline=False)
        embed.add_field(name='💰 Balance',value=f'`{balance:,}`',inline=True); embed.add_field(name='🪙 Ecoins',value=f'`{ecoins:,}`',inline=True); embed.add_field(name='⚠️ Warnings',value=f'`{len(warnings)}`',inline=True)
        embed.add_field(name='💸 Multas',value=f'`{total_fines:,}`',inline=True); embed.add_field(name='⚔️ Avas',value=f'`{ava[0] or 0}`',inline=True); embed.add_field(name='🐉 Dragones',value=f'`{dragon_total}`',inline=True)
        if frame_key in FRAMES: embed.add_field(name='🖼️ Marco',value=f"{FRAMES[frame_key][0]} {FRAMES[frame_key][1]}",inline=True)
        embed.set_footer(text=footer); await ctx.send(embed=embed)
async def setup(bot): await bot.add_cog(Profile(bot))
