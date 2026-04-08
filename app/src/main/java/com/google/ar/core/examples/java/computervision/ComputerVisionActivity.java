/*
 * Copyright 2018 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package com.google.ar.core.examples.java.computervision;

import android.graphics.Bitmap;
import android.media.Image;
import android.opengl.GLES20;
import android.opengl.GLSurfaceView;
import android.os.Bundle;
import android.util.Log;
import android.view.MotionEvent;
import android.view.View;
import android.widget.Button;
import android.widget.RadioButton;
import android.widget.RadioGroup;
import android.widget.Switch;
import android.widget.TextView;
import android.widget.Toast;

import androidx.appcompat.app.AppCompatActivity;

import com.google.ar.core.Anchor;
import com.google.ar.core.ArCoreApk;
import com.google.ar.core.Camera;
import com.google.ar.core.CameraConfig;
import com.google.ar.core.CameraConfigFilter;
import com.google.ar.core.Config;
import com.google.ar.core.Frame;
import com.google.ar.core.HitResult;
import com.google.ar.core.Plane;
import com.google.ar.core.Session;
import com.google.ar.core.TrackingState;
import com.google.ar.core.examples.java.common.helpers.CameraPermissionHelper;
import com.google.ar.core.examples.java.common.helpers.FullScreenHelper;
import com.google.ar.core.examples.java.common.helpers.SnackbarHelper;
import com.google.ar.core.examples.java.common.helpers.TapHelper;
import com.google.ar.core.examples.java.common.helpers.TrackingStateHelper;
import com.google.ar.core.examples.java.common.rendering.PlaneRenderer;
import com.google.ar.core.examples.java.computervision.navigation.NavigationManager;
import com.google.ar.core.examples.java.computervision.navigation.WaypointManager;
import com.google.ar.core.examples.java.computervision.rendering.PathRenderer;
import com.google.ar.core.exceptions.CameraNotAvailableException;
import com.google.ar.core.exceptions.NotYetAvailableException;
import com.google.ar.core.exceptions.UnavailableApkTooOldException;
import com.google.ar.core.exceptions.UnavailableArcoreNotInstalledException;
import com.google.ar.core.exceptions.UnavailableSdkTooOldException;
import com.google.ar.core.exceptions.UnavailableUserDeclinedInstallationException;

import java.io.IOException;
import java.util.ArrayList;
import java.util.Collection;
import java.util.EnumSet;
import java.util.List;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicReference;

import javax.microedition.khronos.egl.EGLConfig;
import javax.microedition.khronos.opengles.GL10;

/**
 * AR Indoor Navigation built on the computervision_java sample.
 *
 * State machine: SCANNING → PLACE_WAYPOINTS → PATHFINDING → NAVIGATING → ARRIVED
 *
 * - SCANNING: plane detection running, user prompted to move phone over floor.
 * - PLACE_WAYPOINTS: tap to place start (green) and intermediate (cyan) dots;
 *   long-press to mark destination (red) and run A*.
 * - PATHFINDING: momentary state while A* executes on background executor.
 * - NAVIGATING: path drawn, real-time turn-by-turn HUD; YOLO marks obstacles.
 * - ARRIVED: "You have arrived!" shown, Reset button resets to PLACE_WAYPOINTS.
 */
public class ComputerVisionActivity extends AppCompatActivity implements GLSurfaceView.Renderer {

  private static final String TAG = ComputerVisionActivity.class.getSimpleName();

  // ── Navigation constants ────────────────────────────────────────────────────
  private static final float ARRIVAL_DISTANCE_M  = 0.35f;
  private static final int   YOLO_EVERY_N_FRAMES = 10;
  private static final float Z_NEAR = 0.1f;
  private static final float Z_FAR  = 100.0f;

  // ── Navigation state machine ────────────────────────────────────────────────
  private enum NavState { SCANNING, PLACE_WAYPOINTS, PATHFINDING, NAVIGATING, ARRIVED }

  private volatile NavState navState = NavState.SCANNING;

  // ── AR session ──────────────────────────────────────────────────────────────
  private GLSurfaceView surfaceView;
  private Session       session;
  private Config        arConfig;
  private boolean       installRequested;

  private final SnackbarHelper            messageSnackbarHelper   = new SnackbarHelper();
  private       CpuImageDisplayRotationHelper cpuImageDisplayRotationHelper;
  private final TrackingStateHelper       trackingStateHelper     = new TrackingStateHelper(this);

