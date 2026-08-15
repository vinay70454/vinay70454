"""Automated unit test suite for Cosmic Defender game engine and components.
"""

import math
import os
import shutil
import tempfile
import unittest
import wave

from audio_synth import AudioManager, generate_laser_sound, generate_explosion_sound, generate_pickup_sound
from particle_system import ParallaxStarfield, Particle, ParticleSystem, Shockwave
from storage import StorageManager, SHIP_CATALOG


class TestStorageManager(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.test_file = os.path.join(self.test_dir, "test_save.json")
        self.sm = StorageManager(filename=self.test_file)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_default_values(self):
        self.assertEqual(self.sm.get_high_score(), 0)
        self.assertEqual(self.sm.get_coins(), 0)
        self.assertEqual(self.sm.get_selected_ship(), "interceptor")
        self.assertTrue(self.sm.is_ship_unlocked("interceptor"))
        self.assertFalse(self.sm.is_ship_unlocked("dreadnought"))

    def test_high_score_persistence(self):
        self.assertTrue(self.sm.set_high_score(500))
        self.assertEqual(self.sm.get_high_score(), 500)
        # Should not overwrite with a lower score
        self.assertFalse(self.sm.set_high_score(200))
        self.assertEqual(self.sm.get_high_score(), 500)

    def test_coin_transactions_and_unlocks(self):
        self.sm.add_coins(400)
        self.assertEqual(self.sm.get_coins(), 400)

        # Unlock Vanguard
        cost = SHIP_CATALOG["vanguard"]["cost"]
        self.assertTrue(self.sm.unlock_ship("vanguard"))
        self.assertTrue(self.sm.is_ship_unlocked("vanguard"))
        self.assertEqual(self.sm.get_coins(), 400 - cost)

    def test_ship_upgrades(self):
        self.sm.add_coins(300)
        lvl_before = self.sm.get_upgrade_level("interceptor", "laser_power")
        self.assertEqual(lvl_before, 1)

        # Upgrade level 1 -> 2 (costs 1 * 50 = 50 coins)
        success = self.sm.upgrade_ship_stat("interceptor", "laser_power")
        self.assertTrue(success)
        self.assertEqual(self.sm.get_upgrade_level("interceptor", "laser_power"), 2)


class TestAudioSynthesis(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_generate_wav_files(self):
        laser_path = os.path.join(self.test_dir, "laser.wav")
        explosion_path = os.path.join(self.test_dir, "explosion.wav")
        pickup_path = os.path.join(self.test_dir, "pickup.wav")

        generate_laser_sound(laser_path)
        generate_explosion_sound(explosion_path)
        generate_pickup_sound(pickup_path)

        for p in [laser_path, explosion_path, pickup_path]:
            self.assertTrue(os.path.exists(p))
            self.assertGreater(os.path.getsize(p), 100)
            # Verify WAV header integrity
            with wave.open(p, "rb") as wf:
                self.assertEqual(wf.getnchannels(), 1)
                self.assertEqual(wf.getsampwidth(), 2)
                self.assertEqual(wf.getframerate(), 22050)
                self.assertGreater(wf.getnframes(), 0)


class TestParticleSystem(unittest.TestCase):
    def test_starfield_motion(self):
        starfield = ParallaxStarfield(width=500, height=800, star_count=20)
        initial_y = [s.y for s in starfield.stars]
        starfield.update(0.1)
        for i, s in enumerate(starfield.stars):
            # Stars move downwards unless wrapped
            if s.y <= starfield.height:
                self.assertNotEqual(s.y, initial_y[i])

    def test_particle_decay_and_culling(self):
        ps = ParticleSystem()
        ps.emit_explosion(100, 100, count=15)
        self.assertGreater(len(ps.particles), 0)

        # Fast forward time
        ps.update(2.0)
        self.assertEqual(len(ps.particles), 0)

    def test_screen_shake(self):
        ps = ParticleSystem()
        ps.trigger_shake(intensity=10.0, duration=0.2)
        ps.update(0.05)
        self.assertNotEqual(ps.shake_offset, (0.0, 0.0))
        # After duration expires
        ps.update(0.3)
        self.assertEqual(ps.shake_offset, (0.0, 0.0))


class TestGameCalculations(unittest.TestCase):
    def test_radial_collision_math(self):
        # Bullet at (100, 100) radius 4
        # Enemy at (105, 100) radius 20
        dist = math.hypot(100 - 105, 100 - 100)
        self.assertEqual(dist, 5.0)
        self.assertLessEqual(dist, 4 + 20)  # Collision confirmed

        # Out of bounds
        dist_miss = math.hypot(100 - 150, 100 - 100)
        self.assertEqual(dist_miss, 50.0)
        self.assertGreater(dist_miss, 4 + 20)  # Miss confirmed


if __name__ == "__main__":
    unittest.main()
