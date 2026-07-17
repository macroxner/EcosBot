import os
import sqlite3
import shutil

LOCAL_DB_PATH = "data.db"
PERSISTENT_DB_PATH = os.getenv("DB_PATH", LOCAL_DB_PATH)

DB_NAME = PERSISTENT_DB_PATH

def migrate_existing_database():
    """
    Copia una base de datos local existente al volumen persistente.

    Solo realiza la copia si:
    - DB_PATH apunta a otra ubicación.
    - Existe data.db en /workspace.
    - Todavía no existe una base en el volumen.
    """
    if PERSISTENT_DB_PATH == LOCAL_DB_PATH:
        return

    persistent_directory = os.path.dirname(PERSISTENT_DB_PATH)

    if persistent_directory:
        os.makedirs(persistent_directory, exist_ok=True)

    if os.path.exists(LOCAL_DB_PATH) and not os.path.exists(PERSISTENT_DB_PATH):
        print(
            f"Migrando base de datos: "
            f"{LOCAL_DB_PATH} -> {PERSISTENT_DB_PATH}"
        )

        shutil.copy2(
            LOCAL_DB_PATH,
            PERSISTENT_DB_PATH
        )

        print("Base de datos migrada correctamente.")

def connect():
    return sqlite3.connect(DB_NAME)


