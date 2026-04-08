package com.google.ar.core.examples.java.computervision.rendering;

import android.content.Context;
import android.opengl.GLES20;
import android.opengl.Matrix;

import com.google.ar.core.examples.java.common.rendering.ShaderUtil;

import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.FloatBuffer;
import java.util.List;

/**
 * Renders the navigation path as a GL_LINE_STRIP and waypoint markers as GL_POINTS.
 *
 * Two GL programs are used:
 *  - lineProgram: simple colour-pass-through for the line strip path
 *  - pointProgram: disc-clipped GL_POINTS for start/dest/waypoint markers
 */
public class PathRenderer {

    private static final String TAG = "PathRenderer";

    // Point-marker shaders (disc effect via gl_PointCoord)
    private static final String VERTEX_SHADER   = "shaders/path_dots.vert";
    private static final String FRAGMENT_SHADER = "shaders/path_dots.frag";

    // Inline line shaders — no gl_PointSize / gl_PointCoord needed
    private static final String LINE_VERT_SRC =
        "attribute vec3 a_Position;\n" +
        "uniform mat4 u_ModelViewProjection;\n" +
        "void main() {\n" +
        "    gl_Position = u_ModelViewProjection * vec4(a_Position, 1.0);\n" +
        "}\n";

    private static final String LINE_FRAG_SRC =
        "precision mediump float;\n" +
        "uniform vec4 u_Color;\n" +
        "void main() {\n" +
        "    gl_FragColor = u_Color;\n" +
        "}\n";

    private static final int BYTES_PER_FLOAT  = Float.SIZE / 8;
    private static final int FLOATS_PER_POINT = 3; // X, Y, Z
    private static final int BYTES_PER_POINT  = BYTES_PER_FLOAT * FLOATS_PER_POINT;
    private static final int INITIAL_CAPACITY = 512; // initial VBO point capacity

    // GL objects — point program (disc markers)
    private int programName;
    private int positionAttrib;
    private int mvpUniform;
    private int colorUniform;
    private int pointSizeUniform;

    // GL objects — line program (path strip)
    private int lineProgramName;
    private int linePositionAttrib;
    private int lineMvpUniform;
    private int lineColorUniform;

    private int vbo;
    private int vboCapacity; // in bytes

    // Perspective-correct point size coefficient: dots appear ~5 cm radius in world space
    // gl_PointSize = POINT_SIZE_COEFF / gl_Position.w
    // At 1 m distance: gl_Position.w ≈ 1 → pixel size ≈ POINT_SIZE_COEFF
    private static final float POINT_SIZE_COEFF = 40.0f;

    // Colours (RGBA)
    private static final float[] COLOR_PATH  = {1.0f, 0.6f, 0.0f, 0.9f}; // orange
    private static final float[] COLOR_START = {0.0f, 1.0f, 0.0f, 1.0f}; // green
    private static final float[] COLOR_DEST  = {1.0f, 0.0f, 0.0f, 1.0f}; // red
    private static final float[] COLOR_WAYPOINT = {0.0f, 0.8f, 1.0f, 0.9f}; // cyan

    // CPU-side buffer for uploading
    private FloatBuffer cpuBuffer;

    public PathRenderer() {}