  // Prevents changing resolution while a frame is in use.
  private final Object frameImageInUseLock = new Object();

  // ── Camera config selection ─────────────────────────────────────────────────
  private enum ImageResolution { LOW_RESOLUTION, MEDIUM_RESOLUTION, HIGH_RESOLUTION }
  private ImageResolution cpuResolution = ImageResolution.LOW_RESOLUTION;

  private CameraConfig cpuLowResolutionCameraConfig;
  private CameraConfig cpuMediumResolutionCameraConfig;
  private CameraConfig cpuHighResolutionCameraConfig;

  // ── Existing CV renderers (kept for full-screen camera background) ──────────
  private final CpuImageRenderer cpuImageRenderer    = new CpuImageRenderer();
  private final TextureReader    textureReader        = new TextureReader();
  private static final int TEXTURE_WIDTH  = 1920;
  private static final int TEXTURE_HEIGHT = 1080;
  private int gpuDownloadFrameBufferIndex = -1;

  // ── Navigation renderers ────────────────────────────────────────────────────
  private final PlaneRenderer planeRenderer = new PlaneRenderer();
  private final PathRenderer  pathRenderer  = new PathRenderer();

  // ── Navigation logic ────────────────────────────────────────────────────────
  private final NavigationManager navigationManager = new NavigationManager();
  private final WaypointManager   waypointManager   = new WaypointManager();

  // Index of the next path node the user is walking toward
  private int nextPathIndex = 1;

  // Latest camera world position — updated every GL frame, used as path start
  private volatile float[] latestCameraPos = new float[3];

  // ── YOLO / computer vision ──────────────────────────────────────────────────
  private ObjectDetectorHelper  objectDetector    = null;
  private final AtomicBoolean   isProcessingFrame = new AtomicBoolean(false);
  private final ExecutorService inferenceExecutor = Executors.newSingleThreadExecutor();
  // Detections produced on the inference thread; consumed on the GL thread for hit-testing.
  private final AtomicReference<List<NavigationOverlayView.Detection>> pendingObstacleDetections
      = new AtomicReference<>(null);

  // ── Tap handling ────────────────────────────────────────────────────────────
  private TapHelper tapHelper;

  // ── Frame counter (GL thread only) ─────────────────────────────────────────
  private int frameCounter = 0;

  // ── UI views ────────────────────────────────────────────────────────────────
  private NavigationOverlayView navOverlay;
  private Button                btnSetDestination;
  private Button                btnReset;

  // Legacy diagnostic UI kept in layout but hidden during navigation
  private Switch     cvModeSwitch;
  private Switch     focusModeSwitch;
  private TextView   cameraIntrinsicsTextView;
  private RadioGroup radioGroup;

  private final FrameTimeHelper renderFrameTimeHelper   = new FrameTimeHelper();
  private final FrameTimeHelper cpuImageFrameTimeHelper = new FrameTimeHelper();

  // ── Activity lifecycle ──────────────────────────────────────────────────────

  @Override
  protected void onCreate(Bundle savedInstanceState) {
    super.onCreate(savedInstanceState);
    setContentView(R.layout.activity_main);

    surfaceView       = findViewById(R.id.surfaceview);
    navOverlay        = findViewById(R.id.nav_overlay);
    btnSetDestination = findViewById(R.id.btn_set_destination);
    btnReset          = findViewById(R.id.btn_reset);
    cvModeSwitch          = findViewById(R.id.switch_cv_mode);
    focusModeSwitch       = findViewById(R.id.switch_focus_mode);
    cameraIntrinsicsTextView = findViewById(R.id.camera_intrinsics_view);
    radioGroup            = findViewById(R.id.radio_camera_configs);

    btnSetDestination.setOnClickListener(v -> onSetDestinationClicked());
    btnReset.setOnClickListener(v -> onResetClicked());

    tapHelper = new TapHelper(this);
    surfaceView.setOnTouchListener(tapHelper);

    cpuImageDisplayRotationHelper = new CpuImageDisplayRotationHelper(this);

    surfaceView.setPreserveEGLContextOnPause(true);
    surfaceView.setEGLContextClientVersion(2);
    surfaceView.setEGLConfigChooser(8, 8, 8, 8, 16, 0);
    surfaceView.setRenderer(this);
    surfaceView.setRenderMode(GLSurfaceView.RENDERMODE_CONTINUOUSLY);
    surfaceView.setWillNotDraw(false);

    getLifecycle().addObserver(renderFrameTimeHelper);
    getLifecycle().addObserver(cpuImageFrameTimeHelper);

    installRequested = false;

    // Load YOLO model off the GL thread to avoid blocking surface creation.
    inferenceExecutor.execute(() -> {
      try {
        objectDetector = new ObjectDetectorHelper(ComputerVisionActivity.this);
        Log.d(TAG, "ObjectDetectorHelper initialized.");
      } catch (IOException e) {
        Log.e(TAG, "Failed to load YOLO model", e);
      }
    });

    updateStateUi(NavState.SCANNING);
  }

