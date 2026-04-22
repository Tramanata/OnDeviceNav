"""
OnDeviceNav Technical Documentation Generator
Produces three PDFs covering SLAM/ARCore, Computer Vision, and Route Planning.
"""

from fpdf import FPDF
import os

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------------------
# Base PDF class with shared helpers
# ---------------------------------------------------------------------------

class DocPDF(FPDF):
    def __init__(self, doc_title):
        super().__init__()
        self.doc_title = doc_title
        self.set_margins(20, 20, 20)
        self.set_auto_page_break(auto=True, margin=22)

    # ---- header/footer ----
    def header(self):
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(120, 120, 120)
        self.cell(0, 8, f"OnDeviceNav  |  {self.doc_title}", align="L")
        self.ln(2)
        self.set_draw_color(180, 180, 180)
        self.set_line_width(0.3)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(4)
        self.set_text_color(0, 0, 0)

    def footer(self):
        self.set_y(-18)
        self.set_draw_color(180, 180, 180)
        self.set_line_width(0.3)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(2)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(130, 130, 130)
        self.cell(0, 6, f"Page {self.page_no()}", align="C")

    # ---- title page ----
    def title_page(self, subtitle, version="v1.0", date="April 2026"):
        self.add_page()
        self.set_fill_color(15, 40, 80)
        self.rect(0, 0, self.w, self.h, "F")

        self.set_y(55)
        self.set_font("Helvetica", "B", 28)
        self.set_text_color(255, 255, 255)
        self.multi_cell(0, 12, self.doc_title, align="C")
        self.ln(6)

        self.set_font("Helvetica", "", 15)
        self.set_text_color(160, 200, 255)
        self.multi_cell(0, 9, subtitle, align="C")
        self.ln(14)

        self.set_draw_color(100, 160, 220)
        self.set_line_width(0.6)
        self.line(40, self.get_y(), self.w - 40, self.get_y())
        self.ln(10)

        self.set_font("Helvetica", "", 11)
        self.set_text_color(200, 220, 255)
        self.cell(0, 7, f"Project: OnDeviceNav  |  {version}  |  {date}", align="C")
        self.ln(5)
        self.cell(0, 7, "AR Indoor Navigation System", align="C")

        self.set_text_color(0, 0, 0)

    # ---- content helpers ----
    def chapter_title(self, text, level=1):
        self.ln(5)
        if level == 1:
            self.set_font("Helvetica", "B", 16)
            self.set_text_color(15, 40, 80)
            self.set_fill_color(230, 238, 255)
            self.cell(0, 10, text, fill=True, ln=True)
            self.set_draw_color(15, 40, 80)
            self.set_line_width(0.5)
            self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        elif level == 2:
            self.set_font("Helvetica", "B", 13)
            self.set_text_color(30, 80, 160)
            self.cell(0, 8, text, ln=True)
            self.set_draw_color(30, 80, 160)
            self.set_line_width(0.3)
            self.line(self.l_margin, self.get_y(), self.l_margin + 90, self.get_y())
        else:
            self.set_font("Helvetica", "BI", 11)
            self.set_text_color(60, 100, 180)
            self.cell(0, 7, text, ln=True)
        self.set_text_color(0, 0, 0)
        self.ln(2)

    def body(self, text, indent=0):
        self.set_font("Helvetica", "", 10)
        self.set_text_color(30, 30, 30)
        x = self.l_margin + indent
        w = self.w - self.l_margin - self.r_margin - indent
        self.set_x(x)
        self.multi_cell(w, 5.5, text)
        self.ln(1)

    def bullet(self, text, indent=8):
        self.set_font("Helvetica", "", 10)
        self.set_text_color(30, 30, 30)
        bx = self.l_margin + indent
        self.set_x(bx)
        self.cell(5, 5.5, chr(149))   # bullet char
        self.multi_cell(self.w - self.l_margin - self.r_margin - indent - 5, 5.5, text)

    def code_block(self, lines):
        """Render a monospaced code block."""
        self.set_fill_color(240, 242, 248)
        self.set_draw_color(180, 185, 200)
        self.set_line_width(0.3)
        self.ln(2)
        # Calculate block height
        line_h = 5.2
        pad = 3
        total_h = len(lines) * line_h + pad * 2
        x0, y0 = self.l_margin, self.get_y()
        block_w = self.w - self.l_margin - self.r_margin
        self.rect(x0, y0, block_w, total_h, "FD")
        self.set_y(y0 + pad)
        self.set_font("Courier", "", 8.5)
        self.set_text_color(20, 20, 80)
        for line in lines:
            self.set_x(x0 + 4)
            self.cell(block_w - 8, line_h, line, ln=True)
        self.ln(3)
        self.set_text_color(0, 0, 0)

    def table(self, headers, rows, col_widths=None):
        """Simple table renderer."""
        if col_widths is None:
            usable = self.w - self.l_margin - self.r_margin
            col_widths = [usable / len(headers)] * len(headers)
        self.ln(2)
        # Header row
        self.set_fill_color(15, 40, 80)
        self.set_text_color(255, 255, 255)
        self.set_font("Helvetica", "B", 9)
        for i, h in enumerate(headers):
            self.cell(col_widths[i], 7, h, border=1, fill=True)
        self.ln()
        # Data rows
        self.set_font("Helvetica", "", 8.5)
        self.set_text_color(20, 20, 20)
        for ri, row in enumerate(rows):
            fill = ri % 2 == 0
            self.set_fill_color(245, 248, 255) if fill else self.set_fill_color(255, 255, 255)
            for i, cell in enumerate(row):
                self.cell(col_widths[i], 6.5, cell, border=1, fill=True)
            self.ln()
        self.ln(3)
        self.set_text_color(0, 0, 0)

    def info_box(self, title, text, color=(230, 245, 230)):
        self.ln(3)
        self.set_fill_color(*color)
        self.set_draw_color(100, 160, 100)
        self.set_line_width(0.4)
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(20, 80, 20)
        self.cell(0, 6, f"  {title}", fill=True, border="LTR", ln=True)
        self.set_font("Helvetica", "", 9)
        self.set_text_color(30, 30, 30)
        self.set_fill_color(*color)
        self.multi_cell(0, 5.5, f"  {text}", fill=True, border="LBR")
        self.ln(3)
        self.set_text_color(0, 0, 0)


# ===========================================================================
# PDF 1  -  SLAM & ARCore
# ===========================================================================