    /** Must be called on the GL thread (typically in onSurfaceCreated). */
    public void createOnGlThread(Context context) throws IOException {
        ShaderUtil.checkGLError(TAG, "before create");

        int[] buffers = new int[1];
        GLES20.glGenBuffers(1, buffers, 0);
        vbo = buffers[0];
        GLES20.glBindBuffer(GLES20.GL_ARRAY_BUFFER, vbo);
        vboCapacity = INITIAL_CAPACITY * BYTES_PER_POINT;
        GLES20.glBufferData(GLES20.GL_ARRAY_BUFFER, vboCapacity, null, GLES20.GL_DYNAMIC_DRAW);
        GLES20.glBindBuffer(GLES20.GL_ARRAY_BUFFER, 0);

        int vert = ShaderUtil.loadGLShader(TAG, context, GLES20.GL_VERTEX_SHADER,   VERTEX_SHADER);
        int frag = ShaderUtil.loadGLShader(TAG, context, GLES20.GL_FRAGMENT_SHADER, FRAGMENT_SHADER);

        programName = GLES20.glCreateProgram();
        GLES20.glAttachShader(programName, vert);
        GLES20.glAttachShader(programName, frag);
        GLES20.glLinkProgram(programName);
        GLES20.glUseProgram(programName);

        positionAttrib  = GLES20.glGetAttribLocation(programName,  "a_Position");
        mvpUniform      = GLES20.glGetUniformLocation(programName, "u_ModelViewProjection");
        colorUniform    = GLES20.glGetUniformLocation(programName, "u_Color");
        pointSizeUniform = GLES20.glGetUniformLocation(programName, "u_PointSize");

        // Compile the line-strip program from inline source strings
        int lineVert = GLES20.glCreateShader(GLES20.GL_VERTEX_SHADER);
        GLES20.glShaderSource(lineVert, LINE_VERT_SRC);
        GLES20.glCompileShader(lineVert);

        int lineFrag = GLES20.glCreateShader(GLES20.GL_FRAGMENT_SHADER);
        GLES20.glShaderSource(lineFrag, LINE_FRAG_SRC);
        GLES20.glCompileShader(lineFrag);

        lineProgramName = GLES20.glCreateProgram();
        GLES20.glAttachShader(lineProgramName, lineVert);
        GLES20.glAttachShader(lineProgramName, lineFrag);
        GLES20.glLinkProgram(lineProgramName);

        linePositionAttrib = GLES20.glGetAttribLocation(lineProgramName,  "a_Position");
        lineMvpUniform     = GLES20.glGetUniformLocation(lineProgramName, "u_ModelViewProjection");
        lineColorUniform   = GLES20.glGetUniformLocation(lineProgramName, "u_Color");

        ShaderUtil.checkGLError(TAG, "after create");

        // Allocate initial CPU buffer
        cpuBuffer = ByteBuffer.allocateDirect(INITIAL_CAPACITY * BYTES_PER_POINT)
                .order(ByteOrder.nativeOrder())
                .asFloatBuffer();
    }

    /**
     * Draw the complete navigation scene: path dots, start marker, destination marker,
     * and intermediate waypoint markers.
     *
     * @param viewMatrix       from camera.getViewMatrix()
     * @param projMatrix       from camera.getProjectionMatrix()
     * @param pathPoints       ordered world-space path positions (may be null)
     * @param startPos         start anchor world position (may be null)
     * @param destPos          destination anchor world position (may be null)
     * @param waypointPositions intermediate waypoint positions (may be null/empty)
     */
    public void draw(float[] viewMatrix, float[] projMatrix,
                     List<float[]> pathPoints,
                     float[] startPos,
                     float[] destPos,
                     List<float[]> waypointPositions) {

        float[] mvp = new float[16];
        Matrix.multiplyMM(mvp, 0, projMatrix, 0, viewMatrix, 0);

        GLES20.glEnable(GLES20.GL_BLEND);
        GLES20.glBlendFunc(GLES20.GL_SRC_ALPHA, GLES20.GL_ONE_MINUS_SRC_ALPHA);

        GLES20.glUseProgram(programName);
        GLES20.glUniformMatrix4fv(mvpUniform, 1, false, mvp, 0);
        GLES20.glUniform1f(pointSizeUniform, POINT_SIZE_COEFF);

        // 1. Path line (orange GL_LINE_STRIP)
        if (pathPoints != null && pathPoints.size() >= 2) {
            drawLine(pathPoints, COLOR_PATH, mvp);
        }

        // 2. Intermediate waypoints (cyan, larger)
        if (waypointPositions != null && !waypointPositions.isEmpty()) {
            drawPoints(waypointPositions, COLOR_WAYPOINT, mvp);
        }

        // 3. Start marker (green, single point)
        if (startPos != null) {
            drawSinglePoint(startPos, COLOR_START, mvp, POINT_SIZE_COEFF * 2f);
        }

        // 4. Destination marker (red, single point)
        if (destPos != null) {
            drawSinglePoint(destPos, COLOR_DEST, mvp, POINT_SIZE_COEFF * 2f);
        }

        GLES20.glDisable(GLES20.GL_BLEND);
    }

    // ── Private helpers ───────────────────────────────────────────────────────

