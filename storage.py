"""Storage manager for Cosmic Defender.
Handles local persistence of player data, scores, coins, ship upgrades, and settings.
Compatible with Android app data directories and desktop environments.
"""

import json
import os
import sys

DEFAULT_DATA = {
    "high_score": 0,
    "coins": 0,
    "selected_ship": "interceptor",
    "unlocked_ships": ["interceptor"],
    "upgrades": {
        "interceptor": {"fire_rate": 1, "laser_power": 1, "shield_capacity": 1, "speed": 1},
        "vanguard": {"fire_rate": 1, "laser_power": 1, "shield_capacity": 1, "speed": 1},
        "dreadnought": {"fire_rate": 1, "laser_power": 1, "shield_capacity": 1, "speed": 1}
    },
    "settings": {
        "sound_enabled": True,
        "music_enabled": True,
        "control_mode": "touch",  # "touch" or "joystick"
        "touch_offset_y": 60,     # finger offset in dp so ship is visible above finger
        "screen_shake": True
    },
    "stats": {
        "games_played": 0,
        "enemies_destroyed": 0,
        "bosses_defeated": 0,
        "highest_wave": 0,
        "total_coins_collected": 0
    }
}

SHIP_CATALOG = {
    "interceptor": {
        "name": "Nova Interceptor",
        "description": "Fast and agile scout vessel. Balanced for tactical combat.",
        "cost": 0,
        "color": [0.2, 0.8, 1.0, 1.0],  # Cyan
        "base_speed": 340,
        "base_health": 100,
        "base_fire_rate": 4.5,  # shots per sec
        "special": "Twin Plasma Blaster"
    },
    "vanguard": {
        "name": "Aegis Vanguard",
        "description": "Heavy assault craft equipped with reinforced plasma shielding.",
        "cost": 150,
        "color": [1.0, 0.6, 0.1, 1.0],  # Amber / Gold
        "base_speed": 290,
        "base_health": 160,
        "base_fire_rate": 4.0,
        "special": "Triple Spread Laser"
    },
    "dreadnought": {
        "name": "Titan Dreadnought",
        "description": "Massive galactic destroyer with devastating beam arrays.",
        "cost": 350,
        "color": [0.9, 0.2, 0.3, 1.0],  # Crimson
        "base_speed": 240,
        "base_health": 240,
        "base_fire_rate": 5.5,
        "special": "Quad Overcharge Cannons"
    }
}


class StorageManager:
    """Manages player progress and game settings persistence."""

    def __init__(self, filename="cosmic_save.json"):
        self.filename = self._get_storage_path(filename)
        self.data = self.load_data()

    def _get_storage_path(self, filename):
        """Determine safe writeable directory across Android and Desktop."""
        try:
            # On Android with Kivy / python-for-android
            from kivy.app import App
            app = App.get_running_app()
            if app and hasattr(app, 'user_data_dir') and app.user_data_dir:
                return os.path.join(app.user_data_dir, filename)
        except Exception:
            pass

        # Fallback to local script folder
        base_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(base_dir, filename)

    def load_data(self):
        """Load user data from JSON file with safe schema migration."""
        if not os.path.exists(self.filename):
            return self._create_default_copy()

        try:
            with open(self.filename, 'r', encoding='utf-8') as f:
                saved = json.load(f)
                return self._merge_with_defaults(saved, DEFAULT_DATA)
        except Exception as e:
            print(f"[StorageManager] Error loading {self.filename}: {e}. Resetting to defaults.")
            return self._create_default_copy()

    def _create_default_copy(self):
        return json.loads(json.dumps(DEFAULT_DATA))

    def _merge_with_defaults(self, source, defaults):
        """Deep merge to ensure newly added config keys exist in older save files."""
        result = {}
        for key, val in defaults.items():
            if key not in source:
                result[key] = json.loads(json.dumps(val)) if isinstance(val, (dict, list)) else val
            elif isinstance(val, dict) and isinstance(source[key], dict):
                result[key] = self._merge_with_defaults(source[key], val)
            else:
                result[key] = source[key]
        return result

    def save_data(self):
        """Atomically persist data to disk."""
        try:
            temp_file = self.filename + ".tmp"
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=2)
            if os.path.exists(self.filename):
                os.replace(temp_file, self.filename)
            else:
                os.rename(temp_file, self.filename)
            return True
        except Exception as e:
            print(f"[StorageManager] Failed to save data: {e}")
            return False

    # Convenience accessors & modifiers
    def get_high_score(self):
        return self.data.get("high_score", 0)

    def set_high_score(self, score):
        if score > self.data.get("high_score", 0):
            self.data["high_score"] = int(score)
            self.save_data()
            return True
        return False

    def get_coins(self):
        return self.data.get("coins", 0)

    def add_coins(self, amount):
        if amount > 0:
            self.data["coins"] = self.data.get("coins", 0) + int(amount)
            self.data["stats"]["total_coins_collected"] += int(amount)
            self.save_data()
            return self.data["coins"]
        return self.data.get("coins", 0)

    def spend_coins(self, amount):
        current = self.data.get("coins", 0)
        if current >= amount:
            self.data["coins"] = current - amount
            self.save_data()
            return True
        return False

    def is_ship_unlocked(self, ship_id):
        return ship_id in self.data.get("unlocked_ships", ["interceptor"])

    def unlock_ship(self, ship_id):
        if ship_id in SHIP_CATALOG and not self.is_ship_unlocked(ship_id):
            cost = SHIP_CATALOG[ship_id]["cost"]
            if self.spend_coins(cost):
                self.data.setdefault("unlocked_ships", []).append(ship_id)
                self.save_data()
                return True
        return False

    def get_selected_ship(self):
        return self.data.get("selected_ship", "interceptor")

    def set_selected_ship(self, ship_id):
        if self.is_ship_unlocked(ship_id):
            self.data["selected_ship"] = ship_id
            self.save_data()
            return True
        return False

    def get_upgrade_level(self, ship_id, upgrade_key):
        return self.data.get("upgrades", {}).get(ship_id, {}).get(upgrade_key, 1)

    def upgrade_ship_stat(self, ship_id, upgrade_key):
        """Upgrade a stat (max level 5). Cost scales with level."""
        current_lvl = self.get_upgrade_level(ship_id, upgrade_key)
        if current_lvl >= 5:
            return False  # Max level reached

        cost = current_lvl * 50
        if self.spend_coins(cost):
            self.data.setdefault("upgrades", {}).setdefault(ship_id, {})[upgrade_key] = current_lvl + 1
            self.save_data()
            return True
        return False

    def record_game_end(self, score, wave, enemies_killed, boss_killed):
        """Update game stats upon game over."""
        self.set_high_score(score)
        self.data["stats"]["games_played"] += 1
        self.data["stats"]["enemies_destroyed"] += enemies_killed
        if boss_killed:
            self.data["stats"]["bosses_defeated"] += 1
        if wave > self.data["stats"]["highest_wave"]:
            self.data["stats"]["highest_wave"] = wave
        self.save_data()


# Singleton instance
storage = StorageManager()