  @Override
  protected void onDestroy() {
    if (session != null) {
      session.close();
      session = null;
    }
    navigationManager.shutdown();
    inferenceExecutor.shutdownNow();
    super.onDestroy();
  }

  @Override
  protected void onResume() {
    super.onResume();

    if (session == null) {
      Exception exception = null;
      String    message   = null;
      try {
        switch (ArCoreApk.getInstance().requestInstall(this, !installRequested)) {
          case INSTALL_REQUESTED:
            installRequested = true;
            return;
          case INSTALLED:
            break;
        }

        if (!CameraPermissionHelper.hasCameraPermission(this)) {
          CameraPermissionHelper.requestCameraPermission(this);
          return;
        }

        session  = new Session(this);
        arConfig = new Config(session);
        // Detect both floor and vertical surfaces (walls, furniture)
        arConfig.setPlaneFindingMode(Config.PlaneFindingMode.HORIZONTAL_AND_VERTICAL);
        arConfig.setFocusMode(Config.FocusMode.AUTO);
        session.configure(arConfig);

      } catch (UnavailableArcoreNotInstalledException
               | UnavailableUserDeclinedInstallationException e) {
        message = "Please install ARCore"; exception = e;
      } catch (UnavailableApkTooOldException e) {
        message = "Please update ARCore"; exception = e;
      } catch (UnavailableSdkTooOldException e) {
        message = "Please update this app"; exception = e;
      } catch (Exception e) {
        message = "This device does not support AR"; exception = e;
      }

      if (message != null) {
        messageSnackbarHelper.showError(this, message);
        Log.e(TAG, "Exception creating session", exception);
        return;
      }
    }

    obtainCameraConfigs();

    try {
      session.resume();
    } catch (CameraNotAvailableException e) {
      messageSnackbarHelper.showError(this, "Camera not available. Try restarting the app.");
      session = null;
      return;
    }
    surfaceView.onResume();
    cpuImageDisplayRotationHelper.onResume();
  }

  @Override
  public void onPause() {
    super.onPause();
    if (session != null) {
      cpuImageDisplayRotationHelper.onPause();
      surfaceView.onPause();
      session.pause();
    }
  }

  @Override
  public void onRequestPermissionsResult(int requestCode, String[] permissions, int[] results) {
    super.onRequestPermissionsResult(requestCode, permissions, results);
    if (!CameraPermissionHelper.hasCameraPermission(this)) {
      Toast.makeText(this, "Camera permission is needed to run this application",
          Toast.LENGTH_LONG).show();
      if (!CameraPermissionHelper.shouldShowRequestPermissionRationale(this)) {
        CameraPermissionHelper.launchPermissionSettings(this);
      }
      finish();
    }
  }

  @Override
  public void onWindowFocusChanged(boolean hasFocus) {
    super.onWindowFocusChanged(hasFocus);
    FullScreenHelper.setFullScreenOnWindowFocusChanged(this, hasFocus);
  }

  // ── GLSurfaceView.Renderer ──────────────────────────────────────────────────

  @Override
  public void onSurfaceCreated(GL10 gl, EGLConfig config) {
    GLES20.glClearColor(0.1f, 0.1f, 0.1f, 1.0f);
    try {
      cpuImageRenderer.createOnGlThread(this);
      cpuImageRenderer.setSplitterPosition(1.0f); // show full camera feed (no grayscale split)
      planeRenderer.createOnGlThread(this, "models/trigrid.png");
      pathRenderer.createOnGlThread(this);
      textureReader.create(this, TextureReaderImage.IMAGE_FORMAT_I8, 1280, 720, false);
    } catch (IOException e) {
      Log.e(TAG, "Failed to create GL resources", e);
    }
  }

