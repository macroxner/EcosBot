import asyncio
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from pathlib import Path

import discord
from discord.ext import commands, tasks

import database
import config
from utils.embeds import error_embed, info_embed, success_embed, warning_embed
from utils.logger import send_log


dragon_messages = {}

MADRID_TZ = ZoneInfo("Europe/Madrid")

DRAGON_SLOTS = [
    {"label": "Main Tank", "group": "Main Tank"},
    {"label": "Offtank 1", "group": "Offtank"},
    {"label": "Offtank 2", "group": "Offtank"},
    {"label": "Main Healer", "group": "Main Healer"},
    {"label": "Healer Party 1 · 1", "group": "Healer Party 1"},
    {"label": "Healer Party 1 · 2", "group": "Healer Party 1"},
    {"label": "Healer Party 2 · 1", "group": "Healer Party 2"},
    {"label": "Healer Party 2 · 2", "group": "Healer Party 2"},
    {"label": "Invocador Oscuro", "group": "Invocador Oscuro"},
    {"label": "Enigmático 1", "group": "Enigmático"},
    {"label": "Enigmático 2", "group": "Enigmático"},
    {"label": "DPS 1", "group": "DPS"},
    {"label": "DPS 2", "group": "DPS"},
    {"label": "DPS 3", "group": "DPS"},
    {"label": "DPS 4", "group": "DPS"},
    {"label": "DPS 5", "group": "DPS"},
    {"label": "DPS 6", "group": "DPS"},
    {"label": "DPS 7", "group": "DPS"},
    {"label": "DPS 8", "group": "DPS"},
    {"label": "DPS 9", "group": "DPS"},
]

DRAGON_PING_IDS = [
    1338207294579539991,
    1332749148000227369,
    1540712364452610178,
]

# El orden importa: los alias específicos se comprueban antes que los genéricos.
ROLE_ALIASES = [
    ("Healer Party 1", ["healer party 1", "healer party1", "caido", "caído"]),
    ("Healer Party 2", ["healer party 2", "healer party2", "redencion", "redención"]),
    ("Main Healer", ["main healer", "mh", "baston sagrado", "bastón sagrado"]),
    ("Invocador Oscuro", ["invocador oscuro", "shadow caller", "shadowcaller", "shadow", "sc"]),
    ("Enigmático", ["enigmatico", "enigmático", "enigmatic"]),
    ("Offtank", ["offtank", "off tank", "off", "ot", "maracas"]),
    ("Main Tank", ["main tank", "maintank", "tank", "tanque"]),
    ("DPS Ballesta", ["repetidora", "wailing", "wailling", "ballesta"]),
    ("DPS Flami", ["flamigero", "flamígero", "flaming", "flami", "fuego", "fire"]),
    ("DPS Pajaro", ["lightcaller", "light caller", "invocador de luz", "pajaro", "pájaro", "lc"]),
]

DPS_GROUPS = {"DPS"}
HEALER_PARTY_GROUPS = {"Healer Party 1", "Healer Party 2"}



def clean_message_text(text: str) -> str:
    return " ".join(text.lower().strip().split())


def build_dragon_ping_text(guild):
    """Devuelve menciones válidas tanto si los IDs son roles como usuarios."""
    mentions = []

    for target_id in DRAGON_PING_IDS:
        role = guild.get_role(target_id)
        if role is not None:
            mentions.append(role.mention)
            continue

        member = guild.get_member(target_id)
        if member is not None:
            mentions.append(member.mention)
            continue

        # Si no está en caché, lo dejamos como mención de usuario.
        mentions.append(f"<@{target_id}>")

    return " ".join(mentions)


def normalize_role(text):
    text = clean_message_text(text)

    if text.startswith("signoff"):
        return "Signoff"

    # Igual que en Avas: si no hay X, no se apunta a nadie.
    if not text.startswith("x"):
        return None

    if "fill" in text:
        return "Fill"

    for role, aliases in ROLE_ALIASES:
        for alias in aliases:
            if alias in text:
                return role

    # `x hp` ocupa el primer hueco libre entre Healer Party 1 y 2.
    words = text.replace("@", " ").split()
    if "hp" in words:
        return "HEALER_PARTY_ANY"

    # `x dps` ocupa cualquier hueco DPS libre.
    if "dps" in words:
        return "DPS_ANY"

    return None