def create_tables():
    conn = connect()
    cursor = conn.cursor()

    try:
        cursor.execute(
            "ALTER TABLE scheduled_avas "
            "ADD COLUMN fame_processed INTEGER DEFAULT 0"
        )
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute(
            "ALTER TABLE scheduled_ava_participants "
            "ADD COLUMN avoid_roles TEXT DEFAULT ''"
        )
    except sqlite3.OperationalError:
        pass

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ava_fame_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ava_message_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        pve_gained INTEGER DEFAULT 0,
        gathering_gained INTEGER DEFAULT 0,
        crafting_gained INTEGER DEFAULT 0,
        kill_gained INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS unlocked_sounds (
        user_id INTEGER NOT NULL,
        sound_key TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (user_id, sound_key)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        balance INTEGER DEFAULT 0,
        ecoins INTEGER DEFAULT 0
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS registered_players (
        discord_id INTEGER PRIMARY KEY,
        albion_id TEXT NOT NULL,
        albion_name TEXT NOT NULL,
        guild_id TEXT,
        guild_name TEXT,
        alliance_id TEXT,
        alliance_name TEXT,
        last_sync TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS scheduled_ava_participants (
        ava_message_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        role TEXT NOT NULL,
        avoid_roles TEXT DEFAULT '',
        PRIMARY KEY (ava_message_id, user_id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ava_fame_snapshots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ava_message_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        snapshot_type TEXT NOT NULL,
        pve_fame INTEGER DEFAULT 0,
        gathering_fame INTEGER DEFAULT 0,
        crafting_fame INTEGER DEFAULT 0,
        kill_fame INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS scheduled_avas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        message_id INTEGER NOT NULL,
        thread_id INTEGER NOT NULL,
        channel_id INTEGER NOT NULL,
        creator_id INTEGER NOT NULL,
        tier TEXT NOT NULL,
        date TEXT NOT NULL,
        start_time TEXT NOT NULL,
        end_time TEXT NOT NULL,
        maseo TEXT NOT NULL,
        reminder_sent INTEGER DEFAULT 0,
        fame_processed INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    try:
        cursor.execute("ALTER TABLE scheduled_avas ADD COLUMN fame_processed INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS warnings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        moderator_id INTEGER NOT NULL,
        reason TEXT,
        fine INTEGER NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ava_participations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        message_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        role TEXT NOT NULL,
        ecoins_given INTEGER NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS processed_splits (
        message_id INTEGER PRIMARY KEY,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_achievements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        achievement_key TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, achievement_key)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        amount INTEGER NOT NULL,
        currency TEXT NOT NULL,
        reason TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS shop_purchases (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        buyer_id INTEGER NOT NULL,
        target_id INTEGER,
        item_key TEXT NOT NULL,
        cost INTEGER NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    conn.close()


def ensure_user(user_id):
    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT OR IGNORE INTO users (user_id, balance, ecoins)
    VALUES (?, 0, 0)
    """, (user_id,))

    conn.commit()
    conn.close()

def upsert_registered_player(discord_id, albion_id, albion_name, guild_id, guild_name, alliance_id, alliance_name):
    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO registered_players
    (discord_id, albion_id, albion_name, guild_id, guild_name, alliance_id, alliance_name)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(discord_id) DO UPDATE SET
        albion_id = excluded.albion_id,
        albion_name = excluded.albion_name,
        guild_id = excluded.guild_id,
        guild_name = excluded.guild_name,
        alliance_id = excluded.alliance_id,
        alliance_name = excluded.alliance_name,
        last_sync = CURRENT_TIMESTAMP
    """, (discord_id, albion_id, albion_name, guild_id, guild_name, alliance_id, alliance_name))

    conn.commit()
    conn.close()


def get_registered_players():
    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT discord_id, albion_id, albion_name, guild_id, guild_name, alliance_id, alliance_name
    FROM registered_players
    ORDER BY guild_name, albion_name
    """)

    result = cursor.fetchall()
    conn.close()
    return result


def get_registered_player(discord_id):
    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT discord_id, albion_id, albion_name, guild_id, guild_name, alliance_id, alliance_name
    FROM registered_players
    WHERE discord_id = ?
    """, (discord_id,))

    result = cursor.fetchone()
    conn.close()
    return result

def get_dashboard_stats():
    conn = connect()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM users")
    users_count = cursor.fetchone()[0]

    cursor.execute("SELECT COALESCE(SUM(balance), 0), COALESCE(SUM(ecoins), 0) FROM users")
    total_balance, total_ecoins = cursor.fetchone()

    cursor.execute("SELECT COUNT(*) FROM warnings")
    warnings_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(DISTINCT message_id) FROM ava_participations")
    ava_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM ava_participations")
    participations_count = cursor.fetchone()[0]

    cursor.execute("SELECT COALESCE(SUM(ecoins_given), 0) FROM ava_participations")
    ecoins_from_avas = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM shop_purchases")
    shop_purchases = cursor.fetchone()[0]

    conn.close()

    return {
        "users_count": users_count,
        "total_balance": total_balance,
        "total_ecoins": total_ecoins,
        "warnings_count": warnings_count,
        "ava_count": ava_count,
        "participations_count": participations_count,
        "ecoins_from_avas": ecoins_from_avas,
        "shop_purchases": shop_purchases
    }


def get_top_by_ava_role(role, limit=5):
    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT user_id, COUNT(*) as count
    FROM ava_participations
    WHERE role = ?
    GROUP BY user_id
    ORDER BY count DESC
    LIMIT ?
    """, (role, limit))

    result = cursor.fetchall()
    conn.close()
    return result


def get_top_warnings(limit=5):
    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT user_id, COUNT(*) as count
    FROM warnings
    GROUP BY user_id
    ORDER BY count DESC
    LIMIT ?
    """, (limit,))

    result = cursor.fetchall()
    conn.close()
    return result


def get_top_shop_buyers(limit=5):
    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT buyer_id, COUNT(*) as count
    FROM shop_purchases
    GROUP BY buyer_id
    ORDER BY count DESC
    LIMIT ?
    """, (limit,))

    result = cursor.fetchall()
    conn.close()
    return result

def get_user(user_id):
    ensure_user(user_id)

    conn = connect()
    cursor = conn.cursor()

    cursor.execute("SELECT balance, ecoins FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()

    conn.close()
    return result


def add_balance(user_id, amount, reason="Movimiento manual"):
    ensure_user(user_id)

    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
    UPDATE users
    SET balance = balance + ?
    WHERE user_id = ?
    """, (amount, user_id))

    conn.commit()
    conn.close()

    add_transaction(user_id, amount, "balance", reason)


def reset_balance(user_id):
    ensure_user(user_id)

    conn = connect()
    cursor = conn.cursor()

    cursor.execute("UPDATE users SET balance = 0 WHERE user_id = ?", (user_id,))

    conn.commit()
    conn.close()

    add_transaction(user_id, 0, "balance", "")


def add_ecoins(user_id, amount, reason="Movimiento manual"):
    ensure_user(user_id)

    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
    UPDATE users
    SET ecoins = ecoins + ?
    WHERE user_id = ?
    """, (amount, user_id))

    conn.commit()
    conn.close()

    add_transaction(user_id, amount, "ecoins", reason)


def get_all_users():
    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT user_id, balance, ecoins
    FROM users
    """)

    result = cursor.fetchall()
    conn.close()
    return result


def add_warning(user_id, moderator_id, reason, fine):
    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO warnings (user_id, moderator_id, reason, fine)
    VALUES (?, ?, ?, ?)
    """, (user_id, moderator_id, reason, fine))

    conn.commit()
    conn.close()


def get_warning_count(user_id):
    conn = connect()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM warnings WHERE user_id = ?", (user_id,))
    count = cursor.fetchone()[0]

    conn.close()
    return count


def get_warnings(user_id):
    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT id, reason, fine, created_at
    FROM warnings
    WHERE user_id = ?
    ORDER BY id DESC
    """, (user_id,))

    result = cursor.fetchall()
    conn.close()
    return result


