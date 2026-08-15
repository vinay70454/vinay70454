# 🚀 Cosmic Defender: Stellar Assault (Python for Android)

A complete, high-octane 2D arcade space shooter game built with **Python & Kivy**, engineered specifically for **Android mobile devices** (with full multi-touch support, responsive DPI scaling, and hardware back-button integration) while also being 100% playable on **Windows, macOS, and Linux**.

---

## 🌟 Game Highlights & Features

- **Mobile-First Touch Navigation**:
  - Drag anywhere on the screen to control your starship with silky smooth interpolation.
  - Smart vertical touch offset (`dp(55)`) so your thumb never obstructs the ship or oncoming projectiles.
  - On-screen touch buttons for pause, screen-clearing EMP bomb, and interactive menus.
- **Dynamic Wave Progression**:
  - **Asteroids**: Tumbling hazards that split into smaller high-speed fragments when destroyed.
  - **Scout Fighters**: Agile interceptors with sinusoidal zigzagging dive patterns.
  - **Heavy Cruisers**: Armored dreadnoughts firing aiming blaster rounds.
  - **Epic Boss Battles**: Giant motherships appearing every 4 waves with multi-phase attacks and health bars.
- **Power-Ups & Drops**:
  - ❖ **Salvage Credits**: Currency dropped by defeated enemies.
  - 🛡️ **Deflector Shield**: Restores shields and absorbs damage.
  - ⚡ **Spread Cannon**: Fires a 3-way spread laser barrage.
  - 🔥 **Rapid Fire**: 2x fire rate for 8 seconds.
  - 💣 **EMP Shockwave Bomb**: Screen-clearing blast with camera shake.
  - 🔧 **Hull Repair**: Restores hull armor.
- **Ship Hangar & Upgrade Shop**:
  - **Nova Interceptor**: High speed scout craft (Balanced).
  - **Aegis Vanguard**: Heavy assault ship with built-in spread cannons.
  - **Titan Dreadnought**: Massive destroyer armed with dual heavy plasma cannons.
  - Upgrade **Laser Power**, **Deflector Shield**, **Rapid Capacitor**, and **Thruster Speed** up to Level 5.
- **Zero Asset Headaches (Pure Python 8-bit Audio)**:
  - Procedural sound synthesizer generates retro 8-bit sound effects (laser, explosion, shield, pickup, EMP bomb) dynamically using standard Python math and wave modules.
- **Android Ready**:
  - Native lifecycle management (`on_pause`, `on_resume`).
  - Android hardware back button handler.
  - Preconfigured `buildozer.spec` and automated **GitHub Actions CI/CD workflow** for 1-click cloud APK compilation.

---

## 🕹️ Running the Game on PC (Windows / Mac / Linux)

### 1. Setup Virtual Environment
```bash
# In the cosmic_defender folder:
python -m venv .venv

# Activate environment:
# Windows (PowerShell):
.\.venv\Scripts\Activate.ps1
# Windows (CMD):
.\.venv\Scripts\activate.bat
# Linux / macOS:
source .venv/bin/activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Launch the Game
```bash
python main.py
```
> The game will launch in a simulated portrait mobile phone window (420x750) with mouse-drag acting as finger touch.

---

## 📱 Building the Android APK

You have two easy ways to compile the game into an installable Android `.apk`:

### Option A: Free 1-Click Cloud Build (GitHub Actions - Recommended)
You don't need Linux or Android SDK installed on your PC!

1. Push this project folder to a GitHub repository:
   ```bash
   git init
   git add .
   git commit -m "Initial Cosmic Defender Android Game"
   git remote add origin https://github.com/<your-username>/<your-repo-name>.git
   git push -u origin main
   ```
2. Go to the **Actions** tab on your GitHub repository.
3. The workflow **"Build Android APK"** will run automatically.
4. Once finished, download the compiled `.apk` file from the **Artifacts** section and install it directly on your Android phone!

---

### Option B: Local Build with Buildozer (Linux or WSL2)
Buildozer requires a Linux environment (Ubuntu or WSL2 on Windows):

1. **Install Prerequisites**:
   ```bash
   sudo apt update
   sudo apt install -y git zip unzip openjdk-17-jdk python3-pip autoconf libtool pkg-config zlib1g-dev \
     libncurses5-dev libncursesw5-dev libtinfo5 cmake libffi-dev libssl-dev build-essential \
     cython3 libsdl2-dev libsdl2-image-dev libsdl2-mixer-dev libsdl2-ttf-dev
   ```

2. **Install Buildozer**:
   ```bash
   pip install --upgrade buildozer Cython
   ```

3. **Compile the APK**:
   ```bash
   buildozer -v android debug
   ```
   The generated `.apk` will be saved inside the `bin/` directory (e.g. `bin/cosmicdefender-1.0.0-arm64-v8a_armeabi-v7a-debug.apk`).

4. **Deploy Directly to a Connected Phone via USB**:
   ```bash
   buildozer android deploy run
   ```

---

## 📂 Project Architecture

```
cosmic_defender/
├── main.py                      # Kivy App entrypoint & Android lifecycle management
├── game_engine.py               # 60 FPS physics loop, entities, spawner, and OpenGL rendering
├── ui_screens.py                # Main Menu, Game Screen, Hangar/Shop, HUD, and Settings
├── particle_system.py           # Starfield parallax, explosion particles, and screen shake
├── audio_synth.py               # Procedural 8-bit audio waveform generator and audio manager
├── storage.py                   # Persistent player data (scores, coins, upgrades)
├── test_game.py                 # Automated test suite
├── buildozer.spec               # Android packaging configuration
├── requirements.txt             # Python dependencies
├── .github/
│   └── workflows/
│       └── build_apk.yml        # Automated GitHub Actions APK build workflow
└── README.md                    # Documentation
```

---

## 🧪 Running Automated Tests

```bash
python -m unittest test_game.py
```
Verifies storage persistence, audio waveform generation, particle physics, and collision mathematics.
