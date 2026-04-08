package com.google.ar.core.examples.java.computervision.navigation;

import android.util.Log;

import com.google.ar.core.Camera;
import com.google.ar.core.CameraIntrinsics;
import com.google.ar.core.Plane;
import com.google.ar.core.Pose;

import java.util.Collection;
import java.util.List;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.atomic.AtomicReference;

import com.google.ar.core.examples.java.computervision.NavigationOverlayView;

/**
 * Orchestrates NavGrid rebuilds, A* pathfinding, and YOLO-obstacle mapping.
 * All heavy work runs on a single background executor thread.
 */
public class NavigationManager {

    private static final String TAG = "NavigationManager";

    private static final long GRID_REBUILD_INTERVAL_MS = 1000; // rebuild at most once/sec

    public interface PathCallback {
        void onPathFound(List<float[]> path);
        void onPathNotFound();
    }

    private final NavGrid        navGrid    = new NavGrid();
    private final AStarPlanner   astar      = new AStarPlanner();
    private final ExecutorService executor   = Executors.newSingleThreadExecutor();

    private final AtomicReference<List<float[]>> latestPath = new AtomicReference<>(null);

    private long lastGridRebuildMs = 0;

    // ── Lifecycle ─────────────────────────────────────────────────────────────

    public void shutdown() {
        executor.shutdownNow();
    }

    // ── Grid management ───────────────────────────────────────────────────────

    public boolean isGridInitialized() { return navGrid.isInitialized(); }

    public float getFloorWorldY() { return navGrid.getFloorWorldY(); }

    public NavGrid getNavGrid() { return navGrid; }

    /**
     * Initialize grid origin from the first large tracked floor plane.
     * Call from the GL thread after at least one plane is tracked.
     */
    public boolean tryInitializeGrid(Collection<Plane> planes) {
        if (navGrid.isInitialized()) return true;
        for (Plane plane : planes) {
            if (plane.getType() == Plane.Type.HORIZONTAL_UPWARD_FACING
                    && plane.getTrackingState() == com.google.ar.core.TrackingState.TRACKING
                    && plane.getSubsumedBy() == null) {
                float extent = Math.min(plane.getExtentX(), plane.getExtentZ());
                if (extent >= 0.5f) {
                    navGrid.initialize(plane.getCenterPose());
                    Log.d(TAG, "Grid initialized. Floor Y=" + navGrid.getFloorWorldY());
                    return true;
                }
            }
        }
        return false;
    }

    /**
     * Schedule a grid rebuild from the current set of tracked planes.
     * Throttled to once per second. Call from GL thread.
     */
    public void scheduleGridRebuild(Collection<Plane> planes) {
        if (!navGrid.isInitialized()) return;
        long now = System.currentTimeMillis();
        if (now - lastGridRebuildMs < GRID_REBUILD_INTERVAL_MS) return;
        lastGridRebuildMs = now;

        // Take a snapshot list to pass to executor (avoid holding GL resources)
        final List<Plane> snapshot = new java.util.ArrayList<>(planes);
        executor.execute(() -> {
            navGrid.rebuildFromPlanes(snapshot);
            Log.d(TAG, "Grid rebuilt. Walkable area: " + navGrid.getWalkableAreaM2() + " m²");
        });
    }

    /**
     * Map YOLO detections to obstacle cells on the nav grid.
     * Call from the GL thread (or background executor) with camera intrinsics.
     *
     * @param detections   YOLO detections with normalized bounding boxes
     * @param camera       ARCore camera for this frame
     * @param frameCounter current frame number (used for obstacle expiry)
     */
    public void processObstacles(List<NavigationOverlayView.Detection> detections,
                                  Camera camera, int frameCounter) {
        if (!navGrid.isInitialized() || detections == null || detections.isEmpty()) return;

        CameraIntrinsics intrinsics = camera.getImageIntrinsics();
        float[] focal       = intrinsics.getFocalLength();   // {fx, fy} in pixels
        float[] principal   = intrinsics.getPrincipalPoint(); // {cx, cy} in pixels
        int[]   dims        = intrinsics.getImageDimensions(); // {w, h} in pixels
        float   fx = focal[0], fy = focal[1];
        float   cx = principal[0], cy = principal[1];

        float floorY = navGrid.getFloorWorldY();

        // Camera world position
        Pose camPose = camera.getPose();
        float camX = camPose.tx(), camY = camPose.ty(), camZ = camPose.tz();

        // Camera rotation matrix (3x3, column-major from 4x4)
        float[] camMatrix = new float[16];
        camPose.toMatrix(camMatrix, 0);

        // 10 seconds at 30 fps — obstacle persists even when camera looks away
        int expiryFrame = frameCounter + 300;

        for (NavigationOverlayView.Detection det : detections) {
            // Only obstacle-like objects (people, furniture)
            if (!isObstacleClass(det.classId)) continue;

            // Sample 5 points along the bottom edge of the bounding box to cover the
            // full width of the obstacle footprint, not just the centre.
            float boxW = det.box.width();
            float[] sampleNormX = {
                det.box.left + boxW * 0.1f,
                det.box.left + boxW * 0.3f,
                det.box.centerX(),
                det.box.left + boxW * 0.7f,
                det.box.left + boxW * 0.9f,
            };

            // Scale obstacle radius with detected bounding-box width:
            // a wider box means a physically larger object. Clamp to [1, 4] cells.
            int obstacleRadius = Math.max(1, Math.min(4, (int)(boxW * dims[0] / 80f)));

            float imgY = det.box.bottom * dims[1];

            for (float normX : sampleNormX) {
                float imgX = normX * dims[0];

                // Image pixel → camera-space ray direction
                float rayCamX = (imgX - cx) / fx;
                float rayCamY = (imgY - cy) / fy;
                float rayCamZ = 1.0f;

                // Normalize
                float len = (float) Math.sqrt(rayCamX * rayCamX + rayCamY * rayCamY + rayCamZ * rayCamZ);
                rayCamX /= len; rayCamY /= len; rayCamZ /= len;

                // Transform ray direction: camera space → world space (rotation only)
                float rwX = camMatrix[0] * rayCamX + camMatrix[4] * rayCamY + camMatrix[8]  * rayCamZ;
                float rwY = camMatrix[1] * rayCamX + camMatrix[5] * rayCamY + camMatrix[9]  * rayCamZ;
                float rwZ = camMatrix[2] * rayCamX + camMatrix[6] * rayCamY + camMatrix[10] * rayCamZ;

                // Intersect ray with floor plane Y = floorY
                if (Math.abs(rwY) < 1e-5f) continue; // ray parallel to floor
                float t = (floorY - camY) / rwY;
                if (t <= 0 || t > 10f) continue;    // behind camera or implausibly far (>10m)

                float hitX = camX + t * rwX;
                float hitZ = camZ + t * rwZ;

                navGrid.markObstacle(hitX, hitZ, obstacleRadius, expiryFrame);
            }
        }
    }