def remove_last_warning(user_id):
    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT id, fine
    FROM warnings
    WHERE user_id = ?
    ORDER BY id DESC
    LIMIT 1
    """, (user_id,))

    row = cursor.fetchone()

    if not row:
        conn.close()
        return None

    warning_id, fine = row

    cursor.execute("DELETE FROM warnings WHERE id = ?", (warning_id,))

    conn.commit()
    conn.close()

    return fine


def is_split_processed(message_id):
    conn = connect()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT message_id FROM processed_splits WHERE message_id = ?",
        (message_id,)
    )

    result = cursor.fetchone()
    conn.close()

    return result is not None


def mark_split_processed(message_id):
    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT OR IGNORE INTO processed_splits (message_id)
    VALUES (?)
    """, (message_id,))

    conn.commit()
    conn.close()

def add_ava_participation(message_id, user_id, role, ecoins_given):
    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO ava_participations (message_id, user_id, role, ecoins_given)
    VALUES (?, ?, ?, ?)
    """, (message_id, user_id, role, ecoins_given))

    conn.commit()
    conn.close()


def get_user_ava_stats(user_id):
    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT
        COUNT(*) as total_avas,
        SUM(CASE WHEN role = 'Caller' THEN 1 ELSE 0 END) as caller_count,
        SUM(CASE WHEN role = 'Scout' THEN 1 ELSE 0 END) as scout_count,
        SUM(CASE WHEN role = 'Party' THEN 1 ELSE 0 END) as party_count,
        SUM(ecoins_given) as total_ecoins_from_avas
    FROM ava_participations
    WHERE user_id = ?
    """, (user_id,))

    result = cursor.fetchone()
    conn.close()

    return result


def get_user_ava_history(user_id, limit=10):
    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT role, ecoins_given, created_at
    FROM ava_participations
    WHERE user_id = ?
    ORDER BY id DESC
    LIMIT ?
    """, (user_id, limit))

    result = cursor.fetchall()
    conn.close()

    return result

def add_transaction(user_id, amount, currency, reason="Sin motivo"):
    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO transactions (user_id, amount, currency, reason)
    VALUES (?, ?, ?, ?)
    """, (user_id, amount, currency, reason))

    conn.commit()
    conn.close()