def parse_fill_avoid(text):
    text = clean_message_text(text)
    if "menos" not in text:
        return set()

    avoid_text = text.split("menos", 1)[1]
    avoid = set()

    # Si escribe menos dps, excluimos todos los DPS.
    if "dps" in avoid_text:
        avoid.update(DPS_GROUPS)

    for role, aliases in ROLE_ALIASES:
        if any(alias in avoid_text for alias in aliases):
            avoid.add(role)

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


def role_matches(slot_group, requested_role):
    if requested_role in {"DPS_ANY", "DPS Ballesta", "DPS Flami", "DPS Pajaro"}:
        return slot_group == "DPS"
    if requested_role == "HEALER_PARTY_ANY":
        return slot_group in HEALER_PARTY_GROUPS
    return slot_group == requested_role


def signup_display_name(requested_role, slot):
    if requested_role == "DPS Ballesta":
        return "DPS Ballesta"
    if requested_role == "DPS Flami":
        return "DPS Flami"
    if requested_role == "DPS Pajaro":
        return "DPS Pajaro"
    if requested_role == "DPS_ANY":
        return "DPS"
    return slot["label"]


def clear_fill_assignments(activity):
    fill_ids = {fill["user"].id for fill in activity["fill_queue"]}
    for slot in activity["slots"]:
        if slot["user"] and slot["user"].id in fill_ids:
            slot["user"] = None
            slot["filled_by_fill"] = False
            slot["signup_role"] = None


def rebuild_fill_assignments(activity):
    clear_fill_assignments(activity)

    for fill in activity["fill_queue"]:
        fill["assigned_role"] = None
        avoid = fill["avoid"]

        for slot in activity["slots"]:
            if slot["user"] is not None:
                continue
            if slot["group"] in avoid:
                continue

            slot["user"] = fill["user"]
            slot["filled_by_fill"] = True
            slot["signup_role"] = slot["label"]
            fill["assigned_role"] = slot["label"]
            break


def add_user(activity, user, requested_role, message_content):
    if is_user_in_activity(activity, user.id):
        return False, "already_registered"

    if requested_role == "Fill":
        activity["fill_queue"].append({
            "user": user,
            "avoid": parse_fill_avoid(message_content),
            "assigned_role": None,
        })
        rebuild_fill_assignments(activity)
        return True, "fill_added"

    # Primero priorizamos un hueco totalmente libre.
    for slot in activity["slots"]:
        if role_matches(slot["group"], requested_role) and slot["user"] is None:
            slot["user"] = user
            slot["filled_by_fill"] = False
            slot["signup_role"] = signup_display_name(requested_role, slot)
            rebuild_fill_assignments(activity)
            return True, "role_added"

    # Si el hueco lo ocupa provisionalmente un Fill, el rol fijo tiene prioridad.
    for slot in activity["slots"]:
        if (
            role_matches(slot["group"], requested_role)
            and slot["user"] is not None
            and slot.get("filled_by_fill", False)
        ):
            slot["user"] = user
            slot["filled_by_fill"] = False
            slot["signup_role"] = signup_display_name(requested_role, slot)
            rebuild_fill_assignments(activity)
            return True, "role_added_replacing_fill"

    return False, "role_full"


def remove_user(activity, user):
    removed = False

    for slot in activity["slots"]:
        if slot["user"] and slot["user"].id == user.id:
            slot["user"] = None
            slot["filled_by_fill"] = False
            slot["signup_role"] = None
            removed = True

    for fill in list(activity["fill_queue"]):
        if fill["user"].id == user.id:
            activity["fill_queue"].remove(fill)
            removed = True

    if removed:
        rebuild_fill_assignments(activity)

    return removed


def madrid_to_utc(date_text, time_text):
    local_dt = datetime.strptime(
        f"{date_text} {time_text}",
        "%d/%m/%Y %H:%M"
    ).replace(tzinfo=MADRID_TZ)

    return local_dt.astimezone(timezone.utc).strftime("%H:%M")