def build_slam_pdf():
    pdf = DocPDF("SLAM & Google ARCore Integration")
    pdf.title_page(
        subtitle="Simultaneous Localisation and Mapping\nvia ARCore 1.52 Session Management, Plane Detection & Anchor Tracking",
    )

    # ------------------------------------------------------------------
    # 1. Overview
    # ------------------------------------------------------------------
    pdf.add_page()
    pdf.chapter_title("1. Overview", 1)
    pdf.body(
        "OnDeviceNav relies on Google ARCore as its sole SLAM (Simultaneous Localisation and Mapping) "
        "backend. ARCore performs continuous 6-DoF visual-inertial odometry on-device, delivering a "
        "stable world-frame camera pose at 30 Hz without any external infrastructure such as beacons "
        "or pre-built maps. The ARCore session is owned by ComputerVisionActivity, which drives the "
        "entire frame loop from the OpenGL ES 3.0 render thread."
    )
    pdf.body(
        "In addition to pose tracking, ARCore's Environmental Understanding API detects planar "
        "surfaces (floors, walls, tables) and populates them into the navigation grid. Hit-testing "
        "converts 2-D screen taps into 3-D world positions anchored to detected planes, enabling "
        "users to place waypoints directly on the floor."
    )

    pdf.info_box(
        "Key ARCore Dependency",
        "com.google.ar:core:1.52.0  (gradle)   -  requires an ARCore-certified device "
        "with Android API 24+ and OpenGL ES 3.0 support.",
        color=(230, 240, 255)
    )

    # ------------------------------------------------------------------
    # 2. Architecture
    # ------------------------------------------------------------------
    pdf.chapter_title("2. Architectural Role in the System", 1)
    pdf.body(
        "ARCore sits at the base of the data pipeline. Every other subsystem consumes its outputs:"
    )
    for item in [
        "Camera Pose  ->  NavigationManager (current position for A* start and HUD bearing)",
        "Plane Collection  ->  NavGrid.rebuildFromPlanes() (walkability map construction)",
        "Hit-Test Results  ->  WaypointManager (floor-level anchor placement)",
        "Camera Image  ->  ObjectDetectorHelper (YOLO11 inference input)",
        "View / Projection Matrices  ->  PathRenderer (AR path overlay in world space)",
    ]:
        pdf.bullet(item)
    pdf.ln(2)

    # ------------------------------------------------------------------
    # 3. Session Lifecycle
    # ------------------------------------------------------------------
    pdf.chapter_title("3. ARCore Session Lifecycle", 1)

    pdf.chapter_title("3.1  Creation & Configuration", 2)
    pdf.body(
        "The ARCore Session is created inside onResume() after the user grants CAMERA permission. "
        "Creation follows three mandatory steps:"
    )
    pdf.code_block([
        "// Step 1  -  Check availability & prompt install if needed",
        "ArCoreApk.InstallStatus status =",
        "    ArCoreApk.getInstance().requestInstall(this, !installRequested);",
        "if (status == ArCoreApk.InstallStatus.INSTALL_REQUESTED) { return; }",
        "",
        "// Step 2  -  Create session bound to this Activity context",
        "session = new Session(this);",
        "",
        "// Step 3  -  Configure plane detection and focus mode",
        "Config arConfig = new Config(session);",
        "arConfig.setPlaneFindingMode(Config.PlaneFindingMode.HORIZONTAL_AND_VERTICAL);",
        "arConfig.setFocusMode(Config.FocusMode.AUTO);",
        "session.configure(arConfig);",
    ])
    pdf.body(
        "HORIZONTAL_AND_VERTICAL mode activates detection for both floor/ceiling planes and "
        "vertical walls. Walls are projected onto the nav grid as static obstacles, while horizontal "
        "planes at floor level become walkable cells."
    )

    pdf.chapter_title("3.2  Resume / Pause Handling", 2)
    pdf.body(
        "session.resume() is called unconditionally in onResume() and session.pause() in onPause(). "
        "The GLSurfaceView rendering is also paused/resumed in lock-step so no frames are dispatched "
        "while the session is suspended. The session object survives across pause/resume cycles; only "
        "the camera stream is interrupted."
    )

    pdf.chapter_title("3.3  Session Teardown", 2)
    pdf.body(
        "In onDestroy() the session is closed with session.close(), which releases the camera and "
        "all native resources. All ARCore Anchors stored in WaypointManager are detached first to "
        "avoid native handle leaks. The YOLO TFLite interpreter is also closed at this point."
    )

    # ------------------------------------------------------------------
    # 4. Frame Loop
    # ------------------------------------------------------------------
    pdf.chapter_title("4. Per-Frame Processing (onDrawFrame)", 1)
    pdf.body(
        "The GL render thread calls onDrawFrame() at up to 30 FPS. The sequence within each frame is:"
    )

    steps = [
        ("session.update()", "Advances the ARCore state machine; returns a Frame containing the latest camera image, pose, and detected trackables."),
        ("frame.getCamera()", "Retrieves the Camera object whose getPose() method returns the current world-frame camera pose."),
        ("camera.getTrackingState()", "Guards all downstream processing  -  only TRACKING permits navigation updates. PAUSED/STOPPED state shows a tracking-lost UI banner."),
        ("camera.getViewMatrix()", "Fills a 4x4 view matrix used by PathRenderer for world-space AR overlays."),
        ("camera.getProjectionMatrix()", "Fills a 4x4 perspective projection matrix (Z_NEAR=0.1 m, Z_FAR=100 m)."),
        ("background.draw(frame)", "Renders the live camera feed as a full-screen quad via the BackgroundRenderer."),
        ("tryPostYoloFrame(frame)", "Every 10 frames: acquires the YUV camera image and dispatches YOLO inference on the background executor."),
        ("planeRenderer.drawPlanes()", "Renders semi-transparent plane polygons over detected surfaces for user awareness."),
        ("pointCloudRenderer.draw()", "Renders sparse feature points to visualise tracking quality."),
        ("pathRenderer.draw()", "Draws the computed A* path and waypoint spheres in AR space."),
    ]
    for step, desc in steps:
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(15, 40, 120)
        pdf.set_x(pdf.l_margin)
        pdf.cell(55, 5.5, step)
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(30, 30, 30)
        pdf.multi_cell(0, 5.5, desc)
    pdf.ln(3)

    # ------------------------------------------------------------------
    # 5. Camera Pose
    # ------------------------------------------------------------------
    pdf.chapter_title("5. Camera Pose & Coordinate System", 1)
    pdf.body(
        "ARCore maintains a right-handed coordinate system with the Y axis pointing upward. The "
        "origin is set at the device's initial position when the session is created. All navigation "
        "positions (waypoints, grid origin, path nodes) are expressed in this coordinate system."
    )
    pdf.body("The camera pose exposes translation and orientation components:")
    pdf.code_block([
        "Pose pose = camera.getPose();",
        "float x = pose.tx();   // right (metres)",
        "float y = pose.ty();   // up (metres)",
        "float z = pose.tz();   // backward (metres, negative = forward)",
        "",
        "// Navigation uses only the XZ (horizontal) plane:",
        "float[] camPos = { pose.tx(), pose.ty(), pose.tz() };",
        "navigationManager.updateCameraPosition(camPos);",
    ])
    pdf.body(
        "The bearing for turn-by-turn instructions is derived from column 2 of the view matrix "
        "(the camera forward direction projected onto the XZ plane), rather than from quaternion "
        "decomposition, to avoid gimbal-lock edge cases on steep inclines."
    )

    # ------------------------------------------------------------------
    # 6. Plane Detection
    # ------------------------------------------------------------------
    pdf.chapter_title("6. Environmental Plane Detection", 1)
    pdf.body(
        "ARCore's Environmental Understanding continuously detects planar surfaces by fitting "
        "homogeneous regions of the point cloud to plane hypotheses. Each Plane object provides "
        "a polygon boundary, type classification, and extent measurements."
    )

    pdf.chapter_title("6.1  Plane Types Used", 2)
    pdf.table(
        ["Plane Type", "ARCore Enum", "NavGrid Classification"],
        [
            ["Floor", "HORIZONTAL_UPWARD_FACING (height <= 0.30 m)", "CELL_WALKABLE"],
            ["Desk / Table", "HORIZONTAL_UPWARD_FACING (height > 0.30 m)", "CELL_STATIC_OBSTACLE"],
            ["Ceiling", "HORIZONTAL_DOWNWARD_FACING", "Ignored"],
            ["Wall", "VERTICAL", "CELL_STATIC_OBSTACLE (1-cell expansion)"],
        ],
        col_widths=[40, 80, 50]
    )

    pdf.chapter_title("6.2  Plane Polygon & Point-in-Polygon Test", 2)
    pdf.body(
        "Each Plane exposes its boundary as a FloatBuffer of XZ vertex pairs (in plane-local space). "
        "NavGrid converts these vertices to world XZ coordinates via the plane's center pose, then "
        "applies a ray-casting point-in-polygon (PIP) test to classify each grid cell:"
    )
    pdf.code_block([
        "FloatBuffer poly = plane.getPolygon();   // [x0,z0, x1,z1, ...]",
        "Pose center = plane.getCenterPose();",
        "for (int row = 0; row < GRID_SIZE; row++) {",
        "    for (int col = 0; col < GRID_SIZE; col++) {",
        "        float[] worldXZ = cellToWorld(row, col);",
        "        if (pointInPolygon(worldXZ, poly, center)) {",
        "            cells[row][col] = CELL_WALKABLE;",
        "        }",
        "    }",
        "}",
    ])
    pdf.body(
        "The size guard (getExtentX() >= 0.5 m && getExtentZ() >= 0.5 m) prevents initialising "
        "the grid on small spurious planes detected at startup."
    )

    # ------------------------------------------------------------------
    # 7. Hit Testing
    # ------------------------------------------------------------------
    pdf.chapter_title("7. Hit-Testing for Waypoint Placement", 1)
    pdf.body(
        "When the user taps the screen, a ray is cast from the camera through the screen coordinates "
        "into the ARCore world. The Frame.hitTest() method intersects this ray with all tracked "
        "planes and returns an ordered list of HitResult objects sorted by distance."
    )
    pdf.code_block([
        "List<HitResult> hits = frame.hitTest(motionEvent);",
        "for (HitResult hit : hits) {",
        "    Trackable trackable = hit.getTrackable();",
        "    if (!(trackable instanceof Plane)) continue;",
        "    Plane plane = (Plane) trackable;",
        "    if (plane.getType() != Plane.Type.HORIZONTAL_UPWARD_FACING) continue;",
        "    if (!plane.isPoseInPolygon(hit.getHitPose())) continue;",
        "",
        "    // Valid floor hit  -  create a persistent anchor",
        "    Anchor anchor = hit.createAnchor();",
        "    waypointManager.addWaypoint(hit.getHitPose(), anchor);",
        "    break;",
        "}",
    ])
    pdf.body(
        "Only HORIZONTAL_UPWARD_FACING planes pass the filter so users cannot accidentally place "
        "waypoints on walls or ceilings. The isPoseInPolygon() check ensures the hit point lies "
        "within the detected plane's tracked extent rather than on its mathematical infinite extension."
    )

    # ------------------------------------------------------------------
    # 8. Anchor Management
    # ------------------------------------------------------------------
    pdf.chapter_title("8. Anchor Management", 1)
    pdf.body(
        "ARCore Anchors bind a world-space pose to a trackable surface. As ARCore refines its map "
        "estimate, anchors are automatically updated so that virtual content stays locked to the "
        "physical world even as the camera pose drifts and corrects."
    )
    for item in [
        "One anchor is created per user-placed waypoint (start and destination at minimum).",
        "Anchors are stored inside Waypoint objects in WaypointManager.",
        "Each frame, the anchor's updated pose is read via anchor.getPose() for rendering.",
        "Anchors in STOPPED tracking state are visually faded but their last known pose is retained.",
        "On navigation reset, all anchors are explicitly detached (anchor.detach()) to free GPU/native memory.",
    ]:
        pdf.bullet(item)

    # ------------------------------------------------------------------
    # 9. Point Cloud & Feature Tracking
    # ------------------------------------------------------------------
    pdf.chapter_title("9. Point Cloud & Visual Feature Tracking", 1)
    pdf.body(
        "ARCore's internal visual-inertial odometry extracts ORB-like feature points from each "
        "camera frame and tracks them across frames using Lucas-Kanade optical flow. The refined "
        "3-D positions of stable features are exposed via Frame.acquirePointCloud()."
    )
    pdf.body(
        "OnDeviceNav uses the point cloud solely for visual feedback  -  the PointCloudRenderer draws "
        "coloured spheres at feature locations so the user can assess tracking quality. The point "
        "cloud is NOT used for navigation or obstacle detection. acquirePointCloud() returns a "
        "reference-counted object that must be explicitly closed to avoid native memory leaks:"
    )
    pdf.code_block([
        "try (PointCloud pointCloud = frame.acquirePointCloud()) {",
        "    pointCloudRenderer.update(pointCloud);",
        "    pointCloudRenderer.draw(viewMatrix, projMatrix);",
        "}",
    ])

    # ------------------------------------------------------------------
    # 10. Rendering Pipeline
    # ------------------------------------------------------------------
    pdf.chapter_title("10. OpenGL Rendering Pipeline", 1)
    pdf.body("Four OpenGL programs are compiled from shader sources in /assets/shaders/:")
    pdf.table(
        ["Shader Pair", "Purpose", "Key Uniform"],
        [
            ["screenquad.vert/frag", "Camera feed background (full-screen quad)", "uTexture (OES_EGL_image_external)"],
            ["plane.vert/frag", "Semi-transparent plane polygons", "uModelViewProjection, uTexture (trigrid.png)"],
            ["point_cloud.vert/frag", "Sparse feature points", "uMVPMatrix, uColor"],
            ["path_dots.vert/frag", "Waypoint spheres + path lines", "uModelViewProjection, uPointSize"],
        ],
        col_widths=[55, 80, 55]
    )
    pdf.body(
        "The BackgroundRenderer uses the GL_OES_EGL_image_external extension to sample the camera "
        "stream YUV texture directly on the GPU, avoiding a CPU-side YUV->RGB conversion for the "
        "background pass. All other renderers operate on standard RGBA textures or solid colours."
    )

    # ------------------------------------------------------------------
    # 11. Performance
    # ------------------------------------------------------------------
    pdf.chapter_title("11. Performance & Constraints", 1)
    pdf.table(
        ["Parameter", "Value", "Notes"],
        [
            ["ARCore version", "1.52.0", "Minimum for ML-based plane finding"],
            ["Min Android SDK", "API 24 (Android 7.0)", "ARCore lower bound"],
            ["Target SDK", "API 36 (Android 15)", "Latest tested"],
            ["OpenGL ES", "3.0", "Required for ES 3 shader features"],
            ["Z_NEAR", "0.1 m", "Prevents near-clip artefacts on close planes"],
            ["Z_FAR", "100 m", "Sufficient for indoor environments"],
            ["Tracking lost banner", "On NOT_TRACKING", "Shown via NavigationOverlayView"],
            ["Camera Feature", "android.hardware.camera.ar", "Required  -  limits to AR-certified devices"],
        ],
        col_widths=[45, 50, 75]
    )

    pdf.output(os.path.join(OUTPUT_DIR, "1_SLAM_ARCore.pdf"))
    print("  [OK] 1_SLAM_ARCore.pdf")