def get_transactions(user_id, currency=None, limit=10):
    conn = connect()
    cursor = conn.cursor()

    if currency:
        cursor.execute("""
        SELECT amount, currency, reason, created_at
        FROM transactions
        WHERE user_id = ? AND currency = ?
        ORDER BY id DESC
        LIMIT ?
        """, (user_id, currency, limit))
    else:
        cursor.execute("""
        SELECT amount, currency, reason, created_at
        FROM transactions
        WHERE user_id = ?
        ORDER BY id DESC
        LIMIT ?
        """, (user_id, limit))

    result = cursor.fetchall()
    conn.close()
    return result

def add_shop_purchase(buyer_id, target_id, item_key, cost):
    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO shop_purchases (buyer_id, target_id, item_key, cost)
    VALUES (?, ?, ?, ?)
    """, (buyer_id, target_id, item_key, cost))

    conn.commit()
    conn.close()

def add_scheduled_ava(message_id, thread_id, channel_id, creator_id, tier, date, start_time, end_time, maseo):
    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO scheduled_avas
    (message_id, thread_id, channel_id, creator_id, tier, date, start_time, end_time, maseo)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (message_id, thread_id, channel_id, creator_id, tier, date, start_time, end_time, maseo))

    conn.commit()
    conn.close()


def get_pending_ava_reminders():
    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT id, thread_id, creator_id, tier, date, start_time, end_time, maseo
    FROM scheduled_avas
    WHERE reminder_sent = 0
    """)

    result = cursor.fetchall()
    conn.close()
    return result


def mark_ava_reminder_sent(ava_id):
    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
    UPDATE scheduled_avas
    SET reminder_sent = 1
    WHERE id = ?
    """, (ava_id,))

    conn.commit()
    conn.close()


def get_calendar_avas(limit=10):
    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT tier, date, start_time, end_time, maseo, creator_id, thread_id
    FROM scheduled_avas
    WHERE datetime(
        substr(date, 7, 4) || '-' ||
        substr(date, 4, 2) || '-' ||
        substr(date, 1, 2) || ' ' ||
        end_time
    ) > datetime('now', 'localtime')
    ORDER BY
        substr(date, 7, 4) || '-' ||
        substr(date, 4, 2) || '-' ||
        substr(date, 1, 2),
        start_time ASC
    LIMIT ?
    """, (limit,))

    result = cursor.fetchall()

    conn.close()
    return result

def delete_finished_avas():
    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
    DELETE FROM scheduled_avas
    WHERE datetime(
        substr(date, 7, 4) || '-' ||
        substr(date, 4, 2) || '-' ||
        substr(date, 1, 2) || ' ' ||
        end_time
    ) <= datetime('now', 'localtime')
    """)

    conn.commit()
    conn.close()

def has_achievement(user_id, achievement_key):
    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_achievements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        achievement_key TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, achievement_key)
    )
    """)

    cursor.execute("""
    SELECT 1 FROM user_achievements
    WHERE user_id = ? AND achievement_key = ?
    """, (user_id, achievement_key))

    result = cursor.fetchone()
    conn.close()

    return result is not None

def add_achievement(user_id, achievement_key):
    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT OR IGNORE INTO user_achievements (user_id, achievement_key)
    VALUES (?, ?)
    """, (user_id, achievement_key))

    conn.commit()
    conn.close()

def add_fame_snapshot(ava_message_id, user_id, snapshot_type, pve, gathering, crafting, kill):
    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO ava_fame_snapshots
    (ava_message_id, user_id, snapshot_type, pve_fame, gathering_fame, crafting_fame, kill_fame)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (ava_message_id, user_id, snapshot_type, pve, gathering, crafting, kill))

    conn.commit()
    conn.close()


def get_start_fame_snapshot(ava_message_id, user_id):
    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT pve_fame, gathering_fame, crafting_fame, kill_fame
    FROM ava_fame_snapshots
    WHERE ava_message_id = ? AND user_id = ? AND snapshot_type = 'start'
    ORDER BY id DESC
    LIMIT 1
    """, (ava_message_id, user_id))

    result = cursor.fetchone()
    conn.close()
    return result