  @Override
  public void onSurfaceChanged(GL10 gl, int width, int height) {
    cpuImageDisplayRotationHelper.onSurfaceChanged(width, height);
    GLES20.glViewport(0, 0, width, height);
  }

  @Override
  public void onDrawFrame(GL10 gl) {
    GLES20.glClear(GLES20.GL_COLOR_BUFFER_BIT | GLES20.GL_DEPTH_BUFFER_BIT);

    if (session == null) return;

    synchronized (frameImageInUseLock) {
      cpuImageDisplayRotationHelper.updateSessionIfNeeded(session);

      try {
        session.setCameraTextureName(cpuImageRenderer.getTextureId());
        final Frame  frame  = session.update();
        final Camera camera = frame.getCamera();

        trackingStateHelper.updateKeepScreenOnFlag(camera.getTrackingState());
        renderFrameTimeHelper.nextFrame();

        // Camera background — pass frame so texture coordinates get updated.
        // Passing null for the CPU-image overlay skips edge-detection; only the
        // camera feed is drawn.
        cpuImageRenderer.drawWithCpuImage(
            frame, 0, 0, null,
            cpuImageDisplayRotationHelper.getViewportAspectRatio(),
            cpuImageDisplayRotationHelper.getCameraToDisplayRotation());

        if (camera.getTrackingState() != TrackingState.TRACKING) return;

        // Keep camera position current so pathfinding always starts from here
        latestCameraPos[0] = camera.getPose().tx();
        latestCameraPos[1] = camera.getPose().ty();
        latestCameraPos[2] = camera.getPose().tz();

        float[] viewMatrix = new float[16];
        float[] projMatrix = new float[16];
        camera.getViewMatrix(viewMatrix, 0);
        camera.getProjectionMatrix(projMatrix, 0, Z_NEAR, Z_FAR);

        Collection<Plane> planes = session.getAllTrackables(Plane.class);
        NavState state = navState; // capture once

        // State-specific work
        switch (state) {
          case SCANNING:
            planeRenderer.drawPlanes(planes, camera.getDisplayOrientedPose(), projMatrix);
            checkScanningTransition(planes);
            break;

          case PLACE_WAYPOINTS:
            planeRenderer.drawPlanes(planes, camera.getDisplayOrientedPose(), projMatrix);
            navigationManager.scheduleGridRebuild(planes);
            processTaps(frame);
            break;

          case NAVIGATING:
            navigationManager.scheduleGridRebuild(planes);
            processQueuedObstacleHitTests(frame);
            checkArrival(camera);
            updateHud(camera);
            break;

          case PATHFINDING:
          case ARRIVED:
            break;
        }

        // Render path + waypoint dots (all states except SCANNING)
        if (state != NavState.SCANNING) {
          List<float[]> path              = navigationManager.getLatestPath();
          List<float[]> waypointPositions = getIntermediateWaypointPositions();
          pathRenderer.draw(viewMatrix, projMatrix, path,
              waypointManager.getStartPosition(),
              waypointManager.getDestinationPosition(),
              waypointPositions);
        }

        // Throttled YOLO inference + obstacle mapping
        frameCounter++;
        if (frameCounter % YOLO_EVERY_N_FRAMES == 0) {
          tryPostYoloFrame(frame, camera);
        }
        navigationManager.tickObstacleDecay(frameCounter);

      } catch (Exception e) {
        Log.e(TAG, "Exception on the OpenGL thread", e);
      }
    }
  }

  // ── Navigation state transitions ────────────────────────────────────────────

  /** Advance to PLACE_WAYPOINTS once the first suitable floor plane is tracked. */
  private void checkScanningTransition(Collection<Plane> planes) {
    if (navigationManager.tryInitializeGrid(planes)) {
      navState = NavState.PLACE_WAYPOINTS;
      runOnUiThread(() -> updateStateUi(NavState.PLACE_WAYPOINTS));
    }
  }

  /** Any tap (or long-press) immediately sets the destination and triggers pathfinding. */
  private void processTaps(Frame frame) {
    MotionEvent tap = tapHelper.pollLongPress();
    if (tap == null) tap = tapHelper.poll();
    if (tap != null) handleHitTest(frame, tap);
  }

