# AIAvatar Unreal Project – Setup Guide

This guide explains how to build and run the **AIAvatar** Unreal Engine side of the AI-Powered MetaHuman Avatar System.  
By the end you will have:

1. A UE 5.x project (`ue/AIAvatar.uproject`) compiled with C++ sources (`AvatarManager`, `UdpReceiverComponent`).
2. Runtime Audio Import & MetaHuman Lip Sync plugins enabled.
3. A level containing your MetaHuman avatar driven by **Python orchestrator** audio over UDP (default `127.0.0.1:5555`).

---

## 0 . Prerequisites

| Component | Version / Notes |
|-----------|-----------------|
| Unreal Engine | **5.2 or newer** (Epic Games Launcher or source build). |
| Visual Studio 2022 (Win) / Xcode 14 (macOS) | C++ workload enabled. |
| Git-cloned repository | Same folder structure as this repo (`ue/…`). |
| Plugins | • **Runtime Audio Importer**  <br> • **Runtime MetaHuman Lip Sync**  <br> *(free on Unreal Marketplace)* |
| MetaHuman Asset | Any MetaHuman downloaded via Quixel Bridge. |

> **Tip:** Install the plugins *before* opening the project the first time to avoid extra compile cycles.

---

## 1 . Project Generation

1. Open a terminal at repository root. Run:
   ```bash
   cd ue
   ```
2. **Windows:**  
   ```powershell
   & "C:\Program Files\Epic Games\UE_5.2\Engine\Build\BatchFiles\GenerateProjectFiles.bat" AIAvatar.uproject
   ```
   **macOS / Linux:**  
   ```bash
   "/Applications/Epic Games/UE_5.2/GenerateProjectFiles.sh" -project="AIAvatar.uproject"
   ```
3. Double-click **AIAvatar.sln** (Win) or open **AIAvatar.xcworkspace** (macOS) and **Build** once to let UE compile initial modules.

---

## 2 . Opening & Compiling in Unreal Editor

1. Launch **AIAvatar.uproject**.  
2. Unreal will detect C++ code and trigger a compile if you didn’t pre-build. Wait for **Hot Reload Complete**.
3. Verify these modules appear in **Output Log**:  
   ```
   LogModules: AIAvatar loaded
   LogModules: RuntimeAudioImporter loaded
   LogModules: MetaHumanRuntimeLipSync loaded
   ```

---

## 3 . Enable / Verify Plugins

Inside the editor:

1. Edit ➜ Plugins.  
2. Search for **Runtime Audio Importer** and **MetaHuman Runtime Lip Sync**; make sure both are **Enabled**.  
3. Restart the editor if prompted.

---

## 4 . Preparing a Level

1. Add / import your **MetaHuman** to the project if not already present.  
2. Create or open a level (e.g., `StarterMap`).  
3. **Drag** the MetaHuman blueprint into the scene.  
4. **Add the AI Manager:**
   - Place **`AvatarManager`** actor (from **All Classes** search) in the level.
   - Select it; in **Details**:
     * **Face Mesh:** choose the MetaHuman face skeletal mesh component (usually `Face`) to let lip sync drive morphs.  
     * **LipSyncComponent:** if not auto-added, add a **MetaHuman Runtime Lip Sync Component** and assign here.  
     * **AudioDirectory:** leave default (`<Project>/Content/Audio`) or change to match Python’s `audio_output_path`.

5. Compile/Save level and set it as **Default Map** (Edit ➜ Project Settings ➜ Maps & Modes).

---

## 5 . Running with Python Orchestrator

1. In another terminal (repo root), set your env vars (`TWITCH_TOKEN`, `OPENAI_API_KEY`, `ELEVEN_API_KEY`, …) then run:
   ```bash
   python run_avatar_bot.py
   ```
   The bot will generate audio files into `./audio_output` and send a UDP message to UE on **port 5555**.

2. Press ▶ **Play** in Unreal.  
   - Upon first UDP packet you should see **log lines**:  
     ```
     UDP message received: audio_output_0.mp3
     Started audio playback
     Started lip sync
     ```
   - The MetaHuman should mouth the words.

> To test before the bot is live: right-click a `.mp3` or `.wav` in `Content/Audio` and call **TestAudioPlayback** on the `AvatarManager` in the **Details** panel.

---

## 6 . Packaging (Standalone EXE)

1. Edit ➜ Project Settings ➜ Packaging  
   - Add `Content/Audio` to **Additional Non-Asset Directories to Package**.  
2. Platforms ➜ Windows/Mac ➜ **Package Project**.  
3. The packaged build will still listen on port 5555; launch the Python orchestrator separately.

---

## 7 . Troubleshooting

| Symptom | Fix |
|---------|-----|
| `UDP Receiver failed to bind port` | Another app uses 5555. Change `UdpPort` on `UdpReceiverComponent` **and** `host/port` in Python config. |
| Audio plays but mouth doesn’t move | Ensure `LipSyncComponent` is attached and `Face Mesh` property is set. Check plugin enabled. |
| No audio heard | Confirm audio files actually appear in `<Project>/Content/Audio` (AvatarManager copies on import). Check volume & that MetaHuman audio component is 2D or near camera. |
| Skipped tests in Python (`pytest-asyncio`) | Add `pytest-asyncio` to pip dev requirements. |

---

## 8 . Contributing & Support

Pull requests welcome! For Unreal-specific issues, open an issue with:

* UE version  
* Log output (from **Saved/Logs** folder)  
* Steps to reproduce  

Happy streaming!  
— The HockHead / AIAvatar Team
