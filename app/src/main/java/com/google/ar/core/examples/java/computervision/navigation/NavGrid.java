package com.google.ar.core.examples.java.computervision.navigation;

import com.google.ar.core.Plane;
import com.google.ar.core.Pose;
import com.google.ar.core.TrackingState;

import java.nio.FloatBuffer;
import java.util.Collection;
import java.util.concurrent.locks.ReentrantLock;

/**
 * A 2D walkable grid built from ARCore plane detections.
 * Each cell is CELL_SIZE x CELL_SIZE metres. The grid origin is set when
 * the first large horizontal plane is detected.
 */
public class NavGrid {

    public static final float CELL_SIZE = 0.20f; // 20 cm per cell

    public static final byte CELL_UNKNOWN         = 0;
    public static final byte CELL_WALKABLE        = 1;
    public static final byte CELL_OBSTACLE        = 2; // dynamic (YOLO), decays over time
    public static final byte CELL_STATIC_OBSTACLE = 3; // elevated surface footprint, rebuilt each cycle

    /**
     * Height above the detected floor plane at which a horizontal surface is
     * considered elevated (desk, counter, sofa, etc.) rather than walkable floor.
     * 30 cm means a step up to a desk top triggers obstacle marking.
     */
    private static final float ELEVATED_SURFACE_THRESHOLD_M = 0.30f;

    private static final int GRID_SIZE = 100; // 100 x 100 = 20m x 20m

    private final byte[][]  cells          = new byte[GRID_SIZE][GRID_SIZE];
    private final int[][]   obstacleExpiry = new int[GRID_SIZE][GRID_SIZE];

    private float originWorldX;
    private float originWorldZ;
    private float floorWorldY;

    private boolean initialized = false;

    private final ReentrantLock lock = new ReentrantLock();

    public ReentrantLock getLock() { return lock; }

    public boolean isInitialized() { return initialized; }

    public float getFloorWorldY() { return floorWorldY; }

    public int getSize() { return GRID_SIZE; }

    /** Set the grid origin from the first detected floor plane centre. */
    public void initialize(Pose firstPlanePose) {
        lock.lock();
        try {
            originWorldX = firstPlanePose.tx() - (GRID_SIZE / 2f) * CELL_SIZE;
            originWorldZ = firstPlanePose.tz() - (GRID_SIZE / 2f) * CELL_SIZE;
            floorWorldY  = firstPlanePose.ty();
            initialized  = true;
        } finally {
            lock.unlock();
        }
    }