  private void handleHitTest(Frame frame, MotionEvent event) {
    List<HitResult> hits = frame.hitTest(event);
    for (HitResult hit : hits) {
      if (!(hit.getTrackable() instanceof Plane)) continue;
      Plane plane = (Plane) hit.getTrackable();
      if (plane.getType() != Plane.Type.HORIZONTAL_UPWARD_FACING) continue;
      if (!plane.isPoseInPolygon(hit.getHitPose())) continue;

      float[] destPos = {hit.getHitPose().tx(), hit.getHitPose().ty(), hit.getHitPose().tz()};
      Anchor  anchor  = hit.createAnchor();

      // Camera is always the start; tapped point is always the destination
      waypointManager.reset();
      float[] startPos = latestCameraPos.clone();
      waypointManager.setStart(startPos, null); // no anchor needed for camera pos
      waypointManager.setDestination(destPos, anchor);
      startPathfinding();
      break;
    }
  }

  private void startPathfinding() {
    float[] startPos = latestCameraPos.clone(); // always start from current camera position
    float[] destPos  = waypointManager.getDestinationPosition();
    if (destPos == null) return;

    navState = NavState.PATHFINDING;
    runOnUiThread(() -> updateStateUi(NavState.PATHFINDING));

    navigationManager.requestPath(startPos, destPos, new NavigationManager.PathCallback() {
      @Override
      public void onPathFound(List<float[]> path) {
        navState      = NavState.NAVIGATING;
        nextPathIndex = 1;
        runOnUiThread(() -> updateStateUi(NavState.NAVIGATING));
      }

      @Override
      public void onPathNotFound() {
        navState = NavState.PLACE_WAYPOINTS;
        runOnUiThread(() -> {
          updateStateUi(NavState.PLACE_WAYPOINTS);
          messageSnackbarHelper.showMessage(ComputerVisionActivity.this,
              "No path found — scan more floor area or reposition waypoints.");
        });
      }
    });
  }

  /**
   * Advance nextPathIndex as path nodes are passed, and detect arrival
   * at the final destination.
   */
  private void checkArrival(Camera camera) {
    List<float[]> path = navigationManager.getLatestPath();
    if (path == null || path.isEmpty()) return;

    float camX = camera.getPose().tx();
    float camZ = camera.getPose().tz();

    while (nextPathIndex < path.size()) {
      float[] node = path.get(nextPathIndex);
      double dist = Math.sqrt(
          Math.pow(node[0] - camX, 2) + Math.pow(node[2] - camZ, 2));
      if (dist < ARRIVAL_DISTANCE_M) {
        nextPathIndex++;
      } else {
        break;
      }
    }

    if (nextPathIndex >= path.size()) {
      navState = NavState.ARRIVED;
      runOnUiThread(() -> updateStateUi(NavState.ARRIVED));
    }
  }

  /** Compute direction + distance to next waypoint and push to HUD overlay. */
  private void updateHud(Camera camera) {
    List<float[]> path = navigationManager.getLatestPath();
    if (path == null || path.isEmpty()) return;

    int     idx    = Math.min(nextPathIndex, path.size() - 1);
    float[] target = path.get(idx);

    float[] instr    = navigationManager.getInstruction(camera, target);
    float   angleDeg = instr[0];
    float   distM    = instr[1];

    String direction;
    if      (distM < ARRIVAL_DISTANCE_M)    direction = "You have arrived!";
    else if (Math.abs(angleDeg) > 135)       direction = "Turn around ↩";
    else if (angleDeg < -45)                 direction = "← Turn left";
    else if (angleDeg > 45)                  direction = "Turn right →";
    else if (Math.abs(angleDeg) <= 15)       direction = "↑ Go straight";
    else if (angleDeg < 0)                   direction = "↖ Bear left";
    else                                     direction = "↗ Bear right";

    String distance = String.format("%.0f ft", distM * 3.28084f);
    runOnUiThread(() -> navOverlay.setNavigationHud(direction, distance));
  }

  // ── YOLO obstacle hit-testing (GL thread) ───────────────────────────────────