def get_latest_scheduled_ava_message_id():
    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT message_id
    FROM scheduled_avas
    ORDER BY id DESC
    LIMIT 1
    """)

    result = cursor.fetchone()
    conn.close()

    return result[0] if result else None

def add_scheduled_ava_participant(
    ava_message_id,
    user_id,
    role,
    avoid_roles=""
):
    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO scheduled_ava_participants
    (ava_message_id, user_id, role, avoid_roles)
    VALUES (?, ?, ?, ?)
    ON CONFLICT(ava_message_id, user_id) DO UPDATE SET
        role = excluded.role,
        avoid_roles = excluded.avoid_roles
    """, (
        ava_message_id,
        user_id,
        role,
        avoid_roles or ""
    ))

    conn.commit()
    conn.close()


def remove_scheduled_ava_participant(ava_message_id, user_id):
    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
    DELETE FROM scheduled_ava_participants
    WHERE ava_message_id = ? AND user_id = ?
    """, (ava_message_id, user_id))

    conn.commit()
    conn.close()


def get_scheduled_ava_participants(ava_message_id):
    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT user_id, role
    FROM scheduled_ava_participants
    WHERE ava_message_id = ?
    """, (ava_message_id,))

    result = cursor.fetchall()
    conn.close()
    return result


def get_scheduled_ava_participants_for_restore(ava_message_id):
    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT user_id, role, COALESCE(avoid_roles, '')
    FROM scheduled_ava_participants
    WHERE ava_message_id = ?
    ORDER BY rowid ASC
    """, (ava_message_id,))

    result = cursor.fetchall()
    conn.close()
    return result


def get_active_avas_for_restore():
    """
    Devuelve todas las avas cuyo final todavía no ha pasado.
    Incluye los IDs necesarios para recuperar el mensaje y el hilo.
    """
    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT
        message_id,
        thread_id,
        channel_id,
        creator_id,
        tier,
        date,
        start_time,
        end_time,
        maseo
    FROM scheduled_avas
    WHERE datetime(
        substr(date, 7, 4) || '-' ||
        substr(date, 4, 2) || '-' ||
        substr(date, 1, 2) || ' ' ||
        end_time
    ) > datetime('now', 'localtime')
    ORDER BY
        substr(date, 7, 4) || '-' ||
        substr(date, 4, 2) || '-' ||
        substr(date, 1, 2),
        start_time ASC
    """)

    result = cursor.fetchall()
    conn.close()
    return result


def get_scheduled_ava_by_thread(thread_id):
    """
    Recupera una ava concreta por el ID de su hilo.

    Se usa como recuperación bajo demanda cuando el hilo no está
    presente en activity_messages.
    """
    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT
        message_id,
        thread_id,
        channel_id,
        creator_id,
        tier,
        date,
        start_time,
        end_time,
        maseo
    FROM scheduled_avas
    WHERE thread_id = ?
    LIMIT 1
    """, (thread_id,))

    result = cursor.fetchone()
    conn.close()
    return result


def get_finished_avas_without_fame():
    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT message_id
    FROM scheduled_avas
    WHERE fame_processed = 0
    AND datetime(
        substr(date, 7, 4) || '-' ||
        substr(date, 4, 2) || '-' ||
        substr(date, 1, 2) || ' ' ||
        end_time
    ) <= datetime('now', 'localtime')
    """)

    result = cursor.fetchall()
    conn.close()
    return result


def mark_ava_fame_processed(message_id):
    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
    UPDATE scheduled_avas
    SET fame_processed = 1
    WHERE message_id = ?
    """, (message_id,))

    conn.commit()
    conn.close()

def add_ava_fame_result(ava_message_id, user_id, pve, gathering, crafting, kill):
    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO ava_fame_results
    (ava_message_id, user_id, pve_gained, gathering_gained, crafting_gained, kill_gained)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (ava_message_id, user_id, pve, gathering, crafting, kill))

    conn.commit()
    conn.close()


def get_user_ava_fame_stats(user_id):
    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT
        COUNT(*) as avas,
        COALESCE(SUM(pve_gained), 0),
        COALESCE(SUM(gathering_gained), 0),
        COALESCE(SUM(crafting_gained), 0),
        COALESCE(SUM(kill_gained), 0),
        COALESCE(MAX(pve_gained), 0),
        COALESCE(AVG(pve_gained), 0)
    FROM ava_fame_results
    WHERE user_id = ?
    """, (user_id,))

    result = cursor.fetchone()
    conn.close()
    return result


