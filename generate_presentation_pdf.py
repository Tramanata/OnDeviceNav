"""
Generate a presentation PDF for the AR Indoor Navigation app.
Run with: python generate_presentation_pdf.py
"""
from fpdf import FPDF
import os

OUT_PATH = os.path.join(os.path.dirname(__file__), "AR_Navigation_Presentation.pdf")

# -- Colours (R, G, B) ------------------------------------------------------
DARK_BG      = (18,  18,  40)
ACCENT_BLUE  = (66, 135, 245)
ACCENT_ORG   = (255, 165,  50)
ACCENT_GRN   = ( 72, 199, 116)
ACCENT_RED   = (242,  82,  82)
WHITE        = (255, 255, 255)
LIGHT_GREY   = (200, 210, 225)
MID_GREY     = (140, 155, 175)
CARD_BG      = ( 30,  35,  60)

class PDF(FPDF):
    def __init__(self):
        super().__init__(orientation="L", unit="mm", format="A4")
        self.set_auto_page_break(auto=False)
        self.set_margins(0, 0, 0)

    # -- Drawing helpers ----------------------------------------------------

    def filled_rect(self, x, y, w, h, r, g, b, corner_radius=0):
        self.set_fill_color(r, g, b)
        self.rect(x, y, w, h, style="F")

    def accent_bar(self, x, y, w=4, h=12, r=66, g=135, b=245):
        """Coloured vertical bar used as a section prefix."""
        self.set_fill_color(r, g, b)
        self.rect(x, y, w, h, style="F")

    def draw_pill(self, x, y, w, h, r, g, b):
        """Simple filled rounded-look rectangle (use for badges)."""
        self.set_fill_color(r, g, b)
        self.rect(x, y, w, h, style="F")

    def heading(self, text, x, y, size=22, r=255, g=255, b=255):
        self.set_font("Helvetica", "B", size)
        self.set_text_color(r, g, b)
        self.set_xy(x, y)
        self.cell(0, size * 0.45, text, ln=0)

    def body(self, text, x, y, w, size=10, r=200, g=210, b=225, align="L", bold=False):
        style = "B" if bold else ""
        self.set_font("Helvetica", style, size)
        self.set_text_color(r, g, b)
        self.set_xy(x, y)
        self.multi_cell(w, size * 0.45, text, align=align)

    def small_label(self, text, x, y, r=140, g=155, b=175):
        self.set_font("Helvetica", "", 8)
        self.set_text_color(r, g, b)
        self.set_xy(x, y)
        self.cell(0, 4, text)

    def bullet(self, text, x, y, w, size=10, dot_r=66, dot_g=135, dot_b=245, indent=4):
        """Render a bullet point with a coloured dot."""
        self.set_fill_color(dot_r, dot_g, dot_b)
        self.ellipse(x, y + size * 0.16, 2, 2, style="F")
        self.body(text, x + indent, y, w - indent, size)

    def page_footer(self, label):
        self.set_font("Helvetica", "", 7)
        self.set_text_color(*MID_GREY)
        self.set_xy(8, 196)
        self.cell(0, 4, label)
        # page number right-aligned
        self.set_xy(0, 196)
        self.set_font("Helvetica", "", 7)
        self.cell(290, 4, f"Page {self.page_no()}", align="R")

    def section_card(self, x, y, w, h, title, title_r=66, title_g=135, title_b=245):
        """Dark card with a coloured title bar strip."""
        self.filled_rect(x, y, w, h, *CARD_BG)
        self.filled_rect(x, y, w, 1.5, title_r, title_g, title_b)
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(title_r, title_g, title_b)
        self.set_xy(x + 3, y + 2.5)
        self.cell(w - 6, 5, title.upper())