  /**
   * Consume the latest YOLO detections and map each obstacle's bounding-box
   * bottom-centre to a world position using ARCore hit-testing.
   *
   * This runs on the GL thread so the coordinate systems are always consistent:
   * the surfaceView pixel space matches what frame.hitTest() expects, and the
   * rotated YOLO image fills the same portrait rectangle as the display.
   *
   * Called every frame while NAVIGATING.
   */
  private void processQueuedObstacleHitTests(Frame frame) {
    List<NavigationOverlayView.Detection> pending = pendingObstacleDetections.getAndSet(null);
    if (pending == null || pending.isEmpty()) return;

    int screenW = surfaceView.getWidth();
    int screenH = surfaceView.getHeight();
    if (screenW == 0 || screenH == 0) return;

    float floorY     = navigationManager.getFloorWorldY();
    int   expiry     = frameCounter + 300; // 10 s at 30 fps
    boolean anyNew   = false;

    for (NavigationOverlayView.Detection det : pending) {
      if (!NavigationManager.isObstacleClass(det.classId)) continue;

      // Sample 3 x-positions across the bounding box bottom edge.
      float boxW = det.box.width();
      float[] sampleNormX = {
          det.box.left + boxW * 0.2f,
          det.box.centerX(),
          det.box.left + boxW * 0.8f,
      };
      float screenY = det.box.bottom * screenH;

      // Obstacle radius scaled by apparent box width — clamped to 1–3 cells (20–60 cm).
      int radius = Math.max(1, Math.min(3, (int)(boxW * screenW / 120f)));

      for (float normX : sampleNormX) {
        float screenX = normX * screenW;

        List<HitResult> hits = frame.hitTest(screenX, screenY);
        for (HitResult hit : hits) {
          if (!(hit.getTrackable() instanceof Plane)) continue;
          Plane hitPlane = (Plane) hit.getTrackable();
          // Accept any upward-facing plane near floor level (allows for slight tilt)
          if (hitPlane.getType() != Plane.Type.HORIZONTAL_UPWARD_FACING) continue;
          float hitY = hit.getHitPose().ty();
          if (Math.abs(hitY - floorY) > 0.40f) continue; // ignore shelves/table tops

          navigationManager.getNavGrid().markObstacle(
              hit.getHitPose().tx(), hit.getHitPose().tz(), radius, expiry);
          anyNew = true;
          break; // first valid hit per sample point is enough
        }
      }
    }

    // If we marked new obstacles, re-plan so the path routes around them.
    if (anyNew && navState == NavState.NAVIGATING) {
      float[] s = latestCameraPos.clone();
      float[] d = waypointManager.getDestinationPosition();
      if (d != null) {
        navigationManager.requestPath(s, d, new NavigationManager.PathCallback() {
          @Override public void onPathFound(List<float[]> p) {
            nextPathIndex = Math.min(nextPathIndex, p.size() - 1);
          }
          @Override public void onPathNotFound() { /* keep existing path until next try */ }
        });
      }
    }
  }

  // ── YOLO inference ──────────────────────────────────────────────────────────

  /**
   * Acquire camera image → convert to Bitmap → close → post to inference executor.
   * All acquisition/conversion happens on the GL thread inside frameImageInUseLock.
   */
  private void tryPostYoloFrame(Frame frame, Camera camera) {
    if (objectDetector == null) return;
    if (!isProcessingFrame.compareAndSet(false, true)) return;

    try {
      Image  cameraImage   = frame.acquireCameraImage();
      int    rotateDegrees = cpuImageDisplayRotationHelper.getCameraToDisplayRotation() * 90;
      Bitmap bitmap        = ImageUtils.imageToBitmap(cameraImage, rotateDegrees);
      cameraImage.close(); // must close before leaving frameImageInUseLock

      final int frameRef = frameCounter;

      inferenceExecutor.execute(() -> {
        try {
          List<NavigationOverlayView.Detection> dets = objectDetector.detect(bitmap);

          // Store for the GL thread to process via ARCore hit-test (correct coordinates).
          // The GL thread consumes this in processQueuedObstacleHitTests() each frame.
          if (!dets.isEmpty()) {
            pendingObstacleDetections.set(new ArrayList<>(dets));
          }

          final List<NavigationOverlayView.Detection> uiDets = dets;
          runOnUiThread(() -> navOverlay.setDetections(uiDets));
        } finally {
          isProcessingFrame.set(false);
        }
      });

    } catch (NotYetAvailableException e) {
      isProcessingFrame.set(false);
    } catch (Exception e) {
      isProcessingFrame.set(false);
      Log.e(TAG, "Error acquiring camera image for YOLO", e);
    }
  }

  // ── Button click handlers ───────────────────────────────────────────────────

  private void onSetDestinationClicked() {
    // No longer used — tap directly sets destination
  }