# ===========================================================================
# PDF 2  -  Computer Vision / YOLO11
# ===========================================================================

def build_cv_pdf():
    pdf = DocPDF("Computer Vision & Object Detection")
    pdf.title_page(
        subtitle="On-Device YOLO11 Obstacle Detection\nvia TensorFlow Lite 2.14 with Dynamic NavGrid Marking",
    )

    # ------------------------------------------------------------------
    # 1. Overview
    # ------------------------------------------------------------------
    pdf.add_page()
    pdf.chapter_title("1. Overview", 1)
    pdf.body(
        "OnDeviceNav's computer vision subsystem runs a quantized YOLO11 model entirely on-device "
        "using TensorFlow Lite 2.14. The detector identifies dynamic obstacles (people, furniture, "
        "bags) from the ARCore camera stream and feeds bounding-box results to the navigation layer, "
        "which marks corresponding grid cells as temporary obstacles and triggers route re-planning."
    )
    pdf.body(
        "The pipeline is deliberately throttled to run every 10 AR frames (approx. 3 Hz at 30 FPS) "
        "on a dedicated background executor so that inference never blocks the GL render thread. "
        "An AtomicReference is used for lock-free handoff of results between the inference thread "
        "and the GL/UI threads."
    )
    pdf.info_box(
        "Model file",
        "assets/yolo11.tflite   -   YOLO version 11, UINT8 quantized, COCO 80-class vocabulary.",
        color=(255, 245, 220)
    )

    # ------------------------------------------------------------------
    # 2. Files
    # ------------------------------------------------------------------
    pdf.chapter_title("2. Source Files", 1)
    pdf.table(
        ["File", "Role"],
        [
            ["ObjectDetectorHelper.java", "TFLite session management, inference, NMS post-processing"],
            ["NavigationManager.java", "Consumes detections; maps obstacles to NavGrid; re-plans route"],
            ["NavigationOverlayView.java", "Canvas-based HUD; draws bounding boxes and direction text"],
            ["ImageUtils.java", "YUV_420_888 -> Bitmap conversion with rotation correction"],
            ["EdgeDetector.java", "Sobel edge map (optional CV visualisation, not used for nav)"],
            ["assets/yolo11.tflite", "Quantized YOLO11 model weights"],
        ],
        col_widths=[70, 100]
    )

    # ------------------------------------------------------------------
    # 3. YOLO11 Model Details
    # ------------------------------------------------------------------
    pdf.chapter_title("3. YOLO11 TFLite Model", 1)

    pdf.chapter_title("3.1  Architecture Summary", 2)
    pdf.body(
        "YOLO11 is the 11th generation of the YOLO (You Only Look Once) single-stage object "
        "detector. The mobile-optimised variant used here applies post-training INT8 quantization "
        "via TFLite's representative-dataset calibration. The model is exported with a fixed "
        "640 x 640 input resolution and outputs predictions in one of three tensor layouts "
        "depending on the export configuration (see Section 3.3)."
    )

    pdf.chapter_title("3.2  Input Tensor", 2)
    pdf.body("The input shape is read dynamically at runtime from the TFLite interpreter:")
    pdf.code_block([
        "int[] inputShape = interpreter.getInputTensor(0).shape();",
        "// Typical: [1, 640, 640, 3]  (NHWC format)",
        "int inputSize  = inputShape[1];   // 640",
        "DataType dtype = interpreter.getInputTensor(0).dataType();",
        "// UINT8 for quantized model, FLOAT32 for full-precision",
    ])
    pdf.body(
        "The bitmap is resized to inputSize x inputSize using Bitmap.createScaledBitmap(). "
        "For UINT8 models the pixel values [0-255] are loaded directly. For FLOAT32 models "
        "each channel is normalised to [0.0, 1.0] by dividing by 255."
    )

    pdf.chapter_title("3.3  Output Tensor Formats", 2)
    pdf.body(
        "ObjectDetectorHelper auto-detects one of three export layouts by inspecting the number "
        "and shape of output tensors:"
    )

    pdf.chapter_title("FORMAT_AI_HUB_3  (3 output tensors)", 3)
    pdf.body("Produced by the AI Hub YOLO11 export pipeline:")
    pdf.table(
        ["Tensor Index", "Shape", "Content"],
        [
            ["0", "[N, 4]", "Bounding boxes in absolute xyxy pixel coordinates"],
            ["1", "[N]", "Per-detection confidence scores [0..1]"],
            ["2", "[N]", "Integer class IDs [0..79]"],
        ],
        col_widths=[35, 35, 100]
    )

    pdf.chapter_title("FORMAT_SPLIT_2  (2 output tensors)", 3)
    pdf.body("Standard Ultralytics export with split coordinate and score tensors:")
    pdf.table(
        ["Tensor Index", "Shape (channel-first)", "Content"],
        [
            ["0", "[1, 4, N]", "Bounding boxes in xywh format (cx, cy, w, h), normalised [0..1]"],
            ["1", "[1, numClasses, N]", "Class probability logits"],
        ],
        col_widths=[35, 50, 85]
    )
    pdf.body(
        "The helper converts xywh -> xyxy: x1 = cx - w/2, y1 = cy - h/2, x2 = cx + w/2, "
        "y2 = cy + h/2. It also handles the transposed [1, N, 4] and [1, N, numClasses] variants "
        "by checking whether dimension 1 or dimension 2 has the larger size."
    )

    pdf.chapter_title("FORMAT_STANDARD  (1 output tensor)", 3)
    pdf.body("Legacy Ultralytics format combining all predictions in a single tensor:")
    pdf.code_block([
        "// Shape: [1, 4+numClasses, N]  or transposed  [1, N, 4+numClasses]",
        "// Columns 0-3: bounding box (xywh normalised)",
        "// Columns 4+: per-class logits",
    ])

    # ------------------------------------------------------------------
    # 4. Inference Pipeline
    # ------------------------------------------------------------------
    pdf.chapter_title("4. Full Inference Pipeline", 1)
    pdf.body("The end-to-end path from camera frame to NavGrid update:")
    pdf.code_block([
        "// GL Thread (onDrawFrame)  -  every 10 frames",
        "if (frameIndex % YOLO_EVERY_N_FRAMES == 0) {",
        "    tryPostYoloFrame(frame, camera);",
        "}",
        "",
        "// tryPostYoloFrame()",
        "Image cameraImage = frame.acquireCameraImage();     // YUV_420_888",
        "Bitmap bmp = ImageUtils.imageToBitmap(             // YUV -> JPEG -> Bitmap",
        "    cameraImage, displayRotation);",
        "cameraImage.close();                               // release native buffer",
        "inferenceExecutor.execute(() -> {",
        "    List<Detection> dets = objectDetector.detect(bmp);",
        "    pendingObstacleDetections.set(dets);            // AtomicReference handoff",
        "    runOnUiThread(() -> overlay.setDetections(dets));",
        "});",
        "",
        "// GL Thread  -  next frame",
        "List<Detection> dets = pendingObstacleDetections.getAndSet(null);",
        "if (dets != null) {",
        "    navigationManager.updateObstacles(dets, frame, camera);",
        "}",
    ])

    # ------------------------------------------------------------------
    # 5. Image Conversion
    # ------------------------------------------------------------------
    pdf.chapter_title("5. Image Conversion: YUV_420_888 -> Bitmap", 1)
    pdf.body(
        "ARCore provides camera images in Android's YUV_420_888 multi-plane format. ImageUtils "
        "converts this to a Bitmap via an intermediate NV21 byte array and JPEG re-encoding, "
        "which is compatible with the BitmapFactory decoder:"
    )
    pdf.code_block([
        "// 1. Extract Y plane (full resolution)",
        "ByteBuffer yBuf = image.getPlanes()[0].getBuffer();",
        "int yStride = image.getPlanes()[0].getRowStride();",
        "",
        "// 2. Extract UV planes (half resolution, potentially interleaved)",
        "ByteBuffer uBuf = image.getPlanes()[1].getBuffer();",
        "ByteBuffer vBuf = image.getPlanes()[2].getBuffer();",
        "int uvPixelStride = image.getPlanes()[1].getPixelStride();",
        "",
        "// 3. Assemble NV21 byte array  (YYYY... VUVU...)",
        "byte[] nv21 = new byte[width * height * 3 / 2];",
        "// ... copy Y rows, interleave VU pairs ...",
        "",
        "// 4. JPEG encode -> BitmapFactory decode -> rotate",
        "YuvImage yuvImage = new YuvImage(nv21, ImageFormat.NV21, width, height, null);",
        "ByteArrayOutputStream out = new ByteArrayOutputStream();",
        "yuvImage.compressToJpeg(new Rect(0,0,width,height), 85, out);",
        "Bitmap bmp = BitmapFactory.decodeByteArray(out.toByteArray(), 0, out.size());",
        "return rotateBitmap(bmp, displayRotation);",
    ])
    pdf.body(
        "The pixelStride check handles both packed UV (stride=1) and interleaved YUV (stride=2) "
        "plane layouts, which vary by device OEM. The rotation step ensures the bitmap is "
        "always upright before being fed to the YOLO model."
    )

    # ------------------------------------------------------------------
    # 6. Post-Processing
    # ------------------------------------------------------------------
    pdf.chapter_title("6. Post-Processing: Confidence Filtering & NMS", 1)

    pdf.chapter_title("6.1  Confidence Threshold", 2)
    pdf.body(
        "After inference, every candidate detection whose confidence score falls below 0.40 (40%) "
        "is discarded immediately. This threshold was chosen empirically to balance false-positive "
        "rate (spurious detections on textured floors/walls) against recall for real obstacles."
    )

    pdf.chapter_title("6.2  Non-Maximum Suppression (NMS)", 2)
    pdf.body(
        "Among the remaining candidates, NMS suppresses redundant overlapping boxes for the same "
        "object. The algorithm is a greedy sort-and-suppress approach:"
    )
    pdf.code_block([
        "// 1. Sort detections by score descending",
        "Collections.sort(candidates, (a, b) ->",
        "    Float.compare(b.score, a.score));",
        "",
        "// 2. Greedy selection",
        "List<Detection> kept = new ArrayList<>();",
        "for (Detection cand : candidates) {",
        "    boolean suppressed = false;",
        "    for (Detection k : kept) {",
        "        if (iou(cand.box, k.box) >= IOU_THRESHOLD) {",
        "            suppressed = true; break;",
        "        }",
        "    }",
        "    if (!suppressed) kept.add(cand);",
        "}",
    ])
    pdf.body(
        "The IoU (Intersection over Union) threshold is 0.45. Two boxes whose overlap ratio "
        "exceeds this value are considered duplicates; only the higher-scoring box is retained."
    )

    # ------------------------------------------------------------------
    # 7. Detection Data Structure
    # ------------------------------------------------------------------
    pdf.chapter_title("7. Detection Data Structure", 1)
    pdf.code_block([
        "public static class Detection {",
        "    RectF  box;       // Normalised [0..1] coordinates: left, top, right, bottom",
        "    float  score;     // Confidence in [0..1]",
        "    int    classId;   // COCO 80-class integer ID",
        "    String label;     // Human-readable name from COCO_LABELS[]",
        "}",
    ])
    pdf.body(
        "Bounding box coordinates are kept normalised throughout the pipeline. Only at rendering "
        "time (NavigationOverlayView) are they scaled to pixel coordinates by multiplying by the "
        "view width/height."
    )

    # ------------------------------------------------------------------
    # 8. Obstacle Class Filter
    # ------------------------------------------------------------------
    pdf.chapter_title("8. Obstacle Class Filter", 1)
    pdf.body(
        "Not all 80 COCO classes constitute navigable obstacles. NavigationManager.isObstacleClass() "
        "returns true only for the following subset  -  objects that physically block a walking path:"
    )
    pdf.table(
        ["COCO ID", "Class Name", "Reason"],
        [
            ["0", "person", "Dynamic, unpredictable movement"],
            ["13", "bench", "Floor-level obstruction"],
            ["24", "backpack", "Dropped bag / luggage"],
            ["26", "handbag", ""],
            ["28", "suitcase", "Large wheeled obstruction"],
            ["56", "chair", "Common indoor obstacle"],
            ["57", "couch", "Large furniture"],
            ["58", "potted plant", "Narrow stem, wide canopy hazard"],
            ["59", "bed", "Room-scale obstruction"],
            ["60", "dining table", "Central room obstacle"],
            ["62", "tv / monitor", "On stand at floor level"],
            ["63", "laptop", "On floor / low table"],
            ["74", "clock", "Floor-standing clock"],
        ],
        col_widths=[20, 45, 105]
    )

    # ------------------------------------------------------------------
    # 9. NavGrid Integration
    # ------------------------------------------------------------------
    pdf.chapter_title("9. NavGrid Integration & Obstacle Marking", 1)
    pdf.body(
        "Detected obstacles must be projected from 2-D image coordinates into 3-D world space "
        "before they can be marked on the NavGrid. This is achieved via ARCore hit-testing at the "
        "bounding-box centre:"
    )
    pdf.code_block([
        "for (Detection det : detections) {",
        "    if (!isObstacleClass(det.classId)) continue;",
        "",
        "    // Map normalised box centre to screen pixels",
        "    float cx = (det.box.left + det.box.right)  / 2f * imageWidth;",
        "    float cy = (det.box.top  + det.box.bottom) / 2f * imageHeight;",
        "",
        "    // ARCore hit-test -> world XZ coordinate on floor plane",
        "    List<HitResult> hits = frame.hitTest(cx, cy);",
        "    if (hits.isEmpty()) continue;",
        "",
        "    float[] worldPos = hits.get(0).getHitPose().getTranslation();",
        "",
        "    // Radius proportional to detection width (1 - 3 cells)",
        "    float widthM = det.box.width() * imageWidth * METRES_PER_PIXEL;",
        "    int radiusCells = (int) Math.max(1, Math.min(3, widthM / CELL_SIZE));",
        "",
        "    navGrid.markObstacle(worldPos[0], worldPos[2], radiusCells);",
        "}",
    ])
    pdf.body(
        "markObstacle() stamps CELL_OBSTACLE on all grid cells within radiusCells of the world "
        "position and records the current frame number. Obstacle cells expire after 300 frames "
        "(approximately 10 seconds at 30 FPS) if no new detection refreshes them, reverting to "
        "CELL_WALKABLE."
    )

    # ------------------------------------------------------------------
    # 10. HUD Rendering
    # ------------------------------------------------------------------
    pdf.chapter_title("10. HUD Rendering (NavigationOverlayView)", 1)
    pdf.body(
        "NavigationOverlayView is a transparent View drawn over the GLSurfaceView. In onDraw() "
        "it renders both the object-detection overlay and the navigation HUD on the same Canvas:"
    )
    for item in [
        "Bounding boxes: thin red rectangles scaled from normalised [0..1] to view pixels.",
        "Class labels: small white text with semi-transparent background above each box.",
        "Confidence scores: displayed alongside the label in parentheses.",
        "Direction arrow / text: large centred white text (e.g. 'Turn left  12.3 ft').",
        "State banner: grey pill showing current AppState (SCANNING / NAVIGATING / ARRIVED).",
    ]:
        pdf.bullet(item)
    pdf.ln(2)
    pdf.body(
        "setDetections() and setNavInstruction() are both called from the UI thread via "
        "runOnUiThread(), ensuring thread-safe Canvas updates. invalidate() triggers the next draw."
    )

    # ------------------------------------------------------------------
    # 11. Edge Detector
    # ------------------------------------------------------------------
    pdf.chapter_title("11. Sobel Edge Detector (EdgeDetector)", 1)
    pdf.body(
        "EdgeDetector implements a CPU-side Sobel filter for optional visualisation. It is NOT "
        "part of the live navigation pipeline but is retained for debugging and future use."
    )
    pdf.code_block([
        "// 3x3 Sobel kernels",
        "int[] Kx = {-1, 0, +1,  -2, 0, +2,  -1, 0, +1};",
        "int[] Ky = {-1, -2, -1,  0, 0, 0,  +1, +2, +1};",
        "",
        "// For each interior pixel:",
        "int gx = convolve(grey, x, y, Kx);",
        "int gy = convolve(grey, x, y, Ky);",
        "int mag = gx*gx + gy*gy;",
        "output[i] = (mag > THRESHOLD) ? 0xFF : 0x1F;  // THRESHOLD = 128^2 = 16384",
    ])

    # ------------------------------------------------------------------
    # 12. Performance
    # ------------------------------------------------------------------
    pdf.chapter_title("12. Performance Parameters", 1)
    pdf.table(
        ["Parameter", "Value", "Notes"],
        [
            ["TFLite version", "2.14.0", ""],
            ["TFLite support lib", "0.4.4", "ImageProcessor utilities"],
            ["Inference threads", "4", "CPU-only; no GPU/NNAPI delegate"],
            ["Input resolution", "640 x 640", "Read from model tensor shape"],
            ["Inference frequency", "Every 10 AR frames", "~3 Hz at 30 FPS camera"],
            ["Confidence threshold", "0.40", "Empirically tuned"],
            ["IoU threshold (NMS)", "0.45", "Standard YOLO default"],
            ["Obstacle expiry", "300 frames (~10 s)", "Prevents ghost obstacles"],
            ["Obstacle radius", "1 - 3 grid cells", "Scales with detection width"],
        ],
        col_widths=[50, 45, 75]
    )

    pdf.output(os.path.join(OUTPUT_DIR, "2_Computer_Vision.pdf"))
    print("  [OK] 2_Computer_Vision.pdf")


