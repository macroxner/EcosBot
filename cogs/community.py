import discord
from discord.ext import commands
import database
from utils.embeds import error_embed, info_embed

PETS = {
    "frog": ("🐸", "Rana", "Pequeña, caótica y sorprendentemente elegante."),
    "cat": ("🐱", "Gato", "Te juzga desde tu perfil, como debe ser."),
    "dog": ("🐶", "Perro", "Leal incluso cuando tus decisiones no lo merecen."),
    "ghost": ("👻", "Fantasma", "Siempre conectado. Nunca responde."),
    "dragon": ("🐉", "Dragón", "Una criatura de prestigio para perfiles con presencia."),
    "axolotl": ("🦎", "Ajolote", "No sabe qué ocurre, pero está encantado de participar."),
}
BADGES = {
    "og": ("💎", "OG", "Para quien quiere llevar el sello de veterano."),
    "chaos": ("🔥", "Caos", "La insignia oficial de las malas ideas excelentes."),
    "social": ("💬", "Social", "Para la gente que mantiene vivo el Discord."),
    "collector": ("🏆", "Coleccionista", "Porque tener cosas también es una habilidad."),
    "meme": ("🤡", "Meme", "No necesita explicación. Tú sabes quién eres."),
    "heart": ("💖", "Corazón", "Un poco de amor entre tanto caos."),
}
FRAMES = {
    "royal": ("👑", "Real"), "inferno": ("🔥", "Infernal"), "ocean": ("🌊", "Abisal"),
    "nature": ("🌿", "Naturaleza"), "void": ("🌌", "Vacío"), "gold": ("✨", "Dorado"),
}

class Community(commands.Cog):
    def __init__(self, bot): self.bot = bot

    @commands.command(name="quote", aliases=["frase"])
    async def quote(self, ctx):
        row = database.get_random_community_quote()
        if not row:
            await ctx.send(embed=info_embed("Frases célebres", "Todavía no hay ninguna frase guardada. Puedes añadirlas desde `?shop`."))
            return
        qid, _, author, text, _ = row
        embed = discord.Embed(title="💬 Frase célebre", description=f"“{text}”", color=discord.Color.gold())
        embed.add_field(name="— Lo dijo", value=author, inline=False)
        embed.set_footer(text=f"EcosBot · Museo de frases · #{qid}")
        await ctx.send(embed=embed)

    @commands.command(name="quotes", aliases=["frases"])
    async def quotes(self, ctx):
        rows = database.get_community_quotes(10)
        if not rows:
            await ctx.send(embed=info_embed("Museo de frases", "Todavía no hay frases guardadas.")); return
        embed = discord.Embed(title="🏛️ Museo de frases célebres", description="Las últimas joyas inmortalizadas por la comunidad.", color=discord.Color.gold())
        for qid, _, author, text, _ in rows:
            shown = text if len(text) <= 180 else text[:177] + "..."
            embed.add_field(name=f"#{qid} · {author}", value=f"“{shown}”", inline=False)
        embed.set_footer(text="EcosBot · ?quote muestra una al azar")
        await ctx.send(embed=embed)

    @commands.command(name="cosmetics", aliases=["cosmeticos"])
    async def cosmetics(self, ctx):
        pet = database.get_user_pet(ctx.author.id)
        badges = database.get_user_badges(ctx.author.id)
        frames = database.get_user_frames(ctx.author.id)
        lines=[]
        if pet:
            emoji,name,_=PETS.get(pet[0],("🐾",pet[0],"")); lines.append(f"**Mascota:** {emoji} {pet[1]} · {name}")
        else: lines.append("**Mascota:** Ninguna")
        lines.append("**Badges:** " + (", ".join((BADGES.get(k,("🏷️",k,""))[0]+" "+BADGES.get(k,("",k,""))[1]) + (" ✓" if eq else "") for k,eq in badges) if badges else "Ninguno"))
        lines.append("**Marcos:** " + (", ".join(FRAMES.get(k,("🖼️",k))[0]+" "+FRAMES.get(k,("",k))[1] + (" ✓" if eq else "") for k,eq in frames) if frames else "Ninguno"))
        await ctx.send(embed=info_embed("✨ Tu colección", "\n".join(lines)))

async def setup(bot): await bot.add_cog(Community(bot))
