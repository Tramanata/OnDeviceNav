# OnDeviceNav — AR Indoor Navigation

OnDeviceNav is an open-source Android application that enables real-time, turn-by-turn indoor navigation using Augmented Reality. The app requires no pre-built floor plans, no cloud connectivity, and no external infrastructure. Everything — from environment mapping to object detection to pathfinding — runs entirely on the device.

Point the camera at the floor, scan the space, tap a destination, and follow the AR path.

---

## Table of Contents

1. [Features](#features)
2. [How It Works](#how-it-works)
   - [SLAM & Environment Mapping](#1-slam--environment-mapping)
   - [Computer Vision & Obstacle Detection](#2-computer-vision--obstacle-detection)
   - [Route Planning & Navigation](#3-route-planning--navigation)
3. [Architecture Overview](#architecture-overview)
4. [Requirements](#requirements)
5. [Getting the Code](#getting-the-code)
6. [Running in Android Studio](#running-in-android-studio)
7. [Project Structure](#project-structure)
8. [Key Configuration Parameters](#key-configuration-parameters)
9. [Navigation State Machine](#navigation-state-machine)
10. [Dependencies](#dependencies)
11. [Contributing](#contributing)
12. [License](#license)

---

## Features

- **Fully on-device** — no internet connection required at runtime
- **No pre-built maps** — the environment is mapped live using ARCore plane detection
- **Real-time obstacle detection** — YOLO11 detects people, furniture, luggage, and other obstacles and routes around them dynamically
- **Wall-aware pathfinding** — vertical plane detection prevents paths from cutting through walls
- **Turn-by-turn HUD** — direction and distance shown in feet with plain English instructions
- **Home screen UI** — clean launcher with Begin Navigating and How to Use options
- **Automatic obstacle expiry** — dynamic obstacles decay after 10 seconds; the path recovers when the way is clear

---

## How It Works

OnDeviceNav is built on three tightly integrated subsystems: a SLAM-based environment mapper, a computer vision obstacle detector, and an A\*-based route planner. Each subsystem runs on its own thread and communicates through thread-safe shared state.

### 1. SLAM & Environment Mapping

**File:** [`NavGrid.java`](app/src/main/java/com/google/ar/core/examples/java/computervision/navigation/NavGrid.java)

This subsystem is responsible for building a navigable 2D map of the physical environment in real time.

#### How it works

ARCore continuously tracks planar surfaces in the camera feed using visual-inertial odometry. OnDeviceNav consumes these tracked planes and projects them into a 100×100 grid, where each cell represents a 20 cm × 20 cm square of floor space. The grid covers a 20 m × 20 m area centered on the first detected floor plane.

**Grid initialization:**
The grid origin is established the moment ARCore detects the first horizontal upward-facing plane with a minimum extent of 0.5 m in both X and Z directions. The Y-coordinate (height) of that plane is stored as the `floorWorldY` reference — every subsequent height comparison uses this value to determine whether a surface is floor-level or elevated.

**Two-pass plane classification:**
On every rebuild cycle (at most once per second), all currently tracked planes are processed in two passes:

- **Pass 1 — Floor surfaces:** Horizontal upward-facing planes whose Y position is within 30 cm of `floorWorldY` are treated as walkable floor. Their polygon boundaries are projected onto the grid and cells inside the polygon are marked `CELL_WALKABLE`.
- **Pass 2 — Elevated surfaces:** Horizontal planes more than 30 cm above the floor — desks, counters, sofa tops, shelves — are treated as static obstacles. Their XZ footprints are stamped `CELL_STATIC_OBSTACLE` on top of any walkable cells, ensuring that A\* routes around furniture rather than through it.

**Polygon erosion (wall-bleed prevention):**
ARCore plane polygons occasionally extend slightly past physical wall boundaries because the sensor cannot see through walls. To counteract this, a cell is only marked `CELL_WALKABLE` if all four of its cardinal-neighbour cells also fall inside the same polygon. This morphological erosion creates a natural 20 cm inset buffer at every plane edge, preventing paths from running along surface boundaries that may abut walls.

**Vertical plane wall projection:**
Vertical planes detected by ARCore (walls, door frames, columns) are projected onto the XZ floor plane. Their bounding boxes are expanded by 40 cm in every direction (two grid cells), and the enclosed cells are marked `CELL_STATIC_OBSTACLE`. This safety margin ensures that A\* keeps paths at least 40 cm away from every detected wall, even accounting for ARCore measurement uncertainty.

**Cell state model:**

| State | Value | Meaning |
|---|---|---|
| `CELL_UNKNOWN` | 0 | Not yet scanned |
| `CELL_WALKABLE` | 1 | Confirmed floor surface |
| `CELL_OBSTACLE` | 2 | Dynamic obstacle from YOLO (decays) |
| `CELL_STATIC_OBSTACLE` | 3 | Elevated surface or wall footprint (rebuilt each cycle) |

**Threading:**
Grid rebuilds run on a dedicated single-thread background executor, protected by a `ReentrantLock`. The GL thread only reads snapshots (deep copies) of the grid for pathfinding, so the AR render loop is never blocked by map updates.

---

### 2. Computer Vision & Obstacle Detection

**Files:** [`ObjectDetectorHelper.java`](app/src/main/java/com/google/ar/core/examples/java/computervision/ObjectDetectorHelper.java), [`NavigationManager.java`](app/src/main/java/com/google/ar/core/examples/java/computervision/navigation/NavigationManager.java)

This subsystem detects moving and static obstacles in the camera frame and projects their locations into the nav grid so the route planner can avoid them.

#### How it works

**YOLO11 on-device inference:**
Every 10 frames (approximately 3 times per second at 30 fps), the current camera frame is sent to a TensorFlow Lite YOLO11 model running on 4 CPU threads. The model takes a resized bitmap as input and outputs bounding boxes, confidence scores, and class IDs for every detected object.

The detector supports three TFLite output formats automatically:
- **Standard format** — single output tensor with `[batch, boxes, 4+classes]` layout
- **Split-2 format** — separate coordinate and class-score tensors (channel-first or channel-last)
- **AI Hub 3-tensor format** — separate box, score, and class index tensors with pixel-space coordinates

The correct format is detected automatically by inspecting tensor shapes and data types at initialization, so the same code works with multiple YOLO11 export configurations.

**Confidence filtering and NMS:**
Detections below a confidence threshold of 0.40 are discarded. The remaining detections are passed through class-aware Non-Maximum Suppression with an IoU threshold of 0.45, eliminating duplicate bounding boxes for the same object.

**Obstacle class filtering:**
Not every detected object is a navigation obstacle. The system filters to a curated set of COCO class IDs that are physically large enough and floor-proximate enough to block a walking path:

| Class ID | Label |
|---|---|
| 0 | person |
| 13 | bench |
| 24 | backpack |
| 26 | handbag |
| 28 | suitcase |
| 56 | chair |
| 57 | couch |
| 58 | potted plant |
| 59 | bed |
| 60 | dining table |
| 62 | tv / monitor |
| 63 | laptop |
| 74 | clock |

All other classes (vehicles, animals, food, small items) are ignored.

**Camera intrinsic ray-casting:**
For each accepted detection, the system must determine where on the floor the detected object sits in world space. It does this using ARCore's camera intrinsics:

1. Five sample points are taken across the bottom edge of the bounding box (at 10%, 30%, 50%, 70%, 90% of the box width) to cover the full physical width of the obstacle rather than just its center.
2. Each sample image pixel `(imgX, imgY)` is converted to a normalized camera-space ray direction using the focal length `(fx, fy)` and principal point `(cx, cy)`:
   ```
   rayCam = [(imgX - cx) / fx,  (imgY - cy) / fy,  1.0]
   ```
3. The ray direction is transformed from camera space to world space using ARCore's camera rotation matrix.
4. The ray is intersected with the floor plane at `Y = floorWorldY`. Rays that are parallel to the floor, point backwards, or intersect more than 10 m away are rejected.
5. The resulting world-space hit point `(hitX, hitZ)` is converted to a grid cell and stamped as `CELL_OBSTACLE` with a radius that scales with the detected bounding box width, clamped to 1–4 grid cells (20–80 cm radius).

**Adaptive obstacle radius:**
```java
int obstacleRadius = Math.max(1, Math.min(4, (int)(boxW * imageWidth / 80f)));
```
A box that fills 80 pixels of a typical image produces a 1-cell radius. A box that fills 320 pixels produces a 4-cell radius. This ensures that a distant, small-looking person takes up less grid space than a chair right in front of the camera.

**Obstacle decay:**
Every dynamic obstacle carries a frame-counter expiry equal to `currentFrame + 300` (10 seconds at 30 fps). Once per second the decay routine scans the grid and reverts expired `CELL_OBSTACLE` cells to `CELL_UNKNOWN`, allowing the path to recover automatically when an obstacle moves away.

---

### 3. Route Planning & Navigation

**Files:** [`AStarPlanner.java`](app/src/main/java/com/google/ar/core/examples/java/computervision/navigation/AStarPlanner.java), [`NavigationManager.java`](app/src/main/java/com/google/ar/core/examples/java/computervision/navigation/NavigationManager.java), [`NavigationOverlayView.java`](app/src/main/java/com/google/ar\core/examples/java/computervision/NavigationOverlayView.java)

This subsystem computes the optimal path through the nav grid and translates it into real-time turn-by-turn instructions rendered as an AR HUD.

#### How it works

**A\* pathfinding on an 8-connected grid:**
When the user taps a destination, the current camera world position becomes the start cell and the tapped floor point becomes the goal cell. A\* searches the 100×100 grid using octile distance as an admissible heuristic, allowing movement in all 8 directions (cardinal + diagonal).

Movement costs:
- Cardinal step: `1.0`
- Diagonal step: `1.414` (√2)
- Adjacent-to-obstacle penalty: `+4.0` — strongly discourages paths that pass close to walls or obstacles, promoting center-of-corridor routing without hard-blocking those cells
- Unscanned cell penalty: `+4.0` — the planner can traverse unscanned cells when no alternative exists, but always prefers confirmed walkable floor

Start and goal cells must not be solid obstacles. If either is blocked, pathfinding immediately returns no-path without running the full search.

**String-pulling (path simplification):**
The raw A\* output is a sequence of adjacent grid cells — typically hundreds of nodes for a modest distance. A Bresenham line-of-sight pass reduces this to only the essential waypoints:

Starting from the first cell, the algorithm tests whether a straight line can be drawn to increasingly distant cells without crossing any non-`CELL_WALKABLE` cell. The moment LOS fails, the last valid cell is kept as a waypoint and the anchor advances. This reduces a 200-node cell sequence to a handful of world-space waypoints, producing smooth-looking AR paths without visible stair-stepping.

**Dynamic replanning:**
While navigating, YOLO detection runs every 10 frames. If a new obstacle is stamped to the grid that overlaps or borders the current planned path, A\* reruns automatically on the background executor. The new path replaces the old one seamlessly — the user never has to stop or reset. If no new path exists (the obstacle fully blocks the only route), the HUD prompts the user to move back.

**Waypoint advancement:**
The system tracks which waypoint in the path list the user is currently heading toward (`nextPathIndex`). Each frame, the XZ distance from the camera to the current waypoint is computed. When that distance drops below 0.35 m, the index advances to the next waypoint. When the final waypoint (the destination) is reached within 0.35 m, the state transitions to `ARRIVED`.

**Turn-by-turn HUD:**
Each frame during navigation, the bearing angle to the next waypoint is computed using the camera's view matrix:

```
forwardWorld = [-viewMatrix[2], -viewMatrix[10]]   (XZ only)
toWaypoint   = [waypointX - camX, waypointZ - camZ]
angleDeg     = atan2(cross(forward, toWaypoint), dot(forward, toWaypoint))
```

The signed angle maps to one of six direction labels:

| Angle range | Instruction |
|---|---|
| `\|angle\| ≤ 15°` | ↑ Go straight |
| `-45° < angle < -15°` | ↖ Bear left |
| `15° < angle < 45°` | ↗ Bear right |
| `angle < -45°` | ← Turn left |
| `angle > 45°` | Turn right → |
| `\|angle\| > 135°` | Turn around ↩ |

Distance to the next waypoint is displayed in feet beneath the direction label.

**3D AR path rendering:**
The computed path is rendered directly into the AR scene using OpenGL. An orange `GL_LINE_STRIP` connects all waypoints at floor level, with `GL_POINTS` markers at each node. The start position is shown as a green marker (2× size) and the destination as a red marker (2× size). Point sizes use perspective-correct scaling (`POINT_SIZE_COEFF / gl_Position.w`) so markers appear as a consistent physical size (~5 cm) at any distance.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│                  MainActivity.java                   │
│           (Home screen: Begin / How to Use)          │
└────────────────────────┬────────────────────────────┘
                         │ startActivity
┌────────────────────────▼────────────────────────────┐
│            ComputerVisionActivity.java               │
│  ┌──────────────┐   ┌──────────────────────────────┐│
│  │  GL Thread   │   │      Background Executor     ││
│  │              │   │                              ││
│  │ ARCore frame │──▶│  NavGrid.rebuildFromPlanes() ││
│  │ Tap handling │   │  AStarPlanner.findPath()     ││
│  │ HUD update   │   │  NavGrid.decayObstacles()    ││
│  └──────┬───────┘   └──────────────────────────────┘│
│         │                                            │
│  ┌──────▼───────────────────────────┐               │
│  │      Inference Executor          │               │
│  │  ObjectDetectorHelper.detect()   │               │
│  │  (YOLO11 TFLite, every 10 frames)│               │
│  └──────────────────────────────────┘               │
│                                                      │
│  ┌──────────────────────────────────────────────┐   │
│  │             NavigationOverlayView             │   │
│  │   YOLO bounding boxes + HUD direction/dist    │   │
│  └──────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
```

---

## Requirements

### Hardware
- Android device with **ARCore support** (see the [full device list](https://developers.google.com/ar/devices))
- Android API level **24 or higher** (Android 7.0 Nougat)
- Rear-facing camera (front camera is not supported by ARCore plane detection)
- Recommended: a device with a processor capable of running TFLite inference smoothly (mid-range 2019+ chipset or better)

### Software
- **Android Studio** Flamingo (2022.2.1) or newer — Hedgehog or Iguana recommended
- **Android SDK** with API level 36 installed
- **Android NDK** (installed automatically via Android Studio if not present)
- **Java 17** (configured in the project's `compileOptions`)
- **Google Play Services for AR** — installed automatically on supported devices via the Play Store; the app will prompt the user to install it if missing

---

## Getting the Code

### Option 1 — Clone with Git (recommended)

Open a terminal and run:

```bash
git clone https://github.com/YourOrg/OnDeviceNav.git
cd OnDeviceNav
```

If you do not have Git installed, download it from [git-scm.com](https://git-scm.com) and follow the installer. On Windows, use Git Bash or PowerShell.

### Option 2 — Download ZIP

1. Navigate to the repository page on GitHub.
2. Click the green **Code** button.
3. Select **Download ZIP**.
4. Extract the ZIP to a folder of your choice (avoid paths with spaces).

---

## Running in Android Studio

Follow these steps exactly. Each step matters — skipping one is the most common cause of build failures.

### Step 1 — Install Android Studio

Download Android Studio from [developer.android.com/studio](https://developer.android.com/studio). Run the installer and follow the setup wizard. When prompted, install the **Android SDK**, **Android SDK Platform**, and the **Android Virtual Device** components. The default selections in the wizard are correct.

### Step 2 — Open the Project

1. Launch Android Studio.
2. On the Welcome screen, click **Open** (or **File → Open** if a project is already open).
3. Navigate to the folder where you cloned or extracted the repository.
4. Select the **root folder** (`OnDeviceNav/`) — the one that contains `build.gradle`, `settings.gradle`, and the `app/` subdirectory.
5. Click **OK**.

> **Important:** Do not open the `app/` subfolder directly. Android Studio must open the root project folder so it can find `settings.gradle` and resolve the module structure.

### Step 3 — Let Gradle Sync Complete

After opening the project, Android Studio will automatically begin a **Gradle sync**. This downloads all dependencies listed in `build.gradle` (ARCore, TensorFlow Lite, AppCompat, Material) from Maven Central and the Google Maven repository.

- Watch the progress bar at the bottom of the Android Studio window.
- The sync may take 2–5 minutes on the first run depending on your internet speed.
- Do **not** click anything or modify files during the sync.

If the sync fails, the most common causes are:

| Error | Fix |
|---|---|
| `SDK location not found` | Open **File → Project Structure → SDK Location** and set the Android SDK path |
| `Gradle version mismatch` | Click **Update Gradle** in the error banner at the top of the editor |
| `Failed to resolve dependency` | Check your internet connection; if behind a proxy, configure it in **File → Settings → Appearance & Behavior → System Settings → HTTP Proxy** |
| `Java version incompatible` | Go to **File → Settings → Build, Execution, Deployment → Build Tools → Gradle** and set Gradle JDK to **Java 17** |

### Step 4 — Install the Android SDK Platform

The project targets **API level 36**. If this platform is not installed:

1. Go to **Tools → SDK Manager**.
2. In the **SDK Platforms** tab, check **Android 16 (API 36)** or the closest available level.
3. Click **Apply** and wait for the download to finish.
4. Click **OK**.

### Step 5 — Connect Your Physical Device

ARCore **does not run on Android emulators**. You must use a real physical Android device.

1. On your Android device, go to **Settings → About Phone** and tap **Build Number** seven times to enable Developer Options.
2. Go to **Settings → Developer Options** and enable **USB Debugging**.
3. Connect your device to your computer via USB.
4. When prompted on your device, tap **Allow** to authorize USB debugging from your computer.
5. In Android Studio, open the device selector dropdown in the toolbar (it shows "No devices" by default). Your device should appear listed by its model name.

If your device does not appear:
- Try a different USB cable (data cable, not charge-only).
- Install the USB driver for your device manufacturer if on Windows (Samsung, OnePlus, etc. have manufacturer-specific drivers).
- Run `adb devices` in a terminal to confirm Android Debug Bridge sees the device.

### Step 6 — Verify ARCore Support

Check that your device appears on Google's [supported ARCore devices list](https://developers.google.com/ar/devices). If your device is not on the list, the app will install but the ARCore session will fail to initialize at runtime.

On supported devices, **Google Play Services for AR** must be installed. It is typically pre-installed or will be prompted for installation automatically when the app first launches.

### Step 7 — Add the YOLO Model File

The YOLO11 TFLite model file is not committed to the repository due to its size. You must place it manually before building.

1. Obtain the `yolo11.tflite` file. You can export one from [Ultralytics](https://docs.ultralytics.com/modes/export/) or use the pre-exported model linked in the project's Releases page.
2. Copy the file to:
   ```
   app/src/main/assets/yolo11.tflite
   ```
3. If the `assets/` folder does not exist, create it at that exact path.

The file name must be exactly `yolo11.tflite` — the app loads it by that literal name in `ObjectDetectorHelper.java`.

### Step 8 — Build and Run

1. In Android Studio, confirm your device is selected in the toolbar dropdown.
2. Click the green **Run** button (▶) or press **Shift + F10**.
3. Android Studio will compile the project, package the APK, install it on your device, and launch the app automatically.
4. The first build takes 2–4 minutes. Subsequent builds are incremental and much faster.

If the build fails:
- Read the error in the **Build** tab at the bottom of Android Studio.
- The most common build-time error is the missing `yolo11.tflite` — verify Step 7.
- A red underline in a Java file usually means the Gradle sync did not complete — re-trigger it via **File → Sync Project with Gradle Files**.

### Step 9 — Grant Camera Permission

When the app launches for the first time, Android will prompt for camera permission. Tap **Allow**. Without camera access, ARCore cannot initialize and the app will not function.

---

## Project Structure

```
OnDeviceNav/
├── app/
│   ├── src/
│   │   └── main/
│   │       ├── assets/
│   │       │   └── yolo11.tflite            # YOLO11 TFLite model (add manually)
│   │       ├── java/com/google/ar/core/examples/java/computervision/
│   │       │   ├── MainActivity.java         # Home screen launcher
│   │       │   ├── HowToUseActivity.java     # Instructions screen
│   │       │   ├── ComputerVisionActivity.java  # Main AR activity & state machine
│   │       │   ├── NavigationOverlayView.java   # Canvas HUD (YOLO boxes + direction)
│   │       │   ├── ObjectDetectorHelper.java    # TFLite YOLO11 inference
│   │       │   ├── navigation/
│   │       │   │   ├── NavGrid.java          # 2D walkable grid from ARCore planes
│   │       │   │   ├── AStarPlanner.java     # A* pathfinding with string-pulling
│   │       │   │   ├── NavigationManager.java # Orchestrates grid, A*, YOLO obstacles
│   │       │   │   └── WaypointManager.java  # ARCore anchor lifecycle
│   │       │   ├── rendering/
│   │       │   │   └── PathRenderer.java     # OpenGL path & waypoint rendering
│   │       │   └── common/rendering/
│   │       │       └── PlaneRenderer.java    # ARCore plane grid visualization
│   │       ├── res/
│   │       │   ├── layout/
│   │       │   │   ├── activity_landing.xml      # Home screen layout
│   │       │   │   ├── activity_main.xml          # AR navigation layout
│   │       │   │   └── activity_how_to_use.xml   # Instructions layout
│   │       │   └── drawable/
│   │       │       └── btn_outline.xml            # Outlined button shape
│   │       └── AndroidManifest.xml
│   └── build.gradle
├── Documentation/
│   ├── 1_SLAM_ARCore.pdf
│   ├── 2_Computer_Vision.pdf
│   └── 3_Route_Planning_Navigation.pdf
├── build.gradle
└── settings.gradle
```

---

## Key Configuration Parameters

All tunable parameters are defined as constants close to their usage site. The most important ones:

| Parameter | File | Value | Effect |
|---|---|---|---|
| `CELL_SIZE` | `NavGrid.java:18` | `0.20 m` | Grid resolution. Smaller = more precise, more compute |
| `GRID_SIZE` | `NavGrid.java:32` | `100` | Grid is 100×100 = 20 m × 20 m total coverage |
| `ELEVATED_SURFACE_THRESHOLD_M` | `NavGrid.java:30` | `0.30 m` | Height above floor at which a surface becomes an obstacle |
| Wall expansion buffer | `NavGrid.java:203` | `2 × CELL_SIZE = 0.40 m` | Safety margin around detected walls |
| `OBSTACLE_PENALTY` | `AStarPlanner.java:19` | `4.0` | Extra A\* cost for cells adjacent to obstacles |
| `UNKNOWN_PENALTY` | `AStarPlanner.java:22` | `4.0` | Extra A\* cost for unscanned cells |
| `ARRIVAL_DISTANCE_M` | `ComputerVisionActivity.java:93` | `0.35 m` | Distance at which the user is considered arrived |
| `YOLO_EVERY_N_FRAMES` | `ComputerVisionActivity.java:94` | `10` | Run YOLO inference every N frames |
| `CONF_THRESH` | `ObjectDetectorHelper.java:31` | `0.40` | Minimum YOLO detection confidence |
| `IOU_THRESH` | `ObjectDetectorHelper.java:32` | `0.45` | NMS IoU threshold |
| Obstacle radius | `NavigationManager.java:143` | `[1, 4] cells` | YOLO obstacle footprint size, scaled by bbox width |
| Obstacle expiry | `NavigationManager.java:124` | `300 frames (~10 s)` | How long a dynamic obstacle persists |
| `GRID_REBUILD_INTERVAL_MS` | `NavigationManager.java:26` | `1000 ms` | Minimum time between grid rebuilds |

---

## Navigation State Machine

The app moves through five states managed by `ComputerVisionActivity`:

```
SCANNING
  The camera is scanning the floor. ARCore is detecting planes.
  The grid is not yet initialized.
  Prompt: "Move phone slowly over the floor"
  Transition: First large horizontal plane detected → PLACE_WAYPOINTS

PLACE_WAYPOINTS
  The grid is initialized. The user taps the floor to set start + destination.
  The grid rebuilds every second as more floor is scanned.
  Transition: Tap detected on floor hit point → PATHFINDING

PATHFINDING
  A* is running on the background executor.
  Prompt: "Computing route…"
  Transition: Path found → NAVIGATING | No path found → PLACE_WAYPOINTS

NAVIGATING
  The user is following the orange AR path.
  YOLO runs every 10 frames; new obstacles trigger immediate replan.
  HUD shows direction and distance to destination.
  Reset button is visible.
  Transition: Distance to final waypoint < 0.35 m → ARRIVED

ARRIVED
  The destination has been reached.
  Prompt: "You have arrived!"
  Transition: Reset button tap → PLACE_WAYPOINTS
```

---

## Dependencies

| Library | Version | Purpose |
|---|---|---|
| `com.google.ar:core` | 1.52.0 | ARCore — plane detection, camera pose, hit testing |
| `org.tensorflow:tensorflow-lite` | 2.14.0 | On-device YOLO11 inference |
| `org.tensorflow:tensorflow-lite-support` | 0.4.4 | TFLite utility classes |
| `androidx.appcompat:appcompat` | 1.1.0 | AppCompatActivity, Toolbar |
| `com.google.android.material:material` | 1.1.0 | Material Design components |
| `de.javagl:obj` | 0.4.0 | Wavefront OBJ loader for 3D rendering assets |
| `androidx.lifecycle:lifecycle-common-java8` | 2.0.0 | Lifecycle-aware components |

All dependencies are resolved automatically via Gradle during the sync step. No manual downloads are needed except for the YOLO model file.

---

## Contributing

Contributions are welcome. To get started:

1. Fork the repository.
2. Create a feature branch: `git checkout -b feature/your-feature-name`
3. Make your changes with clear commit messages.
4. Ensure the app builds and runs on a physical ARCore-supported device.
5. Open a pull request against the `main` branch with a description of what you changed and why.

Areas where contributions are especially valuable:
- ARCore Depth API integration for metric obstacle sizing
- Bezier/Catmull-Rom path smoothing for more natural AR paths
- Corridor width validation before accepting A\* path segments
- Temporal smoothing (detection voting) to reduce YOLO false positives
- Localization / string resources for non-English languages

---

## License

The original source code in this repository is licensed under the **MIT License**. See the [`LICENSE`](LICENSE) file for the full text.

**Third-party notices:**

- **Google ARCore SDK Samples** — Portions of this codebase (particularly in the `rendering/` and `common/` packages) are derived from Google's ARCore Android SDK samples, which are Copyright 2016–2024 Google LLC and licensed under the **Apache License 2.0**. The original copyright headers in those files are preserved as required. Apache 2.0 is compatible with MIT — you may use this project under MIT terms, provided you retain the Apache 2.0 notices in any files that carry them.

- **YOLO11 TFLite model** — The `yolo11.tflite` model artifact is developed by Ultralytics and licensed under the **GNU Affero General Public License v3.0 (AGPL-3.0)**. The model file is **not** covered by the MIT License above. If you distribute this app or a derivative work that includes the YOLO11 model, your distribution must comply with AGPL-3.0. For commercial use without open-sourcing your application, a separate [Ultralytics Enterprise License](https://www.ultralytics.com/license) is required.
