import os
import discord
from discord.ext import commands

import database
from utils.embeds import error_embed, info_embed, success_embed, economy_embed
from utils.logger import send_log


SOUNDS = {
    "horn": {"name": "📯 War Horn", "price": 40, "file": "assets/sounds/horn.mp3"},
    "bruh": {"name": "🗿 Bruh", "price": 25, "file": "assets/sounds/bruh.mp3"},
    "victory": {"name": "🏆 Victory", "price": 50, "file": "assets/sounds/victory.mp3"},
    "wipe": {"name": "💀 Wipe", "price": 35, "file": "assets/sounds/wipe.mp3"},
    "bonk": {"name": "🔨 Bonk", "price": 30, "file": "assets/sounds/bonk.mp3"},
}

RADIOS = {
    "epic": "https://stream.zeno.fm/9sry2k5k4ehvv",
    "lofi": "https://stream.zeno.fm/0r0xa792kwzuv",
}


async def connect_to_user_voice(ctx):
    if not ctx.author.voice:
        await ctx.send(embed=error_embed("Tienes que estar en un canal de voz."))
        return None
    channel = ctx.author.voice.channel
    if ctx.voice_client:
        if ctx.voice_client.channel != channel:
            await ctx.voice_client.move_to(channel)
        return ctx.voice_client
    return await channel.connect()


class Audio(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="soundshop")
    async def soundshop(self, ctx):
        embed = discord.Embed(title="🔊 Tienda de sonidos", color=discord.Color.purple())
        for key, sound in SOUNDS.items():
            embed.add_field(name=sound["name"], value=f"Clave: `{key}`\nPrecio: **{sound['price']} Ecoins**", inline=True)
        embed.description = "Compra con `?buysound horn` · Usa con `?sound horn`."
        embed.set_footer(text="EcosBot · Sonidos")
        await ctx.send(embed=embed)

    @commands.command(name="buysound")
    async def buysound(self, ctx, sound_key: str):
        sound_key = sound_key.lower()
        if sound_key not in SOUNDS:
            await ctx.send(embed=error_embed("Ese sonido no existe."))
            return
        if database.has_sound(ctx.author.id, sound_key):
            await ctx.send(embed=error_embed("Ya tienes ese sonido comprado."))
            return

        price = SOUNDS[sound_key]["price"]
        _, ecoins = database.get_user(ctx.author.id)
        if ecoins < price:
            await ctx.send(embed=error_embed(f"Necesitas **{price} Ecoins** y tienes **{ecoins}**."))
            return

        database.add_ecoins(ctx.author.id, -price, f"Compra sonido: {sound_key}")
        database.unlock_sound(ctx.author.id, sound_key)
        await ctx.send(embed=success_embed("Sonido comprado", f"Has comprado **{SOUNDS[sound_key]['name']}** por **{price} Ecoins**."))
        await send_log(self.bot, "🔊 Sonido comprado", f"Usuario: {ctx.author.mention}\nSonido: {SOUNDS[sound_key]['name']}\nCoste: {price} Ecoins", discord.Color.purple())

    @commands.command(name="mysounds")
    async def mysounds(self, ctx):
        sounds = database.get_user_sounds(ctx.author.id)
        if not sounds:
            await ctx.send(embed=info_embed("Tus sonidos", "No tienes sonidos comprados."))
            return
        embed = discord.Embed(title=f"🔊 Sonidos de {ctx.author.display_name}", color=discord.Color.purple())
        embed.description = "\n".join(f"• `{key}` — {SOUNDS[key]['name']}" for key in sounds if key in SOUNDS)
        embed.set_footer(text="EcosBot · Sonidos")
        await ctx.send(embed=embed)

    @commands.command(name="sound")
    async def sound(self, ctx, sound_key: str):
        sound_key = sound_key.lower()
        if sound_key not in SOUNDS:
            await ctx.send(embed=error_embed("Ese sonido no existe."))
            return
        if not database.has_sound(ctx.author.id, sound_key):
            await ctx.send(embed=error_embed("No tienes ese sonido comprado."))
            return

        path = SOUNDS[sound_key]["file"]
        if not os.path.exists(path):
            await ctx.send(embed=error_embed(f"No encuentro el archivo `{path}`."))
            return

        voice = await connect_to_user_voice(ctx)
        if voice is None:
            return
        if voice.is_playing():
            voice.stop()
        voice.play(discord.FFmpegPCMAudio(path))
        await ctx.send(embed=info_embed("Reproduciendo sonido", SOUNDS[sound_key]["name"]))

    @commands.command(name="radio")
    async def radio(self, ctx, station: str = "epic"):
        station = station.lower()
        if station not in RADIOS:
            await ctx.send(embed=error_embed("Radio no encontrada. Usa: " + ", ".join(f"`{x}`" for x in RADIOS)))
            return
        voice = await connect_to_user_voice(ctx)
        if voice is None:
            return
        if voice.is_playing():
            voice.stop()
        voice.play(discord.FFmpegPCMAudio(RADIOS[station]))
        await ctx.send(embed=info_embed("Radio", f"📻 Reproduciendo **{station}**."))

    @commands.command(name="stop")
    async def stop(self, ctx):
        if ctx.voice_client and ctx.voice_client.is_playing():
            ctx.voice_client.stop()
            await ctx.send(embed=success_embed("Audio detenido", "La reproducción se ha detenido."))
        else:
            await ctx.send(embed=error_embed("No estoy reproduciendo nada."))

    @commands.command(name="leave")
    async def leave(self, ctx):
        if ctx.voice_client:
            await ctx.voice_client.disconnect()
            await ctx.send(embed=success_embed("Desconectado", "He salido del canal de voz."))
        else:
            await ctx.send(embed=error_embed("No estoy en ningún canal de voz."))


async def setup(bot):
    await bot.add_cog(Audio(bot))