    /**
     * Rebuild the nav grid from the current set of tracked horizontal planes.
     *
     * Classification (relative to the stored floorWorldY):
     *   • Within ELEVATED_SURFACE_THRESHOLD_M above floor → CELL_WALKABLE (true floor)
     *   • More than ELEVATED_SURFACE_THRESHOLD_M above floor → CELL_STATIC_OBSTACLE
     *     (desk, counter, sofa top — stamps the XZ footprint so A* routes around it)
     *
     * On each rebuild, previously-computed walkable and static-obstacle cells are
     * cleared and re-derived from the current plane set.  Dynamic YOLO obstacle
     * cells (CELL_OBSTACLE) are preserved and decay on their own timer.
     *
     * Should be called from the background executor.
     */
    public void rebuildFromPlanes(Collection<Plane> planes) {
        lock.lock();
        try {
            // Clear only the cells we derive from planes; preserve dynamic YOLO obstacles.
            for (int r = 0; r < GRID_SIZE; r++) {
                for (int c = 0; c < GRID_SIZE; c++) {
                    byte cell = cells[r][c];
                    if (cell == CELL_WALKABLE || cell == CELL_STATIC_OBSTACLE) {
                        cells[r][c] = CELL_UNKNOWN;
                    }
                }
            }

            // First pass: mark walkable floor cells.
            // Second pass: stamp elevated-surface obstacles (runs after walkable so they win).
            // We do two separate iterations so a floor plane never overwrites an elevated one.

            for (int pass = 0; pass < 2; pass++) {
                for (Plane plane : planes) {
                    if (plane.getTrackingState() != TrackingState.TRACKING) continue;
                    if (plane.getSubsumedBy() != null) continue;
                    if (plane.getType() != Plane.Type.HORIZONTAL_UPWARD_FACING) continue;

                    Pose  planePose = plane.getCenterPose();
                    float planeY    = planePose.ty();

                    // Classify by height above stored floor Y.
                    boolean isElevated = (planeY - floorWorldY) > ELEVATED_SURFACE_THRESHOLD_M;

                    // Pass 0 → floor planes only; pass 1 → elevated planes only.
                    if (pass == 0 && isElevated) continue;
                    if (pass == 1 && !isElevated) continue;

                    FloatBuffer polygon = plane.getPolygon();
                    if (polygon == null || polygon.limit() < 6) continue;

                    // Read polygon boundary: XZ pairs in plane-local space → world
                    int     numVerts = polygon.limit() / 2;
                    float[] polyX    = new float[numVerts];
                    float[] polyZ    = new float[numVerts];

                    for (int i = 0; i < numVerts; i++) {
                        float localX = polygon.get(i * 2);
                        float localZ = polygon.get(i * 2 + 1);
                        float[] localPt = {localX, 0f, localZ};
                        float[] worldPt = new float[3];
                        planePose.transformPoint(localPt, 0, worldPt, 0);
                        polyX[i] = worldPt[0];
                        polyZ[i] = worldPt[2];
                    }

                    // Grid bounding box for this polygon
                    float minX = polyX[0], maxX = polyX[0];
                    float minZ = polyZ[0], maxZ = polyZ[0];
                    for (int i = 1; i < numVerts; i++) {
                        if (polyX[i] < minX) minX = polyX[i];
                        if (polyX[i] > maxX) maxX = polyX[i];
                        if (polyZ[i] < minZ) minZ = polyZ[i];
                        if (polyZ[i] > maxZ) maxZ = polyZ[i];
                    }

                    int[] cellMin = worldToCell(minX, minZ);
                    int[] cellMax = worldToCell(maxX, maxZ);
                    if (cellMin == null || cellMax == null) continue;

                    int rMin = Math.max(0, cellMin[0]);
                    int cMin = Math.max(0, cellMin[1]);
                    int rMax = Math.min(GRID_SIZE - 1, cellMax[0]);
                    int cMax = Math.min(GRID_SIZE - 1, cellMax[1]);

                    for (int r = rMin; r <= rMax; r++) {
                        for (int c = cMin; c <= cMax; c++) {
                            float[] wc = cellToWorld(r, c);
                            if (!isPointInPolygon(wc[0], wc[2], polyX, polyZ)) continue;

                            if (isElevated) {
                                // Elevated surface: block cell unless a dynamic YOLO obstacle
                                // is already there (both mean impassable so no difference).
                                if (cells[r][c] != CELL_OBSTACLE) {
                                    cells[r][c] = CELL_STATIC_OBSTACLE;
                                }
                            } else {
                                // Floor-level: erode polygon boundary by 1 cell so paths never
                                // run along plane edges that may abut walls. Only mark walkable
                                // if all 4 cardinal neighbours also fall inside the polygon.
                                if (cells[r][c] == CELL_UNKNOWN && allCardinalNeighboursInPolygon(r, c, polyX, polyZ)) {
                                    cells[r][c] = CELL_WALKABLE;
                                }
                            }
                        }
                    }
                }
            }

            // Pass 2: vertical plane footprints (walls, door frames, banisters).
            // Project each detected vertical plane's polygon onto the XZ floor plane
            // and mark those cells STATIC_OBSTACLE so A* routes around them.
            for (Plane plane : planes) {
                if (plane.getTrackingState() != TrackingState.TRACKING) continue;
                if (plane.getSubsumedBy() != null) continue;
                if (plane.getType() != Plane.Type.VERTICAL) continue;

                FloatBuffer polygon = plane.getPolygon();
                if (polygon == null || polygon.limit() < 4) continue;

                Pose  planePose = plane.getCenterPose();
                int   numVerts  = polygon.limit() / 2;

                // Compute XZ bounding box of projected polygon vertices.
                // For a vertical plane the polygon stores (X along wall, Y up wall) pairs;
                // Z in plane-local space is always 0. Transforming to world space and taking
                // only worldX/worldZ gives us the wall's horizontal footprint.
                float minX = Float.MAX_VALUE, maxX = -Float.MAX_VALUE;
                float minZ = Float.MAX_VALUE, maxZ = -Float.MAX_VALUE;
                for (int i = 0; i < numVerts; i++) {
                    float[] localPt = {polygon.get(i * 2), polygon.get(i * 2 + 1), 0f};
                    float[] worldPt = new float[3];
                    planePose.transformPoint(localPt, 0, worldPt, 0);
                    if (worldPt[0] < minX) minX = worldPt[0];
                    if (worldPt[0] > maxX) maxX = worldPt[0];
                    if (worldPt[2] < minZ) minZ = worldPt[2];
                    if (worldPt[2] > maxZ) maxZ = worldPt[2];
                }

                // Expand by two cells so A* gets a 40 cm safety margin around walls.
                minX -= 2 * CELL_SIZE; maxX += 2 * CELL_SIZE;
                minZ -= 2 * CELL_SIZE; maxZ += 2 * CELL_SIZE;

                // Compute clamped grid cell range without requiring worldToCell.
                int rMin = Math.max(0, (int) Math.floor((minZ - originWorldZ) / CELL_SIZE));
                int rMax = Math.min(GRID_SIZE - 1, (int) Math.floor((maxZ - originWorldZ) / CELL_SIZE));
                int colMin = Math.max(0, (int) Math.floor((minX - originWorldX) / CELL_SIZE));
                int colMax = Math.min(GRID_SIZE - 1, (int) Math.floor((maxX - originWorldX) / CELL_SIZE));

                if (rMin > rMax || colMin > colMax) continue;

                for (int r = rMin; r <= rMax; r++) {
                    for (int col = colMin; col <= colMax; col++) {
                        if (cells[r][col] != CELL_OBSTACLE) {
                            cells[r][col] = CELL_STATIC_OBSTACLE;
                        }
                    }
                }
            }
        } finally {
            lock.unlock();
        }
    }

