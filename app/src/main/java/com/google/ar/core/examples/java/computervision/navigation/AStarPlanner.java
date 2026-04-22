package com.google.ar.core.examples.java.computervision.navigation;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.PriorityQueue;

/**
 * A* pathfinder on a 2D walkable grid.
 *
 * Uses an 8-connected grid with octile-distance heuristic and a small clearance
 * penalty for cells adjacent to obstacles. After finding the raw cell path a
 * string-pulling pass removes collinear / line-of-sight intermediate nodes.
 */
public class AStarPlanner {

    private static final float COST_CARDINAL    = 1.0f;
    private static final float COST_DIAGONAL    = 1.414f;
    private static final float OBSTACLE_PENALTY = 4.0f; // extra cost for cells adjacent to obstacles
    // Allow traversal through unscanned cells — A* will prefer confirmed walkable cells but
    // won't report "no path found" just because the detour passes through unscanned floor.
    private static final float UNKNOWN_PENALTY  = 4.0f; // strongly prefer walkable, but don't block

    // 8-directional neighbour offsets {drow, dcol, moveCost}
    private static final float[][] DIRS = {
            { 0,  1, COST_CARDINAL},
            { 0, -1, COST_CARDINAL},
            { 1,  0, COST_CARDINAL},
            {-1,  0, COST_CARDINAL},
            { 1,  1, COST_DIAGONAL},
            { 1, -1, COST_DIAGONAL},
            {-1,  1, COST_DIAGONAL},
            {-1, -1, COST_DIAGONAL},
    };

    private static final class Node implements Comparable<Node> {
        final int   row, col;
        float gCost;
        float fCost;
        Node  parent;

        Node(int row, int col) {
            this.row = row;
            this.col = col;
        }

        @Override
        public int compareTo(Node o) {
            return Float.compare(this.fCost, o.fCost);
        }
    }

    /**
     * Find a path from startCell to goalCell through the given grid snapshot.
     *
     * @param grid      NavGrid (used for world-coordinate conversion)
     * @param snap      snapshot of cell states (from NavGrid.getSnapshot())
     * @param startCell {row, col}
     * @param goalCell  {row, col}
     * @return ordered list of world-space {x, y, z} positions, or empty list if no path found
     */
    public List<float[]> findPath(NavGrid grid, byte[][] snap,
                                   int[] startCell, int[] goalCell) {

        int size = snap.length;
        int sr = startCell[0], sc = startCell[1];
        int gr = goalCell[0],  gc = goalCell[1];

        // Start/goal must not be blocked (obstacle). UNKNOWN cells are treated as open.
        if (isBlocked(snap, sr, sc, size) || isBlocked(snap, gr, gc, size)) {
            return Collections.emptyList();
        }

        float[][]  gCosts  = new float[size][size];
        boolean[][] closed = new boolean[size][size];
        Node[][]    nodeMap = new Node[size][size];

        for (int r = 0; r < size; r++) {
            for (int c = 0; c < size; c++) {
                gCosts[r][c] = Float.MAX_VALUE;
            }
        }

        PriorityQueue<Node> open = new PriorityQueue<>();
        Node startNode = new Node(sr, sc);
        startNode.gCost = 0;
        startNode.fCost = octile(sr, sc, gr, gc);
        gCosts[sr][sc]  = 0;
        nodeMap[sr][sc] = startNode;
        open.add(startNode);

        while (!open.isEmpty()) {
            Node current = open.poll();
            int  cr = current.row, cc = current.col;

            if (closed[cr][cc]) continue;
            closed[cr][cc] = true;

            if (cr == gr && cc == gc) {
                // Reconstruct path
                return reconstruct(current, grid, snap, size);
            }

            for (float[] dir : DIRS) {
                int   nr    = cr + (int) dir[0];
                int   nc    = cc + (int) dir[1];
                float dCost = dir[2];

                if (isBlocked(snap, nr, nc, size)) continue; // obstacle or out-of-bounds
                if (closed[nr][nc]) continue;

                // Penalise unscanned cells so the path prefers confirmed walkable floor.
                if (snap[nr][nc] == NavGrid.CELL_UNKNOWN) dCost += UNKNOWN_PENALTY;
                // Extra penalty for cells adjacent to obstacles (clearance).
                if (hasAdjacentObstacle(snap, nr, nc, size)) dCost += OBSTACLE_PENALTY;

                float newG = gCosts[cr][cc] + dCost;
                if (newG < gCosts[nr][nc]) {
                    gCosts[nr][nc] = newG;
                    Node next = new Node(nr, nc);
                    next.gCost  = newG;
                    next.fCost  = newG + octile(nr, nc, gr, gc);
                    next.parent = current;
                    nodeMap[nr][nc] = next;
                    open.add(next);
                }
            }
        }

        return Collections.emptyList(); // no path found
    }