def build_dragon_embed(activity):
    utc_start = madrid_to_utc(activity["fecha"], activity["hora_inicio"])
    utc_end = madrid_to_utc(activity["fecha"], activity["hora_fin"])

    embed = discord.Embed(
        title=f"🐉 DRAGONES · {activity['fecha']}",
        description=(
            f"📅 **{activity['fecha']}**\n"
            f"🕐 **{activity['hora_inicio']} ESP / {utc_start} UTC** "
            f"a **{activity['hora_fin']} ESP / {utc_end} UTC**"
        ),
        color=discord.Color.red(),
    )

    embed.add_field(
        name="⚔️ REQUISITOS DE EQUIPO",
        value=(
            "> 🗡️ **Armas:** `T6.4`\n"
            "> 🛡️ **Armadura:** `T6.3 mínimo`\n"
            "> 💚 **Healers:** `T6.4`\n\n"
            "🧰 **Build, comida, pociones y swaps listos antes de salir.**\n"
            "📸 Revisa la composición oficial fijada en el hilo."
        ),
        inline=False,
    )

    party_lines = []
    for index, slot in enumerate(activity["slots"], start=1):
        if slot["user"]:
            suffix = " *(Fill)*" if slot.get("filled_by_fill") else ""
            value = f"{slot['user'].mention}{suffix}"
        else:
            value = "`Libre`"
        display_label = slot.get("signup_role") or slot["label"]
        party_lines.append(f"**{index}. {display_label}** — {value}")

    # 20 líneas siguen estando dentro del límite del campo.
    embed.add_field(
        name="👥 Party",
        value="\n".join(party_lines),
        inline=False,
    )

    if activity["fill_queue"]:
        fill_lines = []
        for fill in activity["fill_queue"]:
            line = fill["user"].mention
            if fill["avoid"]:
                line += " · menos **" + ", ".join(sorted(fill["avoid"])) + "**"
            if fill.get("assigned_role"):
                line += f" · asignado a **{fill['assigned_role']}**"
            else:
                line += " · `Reserva`"
            fill_lines.append(line)

        embed.add_field(
            name="🟨 Fill / Reserva",
            value="\n".join(fill_lines),
            inline=False,
        )

    embed.set_footer(text="EcosBot · Es obligatorio escribir X para apuntarse")
    return embed


def build_help_embed():
    return info_embed(
        "🐉 Cómo apuntarse a Dragones",
        (
            "Escribe **siempre `x` delante** del rol. También puedes apuntar a otra persona "
            "añadiendo su mención al final.\n\n"
            "🛡️ **Frontline**\n"
            "`x main tank`\n"
            "`x offtank` · `x ot` · `x off` · `x maracas`\n\n"
            "💚 **Healers**\n"
            "`x main healer` · `x mh` · `x baston sagrado`\n"
            "`x healer party 1` · `x caido`\n"
            "`x healer party 2` · `x redencion`\n"
            "`x hp` → primer hueco libre de Healer Party\n\n"
            "🌑 **Support**\n"
            "`x invocador oscuro` · `x sc` · `x shadow`\n"
            "`x enigmatico` · `x enigmatic`\n\n"
            "⚔️ **DPS**\n"
            "`x dps` → cualquier hueco DPS libre\n"
            "`x ballesta` · `x repetidora` · `x wailing` → **DPS Ballesta**\n"
            "`x fuego` · `x fire` · `x flami` → **DPS Flami**\n"
            "`x lc` · `x lightcaller` · `x pajaro` → **DPS Pajaro**\n\n"
            "👥 Para apuntar a otro: `x dps @usuario`\n"
            "🟨 Fill: `x fill` / `x fill menos dps`\n"
            "🚪 Salir: `signoff` / `signoff @usuario`"
        ),
    )



