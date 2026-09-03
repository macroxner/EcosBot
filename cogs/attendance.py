import discord
from discord.ext import commands
import database
import utils.Verificator as Verificator
from utils.embeds import success_embed, error_embed, info_embed


class Attendance(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @staticmethod
    def parse_user_id(raw: str):
        value = raw.strip()
        if value.startswith('<@') and value.endswith('>'):
            value = value[2:-1]
            if value.startswith('!'):
                value = value[1:]
        return int(value) if value.isdigit() else None

    @staticmethod
    def normalize_type(raw: str):
        value = raw.lower().strip()
        if value in ('ava', 'avas', 'avaloniana', 'avalonianas'):
            return 'ava'
        if value in ('dragon', 'dragones', 'dragón', 'dragónes'):
            return 'dragon'
        return None

    @commands.command(name='attendance', aliases=['asistencia', 'editattendance'])
    @commands.check(Verificator.usuario_puede_ejecutar_comando)
    async def attendance(self, ctx, activity_type: str, user: str, amount: int):
        """
        Ajusta manualmente asistencias.
        Ejemplos:
        ?attendance ava @usuario 1
        ?attendance ava 123456789012345678 -1
        ?attendance dragon @usuario 3
        """
        kind = self.normalize_type(activity_type)
        if not kind:
            await ctx.send(embed=error_embed(
                'El tipo debe ser `ava` o `dragon`.\n\n'
                'Ejemplos:\n'
                '`?attendance ava @usuario 1`\n'
                '`?attendance dragon @usuario -1`'
            ))
            return

        user_id = self.parse_user_id(user)
        if user_id is None:
            await ctx.send(embed=error_embed(
                'No he podido interpretar el usuario. Usa una mención o su ID de Discord.'
            ))
            return

        if amount == 0:
            await ctx.send(embed=error_embed('La cantidad no puede ser `0`.'))
            return

        if abs(amount) > 100:
            await ctx.send(embed=error_embed(
                'Por seguridad, solo puedes modificar hasta 100 asistencias de una vez.'
            ))
            return

        before = database.get_manual_attendance_total(kind, user_id)
        changed = database.adjust_attendance(kind, user_id, amount)
        after = database.get_manual_attendance_total(kind, user_id)

        member = ctx.guild.get_member(user_id) if ctx.guild else None
        display = member.mention if member else f'`{user_id}`'
        label = 'Avalonianas' if kind == 'ava' else 'Dragones'

        if amount < 0 and changed == 0:
            await ctx.send(embed=info_embed(
                'Sin cambios',
                f'{display} no tiene asistencias de **{label}** que se puedan eliminar.'
            ))
            return

        sign = '+' if amount > 0 else ''
        embed = success_embed(
            'Asistencia actualizada',
            f'👤 **Usuario:** {display}\n'
            f'🎯 **Actividad:** {label}\n'
            f'✏️ **Cambio solicitado:** `{sign}{amount}`\n'
            f'✅ **Cambio aplicado:** `{changed:+d}`\n\n'
            f'📊 **Antes:** `{before}`\n'
            f'📊 **Ahora:** `{after}`'
        )
        await ctx.send(embed=embed)

        achievements = self.bot.get_cog('Achievements')
        if achievements and ctx.guild:
            await achievements.check_user_achievements(ctx.guild, user_id)

    @attendance.error
    async def attendance_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(embed=error_embed(
                'Faltan argumentos.\n\n'
                '`?attendance ava @usuario 1`\n'
                '`?attendance dragon @usuario -1`\n\n'
                'También puedes usar el ID de Discord si la persona ya no está en el servidor.'
            ))
            return
        if isinstance(error, commands.BadArgument):
            await ctx.send(embed=error_embed(
                'La cantidad debe ser un número entero, por ejemplo `1`, `-1` o `5`.'
            ))
            return
        if isinstance(error, commands.CheckFailure):
            await ctx.send(embed=error_embed('No tienes permisos para editar asistencias.'))
            return
        await ctx.send(embed=error_embed(str(error)))


async def setup(bot):
    await bot.add_cog(Attendance(bot))