    // ── Helpers ───────────────────────────────────────────────────────────────

    /** True if the cell is out-of-bounds or a solid obstacle (dynamic or static). */
    private static boolean isBlocked(byte[][] snap, int r, int c, int size) {
        if (r < 0 || r >= size || c < 0 || c >= size) return true;
        byte cell = snap[r][c];
        return cell == NavGrid.CELL_OBSTACLE || cell == NavGrid.CELL_STATIC_OBSTACLE;
    }

    private static boolean hasAdjacentObstacle(byte[][] snap, int r, int c, int size) {
        for (int dr = -1; dr <= 1; dr++) {
            for (int dc = -1; dc <= 1; dc++) {
                if (dr == 0 && dc == 0) continue;
                int nr = r + dr, nc = c + dc;
                if (nr >= 0 && nr < size && nc >= 0 && nc < size) {
                    byte cell = snap[nr][nc];
                    if (cell == NavGrid.CELL_OBSTACLE || cell == NavGrid.CELL_STATIC_OBSTACLE) {
                        return true;
                    }
                }
            }
        }
        return false;
    }

    /** Octile distance heuristic for 8-connected grid. */
    private static float octile(int r1, int c1, int r2, int c2) {
        float dx = Math.abs(r1 - r2);
        float dz = Math.abs(c1 - c2);
        return Math.max(dx, dz) + (COST_DIAGONAL - 1) * Math.min(dx, dz);
    }

    /** Reconstruct path from goal node back to start, then apply string-pulling. */
    private List<float[]> reconstruct(Node goal, NavGrid grid, byte[][] snap, int size) {
        List<int[]> cells = new ArrayList<>();
        Node n = goal;
        while (n != null) {
            cells.add(new int[]{n.row, n.col});
            n = n.parent;
        }
        Collections.reverse(cells);

        // String-pulling: keep only nodes that aren't line-of-sight-reachable from the last kept node
        List<int[]> pruned = new ArrayList<>();
        pruned.add(cells.get(0));
        int anchor = 0;
        for (int i = 2; i < cells.size(); i++) {
            if (!lineOfSight(snap, size,
                    cells.get(anchor)[0], cells.get(anchor)[1],
                    cells.get(i)[0],      cells.get(i)[1])) {
                pruned.add(cells.get(i - 1));
                anchor = i - 1;
            }
        }
        pruned.add(cells.get(cells.size() - 1));

        // Convert to world coordinates
        List<float[]> worldPath = new ArrayList<>();
        for (int[] cell : pruned) {
            worldPath.add(grid.cellToWorld(cell[0], cell[1]));
        }
        return worldPath;
    }

    /**
     * Bresenham line-of-sight check.
     * Returns true only if every cell on the line is confirmed WALKABLE — this prevents
     * the string-pull from cutting through unscanned or blocked cells.
     */
    private static boolean lineOfSight(byte[][] snap, int size, int r0, int c0, int r1, int c1) {
        int dr = Math.abs(r1 - r0);
        int dc = Math.abs(c1 - c0);
        int sr = r0 < r1 ? 1 : -1;
        int sc = c0 < c1 ? 1 : -1;
        int err = dr - dc;

        int r = r0, c = c0;
        while (true) {
            if (r < 0 || r >= size || c < 0 || c >= size) return false;
            if (snap[r][c] != NavGrid.CELL_WALKABLE) return false; // UNKNOWN or any obstacle breaks LOS
            if (r == r1 && c == c1) return true;

            int e2 = 2 * err;
            if (e2 > -dc) { err -= dc; r += sr; }
            if (e2 <  dr) { err += dr; c += sc; }
        }
    }
}
