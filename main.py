"""Cosmic Defender: Stellar Assault
Main application entry point, screen manager configuration, and Android lifecycle handler.
"""

import os
import sys

# Configure default portrait mobile resolution on desktop for testing
from kivy.config import Config
Config.set('graphics', 'width', '420')
Config.set('graphics', 'height', '750')
Config.set('graphics', 'resizable', '1')
Config.set('kivy', 'exit_on_escape', '0')  # Handle back button manually

from kivy.app import App
from kivy.core.window import Window
from kivy.uix.screenmanager import ScreenManager, FadeTransition

from storage import storage
from ui_screens import GameScreen, HangarScreen, MainMenuScreen, SettingsScreen


class CosmicDefenderApp(App):
    """Main Kivy Application Class."""

    def build(self):
        self.title = "Cosmic Defender: Stellar Assault"
        self.icon = "assets/icon.png"

        # Initialize Screen Manager
        self.sm = ScreenManager(transition=FadeTransition(duration=0.25))

        self.main_menu = MainMenuScreen(name="main_menu")
        self.game_screen = GameScreen(name="game_screen")
        self.hangar_screen = HangarScreen(name="hangar_screen")
        self.settings_screen = SettingsScreen(name="settings_screen")

        self.sm.add_widget(self.main_menu)
        self.sm.add_widget(self.game_screen)
        self.sm.add_widget(self.hangar_screen)
        self.sm.add_widget(self.settings_screen)

        # Android hardware back button handler
        Window.bind(on_keyboard=self._on_key_down)

        return self.sm

    def _on_key_down(self, window, keycode, scancode, codepoint, modifier):
        """Handle Android back button (keycode 27) and Escape key."""
        if keycode == 27:  # Android back key / ESC
            if self.sm.current == "game_screen":
                # Pause game if active
                if self.game_screen.game_widget.is_playing and not self.game_screen.game_widget.is_paused:
                    self.game_screen._show_pause_modal()
                    return True
                else:
                    self.sm.current = "main_menu"
                    return True
            elif self.sm.current in ["hangar_screen", "settings_screen"]:
                self.sm.current = "main_menu"
                return True
            elif self.sm.current == "main_menu":
                # Exit app
                return False
        return False

    def on_pause(self):
        """Android lifecycle: Called when app is placed into background or screen turns off."""
        if self.sm.current == "game_screen" and self.game_screen.game_widget.is_playing:
            self.game_screen.game_widget.pause_game()
        return True

    def on_resume(self):
        """Android lifecycle: Called when app returns from background."""
        pass


if __name__ == "__main__":
    CosmicDefenderApp().run()
