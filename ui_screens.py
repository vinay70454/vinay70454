"""Touch-friendly UI screens for Cosmic Defender.
Includes Main Menu, Game Screen (with HUD, Pause & Game Over overlays),
Ship Hangar & Upgrade Shop, and Settings/Stats.
"""

from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, RoundedRectangle, Line, Rectangle
from kivy.metrics import dp, sp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.modalview import ModalView
from kivy.uix.relativelayout import RelativeLayout
from kivy.uix.screenmanager import Screen
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget

from audio_synth import audio_manager
from game_engine import CosmicGameWidget
from storage import SHIP_CATALOG, storage


class ModernButton(Button):
    """Custom styled glowing sci-fi button with rounded borders."""
    def __init__(self, bg_color=(0.15, 0.35, 0.65, 0.9), border_color=(0.3, 0.7, 1.0, 1.0), **kwargs):
        super().__init__(**kwargs)
        self.background_color = (0, 0, 0, 0)  # transparent native background
        self.background_normal = ''
        self.bg_color = bg_color
        self.border_color = border_color
        self.font_size = sp(16)
        self.bold = True
        self.color = (1.0, 1.0, 1.0, 1.0)
        self.bind(pos=self._update_graphics, size=self._update_graphics, state=self._update_graphics)

    def _update_graphics(self, *args):
        self.canvas.before.clear()
        with self.canvas.before:
            if self.state == 'down':
                Color(self.bg_color[0] * 1.3, self.bg_color[1] * 1.3, self.bg_color[2] * 1.3, 1.0)
            else:
                Color(*self.bg_color)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(10)])
            Color(*self.border_color)
            Line(rounded_rectangle=(self.x, self.y, self.width, self.height, dp(10)), width=1.5)


