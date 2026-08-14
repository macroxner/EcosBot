# IDs de canales

WARNING_CHANNEL = 1341093155407138896
LOG_CHANNEL = 1526639660854546474
SPLIT_CHANNEL = 1332766473684254744
SHOP_CHANNEL = 1526650294476214353
ALBION_API_BASE = "https://gameinfo-ams.albiononline.com/api/gameinfo"
CALENDAR_CHANNEL = 1526640152963846184
INACTIVE_CHANNEL = 1526641806517997598

# Multas

WARNING_TYPES = {

    "noshow": {
        "aliases": [
            "no show",
            "no-show",
            "no asistir",
            "noshow"
        ],

        "escalate": True,

        "fines": [
            500000,
            1000000,
            2000000,
            3000000,
            4000000
        ]
    },

    "swap_block": {
        "aliases": [
            "swap critico",
            "swap crítico"
        ],

        "fine": 5000000
    },

    "swap_damage": {
        "aliases": [
            "swap daño",
            "swap damage"
        ],

        "fine": 1500000
    },

    "swap_slow": {
        "aliases": [
            "swap lento",
            "swap slow"
        ],

        "fine": 700000
    },

    "swap_reported": {
        "aliases": [
            "swap avisado",
            "swap reportado"
        ],

        "fine": 100000
    },

    "wrong_tier": {
        "aliases": [
            "tier",
            "equipamiento"
        ],

        "fine": 1000000
    },

    "small_bag": {
        "aliases": [
            "bolsa",
            "bag"
        ],

        "fine": 5000000
    },

    "caller_money": {
        "aliases": [
            "dinero",
            "tabs"
        ],

        "fine": 5000000
    }
}