class Dragons(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.restore_lock = asyncio.Lock()
        self.restore_task = None
        self.reminder_loop.start()
        self.finalize_loop.start()
        self.auto_calendar_loop.start()
        self.inactive_loop.start()

    async def cog_load(self):
        self.restore_task = asyncio.create_task(self.restore_after_ready())

    def cog_unload(self):
        self.reminder_loop.cancel()
        self.finalize_loop.cancel()
        self.auto_calendar_loop.cancel()
        self.inactive_loop.cancel()
        if self.restore_task:
            self.restore_task.cancel()

    async def get_member_safe(self, guild, user_id):
        member = guild.get_member(int(user_id))
        if member:
            return member
        try:
            return await guild.fetch_member(int(user_id))
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            return None

    async def get_channel_safe(self, channel_id):
        channel = self.bot.get_channel(int(channel_id))
        if channel:
            return channel
        try:
            return await self.bot.fetch_channel(int(channel_id))
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            return None

    async def build_restored(self, row):
        message_id, thread_id, channel_id, creator_id, fecha, hora_inicio, hora_fin = row

        thread = await self.get_channel_safe(thread_id)
        channel = await self.get_channel_safe(channel_id)
        if not thread or not channel:
            return None

        creator = await self.get_member_safe(thread.guild, creator_id)
        if not creator:
            return None

        try:
            main_message = await channel.fetch_message(int(message_id))
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            return None

        activity = {
            "creator": creator,
            "fecha": fecha,
            "hora_inicio": hora_inicio,
            "hora_fin": hora_fin,
            "slots": [
                {
                    "label": slot["label"],
                    "group": slot["group"],
                    "user": None,
                    "filled_by_fill": False,
                    "signup_role": None,
                }
                for slot in DRAGON_SLOTS
            ],
            "fill_queue": [],
        }

        for user_id, role, avoid_roles in database.get_scheduled_dragon_participants(message_id):
            member = await self.get_member_safe(thread.guild, user_id)
            if not member:
                continue

            if role == "Fill":
                activity["fill_queue"].append({
                    "user": member,
                    "avoid": {x for x in (avoid_roles or "").split(",") if x},
                    "assigned_role": None,
                })
                continue

            # Restauración de la composición actual. Los registros de la composición
            # antigua se ignoran si no corresponden a un hueco actual.
            requested_role = role
            if role in {"DPS Ballesta", "DPS Flami", "DPS Pajaro", "DPS"}:
                requested_role = role if role != "DPS" else "DPS_ANY"
            elif role.startswith("DPS "):
                requested_role = "DPS_ANY"
            elif role.startswith("Offtank"):
                requested_role = "Offtank"
            elif role.startswith("Healer Party 1"):
                requested_role = "Healer Party 1"
            elif role.startswith("Healer Party 2"):
                requested_role = "Healer Party 2"
            elif role.startswith("Enigmático"):
                requested_role = "Enigmático"

            for slot in activity["slots"]:
                if slot["user"] is None and role_matches(slot["group"], requested_role):
                    slot["user"] = member
                    slot["signup_role"] = signup_display_name(requested_role, slot)
                    break

        rebuild_fill_assignments(activity)

        return {
            "thread_id": int(thread_id),
            "message": main_message,
            "activity": activity,
            "message_id": int(message_id),
        }

    async def restore_after_ready(self):
        await self.bot.wait_until_ready()
        async with self.restore_lock:
            restored = 0
            for row in database.get_active_dragons_for_restore():
                data = await self.build_restored(row)
                if data:
                    dragon_messages[data["thread_id"]] = {
                        "message": data["message"],
                        "activity": data["activity"],
                        "message_id": data["message_id"],
                    }
                    restored += 1
            print(f"Dragones restaurados tras iniciar el bot: {restored}")

    async def restore_by_thread(self, thread_id):
        async with self.restore_lock:
            if int(thread_id) in dragon_messages:
                return True

            row = database.get_scheduled_dragon_by_thread(thread_id)
            if not row:
                return False

            data = await self.build_restored(row)
            if not data:
                return False

            dragon_messages[data["thread_id"]] = {
                "message": data["message"],
                "activity": data["activity"],
                "message_id": data["message_id"],
            }
            return True

    @commands.command(name="dragon", aliases=["dragones"])
    async def dragon(self, ctx, fecha: str, hora_inicio: str, hora_fin: str):
        try:
            datetime.strptime(fecha, "%d/%m/%Y")
            datetime.strptime(hora_inicio, "%H:%M")
            datetime.strptime(hora_fin, "%H:%M")
            madrid_to_utc(fecha, hora_inicio)
            madrid_to_utc(fecha, hora_fin)
        except ValueError:
            await ctx.send(
                embed=error_embed(
                    "Formato esperado:\n"
                    "`?dragon 03/09/2026 20:00 22:00`",
                    "Fecha u hora no válida",
                )
            )
            return

        activity = {
            "creator": ctx.author,
            "fecha": fecha,
            "hora_inicio": hora_inicio,
            "hora_fin": hora_fin,
            "slots": [
                {
                    "label": slot["label"],
                    "group": slot["group"],
                    "user": None,
                    "filled_by_fill": False,
                    "signup_role": None,
                }
                for slot in DRAGON_SLOTS
            ],
            "fill_queue": [],
        }

        msg = await ctx.send(embed=build_dragon_embed(activity))
        thread = await msg.create_thread(
            name=f"Dragones {fecha} {hora_inicio}",
            auto_archive_duration=1440,
        )

        database.add_scheduled_dragon(
            msg.id,
            thread.id,
            ctx.channel.id,
            ctx.author.id,
            fecha,
            hora_inicio,
            hora_fin,
        )

        dragon_messages[thread.id] = {
            "message": msg,
            "activity": activity,
            "message_id": msg.id,
        }

        # Aviso exclusivo de Dragones: menciones + imagen de composición dentro del hilo.
        ping_text = build_dragon_ping_text(ctx.guild)
        image_path = Path(__file__).resolve().parent.parent / "assets" / "dragon_compo.png"

        if image_path.exists():
            compo_embed = info_embed(
                "🐉 DRAGONES · BUILDS & SWAPS",
                (
                    "⚔️ **Esta es la composición oficial para la salida.**\n\n"
                    "🔹 Revisa tu **build** antes de apuntarte.\n"
                    "🔁 Lleva preparados los **swaps** indicados.\n"
                    "🍲 Comprueba **comida y pociones** antes de salir.\n"
                    "💚 Los **healers** deben ir en `T6.4`.\n\n"
                    "🔥 **Entramos preparados. Sin improvisar dentro.**"
                ),
            )
            compo_embed.set_image(url="attachment://dragon_compo.png")

            await thread.send(
                content=ping_text,
                embed=compo_embed,
                file=discord.File(image_path, filename="dragon_compo.png"),
                allowed_mentions=discord.AllowedMentions(roles=True, users=True),
            )
        else:
            await thread.send(
                content=ping_text,
                embed=warning_embed(
                    "Imagen de composición no encontrada",
                    "No se ha encontrado `assets/dragon_compo.png`.",
                ),
                allowed_mentions=discord.AllowedMentions(roles=True, users=True),
            )

        await thread.send(embed=build_help_embed())

        await send_log(
            self.bot,
            "🐉 Dragones creados",
            (
                f"Creado por: {ctx.author.mention}\n"
                f"Fecha: **{fecha}**\n"
                f"Hora: **{hora_inicio} - {hora_fin} ESP**\n"
                f"Hilo: {thread.mention}"
            ),
            discord.Color.red(),
        )

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        if message.channel.id not in dragon_messages:
            restored = await self.restore_by_thread(message.channel.id)
            if not restored:
                return

        data = dragon_messages[message.channel.id]
        activity = data["activity"]
        role = normalize_role(message.content)

        if role == "Signoff":
            target = message.mentions[0] if message.mentions else message.author

            if remove_user(activity, target):
                database.remove_scheduled_dragon_participant(
                    data["message_id"], target.id
                )
                await data["message"].edit(
                    content=None,
                    embed=build_dragon_embed(activity),
                )
                await message.add_reaction("✅")
            else:
                await message.add_reaction("❌")
            return

        if not role:
            return

        target = message.mentions[0] if message.mentions else message.author
        success, reason = add_user(activity, target, role, message.content)

        if success:
            stored_role = "Fill"
            avoid_roles = ""

            if role == "Fill":
                avoid_roles = ",".join(sorted(parse_fill_avoid(message.content)))
            else:
                assigned = get_user_slot(activity, target.id)
                stored_role = (assigned.get("signup_role") or assigned["label"]) if assigned else role

            database.add_scheduled_dragon_participant(
                data["message_id"],
                target.id,
                stored_role,
                avoid_roles,
            )

            await data["message"].edit(
                content=None,
                embed=build_dragon_embed(activity),
            )
            await message.add_reaction("✅")
            return

        if reason == "already_registered":
            slot = get_user_slot(activity, target.id)
            fill = get_user_fill(activity, target.id)
            current = slot["label"] if slot else "Fill" if fill else "otro rol"
            await message.channel.send(
                embed=error_embed(
                    f"{target.mention} ya está apuntado como **{current}**.\n"
                    f"Usa `signoff {target.mention}` antes de cambiarle.",
                    "Usuario ya apuntado",
                )
            )
        elif reason == "role_full":
            await message.channel.send(
                embed=error_embed(
                    f"No queda ningún hueco compatible para **{role}**.",
                    "Rol completo",
                )
            )

        await message.add_reaction("❌")

    def build_calendar_embed(self, guild):
        rows = database.get_calendar_dragons(20)

        embed = discord.Embed(
            title="🐉 Calendario de Dragones",
            description="Actualizado automáticamente cada 10 minutos.",
            color=discord.Color.red(),
        )

        if not rows:
            embed.description = "🐉 No hay ningún Dragón programado."
            embed.set_footer(text="EcosBot · Dragones")
            return embed

        for fecha, inicio, fin, creator_id, thread_id in rows[:10]:
            creator = guild.get_member(creator_id)
            creator_name = creator.display_name if creator else f"Usuario {creator_id}"
            embed.add_field(
                name=f"📅 {fecha} · {inicio}",
                value=(
                    f"🕐 **{inicio} - {fin} ESP**\n"
                    f"🌍 **{madrid_to_utc(fecha, inicio)} - {madrid_to_utc(fecha, fin)} UTC**\n"
                    f"👤 Creado por **{creator_name}**\n"
                    f"🧵 <#{thread_id}>"
                ),
                inline=False,
            )

        embed.set_footer(text="EcosBot · Calendario automático de Dragones")
        return embed

    def build_inactive_embed(self, guild, days=14):
        rows = database.get_inactive_dragon_players(days)

        embed = discord.Embed(
            title=f"🐉 Sin ir a Dragones en {days} días",
            color=discord.Color.orange(),
        )

        if not rows:
            embed.description = "✅ Todos los jugadores registrados tienen actividad reciente."
            embed.set_footer(text="EcosBot · Control de Dragones")
            return embed

        lines = []
        for discord_id, albion_name, last_dragon in rows[:40]:
            member = guild.get_member(discord_id)
            name = member.display_name if member else albion_name
            if last_dragon:
                display_date = datetime.strptime(last_dragon, "%Y-%m-%d").strftime("%d/%m/%Y")
                lines.append(f"• **{name}** — última: `{display_date}`")
            else:
                lines.append(f"• **{name}** — `Nunca ha ido`")

        embed.description = "\n".join(lines)
        embed.set_footer(
            text=(
                f"Mostrando 40 de {len(rows)} · EcosBot"
                if len(rows) > 40
                else "EcosBot · Control de Dragones"
            )
        )
        return embed

    async def update_auto_calendar_message(self):
        channel = self.bot.get_channel(config.CALENDAR_CHANNEL)
        if not channel:
            return

        embed = self.build_calendar_embed(channel.guild)
        message_id = database.get_setting("dragon_calendar_message_id")

        if message_id:
            try:
                msg = await channel.fetch_message(int(message_id))
                await msg.edit(embed=embed)
                return
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                pass

        msg = await channel.send(embed=embed)
        database.set_setting("dragon_calendar_message_id", msg.id)

    async def update_inactive_message(self):
        channel = self.bot.get_channel(config.INACTIVE_CHANNEL)
        if not channel:
            return

        embed = self.build_inactive_embed(channel.guild, 14)
        message_id = database.get_setting("dragon_inactive_message_id")

        if message_id:
            try:
                msg = await channel.fetch_message(int(message_id))
                await msg.edit(embed=embed)
                return
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                pass

        msg = await channel.send(embed=embed)
        database.set_setting("dragon_inactive_message_id", msg.id)

    @tasks.loop(minutes=10)
    async def auto_calendar_loop(self):
        await self.update_auto_calendar_message()

    @tasks.loop(hours=6)
    async def inactive_loop(self):
        await self.update_inactive_message()

    @commands.command(name="dragoncalendar", aliases=["dcalendar"])
    async def dragon_calendar(self, ctx):
        await ctx.send(embed=self.build_calendar_embed(ctx.guild))

    @commands.command(name="dragonstats", aliases=["dstats"])
    async def dragon_stats(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        total, roles = database.get_user_dragon_stats(member.id)

        embed = discord.Embed(
            title=f"🐉 Dragones de {member.display_name}",
            description=f"Participaciones completadas: **{total}**",
            color=discord.Color.red(),
        )
        embed.set_thumbnail(url=member.display_avatar.url)

        if roles:
            embed.add_field(
                name="⚔️ Roles más usados",
                value="\n".join(
                    f"**{role}** — `{count}`"
                    for role, count in roles[:10]
                ),
                inline=False,
            )
        else:
            embed.add_field(
                name="Sin historial",
                value="Todavía no tiene Dragones completados.",
                inline=False,
            )

        embed.set_footer(text="EcosBot · Estadísticas de Dragones")
        await ctx.send(embed=embed)

    @commands.command(name="dragontop", aliases=["dtop"])
    async def dragon_top(self, ctx):
        rows = database.get_top_dragons(15)
        if not rows:
            await ctx.send(
                embed=info_embed(
                    "Ranking de Dragones",
                    "Todavía no hay participaciones completadas.",
                )
            )
            return

        medals = ["🥇", "🥈", "🥉"]
        lines = []
        for index, (user_id, total) in enumerate(rows, start=1):
            member = ctx.guild.get_member(user_id)
            name = member.display_name if member else f"Usuario {user_id}"
            prefix = medals[index - 1] if index <= 3 else f"**{index}.**"
            lines.append(f"{prefix} **{name}** — `{total}`")

        embed = discord.Embed(
            title="🏆 Ranking de Dragones",
            description="\n".join(lines),
            color=discord.Color.gold(),
        )
        embed.set_footer(text="EcosBot · Dragones completados")
        await ctx.send(embed=embed)

    @commands.command(name="dragoninactive", aliases=["dinactive"])
    async def dragon_inactive(self, ctx, days: int = 14):
        days = max(1, min(days, 365))
        await ctx.send(embed=self.build_inactive_embed(ctx.guild, days))

    @tasks.loop(minutes=1)
    async def reminder_loop(self):
        now = datetime.now(MADRID_TZ)

        for dragon_id, thread_id, creator_id, fecha, inicio, fin in database.get_pending_dragon_reminders():
            try:
                start_dt = datetime.strptime(
                    f"{fecha} {inicio}", "%d/%m/%Y %H:%M"
                ).replace(tzinfo=MADRID_TZ)
            except ValueError:
                continue

            reminder_time = start_dt - timedelta(minutes=15)

            if reminder_time <= now < start_dt:
                thread = await self.get_channel_safe(thread_id)
                if thread:
                    await thread.send(
                        embed=warning_embed(
                            "Dragones en 15 minutos",
                            (
                                f"📅 **{fecha}**\n"
                                f"🕐 **{inicio} - {fin} ESP**\n"
                                f"👤 Creado por <@{creator_id}>\n\n"
                                "Revisad la composición antes de salir."
                            ),
                        )
                    )

                database.mark_dragon_reminder_sent(dragon_id)

    @tasks.loop(minutes=1)
    async def finalize_loop(self):
        rows = database.get_finished_dragons_without_stats()
        if not rows:
            return

        achievements_cog = self.bot.get_cog("Achievements")

        for message_id, event_date in rows:
            participants = database.get_scheduled_dragon_participants(message_id)
            database.finalize_dragon_participations(message_id, event_date)

            if achievements_cog and self.bot.guilds:
                guild = self.bot.guilds[0]
                for user_id, _, _ in participants:
                    await achievements_cog.check_user_achievements(guild, user_id)


async def setup(bot):
    await bot.add_cog(Dragons(bot))