class MainMenuScreen(Screen):
    """Futuristic main menu screen with live starfield and navigation."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.starfield_widget = CosmicGameWidget()
        self.starfield_widget.is_playing = False
        self.add_widget(self.starfield_widget)

        # UI Overlay
        layout = BoxLayout(orientation='vertical', padding=dp(25), spacing=dp(16))

        # Title Section
        title_box = BoxLayout(orientation='vertical', size_hint=(1, 0.38), spacing=dp(4))
        title_label = Label(
            text="COSMIC DEFENDER",
            font_size=sp(32),
            bold=True,
            color=(0.3, 0.85, 1.0, 1.0),
            size_hint=(1, 0.6)
        )
        subtitle_label = Label(
            text="★ STELLAR ASSAULT ★",
            font_size=sp(15),
            color=(1.0, 0.8, 0.2, 0.9),
            size_hint=(1, 0.4)
        )
        title_box.add_widget(title_label)
        title_box.add_widget(subtitle_label)
        layout.add_widget(title_box)

        # Info Badges (High Score & Coins)
        self.info_box = BoxLayout(orientation='horizontal', size_hint=(1, 0.12), spacing=dp(10))
        self.score_badge = Label(
            text=f"HIGH SCORE: {storage.get_high_score()}",
            font_size=sp(14),
            bold=True,
            color=(0.9, 0.9, 0.9, 1.0)
        )
        self.coins_badge = Label(
            text=f"COINS: ❖ {storage.get_coins()}",
            font_size=sp(14),
            bold=True,
            color=(1.0, 0.85, 0.1, 1.0)
        )
        self.info_box.add_widget(self.score_badge)
        self.info_box.add_widget(self.coins_badge)
        layout.add_widget(self.info_box)

        # Action Buttons
        btn_box = BoxLayout(orientation='vertical', size_hint=(1, 0.5), spacing=dp(12))

        play_btn = ModernButton(
            text="LAUNCH MISSION",
            bg_color=(0.1, 0.55, 0.35, 0.95),
            border_color=(0.2, 0.95, 0.5, 1.0),
            size_hint=(1, 0.36)
        )
        play_btn.font_size = sp(18)
        play_btn.bind(on_release=self._on_play)

        hangar_btn = ModernButton(
            text="SHIP HANGAR & UPGRADES",
            bg_color=(0.18, 0.28, 0.55, 0.9),
            border_color=(0.4, 0.65, 1.0, 1.0),
            size_hint=(1, 0.32)
        )
        hangar_btn.bind(on_release=self._on_hangar)

        settings_btn = ModernButton(
            text="SETTINGS & STATS",
            bg_color=(0.25, 0.25, 0.32, 0.9),
            border_color=(0.6, 0.6, 0.7, 1.0),
            size_hint=(1, 0.32)
        )
        settings_btn.bind(on_release=self._on_settings)

        btn_box.add_widget(play_btn)
        btn_box.add_widget(hangar_btn)
        btn_box.add_widget(settings_btn)
        layout.add_widget(btn_box)

        self.add_widget(layout)

    def on_enter(self):
        # Refresh dynamic badges
        self.score_badge.text = f"HIGH SCORE: {storage.get_high_score()}"
        self.coins_badge.text = f"COINS: ❖ {storage.get_coins()}"

    def _on_play(self, *args):
        audio_manager.play("pickup")
        self.manager.current = "game_screen"
        game_screen = self.manager.get_screen("game_screen")
        game_screen.start_session()

    def _on_hangar(self, *args):
        audio_manager.play("pickup")
        self.manager.current = "hangar_screen"

    def _on_settings(self, *args):
        audio_manager.play("pickup")
        self.manager.current = "settings_screen"


class GameScreen(Screen):
    """Screen hosting the active game simulation, live HUD, and modals."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.game_widget = CosmicGameWidget()
        self.game_widget.on_game_over_callback = self._on_game_over
        self.add_widget(self.game_widget)

        # HUD Overlay Layout
        self.hud_layout = RelativeLayout()

        # Score & Wave Label (Top Left)
        self.score_label = Label(
            text="SCORE: 0\nWAVE: 1",
            font_size=sp(14),
            bold=True,
            halign="left",
            valign="top",
            size_hint=(None, None),
            size=(dp(160), dp(50)),
            pos=(dp(15), Window.height - dp(65) if Window.height else dp(535)),
            color=(1.0, 1.0, 1.0, 0.95)
        )
        self.score_label.bind(size=self.score_label.setter('text_size'))
        self.hud_layout.add_widget(self.score_label)

        # Coins Collected (Top Center)
        self.coins_hud = Label(
            text="❖ 0",
            font_size=sp(15),
            bold=True,
            size_hint=(None, None),
            size=(dp(100), dp(40)),
            pos=((Window.width - dp(100)) / 2 if Window.width else dp(150), Window.height - dp(50) if Window.height else dp(550)),
            color=(1.0, 0.85, 0.1, 1.0)
        )
        self.hud_layout.add_widget(self.coins_hud)

        # Pause Button (Top Right)
        self.pause_btn = ModernButton(
            text="❚❚",
            bg_color=(0.2, 0.2, 0.25, 0.8),
            border_color=(0.5, 0.5, 0.6, 0.9),
            size_hint=(None, None),
            size=(dp(44), dp(44)),
            pos=(Window.width - dp(54) if Window.width else dp(346), Window.height - dp(54) if Window.height else dp(546))
        )
        self.pause_btn.font_size = sp(14)
        self.pause_btn.bind(on_release=self._show_pause_modal)
        self.hud_layout.add_widget(self.pause_btn)

        # EMP Bomb Button Label (Bottom Right)
        self.bomb_label = Label(
            text="EMP",
            font_size=sp(12),
            bold=True,
            size_hint=(None, None),
            size=(dp(50), dp(20)),
            pos=(Window.width - dp(70) if Window.width else dp(330), dp(18)),
            color=(0.3, 0.9, 1.0, 0.9)
        )
        self.hud_layout.add_widget(self.bomb_label)

        self.add_widget(self.hud_layout)
        Window.bind(size=self._on_window_resize)
        Clock.schedule_interval(self._update_hud, 1.0 / 20.0)

    def _on_window_resize(self, win, w, h):
        self.score_label.pos = (dp(15), h - dp(65))
        self.coins_hud.pos = ((w - dp(100)) / 2, h - dp(50))
        self.pause_btn.pos = (w - dp(54), h - dp(54))
        self.bomb_label.pos = (w - dp(70), dp(18))

    def start_session(self):
        self.game_widget.start_game()

    def _update_hud(self, dt):
        if not self.game_widget.is_playing:
            return
        self.score_label.text = f"SCORE: {self.game_widget.score:,}\nWAVE: {self.game_widget.wave}"
        self.coins_hud.text = f"❖ {self.game_widget.coins_this_run}"
        if self.game_widget.player:
            self.bomb_label.text = f"EMP x{self.game_widget.player.bombs_count}"

    def _show_pause_modal(self, *args):
        self.game_widget.pause_game()
        modal = ModalView(size_hint=(0.82, 0.45), auto_dismiss=False)
        modal.background_color = [0, 0, 0, 0.7]

        content = BoxLayout(orientation='vertical', padding=dp(20), spacing=dp(14))
        content.canvas.before.clear()
        with content.canvas.before:
            Color(0.08, 0.1, 0.16, 0.95)
            RoundedRectangle(pos=modal.pos, size=modal.size, radius=[dp(14)])
            Color(0.3, 0.6, 1.0, 0.8)
            Line(rounded_rectangle=(modal.x, modal.y, modal.width, modal.height, dp(14)), width=2)

        pause_title = Label(text="MISSION PAUSED", font_size=sp(20), bold=True, color=(0.3, 0.8, 1.0, 1.0))
        resume_btn = ModernButton(text="RESUME", bg_color=(0.15, 0.5, 0.3, 0.9), size_hint=(1, 0.28))
        restart_btn = ModernButton(text="RESTART MISSION", bg_color=(0.2, 0.35, 0.6, 0.9), size_hint=(1, 0.28))
        quit_btn = ModernButton(text="QUIT TO MENU", bg_color=(0.45, 0.15, 0.15, 0.9), size_hint=(1, 0.28))

        def _resume(*_):
            modal.dismiss()
            self.game_widget.resume_game()

        def _restart(*_):
            modal.dismiss()
            self.start_session()

        def _quit(*_):
            modal.dismiss()
            self.game_widget.is_playing = False
            self.manager.current = "main_menu"

        resume_btn.bind(on_release=_resume)
        restart_btn.bind(on_release=_restart)
        quit_btn.bind(on_release=_quit)

        content.add_widget(pause_title)
        content.add_widget(resume_btn)
        content.add_widget(restart_btn)
        content.add_widget(quit_btn)
        modal.add_widget(content)
        modal.open()

    def _on_game_over(self, final_score, wave_reached, coins_collected, enemies_killed):
        is_new_high = final_score > storage.get_high_score()
        storage.record_game_end(final_score, wave_reached, enemies_killed, False)

        modal = ModalView(size_hint=(0.86, 0.60), auto_dismiss=False)
        modal.background_color = [0, 0, 0, 0.8]

        content = BoxLayout(orientation='vertical', padding=dp(20), spacing=dp(10))
        with content.canvas.before:
            Color(0.09, 0.1, 0.18, 0.96)
            RoundedRectangle(pos=modal.pos, size=modal.size, radius=[dp(16)])
            Color(1.0, 0.25, 0.35, 0.8)
            Line(rounded_rectangle=(modal.x, modal.y, modal.width, modal.height, dp(16)), width=2)

        go_title = Label(text="HULL DESTROYED", font_size=sp(22), bold=True, color=(1.0, 0.3, 0.3, 1.0))
        if is_new_high:
            sub = Label(text="★ NEW HIGH SCORE! ★", font_size=sp(15), color=(1.0, 0.85, 0.2, 1.0))
        else:
            sub = Label(text=f"High Score: {storage.get_high_score():,}", font_size=sp(13), color=(0.8, 0.8, 0.8, 1.0))

        stats_text = (
            f"Final Score: {final_score:,}\n"
            f"Sector Reached: Wave {wave_reached}\n"
            f"Enemies Obliterated: {enemies_killed}\n"
            f"Credits Salvaged: ❖ {coins_collected}"
        )
        stats_lbl = Label(text=stats_text, font_size=sp(14), color=(0.9, 0.9, 0.9, 1.0), halign='center')

        retry_btn = ModernButton(text="PLAY AGAIN", bg_color=(0.1, 0.55, 0.3, 0.95), size_hint=(1, 0.25))
        menu_btn = ModernButton(text="MAIN MENU", bg_color=(0.25, 0.3, 0.45, 0.9), size_hint=(1, 0.25))

        def _retry(*_):
            modal.dismiss()
            self.start_session()

        def _to_menu(*_):
            modal.dismiss()
            self.manager.current = "main_menu"

        retry_btn.bind(on_release=_retry)
        menu_btn.bind(on_release=_to_menu)

        content.add_widget(go_title)
        content.add_widget(sub)
        content.add_widget(stats_lbl)
        content.add_widget(retry_btn)
        content.add_widget(menu_btn)
        modal.add_widget(content)
        modal.open()


