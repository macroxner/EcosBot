import asyncio

import discord
from discord.ext import commands, tasks
import database
import config
from utils.logger import send_log
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from utils.embeds import (
    success_embed,
    error_embed,
    warning_embed,
    info_embed,
)

activity_messages = {}

ROLES_ORDER = [
    "Tanque",
    "Offtank",
    "Main Healer",
    "Shadowcaller supp",
    "Falce",
    "Falce",
    "Falce",
    "Falce Daga",
    "Falce Daga",
    "Falce Daga",
    "Scout"
]


ROLE_ALIASES = {
    "Offtank": ["offtank", "off tank", "off-tank"],
    "Scout": ["scout"],
    "Falce Daga": ["falce daga", "daga"],
    "Falce": ["falce", "scythe"],
    "Main Healer": ["main healer", "mh", "healer", "heal"],
    "Shadowcaller supp": ["shadowcaller", "shadow caller", "sc"],
    "Tanque": ["tank", "tanque"],
}


def normalize_role(text):
    text = text.lower().strip()

    if text.startswith("signoff"):
        return "Signoff"

    if "fill" in text:
        return "Fill"

    for role, aliases in ROLE_ALIASES.items():
        for alias in aliases:
            if alias in text:
                return role

    return None


def parse_fill_avoid(text):
    text = text.lower().strip()
    avoid = []

    if "menos" not in text:
        return avoid

    avoid_text = text.split("menos", 1)[1].strip()

    for role, aliases in ROLE_ALIASES.items():
        for alias in aliases:
            if alias in avoid_text:
                if role not in avoid:
                    avoid.append(role)

    return avoid


def get_user_slot(activity, user_id):
    for slot in activity["slots"]:
        if slot["user"] and slot["user"].id == user_id:
            return slot

    return None


def get_user_fill(activity, user_id):
    for fill in activity["fill_queue"]:
        if fill["user"].id == user_id:
            return fill

    return None


def is_user_in_activity(activity, user_id):
    return get_user_slot(activity, user_id) is not None or get_user_fill(activity, user_id) is not None


def clear_fill_assignments(activity):
    fill_ids = [fill["user"].id for fill in activity["fill_queue"]]

    for slot in activity["slots"]:
        if slot["user"] and slot["user"].id in fill_ids:
            slot["user"] = None
            slot["filled_by_fill"] = False


def rebuild_fill_assignments(activity):
    clear_fill_assignments(activity)

    for fill in activity["fill_queue"]:
        user = fill["user"]
        avoid = fill["avoid"]

        for slot in activity["slots"]:
            if slot["user"] is None and slot["role"] not in avoid and slot["role"] != "Tanque":
                slot["user"] = user
                slot["filled_by_fill"] = True
                fill["assigned_role"] = slot["role"]
                break
        else:
            fill["assigned_role"] = None


def add_user_to_activity(activity, user, role_requested, message_content):
    if is_user_in_activity(activity, user.id):
        return False, "already_registered"

    if role_requested == "Fill":
        avoid = parse_fill_avoid(message_content)

        activity["fill_queue"].append({
            "user": user,
            "avoid": avoid,
            "assigned_role": None
        })

        rebuild_fill_assignments(activity)
        return True, "fill_added"

    for slot in activity["slots"]:
        if (
            slot["role"] == role_requested
            and slot["user"] is None
        ):
            slot["user"] = user
            slot["filled_by_fill"] = False

            # Recoloca los fills que sigan esperando
            rebuild_fill_assignments(activity)

            return True, "role_added"

    for slot in activity["slots"]:
        if (
            slot["role"] == role_requested
            and slot["user"] is not None
            and slot.get("filled_by_fill", False)
        ):
            # El Fill no se elimina de fill_queue.
            # Simplemente se sustituye por la persona del rol fijo.
            slot["user"] = user
            slot["filled_by_fill"] = False

            # El Fill desplazado intentará entrar automáticamente en otro rol
            rebuild_fill_assignments(activity)

            return True, "role_added_replacing_fill"

    return False, "role_full"