    /**
     * Request an A* path from start to goal (world-space XZ).
     * Runs on the background executor; result delivered via callback on the calling thread.
     */
    public void requestPath(float[] startWorld, float[] goalWorld, PathCallback callback) {
        if (!navGrid.isInitialized()) {
            callback.onPathNotFound();
            return;
        }

        final byte[][] snap = navGrid.getSnapshot();

        executor.execute(() -> {
            int[] startCell = navGrid.worldToCell(startWorld[0], startWorld[2]);
            int[] goalCell  = navGrid.worldToCell(goalWorld[0],  goalWorld[2]);

            if (startCell == null || goalCell == null) {
                Log.w(TAG, "Start or goal outside grid.");
                callback.onPathNotFound();
                return;
            }

            List<float[]> path = astar.findPath(navGrid, snap, startCell, goalCell);
            if (path.isEmpty()) {
                Log.w(TAG, "A* found no path.");
                callback.onPathNotFound();
            } else {
                Log.d(TAG, "A* path found: " + path.size() + " nodes.");
                latestPath.set(path);
                callback.onPathFound(path);
            }
        });
    }

    public List<float[]> getLatestPath() { return latestPath.get(); }

    public void clearPath() { latestPath.set(null); }

    /**
     * Decay obstacle cells and schedule periodic maintenance.
     * Call from GL thread each frame.
     */
    public void tickObstacleDecay(int currentFrame) {
        if (!navGrid.isInitialized()) return;
        if (currentFrame % 30 == 0) { // check once per second at 30 fps
            executor.execute(() -> navGrid.decayObstacles(currentFrame));
        }
    }

    /**
     * Compute navigation instruction for the current camera pose.
     *
     * @return float[2]: {angleDegrees, distanceMetres}
     *         angleDegrees: negative = turn left, positive = turn right, near 0 = straight
     */
    public float[] getInstruction(Camera camera, float[] nextWaypointWorld) {
        if (nextWaypointWorld == null) return new float[]{0f, Float.MAX_VALUE};

        float[] vm = new float[16];
        camera.getViewMatrix(vm, 0);

        // Camera forward in world XZ (view matrix row 2, negated)
        float fwdX = -vm[2];
        float fwdZ = -vm[10];

        // Vector from camera to next waypoint (XZ only)
        float dx = nextWaypointWorld[0] - camera.getPose().tx();
        float dz = nextWaypointWorld[2] - camera.getPose().tz();
        float dist = (float) Math.sqrt(dx * dx + dz * dz);

        if (dist < 0.01f) return new float[]{0f, dist};

        // Signed angle (atan2 of cross/dot)
        float cross = fwdX * dz - fwdZ * dx;
        float dot   = fwdX * dx + fwdZ * dz;
        float angleDeg = (float) Math.toDegrees(Math.atan2(cross, dot));

        return new float[]{angleDeg, dist};
    }

    // ── Obstacle class filter ─────────────────────────────────────────────────

    // COCO class IDs that represent physical indoor obstacles
    public static boolean isObstacleClass(int classId) {
        switch (classId) {
            case 0:  // person
            case 13: // bench
            case 24: // backpack  ← bags on the floor
            case 26: // handbag
            case 28: // suitcase  ← travel bags, luggage
            case 56: // chair
            case 57: // couch
            case 58: // potted plant
            case 59: // bed
            case 60: // dining table
            case 62: // tv / monitor (on a stand)
            case 63: // laptop
            case 74: // clock
                return true;
            default:
                return false;
        }
    }
}