class HangarScreen(Screen):
    """Starship catalog, unlock store, and stat upgrades."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.selected_idx = 0
        self.ship_keys = list(SHIP_CATALOG.keys())

        layout = BoxLayout(orientation='vertical', padding=dp(18), spacing=dp(12))

        # Header
        header = BoxLayout(orientation='horizontal', size_hint=(1, 0.1))
        back_btn = ModernButton(text="< BACK", bg_color=(0.3, 0.3, 0.35, 0.9), size_hint=(0.28, 1))
        back_btn.bind(on_release=self._on_back)
        self.coin_lbl = Label(text=f"❖ {storage.get_coins()}", font_size=sp(16), bold=True, color=(1.0, 0.85, 0.1, 1.0))
        header.add_widget(back_btn)
        header.add_widget(self.coin_lbl)
        layout.add_widget(header)

        # Ship Carousel Navigator
        nav_box = BoxLayout(orientation='horizontal', size_hint=(1, 0.12), spacing=dp(8))
        prev_btn = ModernButton(text="◀", size_hint=(0.2, 1))
        next_btn = ModernButton(text="▶", size_hint=(0.2, 1))
        prev_btn.bind(on_release=self._prev_ship)
        next_btn.bind(on_release=self._next_ship)

        self.ship_name_lbl = Label(text="", font_size=sp(20), bold=True, color=(0.3, 0.85, 1.0, 1.0))
        nav_box.add_widget(prev_btn)
        nav_box.add_widget(self.ship_name_lbl)
        nav_box.add_widget(next_btn)
        layout.add_widget(nav_box)

        # Ship Details & Special Power
        self.desc_lbl = Label(text="", font_size=sp(12), color=(0.8, 0.8, 0.8, 0.9), size_hint=(1, 0.12))
        layout.add_widget(self.desc_lbl)

        # Upgrade Grid
        self.upgrade_grid = GridLayout(cols=2, spacing=dp(10), size_hint=(1, 0.45))
        layout.add_widget(self.upgrade_grid)

        # Action (Select / Unlock) Button
        self.action_btn = ModernButton(text="SELECT SHIP", bg_color=(0.1, 0.6, 0.35, 0.95), size_hint=(1, 0.14))
        self.action_btn.bind(on_release=self._on_action_clicked)
        layout.add_widget(self.action_btn)

        self.add_widget(layout)

    def on_enter(self):
        current_ship = storage.get_selected_ship()
        if current_ship in self.ship_keys:
            self.selected_idx = self.ship_keys.index(current_ship)
        self._refresh_view()

    def _prev_ship(self, *args):
        self.selected_idx = (self.selected_idx - 1) % len(self.ship_keys)
        self._refresh_view()

    def _next_ship(self, *args):
        self.selected_idx = (self.selected_idx + 1) % len(self.ship_keys)
        self._refresh_view()

    def _refresh_view(self):
        ship_id = self.ship_keys[self.selected_idx]
        info = SHIP_CATALOG[ship_id]
        unlocked = storage.is_ship_unlocked(ship_id)
        selected = storage.get_selected_ship() == ship_id

        self.coin_lbl.text = f"❖ {storage.get_coins()} COINS"
        self.ship_name_lbl.text = info["name"]
        self.desc_lbl.text = f"{info['description']}\nSpecial Weapon: {info['special']}"

        # Action Button State
        if not unlocked:
            self.action_btn.text = f"UNLOCK FOR ❖ {info['cost']}"
            self.action_btn.bg_color = (0.7, 0.4, 0.1, 0.95)
        elif selected:
            self.action_btn.text = "EQUIPPED"
            self.action_btn.bg_color = (0.2, 0.4, 0.25, 0.8)
        else:
            self.action_btn.text = "EQUIP SHIP"
            self.action_btn.bg_color = (0.15, 0.55, 0.35, 0.95)

        # Build upgrade tiles
        self.upgrade_grid.clear_widgets()
        upgrade_items = [
            ("laser_power", "Laser Cannon"),
            ("shield_capacity", "Deflector Shield"),
            ("fire_rate", "Rapid Capacitor"),
            ("speed", "Thruster Boost")
        ]

        for key, display_name in upgrade_items:
            lvl = storage.get_upgrade_level(ship_id, key)
            cost = lvl * 50
            tile = BoxLayout(orientation='vertical', spacing=dp(3))
            lbl = Label(text=f"{display_name} (Lvl {lvl}/5)", font_size=sp(12), color=(0.9, 0.9, 0.9, 1.0))

            if lvl >= 5:
                up_btn = ModernButton(text="MAX", bg_color=(0.25, 0.25, 0.25, 0.7), size_hint=(1, 0.6))
            else:
                up_btn = ModernButton(text=f"+1 (❖ {cost})", bg_color=(0.2, 0.4, 0.7, 0.9), size_hint=(1, 0.6))
                up_btn.font_size = sp(12)
                up_btn.bind(on_release=lambda btn, sk=key: self._on_upgrade(ship_id, sk))

            tile.add_widget(lbl)
            tile.add_widget(up_btn)
            self.upgrade_grid.add_widget(tile)

    def _on_upgrade(self, ship_id, upgrade_key):
        if storage.upgrade_ship_stat(ship_id, upgrade_key):
            audio_manager.play("pickup")
            self._refresh_view()
        else:
            audio_manager.play("hit")

    def _on_action_clicked(self, *args):
        ship_id = self.ship_keys[self.selected_idx]
        if not storage.is_ship_unlocked(ship_id):
            if storage.unlock_ship(ship_id):
                storage.set_selected_ship(ship_id)
                audio_manager.play("shield")
                self._refresh_view()
            else:
                audio_manager.play("hit")
        else:
            storage.set_selected_ship(ship_id)
            audio_manager.play("pickup")
            self._refresh_view()

    def _on_back(self, *args):
        self.manager.current = "main_menu"


class SettingsScreen(Screen):
    """Game settings and lifetime statistics."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation='vertical', padding=dp(20), spacing=dp(14))

        # Header
        header = BoxLayout(orientation='horizontal', size_hint=(1, 0.1))
        back_btn = ModernButton(text="< BACK", bg_color=(0.3, 0.3, 0.35, 0.9), size_hint=(0.28, 1))
        back_btn.bind(on_release=lambda *_: setattr(self.manager, 'current', 'main_menu'))
        title = Label(text="SETTINGS & STATS", font_size=sp(18), bold=True, color=(0.3, 0.85, 1.0, 1.0))
        header.add_widget(back_btn)
        header.add_widget(title)
        layout.add_widget(header)

        # Settings Controls
        settings_box = BoxLayout(orientation='vertical', spacing=dp(10), size_hint=(1, 0.35))

        # Sound Toggle
        snd_row = BoxLayout(orientation='horizontal', size_hint=(1, 0.45))
        snd_lbl = Label(text="Audio Sound FX", font_size=sp(15), halign='left')
        snd_lbl.bind(size=snd_lbl.setter('text_size'))
        self.snd_btn = ModernButton(
            text="ON" if audio_manager.enabled else "OFF",
            bg_color=(0.15, 0.55, 0.3, 0.9) if audio_manager.enabled else (0.5, 0.2, 0.2, 0.9),
            size_hint=(0.35, 1)
        )
        self.snd_btn.bind(on_release=self._toggle_sound)
        snd_row.add_widget(snd_lbl)
        snd_row.add_widget(self.snd_btn)
        settings_box.add_widget(snd_row)

        layout.add_widget(settings_box)

        # Stats Section
        self.stats_lbl = Label(
            text="",
            font_size=sp(13),
            color=(0.85, 0.85, 0.9, 1.0),
            halign='center',
            size_hint=(1, 0.45)
        )
        layout.add_widget(self.stats_lbl)

        self.add_widget(layout)

    def on_enter(self):
        stats = storage.data.get("stats", {})
        self.stats_lbl.text = (
            "═══ LIFETIME PILOT STATS ═══\n\n"
            f"Missions Launched: {stats.get('games_played', 0)}\n"
            f"Enemies Destroyed: {stats.get('enemies_destroyed', 0):,}\n"
            f"Bosses Crushed: {stats.get('bosses_defeated', 0)}\n"
            f"Highest Sector: Wave {stats.get('highest_wave', 0)}\n"
            f"Total Salvaged Credits: ❖ {stats.get('total_coins_collected', 0):,}\n\n"
            "Buildozer / Android Ready | OpenGL ES 2.0 Engine"
        )

    def _toggle_sound(self, *args):
        audio_manager.enabled = not audio_manager.enabled
        storage.data["settings"]["sound_enabled"] = audio_manager.enabled
        storage.save_data()
        self.snd_btn.text = "ON" if audio_manager.enabled else "OFF"
        self.snd_btn.bg_color = (0.15, 0.55, 0.3, 0.9) if audio_manager.enabled else (0.5, 0.2, 0.2, 0.9)
        self.snd_btn._update_graphics()
