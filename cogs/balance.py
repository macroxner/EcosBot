import discord
from discord.ext import commands
import database
import utils.Verificator as Verificator


class Balance(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def bal(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        balance, ecoins = database.get_user(member.id)

        await ctx.send(
            f"💰 Balance de {member.mention}\n"
            f"Balance: {balance}\n"
            f"Ecoins: {ecoins}"
        )
        
    @commands.command()
    @commands.check(Verificator.usuario_puede_ejecutar_comando)
    async def addbal(self, ctx, member: discord.Member, amount: int):
        database.add_balance(member.id, amount)
        await ctx.send(f"✅ Sumados {amount} al balance de {member.mention}")


    

    @commands.command()
    @commands.check(Verificator.usuario_puede_ejecutar_comando)
    async def removebal(self, ctx, member: discord.Member, amount: int):
        database.add_balance(member.id, -amount)
        await ctx.send(f"❌ Restados {amount} al balance de {member.mention}")

    @commands.command()
    @commands.check(Verificator.usuario_puede_ejecutar_comando)
    async def resetbal(self, ctx, member: discord.Member):
        database.reset_balance(member.id)
        await ctx.send(f"🧹 Balance de {member.mention} reiniciado a 0")

    @commands.command()
    @commands.check(Verificator.usuario_puede_ejecutar_comando)
    async def addrolebal(self, ctx, role: discord.Role, amount: int):
        count = 0

        for member in role.members:
            if not member.bot:
                database.add_balance(member.id, amount)
                count += 1

        await ctx.send(
            f"✅ Sumados {amount} de balance a {count} miembros con el rol {role.name}"
        )
    
    @addrolebal.error
    @resetbal.error
    @removebal.error
    @addbal.error
    async def error_permisos(clase, contexto:commands.Context, error):
        await contexto.send(error)


async def setup(bot):
    await bot.add_cog(Balance(bot))