def remove_user_from_activity(activity, user):
    removed = False

    for slot in activity["slots"]:
        if slot["user"] and slot["user"].id == user.id:
            slot["user"] = None
            slot["filled_by_fill"] = False
            removed = True

    for fill in list(activity["fill_queue"]):
        if fill["user"].id == user.id:
            activity["fill_queue"].remove(fill)
            removed = True

    if removed:
        rebuild_fill_assignments(activity)

    return removed


def format_fill_queue(activity):
    if not activity["fill_queue"]:
        return []

    lines = [
        "",
        "🟨 **Fill / Reserva**"
    ]

    for fill in activity["fill_queue"]:
        user = fill["user"]
        avoid = fill["avoid"]
        assigned = fill.get("assigned_role")

        text = f"- {user.mention}"

        if avoid:
            text += f" | menos: {', '.join(avoid)}"

        if assigned:
            text += f" | asignado: **{assigned}**"
        else:
            text += " | esperando hueco"

        lines.append(text)

    return lines


def render_activity_message(activity):
    creator = activity["creator"]

    lines = [
        f"**{activity['tier']} {activity['fecha']} {activity['hora_inicio']} - {activity['hora_fin']} {creator.display_name}**",
        "",
        f"Hora: {activity['hora_inicio']} - {activity['hora_fin']} España",
        f"Fecha: {activity['fecha']}",
        f"Maseo: {activity['maseo']}",
        "",
        "HEALER | SWAP arma 6.4 / 7.3 | offhand 7.3",
        "FALCES: | 6.4 2 stats (10% daño mínimo) || 7.4 (1 stat)",
        "COMIDA | tortilla 7.1 |",
        "POCIONES | SC acido t3 60-100 | Falce energia t4 40",
        ""
    ]

    for slot in activity["slots"]:
        if slot["user"]:
            if slot.get("filled_by_fill"):
                lines.append(f"{slot['role']} : {slot['user'].mention} *(fill)*")
            else:
                lines.append(f"{slot['role']} : {slot['user'].mention}")
        else:
            lines.append(f"{slot['role']} :")

    lines += format_fill_queue(activity)

    lines += [
        "",
        "<@&1332749148000227369> <@&1338207294579539991>",
        f"/join {creator.display_name}",
        "",
        "OBLIGATORIO #forcecityoverload true"
    ]

    return "\n".join(lines)