    /**
     * Mark a radius of cells around (worldX, worldZ) as obstacles expiring at expiryFrame.
     */
    public void markObstacle(float worldX, float worldZ, int radius, int expiryFrame) {
        lock.lock();
        try {
            int[] cell = worldToCell(worldX, worldZ);
            if (cell == null) return;
            int row = cell[0], col = cell[1];
            for (int dr = -radius; dr <= radius; dr++) {
                for (int dc = -radius; dc <= radius; dc++) {
                    int r = row + dr;
                    int c = col + dc;
                    if (r >= 0 && r < GRID_SIZE && c >= 0 && c < GRID_SIZE) {
                        cells[r][c]          = CELL_OBSTACLE;
                        obstacleExpiry[r][c] = expiryFrame;
                    }
                }
            }
        } finally {
            lock.unlock();
        }
    }

    /** Clear dynamic YOLO obstacle cells whose expiry frame has passed.
     *  CELL_STATIC_OBSTACLE (elevated-surface footprints) are managed by rebuildFromPlanes(). */
    public void decayObstacles(int currentFrame) {
        lock.lock();
        try {
            for (int r = 0; r < GRID_SIZE; r++) {
                for (int c = 0; c < GRID_SIZE; c++) {
                    if (cells[r][c] == CELL_OBSTACLE && obstacleExpiry[r][c] <= currentFrame) {
                        cells[r][c] = CELL_UNKNOWN;
                    }
                }
            }
        } finally {
            lock.unlock();
        }
    }

    /** Returns a deep copy of the cell grid for use by A* without holding the lock. */
    public byte[][] getSnapshot() {
        lock.lock();
        try {
            byte[][] snap = new byte[GRID_SIZE][GRID_SIZE];
            for (int r = 0; r < GRID_SIZE; r++) {
                System.arraycopy(cells[r], 0, snap[r], 0, GRID_SIZE);
            }
            return snap;
        } finally {
            lock.unlock();
        }
    }

    public boolean isWalkable(int row, int col) {
        if (row < 0 || row >= GRID_SIZE || col < 0 || col >= GRID_SIZE) return false;
        return cells[row][col] == CELL_WALKABLE; // OBSTACLE and STATIC_OBSTACLE both impassable
    }

    /** Returns {row, col} for a world position, or null if outside grid. */
    public int[] worldToCell(float worldX, float worldZ) {
        if (!initialized) return null;
        int c = (int) Math.floor((worldX - originWorldX) / CELL_SIZE);
        int r = (int) Math.floor((worldZ - originWorldZ) / CELL_SIZE);
        if (r < 0 || r >= GRID_SIZE || c < 0 || c >= GRID_SIZE) return null;
        return new int[]{r, c};
    }

    /** Returns world-space XYZ of the centre of cell (row, col). Y is floor + 3 cm offset. */
    public float[] cellToWorld(int row, int col) {
        float worldX = originWorldX + (col + 0.5f) * CELL_SIZE;
        float worldZ = originWorldZ + (row + 0.5f) * CELL_SIZE;
        return new float[]{worldX, floorWorldY + 0.03f, worldZ};
    }

    /** Returns total walkable area in m² (used to decide when enough has been scanned). */
    public float getWalkableAreaM2() {
        lock.lock();
        try {
            int count = 0;
            for (int r = 0; r < GRID_SIZE; r++) {
                for (int c = 0; c < GRID_SIZE; c++) {
                    if (cells[r][c] == CELL_WALKABLE) count++;
                }
            }
            return count * CELL_SIZE * CELL_SIZE;
        } finally {
            lock.unlock();
        }
    }

    /**
     * Returns true only if the 4 cardinal-neighbour cell centres of (row, col) are all
     * inside the given polygon. Used to erode floor polygon boundaries by 1 cell so that
     * walkable cells are never placed right at a plane edge (which may coincide with a wall).
     */
    private boolean allCardinalNeighboursInPolygon(int row, int col,
                                                    float[] polyX, float[] polyZ) {
        int[][] cardinals = {{row - 1, col}, {row + 1, col}, {row, col - 1}, {row, col + 1}};
        for (int[] nb : cardinals) {
            float[] wc = cellToWorld(nb[0], nb[1]);
            if (!isPointInPolygon(wc[0], wc[2], polyX, polyZ)) return false;
        }
        return true;
    }

    // Standard ray-cast point-in-polygon test (XZ plane)
    private static boolean isPointInPolygon(float px, float pz,
                                             float[] polyX, float[] polyZ) {
        int     n      = polyX.length;
        boolean inside = false;
        for (int i = 0, j = n - 1; i < n; j = i++) {
            float xi = polyX[i], zi = polyZ[i];
            float xj = polyX[j], zj = polyZ[j];
            if (((zi > pz) != (zj > pz))
                    && (px < (xj - xi) * (pz - zi) / (zj - zi) + xi)) {
                inside = !inside;
            }
        }
        return inside;
    }
}
