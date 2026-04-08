package com.google.ar.core.examples.java.computervision.navigation;

import com.google.ar.core.Anchor;

import java.util.ArrayList;
import java.util.List;

/**
 * Manages the lifecycle of user-placed waypoint anchors.
 *
 * Flow:
 *   1. setStart()       – first tap on floor (green marker)
 *   2. addWaypoint()    – subsequent taps (cyan markers, optional intermediates)
 *   3. setDestination() – triggered by button or long-press (red marker)
 *   4. reset()          – detaches all anchors, clears state
 */
public class WaypointManager {

    private static final int MAX_WAYPOINTS = 10;

    /** A placed point: world-space position + ARCore anchor. */
    public static class Waypoint {
        public final float[] position; // {x, y, z} world space
        public final Anchor  anchor;
        public final boolean isDestination;

        Waypoint(float[] position, Anchor anchor, boolean isDestination) {
            this.position      = position;
            this.anchor        = anchor;
            this.isDestination = isDestination;
        }
    }

    private Waypoint          start       = null;
    private final List<Waypoint> waypoints = new ArrayList<>(); // intermediate points
    private Waypoint          destination = null;

    public boolean hasStart()       { return start != null; }
    public boolean hasDestination() { return destination != null; }

    public float[] getStartPosition()       { return start != null       ? start.position       : null; }
    public float[] getDestinationPosition() { return destination != null ? destination.position : null; }

    /** All rendered markers: start + intermediates + destination. */
    public List<Waypoint> getAllWaypoints() {
        List<Waypoint> all = new ArrayList<>();
        if (start != null)       all.add(start);
        all.addAll(waypoints);
        if (destination != null) all.add(destination);
        return all;
    }

    private static void detach(Anchor anchor) {
        if (anchor != null) anchor.detach();
    }

    public void setStart(float[] worldPos, Anchor anchor) {
        if (start != null) detach(start.anchor);
        start = new Waypoint(worldPos.clone(), anchor, false);
    }

    public void addWaypoint(float[] worldPos, Anchor anchor) {
        if (waypoints.size() >= MAX_WAYPOINTS) {
            detach(waypoints.get(0).anchor);
            waypoints.remove(0);
        }
        waypoints.add(new Waypoint(worldPos.clone(), anchor, false));
    }

    public void setDestination(float[] worldPos, Anchor anchor) {
        if (destination != null) detach(destination.anchor);
        destination = new Waypoint(worldPos.clone(), anchor, true);
    }

    /** Detach all anchors and clear all waypoints. */
    public void reset() {
        if (start != null) { detach(start.anchor); start = null; }
        for (Waypoint w : waypoints) detach(w.anchor);
        waypoints.clear();
        if (destination != null) { detach(destination.anchor); destination = null; }
    }
}