# ===========================================================================
# PDF 3  -  Route Planning & Navigation
# ===========================================================================

def build_nav_pdf():
    pdf = DocPDF("Route Planning & Navigation")
    pdf.title_page(
        subtitle="A* Pathfinding on a Dynamic 20m x 20m NavGrid\nWith String-Pulling, Turn-by-Turn HUD & Obstacle-Triggered Re-Planning",
    )

    # ------------------------------------------------------------------
    # 1. Overview
    # ------------------------------------------------------------------
    pdf.add_page()
    pdf.chapter_title("1. Overview", 1)
    pdf.body(
        "The navigation subsystem translates ARCore spatial data and YOLO obstacle detections into "
        "an actionable walking route. It consists of four tightly integrated components: a 2-D "
        "occupancy grid (NavGrid), an A* path planner (AStarPlanner), a waypoint lifecycle manager "
        "(WaypointManager), and the real-time instruction engine inside NavigationManager. Together "
        "they provide collision-free, continuously updated turn-by-turn indoor navigation."
    )

    pdf.info_box(
        "State Machine",
        "SCANNING  ->  PLACE_WAYPOINTS  ->  PATHFINDING  ->  NAVIGATING  ->  ARRIVED\n"
        "Navigation only runs while the app is in NAVIGATING state.",
        color=(240, 230, 255)
    )

    # ------------------------------------------------------------------
    # 2. Files
    # ------------------------------------------------------------------
    pdf.chapter_title("2. Source Files", 1)
    pdf.table(
        ["File", "Role"],
        [
            ["NavigationManager.java", "Orchestrates all navigation; owns state machine; issues re-plan requests"],
            ["AStarPlanner.java", "8-connected A* with octile heuristic and string-pulling post-processor"],
            ["NavGrid.java", "100x100 occupancy grid; rebuilt from ARCore planes; tracks obstacle expiry"],
            ["WaypointManager.java", "Manages user-placed start / waypoint / destination anchors"],
            ["PathRenderer.java", "OpenGL ES rendering of path lines and coloured waypoint spheres"],
            ["NavigationOverlayView.java", "Canvas HUD: bounding boxes, direction text, distance readout"],
        ],
        col_widths=[65, 105]
    )

    # ------------------------------------------------------------------
    # 3. NavGrid
    # ------------------------------------------------------------------
    pdf.chapter_title("3. NavGrid: 2-D Occupancy Grid", 1)
    pdf.body(
        "NavGrid represents the navigable environment as a 100 x 100 grid of 20 cm cells, covering "
        "a 20 m x 20 m area centred on the first detected floor plane. Each cell carries one of four "
        "states:"
    )
    pdf.table(
        ["State Constant", "Value", "Meaning"],
        [
            ["CELL_UNKNOWN", "0", "Not yet observed by ARCore"],
            ["CELL_WALKABLE", "1", "Floor surface confirmed by ARCore horizontal plane"],
            ["CELL_OBSTACLE", "2", "Dynamic obstacle (YOLO); expires after 300 frames"],
            ["CELL_STATIC_OBSTACLE", "3", "Permanent: elevated surface or wall footprint"],
        ],
        col_widths=[50, 20, 100]
    )

    pdf.chapter_title("3.1  Grid Coordinate Mapping", 2)
    pdf.body("Conversion between world (metres) and grid (row, col) coordinates:")
    pdf.code_block([
        "static final float CELL_SIZE  = 0.20f;   // 0.20 m per cell",
        "static final int   GRID_SIZE  = 100;      // 100 x 100 cells",
        "",
        "// World  ->  Grid",
        "int row = (int) ((worldX - originX) / CELL_SIZE);",
        "int col = (int) ((worldZ - originZ) / CELL_SIZE);",
        "",
        "// Grid  ->  World  (cell centre)",
        "float worldX = originX + (row + 0.5f) * CELL_SIZE;",
        "float worldZ = originZ + (col + 0.5f) * CELL_SIZE;",
    ])
    pdf.body(
        "The origin is set to the detected first floor plane's centre, offset by half the grid size "
        "in both X and Z so that the plane occupies approximately the centre of the grid."
    )

    pdf.chapter_title("3.2  Grid Rebuild from ARCore Planes", 2)
    pdf.body(
        "rebuildFromPlanes() is called on the background executor whenever ARCore reports new or "
        "updated planes. It processes planes in three passes to maintain correct priority:"
    )

    passes = [
        ("Pass 0  -  Walkable Floor",
         "Selects HORIZONTAL_UPWARD_FACING planes whose Y-coordinate is within 0.30 m of the "
         "known floor level. For each such plane, every grid cell whose world-space XZ centre "
         "falls within the plane's polygon boundary is set to CELL_WALKABLE.",
         [
             "for (Plane plane : planes) {",
             "    if (plane.getType() != HORIZONTAL_UPWARD_FACING) continue;",
             "    if (Math.abs(plane.getCenterPose().ty() - floorY) > 0.30f) continue;",
             "    markWalkableCells(plane);",
             "}",
         ]),
        ("Pass 1  -  Elevated Surfaces (Desks, Tables)",
         "Selects HORIZONTAL_UPWARD_FACING planes more than 0.30 m above floor level. Their "
         "footprints are marked as CELL_STATIC_OBSTACLE, preventing the router from directing "
         "the user to walk through furniture.",
         [
             "if (plane.getCenterPose().ty() - floorY > 0.30f) {",
             "    markStaticObstacle(plane, /* expand = */ 0);",
             "}",
         ]),
        ("Pass 2  -  Vertical Planes (Walls, Doors)",
         "Projects VERTICAL planes onto the XZ ground plane and marks their footprint plus a "
         "1-cell expansion as CELL_STATIC_OBSTACLE. The expansion provides a safety buffer so "
         "A* paths do not graze wall edges.",
         [
             "if (plane.getType() == VERTICAL) {",
             "    projectWallToGrid(plane, /* expandCells = */ 1);",
             "}",
         ]),
    ]
    for title, desc, code in passes:
        pdf.chapter_title(title, 3)
        pdf.body(desc)
        pdf.code_block(code)

    pdf.chapter_title("3.3  Dynamic Obstacle Marking", 2)
    pdf.body(
        "YOLO detections are mapped to grid cells via ARCore hit-testing (see Computer Vision PDF). "
        "The NavGrid records the frame number at which each CELL_OBSTACLE was last refreshed. "
        "A background check runs once per second (frameIndex % 30 == 0) to expire stale obstacles:"
    )
    pdf.code_block([
        "for (int r = 0; r < GRID_SIZE; r++) {",
        "    for (int c = 0; c < GRID_SIZE; c++) {",
        "        if (cells[r][c] == CELL_OBSTACLE) {",
        "            if (currentFrame - obstacleTimestamp[r][c] > OBSTACLE_EXPIRY) {",
        "                cells[r][c] = CELL_WALKABLE;  // revert",
        "            }",
        "        }",
        "    }",
        "}",
    ])

    pdf.chapter_title("3.4  Thread Safety", 2)
    pdf.body(
        "The cell array is protected by a ReentrantLock. Two threads contend for it:"
    )
    for item in [
        "GL thread: reads cell states during A* trigger evaluation and calls scheduleRebuild().",
        "Background executor: writes cells during rebuildFromPlanes() and obstacle marking.",
    ]:
        pdf.bullet(item)
    pdf.body(
        "AStarPlanner receives a deep copy via getSnapshot() so it can run without holding the "
        "lock for the (potentially slow) search duration."
    )

    # ------------------------------------------------------------------
    # 4. A* Pathfinder
    # ------------------------------------------------------------------
    pdf.chapter_title("4. A* Pathfinder (AStarPlanner)", 1)

    pdf.chapter_title("4.1  Graph Structure", 2)
    pdf.body(
        "The search graph is the 100x100 NavGrid cell array with 8-connectivity (cardinal and "
        "diagonal neighbours). Movement costs reflect physical distance:"
    )
    pdf.table(
        ["Direction", "Cost", "Rationale"],
        [
            ["Cardinal (N/S/E/W)", "1.0", "One cell = 0.20 m"],
            ["Diagonal (NE/NW/SE/SW)", "1.414", "sqrt(2) for diagonal distance"],
            ["Adjacent to obstacle", "+2.0", "Clearance penalty (prefer centre of corridor)"],
            ["Unknown / unscanned cell", "+4.0", "Strongly prefer confirmed walkable ground"],
        ],
        col_widths=[55, 25, 90]
    )

    pdf.chapter_title("4.2  Heuristic Function", 2)
    pdf.body(
        "The admissible heuristic is the octile distance, which exactly models the true minimum "
        "cost in an 8-connected grid and never overestimates:"
    )
    pdf.code_block([
        "// Octile distance heuristic",
        "float dr = Math.abs(goalRow - row);",
        "float dc = Math.abs(goalCol - col);",
        "float h  = Math.max(dr, dc) + (SQRT2 - 1f) * Math.min(dr, dc);",
        "// SQRT2 = 1.41421356f",
    ])
    pdf.body(
        "Because the heuristic is admissible and the edge costs are non-negative, A* is guaranteed "
        "to return the optimal path. The consistent (monotone) property also means no re-expansion "
        "of already-closed nodes is necessary."
    )

    pdf.chapter_title("4.3  Data Structures", 2)
    pdf.code_block([
        "// Open list  -  min-heap ordered by f = g + h",
        "PriorityQueue<Node> openList = new PriorityQueue<>(",
        "    Comparator.comparingDouble(n -> n.f));",
        "",
        "// Closed set  -  O(1) lookup",
        "boolean[][] closed = new boolean[GRID_SIZE][GRID_SIZE];",
        "",
        "// Cost-so-far and parent tracking",
        "float[][]  gCost  = new float[GRID_SIZE][GRID_SIZE];  // init to Float.MAX_VALUE",
        "int[][]    parentRow = new int[GRID_SIZE][GRID_SIZE];",
        "int[][]    parentCol = new int[GRID_SIZE][GRID_SIZE];",
        "",
        "class Node {",
        "    int row, col;",
        "    float g, h, f;   // f = g + h",
        "}",
    ])

    pdf.chapter_title("4.4  Search Loop", 2)
    pdf.code_block([
        "openList.add(new Node(startRow, startCol, 0, heuristic(start, goal)));",
        "",
        "while (!openList.isEmpty()) {",
        "    Node cur = openList.poll();",
        "    if (closed[cur.row][cur.col]) continue;",
        "    closed[cur.row][cur.col] = true;",
        "",
        "    if (cur.row == goalRow && cur.col == goalCol) {",
        "        return reconstructPath(parentRow, parentCol, goalRow, goalCol);",
        "    }",
        "",
        "    for (int[] nb : neighbours8(cur.row, cur.col)) {",
        "        if (closed[nb[0]][nb[1]]) continue;",
        "        int cellState = snapshot[nb[0]][nb[1]];",
        "        if (cellState == CELL_STATIC_OBSTACLE) continue;  // hard block",
        "",
        "        float moveCost = isDiagonal(cur, nb) ? SQRT2 : 1.0f;",
        "        moveCost += penaltyFor(cellState);               // obstacle/unknown surcharge",
        "        float newG = cur.g + moveCost;",
        "",
        "        if (newG < gCost[nb[0]][nb[1]]) {",
        "            gCost[nb[0]][nb[1]] = newG;",
        "            parentRow[nb[0]][nb[1]] = cur.row;",
        "            parentCol[nb[0]][nb[1]] = cur.col;",
        "            openList.add(new Node(nb[0], nb[1], newG,",
        "                newG + heuristic(nb, goal)));",
        "        }",
        "    }",
        "}",
        "return null;  // no path found",
    ])

    # ------------------------------------------------------------------
    # 5. String Pulling
    # ------------------------------------------------------------------
    pdf.chapter_title("5. String-Pulling Post-Processing", 1)
    pdf.body(
        "Raw A* paths on a grid consist of cell-to-cell steps and can contain 50+ waypoints for a "
        "10 m route. String-pulling simplifies the path by removing intermediate nodes that are "
        "collinear and unobstructed, reducing it to ~10 key waypoints."
    )

    pdf.chapter_title("5.1  Algorithm", 2)
    pdf.code_block([
        "List<int[]> raw  = aStarCellPath;   // e.g. 55 cells",
        "List<float[]> pulled = new ArrayList<>();",
        "pulled.add(cellToWorld(raw.get(0)));",
        "",
        "int anchor = 0;",
        "for (int i = 2; i < raw.size(); i++) {",
        "    if (!lineOfSight(raw.get(anchor), raw.get(i))) {",
        "        // Can't see i from anchor  -  commit i-1 as a waypoint",
        "        pulled.add(cellToWorld(raw.get(i - 1)));",
        "        anchor = i - 1;",
        "    }",
        "}",
        "pulled.add(cellToWorld(raw.get(raw.size() - 1)));  // always include goal",
    ])

    pdf.chapter_title("5.2  Line-of-Sight Check (Bresenham)", 2)
    pdf.body(
        "The visibility test walks the Bresenham integer line between two cells and checks "
        "that every cell on the line is CELL_WALKABLE (state == 1). CELL_UNKNOWN or "
        "CELL_OBSTACLE cells break visibility, forcing a waypoint insertion:"
    )
    pdf.code_block([
        "boolean lineOfSight(int[] from, int[] to) {",
        "    // Bresenham line traversal",
        "    int dr = Math.abs(to[0]-from[0]), dc = Math.abs(to[1]-from[1]);",
        "    int r = from[0], c = from[1];",
        "    int err = dr - dc;",
        "    while (r != to[0] || c != to[1]) {",
        "        if (snapshot[r][c] != CELL_WALKABLE) return false;",
        "        int e2 = 2 * err;",
        "        if (e2 > -dc) { err -= dc; r += sr; }",
        "        if (e2 <  dr) { err += dr; c += sc; }",
        "    }",
        "    return true;",
        "}",
    ])

    # ------------------------------------------------------------------
    # 6. WaypointManager
    # ------------------------------------------------------------------
    pdf.chapter_title("6. WaypointManager: User-Placed Markers", 1)
    pdf.body("Three categories of waypoints are managed:")
    pdf.table(
        ["Type", "Created By", "Colour", "ARCore Anchor", "Role in Pathfinding"],
        [
            ["Start", "Auto (camera pos)", "Green", "No", "A* search origin"],
            ["Intermediate", "Short tap", "Cyan", "Yes", "Visual reference only"],
            ["Destination", "Long press", "Red", "Yes", "A* search goal"],
        ],
        col_widths=[28, 38, 20, 28, 56]
    )
    pdf.body(
        "Intermediate waypoints are rendered as AR spheres but are NOT threaded through the A* "
        "search. The planner finds a single optimal route from camera position to destination, "
        "passing through walkable cells. The cyan markers provide visual cues for users who want "
        "to indicate approximate corridor choices."
    )
    pdf.code_block([
        "class Waypoint {",
        "    float[] position;       // {x, y, z} in ARCore world space",
        "    Anchor  anchor;         // null for start (camera position)",
        "    boolean isDestination;  // triggers A* on placement",
        "}",
    ])

    # ------------------------------------------------------------------
    # 7. NavigationManager
    # ------------------------------------------------------------------
    pdf.chapter_title("7. NavigationManager: Orchestration", 1)

    pdf.chapter_title("7.1  Path Request Flow", 2)
    pdf.code_block([
        "void requestPath(float[] start, float[] goal) {",
        "    navState = AppState.PATHFINDING;",
        "    executor.execute(() -> {",
        "        int[]   startCell = navGrid.worldToCell(start[0], start[2]);",
        "        int[]   goalCell  = navGrid.worldToCell(goal[0],  goal[2]);",
        "        int[][] snapshot  = navGrid.getSnapshot();",
        "",
        "        List<float[]> path = AStarPlanner.findPath(",
        "            snapshot, GRID_SIZE, startCell, goalCell,",
        "            navGrid::cellToWorld);",
        "",
        "        if (path != null) {",
        "            latestPath.set(path);       // AtomicReference for GL thread",
        "            nextPathIndex = 0;",
        "            navState = AppState.NAVIGATING;",
        "            callback.onPathFound(path);",
        "        } else {",
        "            navState = AppState.PLACE_WAYPOINTS;",
        "            callback.onPathNotFound();",
        "        }",
        "    });",
        "}",
    ])

    pdf.chapter_title("7.2  Real-Time Direction Calculation", 2)
    pdf.body(
        "Every frame while in NAVIGATING state, getInstruction() computes the bearing from the "
        "camera to the next path waypoint:"
    )
    pdf.code_block([
        "NavInstruction getInstruction(float[] viewMatrix, float[] camPos) {",
        "    float[] nextWP = latestPath.get().get(nextPathIndex);",
        "",
        "    // Camera forward direction (world space) from view matrix column 2",
        "    float fwdX = -viewMatrix[2];",
        "    float fwdZ = -viewMatrix[10];",
        "",
        "    // Vector to next waypoint (XZ plane only)",
        "    float dx = nextWP[0] - camPos[0];",
        "    float dz = nextWP[2] - camPos[2];",
        "    float dist = (float) Math.sqrt(dx*dx + dz*dz);",
        "",
        "    // Signed angle between forward and target (radians -> degrees)",
        "    float cross = fwdX*dz - fwdZ*dx;   // sin component",
        "    float dot   = fwdX*dx + fwdZ*dz;   // cos component",
        "    float angleDeg = (float) Math.toDegrees(Math.atan2(cross, dot));",
        "",
        "    return new NavInstruction(directionLabel(angleDeg), dist);",
        "}",
    ])
    pdf.body("The bearing thresholds that map to direction labels:")
    pdf.table(
        ["Angle Range", "Label"],
        [
            ["|angle| > 135°", "Turn around"],
            ["-135° to -45°", "Turn left"],
            ["+45° to +135°", "Turn right"],
            ["|angle| <= 15°", "Go straight"],
            ["-45° to 0°", "Bear left"],
            ["0° to +45°", "Bear right"],
            ["dist < 0.6 m (final node)", "You have arrived!"],
        ],
        col_widths=[60, 110]
    )

    pdf.chapter_title("7.3  Waypoint Advance & Arrival", 2)
    pdf.code_block([
        "// Called every frame in NAVIGATING state",
        "if (dist < ARRIVAL_DISTANCE) {         // 0.6 m threshold",
        "    nextPathIndex++;",
        "    if (nextPathIndex >= latestPath.get().size()) {",
        "        navState = AppState.ARRIVED;",
        "        callback.onArrived();",
        "    }",
        "}",
    ])

    # ------------------------------------------------------------------
    # 8. Dynamic Re-Planning
    # ------------------------------------------------------------------
    pdf.chapter_title("8. Dynamic Re-Planning", 1)
    pdf.body(
        "When NavGrid.markObstacle() stamps a new CELL_OBSTACLE and the app is in NAVIGATING state, "
        "NavigationManager checks whether the newly blocked cells intersect the current path. If the "
        "obstacle lies within a threshold distance ahead of the user, requestPath() is called again "
        "from the current camera position to the same destination. The previous path remains "
        "displayed until the new path is ready, providing seamless visual continuity."
    )
    pdf.code_block([
        "// Called after each NavGrid.markObstacle()",
        "if (navState == AppState.NAVIGATING && obstacleOnCurrentPath(worldX, worldZ)) {",
        "    // Re-plan from current camera position to same destination",
        "    requestPath(latestCameraPos, destinationWorld);",
        "}",
    ])

    # ------------------------------------------------------------------
    # 9. PathRenderer
    # ------------------------------------------------------------------
    pdf.chapter_title("9. PathRenderer: AR Path Visualisation", 1)
    pdf.body(
        "PathRenderer draws two visual elements using OpenGL ES 3.0 and the path_dots.vert/frag "
        "shader pair:"
    )
    for item in [
        "Path line: a GL_LINE_STRIP connecting each successive float[3] world node. Colour: orange (1.0, 0.5, 0.0).",
        "Waypoint spheres: GL_POINTS with path_dots.frag clipping pixels outside a unit disc radius (round billboard effect). Colours: green (start), cyan (intermediate), red (destination).",
        "The view and projection matrices from ARCore are passed as uniforms each frame so the geometry stays locked to world space.",
    ]:
        pdf.bullet(item)

    # ------------------------------------------------------------------
    # 10. Constants & Parameters
    # ------------------------------------------------------------------
    pdf.chapter_title("10. Key Constants & Configuration", 1)
    pdf.table(
        ["Constant", "Value", "File", "Purpose"],
        [
            ["CELL_SIZE", "0.20 m", "NavGrid", "Grid granularity"],
            ["GRID_SIZE", "100 x 100", "NavGrid", "20m x 20m coverage area"],
            ["ELEVATED_SURFACE_THRESHOLD", "0.30 m", "NavGrid", "Desk/floor classification height"],
            ["OBSTACLE_EXPIRY", "300 frames", "NavGrid", "~10 s at 30 FPS"],
            ["ARRIVAL_DISTANCE", "0.60 m", "NavigationManager", "Waypoint reach radius"],
            ["A*_CARDINAL_COST", "1.0", "AStarPlanner", "Straight move cost"],
            ["A*_DIAGONAL_COST", "1.414", "AStarPlanner", "Diagonal move cost (sqrt2)"],
            ["A*_UNKNOWN_PENALTY", "4.0", "AStarPlanner", "Cost surcharge on unscanned cells"],
            ["A*_OBSTACLE_PENALTY", "2.0", "AStarPlanner", "Clearance penalty near CELL_OBSTACLE"],
            ["YOLO_EVERY_N_FRAMES", "10", "ComputerVisionActivity", "Inference throttle"],
            ["OBSTACLE_EXPAND_CELLS", "1", "NavGrid", "Wall safety margin"],
        ],
        col_widths=[58, 28, 44, 40]
    )

    # ------------------------------------------------------------------
    # 11. End-to-End Data Flow
    # ------------------------------------------------------------------
    pdf.chapter_title("11. End-to-End Data Flow Summary", 1)
    pdf.body("The complete navigation data flow across all threads:")
    pdf.code_block([
        "GL Thread (30 Hz)                   Background Executor",
        "--------------------                ------------------------------",
        "session.update()                    rebuildFromPlanes(planes)",
        "  -> camera.getPose()                  -> NavGrid.markWalkable()",
        "  -> latestCameraPos                   -> NavGrid.markStaticObstacle()",
        "  -> planes snapshot                   -> NavGrid.projectWall()",
        "                                    AStarPlanner.findPath(snapshot)",
        "frame image (every 10)                -> PriorityQueue search",
        "  -> imageToBitmap()                   -> string-pulling",
        "  -> inferenceExecutor  ----------->  ObjectDetectorHelper.detect()",
        "                                        -> NMS post-process",
        "pendingDetections.get()  <----------  pendingDetections.set(dets)",
        "  -> navGrid.markObstacle()",
        "  -> requestPath() if on path",
        "                       ----------->  AStarPlanner.findPath(snapshot)",
        "                                        -> latestPath.set(path)",
        "getInstruction(viewMatrix)  <-------  (path available on next frame)",
        "  -> NavigationOverlayView.setText()",
        "pathRenderer.draw(latestPath)",
    ])

    pdf.output(os.path.join(OUTPUT_DIR, "3_Route_Planning_Navigation.pdf"))
    print("  [OK] 3_Route_Planning_Navigation.pdf")


# ===========================================================================
# Main
# ===========================================================================

if __name__ == "__main__":
    print("Generating OnDeviceNav technical documentation PDFs...")
    build_slam_pdf()
    build_cv_pdf()
    build_nav_pdf()
    print("Done. Three PDFs written to:", OUTPUT_DIR)