class CalendarView(discord.ui.View):
    def __init__(self, ctx, avas):
        super().__init__(timeout=180)
        self.ctx = ctx
        self.avas = avas
        self.page = 0
        self.page_size = 5

    def build_embed(self):
        total_pages = max(1, (len(self.avas) + self.page_size - 1) // self.page_size)

        embed = discord.Embed(
            title="📅 Próximas Avalonianas",
            description=f"Página {self.page + 1}/{total_pages}",
            color=discord.Color.blue()
        )

        start = self.page * self.page_size
        end = start + self.page_size

        for tier, date, start_time, end_time, maseo, creator_id, thread_id in self.avas[start:end]:
            caller = self.ctx.guild.get_member(creator_id)
            caller_name = caller.display_name if caller else "Desconocido"

            embed.add_field(
                name=f"⚔️ {tier} | {date}",
                value=(
                    f"🕒 **{start_time} - {end_time}**\n"
                    f"👤 Caller: **{caller_name}**\n"
                    f"📍 Maseo: **{maseo}**\n"
                    f"🧵 <#{thread_id}>"
                ),
                inline=False
            )

        return embed

    async def update(self, interaction):
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message(
                "❌ Este calendario no es tuyo.",
                ephemeral=True
            )
            return

        await interaction.response.edit_message(
            embed=self.build_embed(),
            view=self
        )

    @discord.ui.button(label="⬅️ Anterior", style=discord.ButtonStyle.secondary)
    async def previous(self, interaction, button):
        if self.page > 0:
            self.page -= 1

        await self.update(interaction)

    @discord.ui.button(label="➡️ Siguiente", style=discord.ButtonStyle.secondary)
    async def next(self, interaction, button):
        total_pages = max(1, (len(self.avas) + self.page_size - 1) // self.page_size)

        if self.page < total_pages - 1:
            self.page += 1

        await self.update(interaction)


class Activities(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.restore_lock = asyncio.Lock()
        self.activities_restored = False
        self.restore_task = None

        self.reminder_loop.start()
        self.fame_finish_loop.start()
        self.auto_calendar_loop.start()
        self.inactive_loop.start()

    async def cog_load(self):
        self.restore_task = asyncio.create_task(
            self.restore_activities_after_ready()
        )

    async def restore_activities_after_ready(self):
        await self.bot.wait_until_ready()

        try:
            await self.restore_active_activities()
        except Exception as error:
            print(
                "Error restaurando actividades: "
                f"{type(error).__name__}: {error}"
            )

    def cog_unload(self):
        self.reminder_loop.cancel()
        self.fame_finish_loop.cancel()
        self.auto_calendar_loop.cancel()
        self.inactive_loop.cancel()

        if self.restore_task:
            self.restore_task.cancel()

    async def get_member_safe(self, guild, user_id):
        member = guild.get_member(int(user_id))

        if member is not None:
            return member

        try:
            return await guild.fetch_member(int(user_id))
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            return None

    async def get_channel_safe(self, channel_id):
        channel = self.bot.get_channel(int(channel_id))

        if channel is not None:
            return channel

        try:
            return await self.bot.fetch_channel(int(channel_id))
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            return None

    async def build_restored_activity(self, row):
        (
            message_id,
            thread_id,
            channel_id,
            creator_id,
            tier,
            fecha,
            hora_inicio,
            hora_fin,
            maseo,
        ) = row

        thread = await self.get_channel_safe(thread_id)
        channel = await self.get_channel_safe(channel_id)

        if thread is None or channel is None:
            return None

        guild = thread.guild
        creator = await self.get_member_safe(guild, creator_id)

        if creator is None:
            return None

        try:
            main_message = await channel.fetch_message(int(message_id))
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            return None

        slots = [
            {
                "role": role,
                "user": None,
                "filled_by_fill": False,
            }
            for role in ROLES_ORDER
        ]

        fill_queue = []

        participants = database.get_scheduled_ava_participants_for_restore(
            message_id
        )

        for participant in participants:
            user_id, role, avoid_roles = participant
            member = await self.get_member_safe(guild, user_id)

            if member is None:
                continue

            if role == "Fill":
                avoid = [
                    item.strip()
                    for item in (avoid_roles or "").split(",")
                    if item.strip()
                ]

                fill_queue.append({
                    "user": member,
                    "avoid": avoid,
                    "assigned_role": None,
                })
                continue

            for slot in slots:
                if slot["role"] == role and slot["user"] is None:
                    slot["user"] = member
                    slot["filled_by_fill"] = False
                    break

        # Compatibilidad con actividades antiguas en las que el tanque
        # no estuviera guardado correctamente en participantes.
        if not any(
            slot["role"] == "Tanque" and slot["user"] is not None
            for slot in slots
        ):
            for slot in slots:
                if slot["role"] == "Tanque":
                    slot["user"] = creator
                    break

        activity = {
            "creator": creator,
            "tier": tier,
            "fecha": fecha,
            "hora_inicio": hora_inicio,
            "hora_fin": hora_fin,
            "maseo": maseo,
            "slots": slots,
            "fill_queue": fill_queue,
        }

        rebuild_fill_assignments(activity)

        return {
            "thread_id": int(thread_id),
            "message": main_message,
            "activity": activity,
            "message_id": int(message_id),
        }

    async def restore_active_activities(self):
        async with self.restore_lock:
            rows = database.get_active_avas_for_restore()
            restored = 0

            for row in rows:
                data = await self.build_restored_activity(row)

                if data is None:
                    continue

                activity_messages[data["thread_id"]] = {
                    "message": data["message"],
                    "activity": data["activity"],
                    "message_id": data["message_id"],
                }

                restored += 1

            self.activities_restored = True
            print(
                f"Actividades restauradas tras iniciar el bot: {restored}"
            )

    async def restore_activity_by_thread(self, thread_id):
        """
        Segunda protección: si un hilo no está en RAM, intenta recuperarlo
        directamente desde SQLite al recibir un mensaje.
        """
        async with self.restore_lock:
            if int(thread_id) in activity_messages:
                return True

            row = database.get_scheduled_ava_by_thread(thread_id)

            if row is None:
                return False

            data = await self.build_restored_activity(row)

            if data is None:
                return False

            activity_messages[data["thread_id"]] = {
                "message": data["message"],
                "activity": data["activity"],
                "message_id": data["message_id"],
            }

            print(
                f"Actividad del hilo {thread_id} restaurada bajo demanda."
            )
            return True

    @tasks.loop(minutes=1)
    async def fame_finish_loop(self):
        fame_cog = self.bot.get_cog("FameTracker")

        if not fame_cog:
            return

        finished_avas = database.get_finished_avas_without_fame()

        for (ava_message_id,) in finished_avas:
            participants = database.get_scheduled_ava_participants(ava_message_id)

            if not participants:
                database.mark_ava_fame_processed(ava_message_id)
                continue

            user_ids = [user_id for user_id, role in participants]

            guild = self.bot.guilds[0]

            await fame_cog.process_ava_fame_end(
                guild,
                ava_message_id,
                user_ids
            )

            database.mark_ava_fame_processed(ava_message_id)

    @commands.command(name="calendar")
    async def calendar(self, ctx):
        database.delete_finished_avas()

        avas = database.get_calendar_avas(50)

        if not avas:
            await ctx.send(
                embed=info_embed(
                    "Calendario",
                    "No hay Avalonianas programadas."
                )
            )
            return

        view = CalendarView(ctx, avas)
        await ctx.send(embed=view.build_embed(), view=view)

    @commands.command()
    async def ava(self, ctx, tier: str, fecha: str, hora_inicio: str, hora_fin: str, *, maseo: str):
        creator = ctx.author

        slots = []

        for role in ROLES_ORDER:
            if role == "Tanque":
                slots.append({
                    "role": role,
                    "user": creator,
                    "filled_by_fill": False
                })
            else:
                slots.append({
                    "role": role,
                    "user": None,
                    "filled_by_fill": False
                })

        activity = {
            "creator": creator,
            "tier": tier,
            "fecha": fecha,
            "hora_inicio": hora_inicio,
            "hora_fin": hora_fin,
            "maseo": maseo,
            "slots": slots,
            "fill_queue": []
        }

        msg = await ctx.send(render_activity_message(activity))

        fame_cog = self.bot.get_cog("FameTracker")

        if fame_cog:
            await fame_cog.snapshot_all_registered_start(msg.id)

        thread = await msg.create_thread(
            name=f"Avaloniana {tier} - {fecha} {hora_inicio}",
            auto_archive_duration=1440
        )

        database.add_scheduled_ava(
            msg.id,
            thread.id,
            ctx.channel.id,
            creator.id,
            tier,
            fecha,
            hora_inicio,
            hora_fin,
            maseo
        )

        database.add_scheduled_ava_participant(msg.id, creator.id, "Tanque")

        activity_messages[thread.id] = {
            "message": msg,
            "activity": activity,
            "message_id": msg.id
        }

        await thread.send(
            "Escribid aquí cosas como:\n"
            "`x falce`, `x healer`, `x mh`, `x scout`, `x offtank`\n\n"
            "Para fill:\n"
            "`x fill`\n"
            "`x fill menos scout`\n"
            "`x fill menos sc`\n"
            "`x fill menos healer`\n\n"
            "Para borrarte de la lista escribe: `signoff`\n"
            "Para borrar a otra persona escribe: `signoff @usuario`"
        )

        await send_log(
            self.bot,
            "📢 Avaloniana creada",
            f"Caller: {creator.mention}\n"
            f"Tier: {tier}\n"
            f"Fecha: {fecha}\n"
            f"Hora: {hora_inicio} - {hora_fin}\n"
            f"Maseo: {maseo}",
            discord.Color.blue()
        )

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        if message.channel.id not in activity_messages:
            restored = await self.restore_activity_by_thread(
                message.channel.id
            )

            if not restored:
                return

        data = activity_messages[message.channel.id]
        activity = data["activity"]
        main_message = data["message"]

        role = normalize_role(message.content)

        if role == "Signoff":
            target_user = message.author

            if message.mentions:
                target_user = message.mentions[0]

            success = remove_user_from_activity(activity, target_user)

            if success:
                database.remove_scheduled_ava_participant(
                    data["message_id"],
                    target_user.id
                )

                await main_message.edit(content=render_activity_message(activity))
                await message.add_reaction("✅")
            else:
                await message.add_reaction("❌")

        elif role:
            success, reason = add_user_to_activity(
                activity,
                message.author,
                role,
                message.content
            )

            if success:
                avoid_roles = ""

                if role == "Fill":
                    avoid_roles = ",".join(
                        parse_fill_avoid(message.content)
                    )

                database.add_scheduled_ava_participant(
                    data["message_id"],
                    message.author.id,
                    role,
                    avoid_roles
                )

                await main_message.edit(content=render_activity_message(activity))
                await message.add_reaction("✅")

            else:
                if reason == "already_registered":
                    existing_slot = get_user_slot(activity, message.author.id)
                    existing_fill = get_user_fill(activity, message.author.id)

                    if existing_slot:
                        await message.channel.send(
                            embed=error_embed(
                                f"{message.author.mention}, ya estás apuntado como **{existing_slot['role']}**. "
                                f"Usa `signoff` antes de cambiar de rol."
                            )
                        )
                    elif existing_fill:
                        await message.channel.send(
                            embed=error_embed(
                                f"{message.author.mention}, ya estás apuntado como **Fill**."
                                f"Usa `signoff` antes de cambiar."
                            )
                        )

                elif reason == "role_full":
                    await message.channel.send(
                        embed=error_embed(
                            f"{message.author.mention}, ese rol ya está lleno.",
                            "Rol completo"
                        )
                    )

                await message.add_reaction("❌")

    def build_auto_calendar_embed(self, guild, avas):
        embed = discord.Embed(
            title="📅 Calendario de Avalonianas",
            description="Actualizado automáticamente cada 10 minutos.",
            color=discord.Color.blue()
        )

        if not avas:
            embed.description = "📅 No hay Avalonianas programadas."
            return embed

        for tier, date, start_time, end_time, maseo, creator_id, thread_id in avas[:10]:
            caller = guild.get_member(creator_id)
            caller_name = caller.display_name if caller else "Desconocido"

            embed.add_field(
                name=f"⚔️ {tier} | {date}",
                value=(
                    f"🕒 **{start_time} - {end_time}**\n"
                    f"👤 Caller: **{caller_name}**\n"
                    f"📍 Maseo: **{maseo}**\n"
                    f"🧵 <#{thread_id}>"
                ),
                inline=False
            )

        embed.set_footer(text="EcosBot · Calendario automático")
        return embed


    async def update_auto_calendar_message(self):
        channel = self.bot.get_channel(config.CALENDAR_CHANNEL)

        if not channel:
            return

        database.delete_finished_avas()
        avas = database.get_calendar_avas(50)

        guild = channel.guild
        embed = self.build_auto_calendar_embed(guild, avas)

        message_id = database.get_setting("calendar_message_id")

        if message_id:
            try:
                msg = await channel.fetch_message(int(message_id))
                await msg.edit(embed=embed)
                return
            except:
                pass

        msg = await channel.send(embed=embed)
        database.set_setting("calendar_message_id", msg.id)


    def build_inactive_embed(self, guild, inactive_users):
        embed = discord.Embed(
            title="⚠️ Usuarios inactivos 14 días",
            description="Usuarios registrados que no aparecen en ninguna Avaloniana reciente.",
            color=discord.Color.orange()
        )

        if not inactive_users:
            embed.description = "✅ No hay usuarios inactivos ahora mismo."
            return embed

        lines = []

        for discord_id, albion_name, last_ava in inactive_users[:30]:
            member = guild.get_member(discord_id)
            name = member.display_name if member else albion_name

            if last_ava:
                lines.append(f"• **{name}** — última ava: `{last_ava}`")
            else:
                lines.append(f"• **{name}** — nunca se ha apuntado")

        embed.description = "\n".join(lines)
        embed.set_footer(text="EcosBot · Control de actividad")
        return embed


    async def update_inactive_message(self):
        channel = self.bot.get_channel(config.INACTIVE_CHANNEL)

        if not channel:
            return

        inactive_users = database.get_inactive_registered_players(14)

        guild = channel.guild
        embed = self.build_inactive_embed(guild, inactive_users)

        message_id = database.get_setting("inactive_message_id")

        if message_id:
            try:
                msg = await channel.fetch_message(int(message_id))
                await msg.edit(embed=embed)
                return
            except:
                pass

        msg = await channel.send(embed=embed)
        database.set_setting("inactive_message_id", msg.id)


    @tasks.loop(minutes=10)
    async def auto_calendar_loop(self):
        await self.update_auto_calendar_message()


    @tasks.loop(hours=6)
    async def inactive_loop(self):
        await self.update_inactive_message()

@tasks.loop(minutes=1)
async def reminder_loop(self):
    madrid_tz = ZoneInfo("Europe/Madrid")
    now = datetime.now(madrid_tz)

    avas = database.get_pending_ava_reminders()

    for (
        ava_id,
        thread_id,
        creator_id,
        tier,
        date,
        start_time,
        end_time,
        maseo
    ) in avas:

        try:
            ava_datetime = datetime.strptime(
                f"{date} {start_time}",
                "%d/%m/%Y %H:%M"
            )

            # La hora introducida en !ava siempre se interpreta
            # como hora española.
            ava_datetime = ava_datetime.replace(
                tzinfo=madrid_tz
            )

        except ValueError:
            print(
                f"Fecha/hora inválida en AVA {ava_id}: "
                f"{date} {start_time}"
            )
            continue

        reminder_time = ava_datetime - timedelta(
            minutes=15
        )

        # Solo manda el recordatorio si estamos entre
        # 15 minutos antes y la hora de inicio.
        #
        # Esto evita que una ava antigua mande el aviso tarde
        # después de un reinicio del bot.
        if reminder_time <= now < ava_datetime:
            thread = self.bot.get_channel(thread_id)

            if thread is None:
                try:
                    thread = await self.bot.fetch_channel(
                        thread_id
                    )
                except (
                    discord.NotFound,
                    discord.Forbidden,
                    discord.HTTPException
                ):
                    thread = None

            if thread:
                embed = warning_embed(
                    "Avaloniana en 15 minutos",
                    (
                        "⏰ **Recordatorio de Avaloniana**\n\n"
                        f"Tier: **{tier}**\n"
                        f"Hora: **{start_time} - {end_time}**\n"
                        f"Maseo: **{maseo}**\n"
                        f"Caller: <@{creator_id}>"
                    )
                )

                await thread.send(embed=embed)

            database.mark_ava_reminder_sent(
                ava_id
            )


async def setup(bot):
    await bot.add_cog(Activities(bot))