def get_user_ava_fame_history(user_id, limit=10):
    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT ava_message_id, pve_gained, gathering_gained, crafting_gained, kill_gained, created_at
    FROM ava_fame_results
    WHERE user_id = ?
    ORDER BY id DESC
    LIMIT ?
    """, (user_id, limit))

    result = cursor.fetchall()
    conn.close()
    return result


def get_top_ava_fame(limit=10):
    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT user_id, COALESCE(SUM(pve_gained), 0) as total_pve
    FROM ava_fame_results
    GROUP BY user_id
    ORDER BY total_pve DESC
    LIMIT ?
    """, (limit,))

    result = cursor.fetchall()
    conn.close()
    return result


def get_last_ava_fame_results():
    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT ava_message_id
    FROM ava_fame_results
    ORDER BY id DESC
    LIMIT 1
    """)

    row = cursor.fetchone()

    if not row:
        conn.close()
        return []

    ava_message_id = row[0]

    cursor.execute("""
    SELECT user_id, pve_gained, gathering_gained, crafting_gained, kill_gained
    FROM ava_fame_results
    WHERE ava_message_id = ?
    ORDER BY pve_gained DESC
    """, (ava_message_id,))

    result = cursor.fetchall()
    conn.close()
    return result


def get_guild_ava_fame_stats():
    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT
        rp.guild_name,
        COUNT(DISTINCT afr.user_id),
        COALESCE(SUM(afr.pve_gained), 0)
    FROM ava_fame_results afr
    LEFT JOIN registered_players rp
        ON afr.user_id = rp.discord_id
    GROUP BY rp.guild_name
    ORDER BY SUM(afr.pve_gained) DESC
    """)

    result = cursor.fetchall()
    conn.close()
    return result

def unlock_sound(user_id, sound_key):
    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT OR IGNORE INTO unlocked_sounds (user_id, sound_key)
    VALUES (?, ?)
    """, (user_id, sound_key))

    conn.commit()
    conn.close()


def has_sound(user_id, sound_key):
    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT 1 FROM unlocked_sounds
    WHERE user_id = ? AND sound_key = ?
    """, (user_id, sound_key))

    result = cursor.fetchone()
    conn.close()
    return result is not None

def get_user_sounds(user_id):
    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT sound_key
    FROM unlocked_sounds
    WHERE user_id = ?
    """, (user_id,))

    result = [row[0] for row in cursor.fetchall()]
    conn.close()
    return result

def get_setting(key):
    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS bot_settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )
    """)

    cursor.execute("SELECT value FROM bot_settings WHERE key = ?", (key,))
    row = cursor.fetchone()

    conn.close()
    return row[0] if row else None


def set_setting(key, value):
    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS bot_settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )
    """)

    cursor.execute("""
    INSERT INTO bot_settings (key, value)
    VALUES (?, ?)
    ON CONFLICT(key) DO UPDATE SET value = excluded.value
    """, (key, str(value)))

    conn.commit()
    conn.close()


def get_inactive_registered_players(days=14):
    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT
        rp.discord_id,
        rp.albion_name,
        MAX(sa.created_at) as last_ava
    FROM registered_players rp
    LEFT JOIN scheduled_ava_participants sap
        ON rp.discord_id = sap.user_id
    LEFT JOIN scheduled_avas sa
        ON sap.ava_message_id = sa.message_id
    GROUP BY rp.discord_id, rp.albion_name
    HAVING last_ava IS NULL
       OR datetime(last_ava) <= datetime('now', ?)
    ORDER BY last_ava ASC
    """, (f"-{days} days",))

    result = cursor.fetchall()
    conn.close()
    return result