  private void onResetClicked() {
    waypointManager.reset();
    navigationManager.clearPath();
    navState      = NavState.PLACE_WAYPOINTS;
    nextPathIndex = 1;
    runOnUiThread(() -> {
      navOverlay.setDetections(null);
      navOverlay.hideNavigationHud();
      updateStateUi(NavState.PLACE_WAYPOINTS);
    });
  }

  // ── UI helpers ──────────────────────────────────────────────────────────────

  private void updateStateUi(NavState state) {
    switch (state) {
      case SCANNING:
        navOverlay.setStatePrompt("Move phone slowly over the floor to scan");
        navOverlay.hideNavigationHud();
        btnSetDestination.setVisibility(View.GONE);
        btnReset.setVisibility(View.GONE);
        break;

      case PLACE_WAYPOINTS:
        navOverlay.setStatePrompt("Tap the floor to set your destination");
        navOverlay.hideNavigationHud();
        btnSetDestination.setVisibility(View.GONE);
        btnReset.setVisibility(View.GONE);
        break;

      case PATHFINDING:
        navOverlay.setStatePrompt("Computing route…");
        navOverlay.hideNavigationHud();
        btnSetDestination.setVisibility(View.GONE);
        btnReset.setVisibility(View.VISIBLE);
        break;

      case NAVIGATING:
        navOverlay.setStatePrompt("");
        btnSetDestination.setVisibility(View.GONE);
        btnReset.setVisibility(View.VISIBLE);
        break;

      case ARRIVED:
        navOverlay.setStatePrompt("You have arrived! \uD83C\uDFC1");
        navOverlay.hideNavigationHud();
        btnSetDestination.setVisibility(View.GONE);
        btnReset.setVisibility(View.VISIBLE);
        break;
    }
  }

  private List<float[]> getIntermediateWaypointPositions() {
    List<WaypointManager.Waypoint> all = waypointManager.getAllWaypoints();
    List<float[]> positions = new ArrayList<>();
    for (int i = 1; i < all.size() - 1; i++) {
      positions.add(all.get(i).position);
    }
    return positions;
  }

  // ── Legacy camera config methods (kept for optional diagnostic use) ─────────

  public void onLowResolutionRadioButtonClicked(View view) {
    if (((RadioButton) view).isChecked() && cpuResolution != ImageResolution.LOW_RESOLUTION) {
      onCameraConfigChanged(cpuLowResolutionCameraConfig);
      cpuResolution = ImageResolution.LOW_RESOLUTION;
    }
  }

  public void onMediumResolutionRadioButtonClicked(View view) {
    if (((RadioButton) view).isChecked() && cpuResolution != ImageResolution.MEDIUM_RESOLUTION) {
      onCameraConfigChanged(cpuMediumResolutionCameraConfig);
      cpuResolution = ImageResolution.MEDIUM_RESOLUTION;
    }
  }

  public void onHighResolutionRadioButtonClicked(View view) {
    if (((RadioButton) view).isChecked() && cpuResolution != ImageResolution.HIGH_RESOLUTION) {
      onCameraConfigChanged(cpuHighResolutionCameraConfig);
      cpuResolution = ImageResolution.HIGH_RESOLUTION;
    }
  }

  private void onCameraConfigChanged(CameraConfig cameraConfig) {
    if (session != null && cameraConfig != null) {
      synchronized (frameImageInUseLock) {
        session.pause();
        session.setCameraConfig(cameraConfig);
        try {
          session.resume();
        } catch (CameraNotAvailableException ex) {
          messageSnackbarHelper.showError(this, "Camera not available. Try restarting the app.");
          session = null;
        }
      }
    }
  }

  private void obtainCameraConfigs() {
    if (session == null) return;
    CameraConfigFilter filter = new CameraConfigFilter(session)
        .setTargetFps(EnumSet.of(
            CameraConfig.TargetFps.TARGET_FPS_30,
            CameraConfig.TargetFps.TARGET_FPS_60));
    List<CameraConfig> configs = new ArrayList<>(session.getSupportedCameraConfigs(filter));
    if (configs.isEmpty()) return;

    java.util.Collections.sort(configs, (a, b) ->
        Integer.compare(a.getImageSize().getHeight(), b.getImageSize().getHeight()));

    int sz = configs.size();
    cpuLowResolutionCameraConfig    = configs.get(0);
    cpuMediumResolutionCameraConfig = configs.get(Math.max(0, sz / 2));
    cpuHighResolutionCameraConfig   = configs.get(sz - 1);
  }
}