# ==============================================================================
#  PAGE 1 -- TITLE
# ==============================================================================
def page_title(pdf: PDF):
    pdf.add_page()
    W, H = 297, 210

    # Background gradient simulation (two rects)
    pdf.filled_rect(0, 0, W, H, *DARK_BG)
    pdf.filled_rect(0, 0, W//2, H, 22, 22, 48)   # slightly lighter left half

    # Large accent line at top
    pdf.filled_rect(0, 0, W, 3, *ACCENT_BLUE)

    # Decorative corner circle
    pdf.set_fill_color(66, 135, 245)
    pdf.ellipse(220, -30, 120, 120, style="F")
    pdf.set_fill_color(*DARK_BG)
    pdf.ellipse(235, -20, 100, 100, style="F")

    # Badge
    pdf.draw_pill(18, 30, 55, 8, *ACCENT_BLUE)
    pdf.set_font("Helvetica", "B", 7)
    pdf.set_text_color(*WHITE)
    pdf.set_xy(18, 30)
    pdf.cell(55, 8, "TECHNICAL PRESENTATION", align="C")

    # Main title
    pdf.set_font("Helvetica", "B", 36)
    pdf.set_text_color(*WHITE)
    pdf.set_xy(18, 50)
    pdf.cell(0, 16, "AR Indoor Navigation")

    pdf.set_font("Helvetica", "B", 22)
    pdf.set_text_color(*ACCENT_BLUE)
    pdf.set_xy(18, 68)
    pdf.cell(0, 10, "SLAM  ·  Computer Vision  ·  Route Planning")

    pdf.set_font("Helvetica", "", 12)
    pdf.set_text_color(*LIGHT_GREY)
    pdf.set_xy(18, 83)
    pdf.cell(0, 6, "How three technologies fuse into a real-time indoor navigation system")

    # Divider
    pdf.filled_rect(18, 95, 80, 0.8, *ACCENT_BLUE)

    # Subtitle block -- three tech pills
    cols = [(ACCENT_BLUE, "Google ARCore SLAM"), (ACCENT_ORG, "YOLO11 Object Detection"),
            (ACCENT_GRN, "A* Route Planning")]
    sx = 18
    for col, label in cols:
        pdf.draw_pill(sx, 102, 72, 9, *col)
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_text_color(*WHITE)
        pdf.set_xy(sx, 102)
        pdf.cell(72, 9, label, align="C")
        sx += 78

    # Summary description
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(*LIGHT_GREY)
    pdf.set_xy(18, 118)
    pdf.multi_cell(180, 5,
        "Built on the ARCore ComputerVision sample, this Android app turns any smartphone into\n"
        "a fully self-contained indoor navigator -- no beacons, no pre-built maps, no internet.\n"
        "The phone scans, plans, and guides in real time using only its camera and ARCore.", align="L")

    # Stat boxes
    stats = [("20 m × 20 m", "Nav Grid Coverage"), ("0.20 m", "Grid Cell Resolution"),
             ("30 Hz", "ARCore SLAM Update"), ("Every 10 frames", "YOLO Inference")]
    bx = 18
    for val, lbl in stats:
        pdf.filled_rect(bx, 148, 62, 22, *CARD_BG)
        pdf.filled_rect(bx, 148, 62, 1.5, *ACCENT_BLUE)
        pdf.set_font("Helvetica", "B", 13)
        pdf.set_text_color(*ACCENT_BLUE)
        pdf.set_xy(bx + 2, 151)
        pdf.cell(58, 7, val, align="C")
        pdf.set_font("Helvetica", "", 7.5)
        pdf.set_text_color(*LIGHT_GREY)
        pdf.set_xy(bx + 2, 159)
        pdf.cell(58, 4, lbl, align="C")
        bx += 67

    pdf.page_footer("AR Indoor Navigation -- Technical Overview")


# ==============================================================================
#  PAGE 2 -- SYSTEM ARCHITECTURE OVERVIEW
# ==============================================================================
def page_architecture(pdf: PDF):
    pdf.add_page()
    W, H = 297, 210
    pdf.filled_rect(0, 0, W, H, *DARK_BG)
    pdf.filled_rect(0, 0, W, 3, *ACCENT_BLUE)

    pdf.heading("System Architecture", 12, 8, 18)
    pdf.body("How the three subsystems are wired together every frame", 12, 20, 200, 10, *MID_GREY)

    # -- Central flow diagram (simplified boxes + arrows) ------------------
    # Row 1: Inputs
    input_y = 32
    pdf.section_card(12, input_y, 60, 26, "Camera Hardware", *ACCENT_BLUE)
    pdf.body("RGB + IMU sensor stream\nAndroid camera2 API", 15, input_y + 8, 54, 9)

    pdf.section_card(118, input_y, 60, 26, "ARCore Session", *ACCENT_BLUE)
    pdf.body("Processes camera + IMU\nOutputs: Frame, Planes, Pose", 121, input_y + 8, 54, 9)

    pdf.section_card(224, input_y, 60, 26, "CPU Image", *ACCENT_ORG)
    pdf.body("YUV_420_888 bitmap\nCopied to YOLO queue", 227, input_y + 8, 54, 9)

    # Arrows row 1 -> row 2
    def arrow_right(x, y):
        pdf.set_draw_color(*ACCENT_BLUE)
        pdf.set_line_width(0.5)
        pdf.line(x, y, x + 8, y)
        pdf.set_fill_color(*ACCENT_BLUE)
        pdf.polygon([[x+8, y-1.5], [x+8, y+1.5], [x+11, y]], style="F")

    arrow_right(72, input_y + 13)
    arrow_right(178, input_y + 13)

    # Row 2: processing
    proc_y = 72
    pdf.section_card(12, proc_y, 80, 32, "SLAM / Plane Detection", *ACCENT_BLUE)
    pdf.body(
        "Visual-Inertial Odometry (VIO)\n"
        "- Tracks 6-DOF phone pose @ 30Hz\n"
        "- Detects horizontal floor planes\n"
        "- Provides world-space anchors",
        15, proc_y + 8, 74, 9)

    pdf.section_card(108, proc_y, 80, 32, "NavGrid Builder", *ACCENT_GRN)
    pdf.body(
        "100×100 grid (20m × 20m, 0.20m cells)\n"
        "- WALKABLE -- floor polygon cells\n"
        "- STATIC_OBSTACLE -- elevated planes\n"
        "- Rebuilt from planes every 1 second",
        111, proc_y + 8, 74, 9)

    pdf.section_card(204, proc_y, 80, 32, "YOLO11 Inference", *ACCENT_ORG)
    pdf.body(
        "TFLite YOLO11 model (80 COCO classes)\n"
        "- Runs on background thread\n"
        "- Detects people, chairs, bags...\n"
        "- Projects bbox bottom edge -> floor",
        207, proc_y + 8, 74, 9)

    # Vertical arrows row2 -> row3
    def arrow_down(x, y):
        pdf.set_draw_color(*ACCENT_GRN)
        pdf.set_line_width(0.5)
        pdf.line(x, y, x, y + 8)
        pdf.set_fill_color(*ACCENT_GRN)
        pdf.polygon([[x-1.5, y+8], [x+1.5, y+8], [x, y+11]], style="F")

    arrow_down(52, proc_y + 32)
    arrow_down(148, proc_y + 32)
    arrow_down(244, proc_y + 32)

    # Row 3: A* + HUD
    plan_y = 118
    pdf.section_card(12, plan_y, 80, 30, "A* Pathfinder", *ACCENT_GRN)
    pdf.body(
        "8-connected grid, octile heuristic\n"
        "- Obstacle penalty + clearance cost\n"
        "- String-pulling (Bresenham LOS)\n"
        "- Returns world-space waypoints",
        15, plan_y + 8, 74, 9)

    pdf.section_card(108, plan_y, 80, 30, "PathRenderer", *ACCENT_ORG)
    pdf.body(
        "OpenGL ES 2.0 GL_POINTS shader\n"
        "- Orange dots on the floor plane\n"
        "- Updated atomically each frame\n"
        "- Projects 3-D world -> screen",
        111, plan_y + 8, 74, 9)

    pdf.section_card(204, plan_y, 80, 30, "HUD Overlay + State Machine", *ACCENT_RED)
    pdf.body(
        "Canvas drawn over GL surface\n"
        "- Turn direction + distance to target\n"
        "- YOLO detection bounding boxes\n"
        "- State: SCANNING -> NAVIGATING",
        207, plan_y + 8, 74, 9)

    # Join A* -> PathRenderer
    arrow_right(92, plan_y + 15)
    arrow_right(188, plan_y + 15)

    # Thread legend
    thread_y = 158
    pdf.filled_rect(12, thread_y, 272, 18, *CARD_BG)
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(*LIGHT_GREY)
    pdf.set_xy(16, thread_y + 3)
    pdf.cell(0, 4, "THREADING MODEL")
    labels = [
        (ACCENT_BLUE,  "GL Thread -- ARCore update, hit-test, state transitions, rendering"),
        (ACCENT_ORG,   "Background Executor -- YOLO inference, NavGrid rebuild, A* pathfinding"),
        (ACCENT_GRN,   "UI Thread -- HUD text updates, button visibility"),
    ]
    lx = 16
    for col, lbl in labels:
        pdf.draw_pill(lx, thread_y + 10, 7, 4, *col)
        pdf.set_font("Helvetica", "", 7.5)
        pdf.set_text_color(*LIGHT_GREY)
        pdf.set_xy(lx + 9, thread_y + 10)
        pdf.cell(80, 4, lbl)
        lx += 90

    pdf.page_footer("AR Indoor Navigation -- Technical Overview")


# ==============================================================================
#  PAGE 3 -- ARCore SLAM
# ==============================================================================
def page_slam(pdf: PDF):
    pdf.add_page()
    W, H = 297, 210
    pdf.filled_rect(0, 0, W, H, *DARK_BG)
    pdf.filled_rect(0, 0, W, 3, *ACCENT_BLUE)

    pdf.heading("Google ARCore -- SLAM & Plane Detection", 12, 8, 18, *WHITE)
    pdf.body("How the phone knows where it is and what the floor looks like", 12, 21, 250, 10, *MID_GREY)

    # Left column -- SLAM explanation
    col1_x = 12
    pdf.accent_bar(col1_x, 32, 4, 12, *ACCENT_BLUE)
    pdf.heading("What is SLAM?", col1_x + 7, 31, 13, *ACCENT_BLUE)
    pdf.body(
        "Simultaneous Localisation And Mapping (SLAM) lets the device\n"
        "build a map of its surroundings while simultaneously tracking\n"
        "its own position within that map -- all in real time, with no\n"
        "external reference (GPS, beacons, etc.).",
        col1_x, 46, 130, 10)

    pdf.accent_bar(col1_x, 78, 4, 12, *ACCENT_BLUE)
    pdf.heading("Visual-Inertial Odometry (VIO)", col1_x + 7, 77, 13, *ACCENT_BLUE)
    pdf.body(
        "ARCore fuses two sensor streams every frame:",
        col1_x, 92, 130, 10)

    bullets_vio = [
        ("Camera", "Tracks thousands of corner / edge feature points across frames. "
                   "Optical-flow estimates how the scene moved -> infers camera motion."),
        ("IMU (accelerometer + gyroscope)", "Measures raw acceleration and rotation at ~1 kHz. "
                   "Fused with vision using an Extended Kalman Filter (EKF)."),
    ]
    by = 102
    for title, desc in bullets_vio:
        pdf.set_fill_color(*ACCENT_BLUE)
        pdf.ellipse(col1_x + 1, by + 1.5, 2.5, 2.5, style="F")
        pdf.set_font("Helvetica", "B", 9.5)
        pdf.set_text_color(*ACCENT_BLUE)
        pdf.set_xy(col1_x + 5, by)
        pdf.cell(120, 5, title)
        by += 6
        pdf.body(desc, col1_x + 5, by, 120, 9)
        by += 10

    pdf.accent_bar(col1_x, 132, 4, 12, *ACCENT_BLUE)
    pdf.heading("6-DOF Pose Output", col1_x + 7, 131, 13, *ACCENT_BLUE)
    pdf.body(
        "Every call to session.update() returns a Camera.getPose() -- a full\n"
        "six-degree-of-freedom transform: X/Y/Z position (metres) and a\n"
        "quaternion orientation. This is the foundation for all AR rendering\n"
        "and our navigation HUD.",
        col1_x, 146, 130, 10)

    # Right column -- Plane detection
    col2_x = 155
    pdf.accent_bar(col2_x, 32, 4, 12, *ACCENT_GRN)
    pdf.heading("Plane Detection", col2_x + 7, 31, 13, *ACCENT_GRN)
    pdf.body(
        "ARCore analyses depth cues in the image to find large, flat\n"
        "surfaces. Each detected Plane object carries:\n",
        col2_x, 46, 130, 10)

    plane_props = [
        ("Center Pose",   "World-space position and orientation of the plane"),
        ("Polygon",       "Boundary vertices in plane-local coordinates"),
        ("Type",          "HORIZONTAL_UPWARD_FACING -- the walkable floor"),
        ("Extent X/Z",    "Physical width and length in metres"),
        ("TrackingState", "TRACKING = reliable; PAUSED = temporarily lost"),
    ]
    py = 64
    for prop, desc in plane_props:
        pdf.set_fill_color(*ACCENT_GRN)
        pdf.rect(col2_x + 1, py, 28, 5, style="F")
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_text_color(*WHITE)
        pdf.set_xy(col2_x + 1, py)
        pdf.cell(28, 5, prop, align="C")
        pdf.body(desc, col2_x + 31, py, 95, 9, *LIGHT_GREY)
        py += 8

    pdf.accent_bar(col2_x, 110, 4, 12, *ACCENT_GRN)
    pdf.heading("Floor -> Grid Translation", col2_x + 7, 109, 13, *ACCENT_GRN)
    pdf.body(
        "For each tracked floor plane the app:\n"
        "1. Reads the polygon vertex list (plane-local XZ)\n"
        "2. Calls Pose.transformPoint() -> world-space XZ\n"
        "3. Ray-casts each 20 cm grid cell centre against the polygon\n"
        "4. Marks cells inside the polygon as WALKABLE\n"
        "5. Marks elevated planes (>30 cm above floor) as STATIC_OBSTACLE\n\n"
        "This rebuild runs on a background thread at most once per second\n"
        "so it never blocks the 30 Hz render loop.",
        col2_x, 124, 130, 10)

    # Key code snippet
    pdf.filled_rect(col2_x, 170, 130, 28, 25, 28, 55)
    pdf.set_font("Courier", "", 7.5)
    pdf.set_text_color(*ACCENT_GRN)
    pdf.set_xy(col2_x + 2, 172)
    snippet = (
        "// ARCore: get 6-DOF camera pose\n"
        "Pose pose = camera.getPose();\n"
        "float x=pose.tx(), y=pose.ty(), z=pose.tz();\n\n"
        "// Transform plane polygon vertex to world space\n"
        "planePose.transformPoint(localPt,0, worldPt,0);\n\n"
        "// Mark cell walkable if inside polygon\n"
        "if (isPointInPolygon(wx, wz, polyX, polyZ))\n"
        "    cells[r][c] = CELL_WALKABLE;"
    )
    pdf.multi_cell(126, 3.5, snippet)

    pdf.page_footer("AR Indoor Navigation -- Technical Overview")


# ==============================================================================
#  PAGE 4 -- ROUTE PLANNING (NavGrid + A*)
# ==============================================================================
def page_routing(pdf: PDF):
    pdf.add_page()
    W, H = 297, 210
    pdf.filled_rect(0, 0, W, H, *DARK_BG)
    pdf.filled_rect(0, 0, W, 3, *ACCENT_GRN)

    pdf.heading("Route Planning -- NavGrid + A* Pathfinder", 12, 8, 18, *WHITE)
    pdf.body("Building a navigable map from live AR data and finding the shortest safe path", 12, 21, 250, 10, *MID_GREY)

    # -- NavGrid column ----------------------------------------------------
    cx = 12
    pdf.accent_bar(cx, 32, 4, 12, *ACCENT_GRN)
    pdf.heading("NavGrid -- The Walkable Map", cx + 7, 31, 13, *ACCENT_GRN)
    pdf.body(
        "A 100 × 100 array of 20 cm cells covering a 20 m × 20 m area.\n"
        "The grid origin is placed at the centre of the first detected floor\n"
        "plane when the app transitions out of the SCANNING state.",
        cx, 46, 132, 10)

    cell_types = [
        (ACCENT_GRN,   "WALKABLE",         "Inside an ARCore floor plane polygon"),
        (ACCENT_RED,   "OBSTACLE",         "YOLO detection projected to floor (decays in 10s)"),
        ((160,80,200), "STATIC_OBSTACLE",  "Elevated plane footprint (desk, sofa top)"),
        (MID_GREY,     "UNKNOWN",          "Not yet seen by the camera"),
    ]
    ty = 74
    for col, label, desc in cell_types:
        pdf.set_fill_color(*col)
        pdf.rect(cx, ty, 8, 5, style="F")
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(*col)
        pdf.set_xy(cx + 10, ty)
        pdf.cell(40, 5, label)
        pdf.body(desc, cx + 52, ty, 88, 9, *LIGHT_GREY)
        ty += 9

    pdf.accent_bar(cx, 114, 4, 12, *ACCENT_GRN)
    pdf.heading("Obstacle Decay", cx + 7, 113, 13, *ACCENT_GRN)
    pdf.body(
        "YOLO obstacles are timestamped with an expiry frame (current + 300\n"
        "frames ~ 10 seconds). Every second on the background thread,\n"
        "decayObstacles() scans the grid and clears expired cells back to\n"
        "UNKNOWN. This keeps the map fresh as people move around.",
        cx, 128, 132, 10)

    pdf.accent_bar(cx, 158, 4, 12, *ACCENT_GRN)
    pdf.heading("User Interaction", cx + 7, 157, 13, *ACCENT_GRN)
    pdf.body(
        "- User taps the floor -> ARCore hit-test returns the 3-D world point\n"
        "- Camera position becomes the start; tapped point becomes the goal\n"
        "- requestPath() is called immediately -- result arrives via callback",
        cx, 172, 132, 10)

    # -- A* column --------------------------------------------------------
    ax = 155
    pdf.accent_bar(ax, 32, 4, 12, *ACCENT_GRN)
    pdf.heading("A* Algorithm Details", ax + 7, 31, 13, *ACCENT_GRN)

    astar_points = [
        ("8-Connected Grid",
         "Each cell can move to its 8 neighbours -- cardinal cost 1.0, diagonal 1.414."),
        ("Octile Heuristic",
         "max(|Drow|, |Dcol|) + (sqrt2-1)·min(|Drow|, |Dcol|) -- admissible and consistent."),
        ("Obstacle Clearance Penalty",
         "Cells adjacent to any obstacle incur +2.0 cost, pushing the path away from walls."),
        ("Unknown-Cell Penalty",
         "+4.0 cost for UNKNOWN cells -- A* prefers confirmed floor but won't give up."),
        ("Grid Snapshot",
         "NavGrid.getSnapshot() clones the cell array before A* runs, so the grid can keep\n"
         "updating without a lock held during the search."),
        ("String-Pulling",
         "After raw A* finds a cell path, a Bresenham line-of-sight pass removes collinear\n"
         "intermediate nodes -- the result is a short list of corner waypoints."),
    ]
    ay = 46
    for title, desc in astar_points:
        pdf.set_fill_color(*ACCENT_GRN)
        pdf.ellipse(ax + 1, ay + 1.5, 2.5, 2.5, style="F")
        pdf.set_font("Helvetica", "B", 9.5)
        pdf.set_text_color(*ACCENT_GRN)
        pdf.set_xy(ax + 5, ay)
        pdf.cell(125, 5, title)
        ay += 6
        pdf.body(desc, ax + 5, ay, 125, 9)
        ay += 12 if "\n" in desc else 8

    # Code snippet
    pdf.filled_rect(ax, 164, 130, 34, 25, 28, 55)
    pdf.set_font("Courier", "", 7)
    pdf.set_text_color(*ACCENT_GRN)
    pdf.set_xy(ax + 2, 166)
    snippet = (
        "// A* cost with clearance penalty\n"
        "float dCost = dir[2]; // 1.0 or 1.414\n"
        "if (snap[nr][nc] == CELL_UNKNOWN)  dCost += 4.0f;\n"
        "if (hasAdjacentObstacle(...))       dCost += 2.0f;\n\n"
        "// Octile heuristic\n"
        "float octile(r1,c1,r2,c2) {\n"
        "  float dx=|r1-r2|, dz=|c1-c2|;\n"
        "  return max(dx,dz) + 0.414*min(dx,dz);\n"
        "}\n\n"
        "// String-pull: keep node only if LOS from anchor is blocked\n"
        "if (!lineOfSight(snap,anchor,i)) { pruned.add(i-1); anchor=i-1; }"
    )
    pdf.multi_cell(126, 3.2, snippet)

    pdf.page_footer("AR Indoor Navigation -- Technical Overview")


# ==============================================================================
#  PAGE 5 -- COMPUTER VISION (YOLO11)
# ==============================================================================
def page_cv(pdf: PDF):
    pdf.add_page()
    W, H = 297, 210
    pdf.filled_rect(0, 0, W, H, *DARK_BG)
    pdf.filled_rect(0, 0, W, 3, *ACCENT_ORG)

    pdf.heading("Computer Vision -- YOLO11 Object Detection", 12, 8, 18, *WHITE)
    pdf.body("Real-time obstacle identification fused with the ARCore world model", 12, 21, 250, 10, *MID_GREY)

    # Left -- YOLO pipeline
    cx = 12
    pdf.accent_bar(cx, 32, 4, 12, *ACCENT_ORG)
    pdf.heading("YOLO11 Inference Pipeline", cx + 7, 31, 13, *ACCENT_ORG)

    steps = [
        ("1. Acquire Frame",
         "Every 10th GL frame (~3 Hz), acquireCameraImage() grabs a YUV_420_888\n"
         "image from the ARCore session on the GL thread inside frameImageInUseLock."),
        ("2. Convert to Bitmap",
         "ImageUtils.imageToBitmap() converts YUV planes to an ARGB Bitmap and\n"
         "rotates it by getCameraToDisplayRotation() × 90° so the model sees\n"
         "the image the right way up."),
        ("3. Run YOLO11",
         "ObjectDetectorHelper.detect() scales the bitmap to the model input size,\n"
         "runs TFLite inference, applies Non-Max Suppression, and returns a list\n"
         "of Detection objects (classId, confidence, normalised bounding box)."),
        ("4. Floor Projection",
         "For each obstacle-class detection, 5 sample points along the bottom edge\n"
         "of the bounding box are un-projected through the camera intrinsics (fx, fy,\n"
         "cx, cy) to a ray in camera space, rotated to world space, then intersected\n"
         "with the floor plane (Y = floorWorldY) to get a 3-D foot position."),
        ("5. Mark Obstacles",
         "NavGrid.markObstacle() stamps a radius of cells (scaled with bbox width)\n"
         "as CELL_OBSTACLE with an expiry timestamp. The larger the detected object,\n"
         "the wider the blocked zone (clamped to 2-6 cells = 40-120 cm)."),
        ("6. Re-route",
         "If the app is NAVIGATING and new obstacles appear, requestPath() is called\n"
         "again immediately. A* finds a fresh route around the new blockage."),
    ]
    sy = 46
    for title, desc in steps:
        pdf.set_fill_color(*ACCENT_ORG)
        pdf.ellipse(cx + 1, sy + 1.5, 2.5, 2.5, style="F")
        pdf.set_font("Helvetica", "B", 9.5)
        pdf.set_text_color(*ACCENT_ORG)
        pdf.set_xy(cx + 5, sy)
        pdf.cell(120, 5, title)
        sy += 6
        pdf.body(desc, cx + 5, sy, 125, 9)
        sy += 14 if "\n\n" not in desc else 18

    # Right -- Camera intrinsics + obstacle classes
    rx = 155
    pdf.accent_bar(rx, 32, 4, 12, *ACCENT_ORG)
    pdf.heading("Camera Intrinsics Explained", rx + 7, 31, 13, *ACCENT_ORG)
    pdf.body(
        "ARCore provides the camera's intrinsic parameters so we can convert\n"
        "from 2-D image pixels to 3-D world-space rays:\n",
        rx, 46, 130, 10)

    intrinsics = [
        ("fx, fy", "Focal length in pixels (horizontal, vertical)"),
        ("cx, cy", "Principal point -- optical centre of the image"),
        ("Formula", "ray_x = (px - cx) / fx;  ray_y = (py - cy) / fy;  ray_z = 1"),
        ("Floor hit", "t = (floorY - camY) / ray_world_Y;  hitXZ = cam + t·rayXZ"),
    ]
    iy = 62
    for k, v in intrinsics:
        pdf.set_fill_color(*ACCENT_ORG)
        pdf.rect(rx, iy, 18, 5, style="F")
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_text_color(*WHITE)
        pdf.set_xy(rx, iy)
        pdf.cell(18, 5, k, align="C")
        pdf.body(v, rx + 20, iy, 108, 9, *LIGHT_GREY)
        iy += 8

    pdf.accent_bar(rx, 100, 4, 12, *ACCENT_ORG)
    pdf.heading("Obstacle Classes (COCO IDs)", rx + 7, 99, 13, *ACCENT_ORG)
    classes = [
        "0 -- Person", "13 -- Bench", "24 -- Backpack", "26 -- Handbag",
        "28 -- Suitcase", "56 -- Chair", "57 -- Couch", "58 -- Potted plant",
        "59 -- Bed", "60 -- Dining table", "62 -- TV / Monitor", "63 -- Laptop",
    ]
    oc_y = 114
    oc_x = rx
    for i, cls in enumerate(classes):
        pdf.draw_pill(oc_x, oc_y, 60, 6, *CARD_BG)
        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(*LIGHT_GREY)
        pdf.set_xy(oc_x + 2, oc_y)
        pdf.cell(58, 6, cls)
        oc_x += 65
        if (i + 1) % 2 == 0:
            oc_x = rx
            oc_y += 8

    pdf.accent_bar(rx, 164, 4, 12, *ACCENT_ORG)
    pdf.heading("Threading -- No GL Stalls", rx + 7, 163, 13, *ACCENT_ORG)
    pdf.body(
        "YOLO runs entirely on a separate background ExecutorService. The GL\n"
        "thread only:\n"
        "  a) acquires + immediately closes the camera image\n"
        "  b) converts YUV -> Bitmap\n"
        "  c) posts the Bitmap to the executor\n\n"
        "An AtomicBoolean gate (isProcessingFrame) ensures that if the previous\n"
        "inference hasn't finished, the new frame is skipped -- no backpressure.",
        rx, 178, 130, 9.5)

    pdf.page_footer("AR Indoor Navigation -- Technical Overview")


# ==============================================================================
#  PAGE 6 -- STATE MACHINE + DEMO FLOW
# ==============================================================================
def page_states(pdf: PDF):
    pdf.add_page()
    W, H = 297, 210
    pdf.filled_rect(0, 0, W, H, *DARK_BG)
    pdf.filled_rect(0, 0, W, 3, *ACCENT_BLUE)

    pdf.heading("State Machine & Demo Flow", 12, 8, 18, *WHITE)
    pdf.body("Five states that drive the entire app experience", 12, 21, 250, 10, *MID_GREY)

    # State boxes ---------------------------------------------------------
    states = [
        ("SCANNING",       ACCENT_BLUE,
         "Move phone over floor",
         "ARCore detects first floor plane (>=0.5 m extent) -> NavGrid initialised"),
        ("PLACE_WAYPOINTS", ACCENT_GRN,
         "Tap the floor",
         "ARCore hit-test returns 3-D point. Camera = start. Tap = destination."),
        ("PATHFINDING",    ACCENT_ORG,
         "Computing route...",
         "NavGrid snapshot taken. A* runs on background thread. Path delivered via callback."),
        ("NAVIGATING",     (72, 199, 116),
         "Follow the dots",
         "PathRenderer draws orange floor dots. HUD shows direction + distance to next node. YOLO re-routes on obstacle."),
        ("ARRIVED",        ACCENT_RED,
         "You have arrived!",
         "nextPathIndex >= path.size(). Reset button returns to PLACE_WAYPOINTS."),
    ]

    sx = 12
    for i, (name, col, prompt, detail) in enumerate(states):
        # State box
        pdf.filled_rect(sx, 32, 50, 40, *CARD_BG)
        pdf.filled_rect(sx, 32, 50, 3, *col)
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(*col)
        pdf.set_xy(sx + 2, 36)
        pdf.cell(46, 5, name, align="C")
        pdf.set_font("Helvetica", "I", 8)
        pdf.set_text_color(*WHITE)
        pdf.set_xy(sx + 2, 43)
        pdf.cell(46, 4, f'"{prompt}"', align="C")
        pdf.body(detail, sx + 2, 49, 46, 8, *LIGHT_GREY)

        # Arrow between states
        if i < len(states) - 1:
            pdf.set_draw_color(*col)
            pdf.set_line_width(0.6)
            pdf.line(sx + 50, 52, sx + 57, 52)
            pdf.set_fill_color(*col)
            pdf.polygon([[sx+57, 50.5], [sx+57, 53.5], [sx+60, 52]], style="F")

        sx += 57

    # Detailed interaction diagram -----------------------------------------
    pdf.accent_bar(12, 82, 4, 12, *ACCENT_BLUE)
    pdf.heading("Per-Frame Loop (NAVIGATING state)", 19, 81, 13, *ACCENT_BLUE)

    loop_steps = [
        ("GL Thread -- every frame (~30 Hz)",
         ACCENT_BLUE,
         [
             "session.update() -> get Frame, Camera, Planes",
             "camera.getPose() -> update latestCameraPos",
             "navigationManager.scheduleGridRebuild(planes) -> posts to background if >=1s",
             "checkArrival() -> advance nextPathIndex as camera nears each node",
             "updateHud() -> compute angle + distance -> push to navOverlay on UI thread",
             "pathRenderer.draw() -> render orange GL_POINTS dot trail",
             "Every 10th frame: tryPostYoloFrame() -> Bitmap -> background executor",
             "tickObstacleDecay() -> every 30 frames, prune expired obstacles",
         ]),
        ("Background Executor (single thread, queued)",
         ACCENT_ORG,
         [
             "navGrid.rebuildFromPlanes() -> reclassify all cells from current planes",
             "objectDetector.detect(bitmap) -> YOLO11 inference -> Detection list",
             "navigationManager.processObstacles() -> project detections -> mark grid cells",
             "astar.findPath() -> grid snapshot search -> string-pulled world path",
         ]),
    ]

    ly = 98
    for title, col, items in loop_steps:
        pdf.filled_rect(12, ly, 272, 6, *col)
        pdf.set_font("Helvetica", "B", 8.5)
        pdf.set_text_color(*WHITE)
        pdf.set_xy(14, ly)
        pdf.cell(270, 6, title)
        ly += 8
        ix = 14
        col_count = 0
        for item in items:
            pdf.set_fill_color(*col)
            pdf.ellipse(ix, ly + 1.5, 2, 2, style="F")
            pdf.set_font("Helvetica", "", 8.5)
            pdf.set_text_color(*LIGHT_GREY)
            pdf.set_xy(ix + 4, ly)
            pdf.cell(128, 4.5, item)
            col_count += 1
            if col_count % 2 == 0:
                ix = 14
                ly += 6
            else:
                ix = 150
        if col_count % 2 != 0:
            ly += 6
        ly += 3

    pdf.page_footer("AR Indoor Navigation -- Technical Overview")


# ==============================================================================
#  PAGE 7 -- RENDERING + KEY DESIGN DECISIONS
# ==============================================================================
def page_rendering(pdf: PDF):
    pdf.add_page()
    W, H = 297, 210
    pdf.filled_rect(0, 0, W, H, *DARK_BG)
    pdf.filled_rect(0, 0, W, 3, *ACCENT_ORG)

    pdf.heading("Rendering & Key Design Decisions", 12, 8, 18, *WHITE)
    pdf.body("How the navigation path is drawn in 3-D and the trade-offs behind each choice", 12, 21, 250, 10, *MID_GREY)

    # Rendering column
    cx = 12
    pdf.accent_bar(cx, 32, 4, 12, *ACCENT_ORG)
    pdf.heading("PathRenderer -- GL_POINTS Dot Trail", cx + 7, 31, 13, *ACCENT_ORG)
    pdf.body(
        "The navigation path is visualised as a series of orange circles\n"
        "lying flat on the floor, spaced 20 cm apart (one per grid cell).\n"
        "This was chosen over a line mesh because:\n",
        cx, 46, 130, 10)
    render_bullets = [
        "GL_POINTS is the cheapest GL primitive -- no index buffers, no strip topology",
        "gl_PointSize in the vertex shader lets each point appear as a round disc",
        "Points auto-scale with depth (perspective divide) keeping them consistent",
        "The fragment shader discards pixels outside the inscribed circle for a clean look",
    ]
    ry = 68
    for b in render_bullets:
        pdf.bullet(b, cx, ry, 132, 9, *ACCENT_ORG)
        ry += 8

    pdf.accent_bar(cx, 105, 4, 12, *ACCENT_ORG)
    pdf.heading("PlaneRenderer -- Floor Visualisation", cx + 7, 104, 13, *ACCENT_ORG)
    pdf.body(
        "ARCore's built-in PlaneRenderer draws a transparent grid texture\n"
        "(trigrid.png) on each detected floor plane during SCANNING and\n"
        "PLACE_WAYPOINTS. It disappears in NAVIGATING to reduce visual clutter.",
        cx, 119, 130, 10)

    pdf.accent_bar(cx, 145, 4, 12, *ACCENT_ORG)
    pdf.heading("HUD Overlay (NavigationOverlayView)", cx + 7, 144, 13, *ACCENT_ORG)
    pdf.body(
        "A transparent Android View drawn over the GLSurfaceView. It renders:\n"
        "- Large direction arrow + text (Turn left / Go straight / Arrived)\n"
        "- Distance readout in metres\n"
        "- YOLO bounding boxes with class label and confidence\n"
        "- State prompt (e.g. 'Tap the floor to set your destination')\n\n"
        "All updates are posted with runOnUiThread() from the GL or background\n"
        "thread -- the View itself never touches AR data directly.",
        cx, 159, 130, 10)

    # Design decisions column
    rx = 155
    pdf.accent_bar(rx, 32, 4, 12, *ACCENT_BLUE)
    pdf.heading("Key Design Decisions", rx + 7, 31, 13, *ACCENT_BLUE)

    decisions = [
        ("No Pre-built Map",
         "The app builds its map live from ARCore planes. Users point the camera\n"
         "at the floor for 3-5 seconds before navigating -- zero setup required."),
        ("Camera = Navigation Start",
         "Rather than placing a 'start waypoint', the camera's current world\n"
         "position is always the path start. This means the path updates from\n"
         "the current location whenever re-routing occurs."),
        ("Unknown Cells != Blocked",
         "A* treats unscanned cells with a penalty (cost +4) but not as walls.\n"
         "This prevents 'no path found' failures in partially scanned spaces."),
        ("Single Background Executor",
         "One single-threaded ExecutorService serialises grid rebuilds, YOLO\n"
         "inference, and A* calls. No concurrency bugs; tasks naturally queue."),
        ("Obstacle Expiry (10 s)",
         "YOLO obstacles decay after 300 frames (~10 s) to handle moving people.\n"
         "Static furniture is captured by the plane-based STATIC_OBSTACLE system."),
        ("Throttled Rebuild (1 Hz)",
         "NavGrid.rebuildFromPlanes() is expensive on large grids, so it is\n"
         "throttled to once per second -- sufficient for indoor walking speeds."),
    ]
    dy = 46
    for title, desc in decisions:
        pdf.set_fill_color(*ACCENT_BLUE)
        pdf.ellipse(rx + 1, dy + 1.5, 2.5, 2.5, style="F")
        pdf.set_font("Helvetica", "B", 9.5)
        pdf.set_text_color(*ACCENT_BLUE)
        pdf.set_xy(rx + 5, dy)
        pdf.cell(125, 5, title)
        dy += 6
        pdf.body(desc, rx + 5, dy, 125, 9)
        dy += 14 if "\n" in desc else 10

    pdf.page_footer("AR Indoor Navigation -- Technical Overview")


# ==============================================================================
#  PAGE 8 -- SUMMARY / DEMO CHEAT-SHEET
# ==============================================================================
def page_summary(pdf: PDF):
    pdf.add_page()
    W, H = 297, 210
    pdf.filled_rect(0, 0, W, H, *DARK_BG)
    pdf.filled_rect(0, 0, W, 3, *ACCENT_BLUE)

    pdf.heading("Summary & Demo Cheat-Sheet", 12, 8, 18, *WHITE)
    pdf.body("Everything on one page for a quick reference during the presentation", 12, 21, 250, 10, *MID_GREY)

    # Integration diagram -- concise text version
    pdf.accent_bar(12, 30, 4, 12, *ACCENT_BLUE)
    pdf.heading("How the Three Systems Integrate", 19, 29, 13, *ACCENT_BLUE)
    pdf.body(
        "SLAM (ARCore)  ->  provides real-time 6-DOF pose + floor polygon data\n"
        "NavGrid         ->  converts polygons into a 2-D walkable occupancy grid\n"
        "YOLO11 (CV)    ->  detects obstacles from camera frames, projects to the grid\n"
        "A* Planner      ->  searches the grid for the shortest clear path\n"
        "PathRenderer   ->  draws the path as 3-D orange dots anchored to the floor\n"
        "HUD Overlay    ->  reads camera pose vs path nodes -> real-time turn-by-turn\n",
        12, 44, 272, 10)

    # Three-column tech summary cards
    cards = [
        ("ARCore SLAM", ACCENT_BLUE, [
            ("Input",    "Camera RGB + IMU"),
            ("Output",   "6-DOF Pose @ 30 Hz"),
            ("Planes",   "Polygon + Pose + Type"),
            ("Key API",  "session.update()"),
            ("Key API",  "frame.hitTest()"),
            ("Key API",  "camera.getPose()"),
        ]),
        ("YOLO11 CV", ACCENT_ORG, [
            ("Model",    "YOLO11 TFLite (80 classes)"),
            ("Rate",     "~3 Hz (every 10 frames)"),
            ("Thread",   "Background executor"),
            ("Output",   "BBox + classId + confidence"),
            ("Mapping",  "BBox bottom -> floor ray cast"),
            ("Classes",  "Person, chair, bag, couch..."),
        ]),
        ("Route Planning", ACCENT_GRN, [
            ("Grid",     "100×100 cells, 0.20 m each"),
            ("Coverage", "20 m × 20 m area"),
            ("Algorithm","A* octile, 8-connected"),
            ("Penalty",  "+2 clearance, +4 unknown"),
            ("Smoothing","Bresenham string-pulling"),
            ("Re-route", "On every new obstacle set"),
        ]),
    ]

    card_y = 96
    card_x = 12
    card_w = 87
    for title, col, rows in cards:
        pdf.filled_rect(card_x, card_y, card_w, 80, *CARD_BG)
        pdf.filled_rect(card_x, card_y, card_w, 8, *col)
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(*WHITE)
        pdf.set_xy(card_x, card_y)
        pdf.cell(card_w, 8, title, align="C")
        ry = card_y + 10
        for k, v in rows:
            pdf.set_font("Helvetica", "B", 8)
            pdf.set_text_color(*col)
            pdf.set_xy(card_x + 3, ry)
            pdf.cell(20, 5, k)
            pdf.body(v, card_x + 24, ry, card_w - 26, 8.5, *LIGHT_GREY)
            ry += 10
        card_x += card_w + 6

    # Demo talking points
    card_x2 = 12 + 3 * (card_w + 6) + 4
    pdf.accent_bar(card_x2, 96, 4, 12, *ACCENT_RED)
    pdf.heading("15-Minute Demo Script", card_x2 + 7, 95, 11, *ACCENT_RED)
    script = [
        ("0:00-2:00",  "Open app -> show SCANNING state. Walk slowly over floor.\n"
                       "Explain: ARCore is running VIO + plane detection right now."),
        ("2:00-4:00",  "State flips to PLACE_WAYPOINTS. Explain the NavGrid --\n"
                       "point to the visualised floor polygons."),
        ("4:00-6:00",  "Tap a point 4-5 m away. Show A* running and path dots\n"
                       "appearing on the floor. Explain string-pulling briefly."),
        ("6:00-9:00",  "Walk toward destination. Show HUD direction arrow updating.\n"
                       "Explain: camera pose vs path node -> signed angle -> text."),
        ("9:00-11:00", "Place a chair in the path. Show YOLO detecting it, bounding\n"
                       "box on screen, and path re-routing around the obstacle."),
        ("11:00-13:00","Walk to destination -> 'You have arrived!'. Tap Reset and\n"
                       "set a new destination to show the reset flow."),
        ("13:00-15:00","Questions. If time allows, show the code for A* octile\n"
                       "heuristic and the floor ray-cast projection."),
    ]
    sy = 108
    for time, text in script:
        pdf.draw_pill(card_x2, sy, 20, 5, *CARD_BG)
        pdf.set_font("Helvetica", "B", 7)
        pdf.set_text_color(*ACCENT_RED)
        pdf.set_xy(card_x2, sy)
        pdf.cell(20, 5, time, align="C")
        pdf.body(text, card_x2 + 22, sy, 72, 8, *LIGHT_GREY)
        sy += 14

    pdf.page_footer("AR Indoor Navigation -- Technical Overview")


# ==============================================================================
#  MAIN
# ==============================================================================
if __name__ == "__main__":
    pdf = PDF()

    page_title(pdf)
    page_architecture(pdf)
    page_slam(pdf)
    page_routing(pdf)
    page_cv(pdf)
    page_states(pdf)
    page_rendering(pdf)
    page_summary(pdf)

    pdf.output(OUT_PATH)
    print(f"PDF written to: {OUT_PATH}")
