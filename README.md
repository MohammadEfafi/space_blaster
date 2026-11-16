<div align="center">

🌐 **Language / زبان:**
**[🇬🇧 English (you are here)]** &nbsp;·&nbsp; [🇮🇷 فارسی — Click here](README.fa.md)

# SPACE BLASTER

**A fast-paced, action-packed top-down space shooter built from scratch with Python and Pygame.**

*No external sprites. No audio files. Everything is procedurally generated.*

[![CI](https://github.com/MohammadEfafi/space_blaster/actions/workflows/ci.yml/badge.svg)](https://github.com/MohammadEfafi/space_blaster/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![Pygame](https://img.shields.io/badge/Pygame-CE-green.svg?style=flat&logo=pygame&logoColor=white)](https://pyga.me/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

<br>

### Ready to Play?
**No installation, no Python, no setup. Just download and double-click!**

<br>

<a href="https://mohammad-efafi.itch.io/space-blaster">
  <img src="https://img.shields.io/badge/PLAY_ON_ITCH.IO-15_MB-00C853?style=for-the-badge&logo=itch.io&logoColor=white" alt="Play on itch.io" height="55">
</a>

<br><br>

**Click the green button above to download**

<br>

*For Windows 10/11 • 15 MB • 100% Free*

<br>

<sub>
If itch.io is blocked in your region, use these direct mirrors:
<br>
<a href="https://gh-proxy.com/https://github.com/MohammadEfafi/space_blaster/releases/latest/download/SpaceBlaster.exe">Direct Download 1 (gh-proxy)</a>
&nbsp;·&nbsp;
<a href="https://xget.xi-xu.me/gh/MohammadEfafi/space_blaster/releases/latest/download/SpaceBlaster.exe">Direct Download 2 (xget)</a>
</sub>

<br>

[Report Bug](https://github.com/MohammadEfafi/space_blaster/issues) · [Request Feature](https://github.com/MohammadEfafi/space_blaster/issues)

</div>

---

## About the Game

**SPACE BLASTER** is a modern take on the classic arcade space shooter. It features fluid movement, screen-shaking explosions, and intense boss battles. The entire game — graphics, particle effects, UI, and sound effects — is generated at runtime using pure code.

Whether you're dodging bullet hell attacks from the **Omega Core** or pushing your score to the top of the **Hall of Fame**, every run is a test of reflexes and strategy.

<div align="center">
  <img src="screenshots/gameplay.gif" width="90%" alt="Gameplay Preview" />
</div>

## Key Features

- **4 Unique Playable Ships:** Interceptor, Vanguard, Phantom, and Devastator — each with distinct stats, weapon loadouts, and playstyles.
- **8 Enemy Types:** From fast kamikaze drones to heavy bombers and snipers.
- **4 Epic Boss Fights:** Featuring multi-phase mechanics, unique attack patterns, and dynamic visual telegraphs.
- **Procedural Generation:** No `.png` or `.wav` files. Everything is drawn with math and synthesized via waveforms.
- **Modern Game Feel:** Trauma-based screen shake, particle pooling, hit-stun, and smooth UI animations.
- **Dynamic Wave System:** Difficulty scales smoothly, introducing elite enemies, advanced waves, and random boss encounters.
- **Persistent Leaderboard:** Local high-score saving with top-10 tracking and detailed stats.

---

## Gallery

### The Fleet

<div align="center">
  <img src="screenshots/interceptor.png" width="49%" alt="Interceptor" />
  <img src="screenshots/vanguard.png" width="49%" alt="Vanguard" />
  <br>
  <img src="screenshots/phantom.png" width="49%" alt="Phantom" />
  <img src="screenshots/devastator.png" width="49%" alt="Devastator" />
</div>

### Boss Encounters

<div align="center">
  <img src="screenshots/dreadnought.png" width="49%" alt="Iron Dreadnought" />
  <img src="screenshots/sentinel.png" width="49%" alt="Void Sentinel" />
  <br>
  <img src="screenshots/wraith.png" width="49%" alt="Plasma Wraith" />
  <img src="screenshots/omega.png" width="49%" alt="Omega Core" />
</div>

### Hall of Fame

<div align="center">
  <img src="screenshots/leaderboard.png" width="80%" alt="Leaderboard" />
</div>

---

## How to Play

### Option 1: Download the Executable (Windows)

You don't need Python to play!

1. Go to the [Releases](https://github.com/MohammadEfafi/space_blaster/releases/latest) page.
2. Download `SpaceBlaster.exe`.
3. Double-click and play!

*Note: Windows Defender might show a false positive due to PyInstaller. Click "More info" and then "Run anyway".*

### Option 2: Run from Source

```bash
# 1. Clone the repository
git clone https://github.com/MohammadEfafi/space_blaster.git
cd space_blaster

# 2. Create a virtual environment
python -m venv .venv

# Activate the virtual environment
# Windows:
.venv\Scripts\activate

# Linux / macOS:
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Launch the game
python main.py
```

## Controls

| **Action** | **Key** |
| :--- | :--- |
| **Movement** | `W`, `A`, `S`, `D` or Arrow Keys |
| **Shoot** | `Space` |
| **Pause** | `P` or `Esc` |
| **Fullscreen** | `F11` |

---

## Architecture & Technology

This project is built with a strong focus on **clean architecture** and **performance**:

- **Game Core:** Custom Scene Manager with deferred state transitions.
- **Collision System:** Spatial Hash Grid for broad-phase detection and circle-based collision for narrow-phase detection.
- **Particle Engine:** Object Pooling architecture to manage thousands of particles without frame drops.
- **Camera:** Trauma-based screen shake (Squirrel Eiseloh method) with dynamic zoom.
- **Audio:** Procedural sound synthesis (generating `.wav` buffers in memory using `math` and `array`).
- **Testing:** Automated CI pipeline with `pytest` to ensure the stability of core game logic.

---

## License

Released under the MIT License. See the `LICENSE` file for more information.

<div align="center">
  <b>Made with Python</b>
</div>