    private void drawPoints(List<float[]> points, float[] color, float[] mvp) {
        int numPoints = points.size();
        int needed    = numPoints * BYTES_PER_POINT;

        // Grow VBO if needed
        GLES20.glBindBuffer(GLES20.GL_ARRAY_BUFFER, vbo);
        if (needed > vboCapacity) {
            while (vboCapacity < needed) vboCapacity *= 2;
            GLES20.glBufferData(GLES20.GL_ARRAY_BUFFER, vboCapacity, null, GLES20.GL_DYNAMIC_DRAW);
        }

        // Resize CPU buffer if needed
        if (cpuBuffer.capacity() < numPoints * FLOATS_PER_POINT) {
            cpuBuffer = ByteBuffer.allocateDirect(needed)
                    .order(ByteOrder.nativeOrder())
                    .asFloatBuffer();
        }

        cpuBuffer.clear();
        for (float[] p : points) {
            cpuBuffer.put(p[0]).put(p[1]).put(p[2]);
        }
        cpuBuffer.rewind();

        GLES20.glBufferSubData(GLES20.GL_ARRAY_BUFFER, 0, needed, cpuBuffer);

        GLES20.glUniform4f(colorUniform, color[0], color[1], color[2], color[3]);
        GLES20.glUniformMatrix4fv(mvpUniform, 1, false, mvp, 0);
        GLES20.glUniform1f(pointSizeUniform, POINT_SIZE_COEFF);

        GLES20.glEnableVertexAttribArray(positionAttrib);
        GLES20.glVertexAttribPointer(positionAttrib, 3, GLES20.GL_FLOAT, false, BYTES_PER_POINT, 0);
        GLES20.glDrawArrays(GLES20.GL_POINTS, 0, numPoints);
        GLES20.glDisableVertexAttribArray(positionAttrib);

        GLES20.glBindBuffer(GLES20.GL_ARRAY_BUFFER, 0);
        ShaderUtil.checkGLError(TAG, "drawPoints");
    }

    /** Draw a list of points as a connected GL_LINE_STRIP using the line shader program. */
    private void drawLine(List<float[]> points, float[] color, float[] mvp) {
        int numPoints = points.size();
        int needed    = numPoints * BYTES_PER_POINT;

        GLES20.glBindBuffer(GLES20.GL_ARRAY_BUFFER, vbo);
        if (needed > vboCapacity) {
            while (vboCapacity < needed) vboCapacity *= 2;
            GLES20.glBufferData(GLES20.GL_ARRAY_BUFFER, vboCapacity, null, GLES20.GL_DYNAMIC_DRAW);
        }
        if (cpuBuffer.capacity() < numPoints * FLOATS_PER_POINT) {
            cpuBuffer = ByteBuffer.allocateDirect(needed)
                    .order(ByteOrder.nativeOrder())
                    .asFloatBuffer();
        }

        cpuBuffer.clear();
        for (float[] p : points) {
            cpuBuffer.put(p[0]).put(p[1]).put(p[2]);
        }
        cpuBuffer.rewind();
        GLES20.glBufferSubData(GLES20.GL_ARRAY_BUFFER, 0, needed, cpuBuffer);

        GLES20.glUseProgram(lineProgramName);
        GLES20.glUniformMatrix4fv(lineMvpUniform, 1, false, mvp, 0);
        GLES20.glUniform4f(lineColorUniform, color[0], color[1], color[2], color[3]);

        GLES20.glLineWidth(8.0f);
        GLES20.glEnableVertexAttribArray(linePositionAttrib);
        GLES20.glVertexAttribPointer(linePositionAttrib, 3, GLES20.GL_FLOAT, false, BYTES_PER_POINT, 0);
        GLES20.glDrawArrays(GLES20.GL_LINE_STRIP, 0, numPoints);
        GLES20.glDisableVertexAttribArray(linePositionAttrib);

        // Restore the point program for subsequent draws
        GLES20.glUseProgram(programName);
        GLES20.glBindBuffer(GLES20.GL_ARRAY_BUFFER, 0);
        ShaderUtil.checkGLError(TAG, "drawLine");
    }

    private void drawSinglePoint(float[] pos, float[] color, float[] mvp, float size) {
        GLES20.glBindBuffer(GLES20.GL_ARRAY_BUFFER, vbo);

        cpuBuffer.clear();
        cpuBuffer.put(pos[0]).put(pos[1]).put(pos[2]);
        cpuBuffer.rewind();

        GLES20.glBufferSubData(GLES20.GL_ARRAY_BUFFER, 0, BYTES_PER_POINT, cpuBuffer);

        GLES20.glUniform4f(colorUniform, color[0], color[1], color[2], color[3]);
        GLES20.glUniformMatrix4fv(mvpUniform, 1, false, mvp, 0);
        GLES20.glUniform1f(pointSizeUniform, size);

        GLES20.glEnableVertexAttribArray(positionAttrib);
        GLES20.glVertexAttribPointer(positionAttrib, 3, GLES20.GL_FLOAT, false, BYTES_PER_POINT, 0);
        GLES20.glDrawArrays(GLES20.GL_POINTS, 0, 1);
        GLES20.glDisableVertexAttribArray(positionAttrib);

        GLES20.glBindBuffer(GLES20.GL_ARRAY_BUFFER, 0);
    }
}
