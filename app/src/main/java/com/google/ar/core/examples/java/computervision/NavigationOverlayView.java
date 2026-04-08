package com.google.ar.core.examples.java.computervision;

import android.content.Context;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.graphics.RectF;
import android.util.AttributeSet;
import android.view.View;

import java.util.ArrayList;
import java.util.List;

/**
 * Canvas overlay drawn on top of the GL surface.
 *
 * Responsibilities:
 *  - Draws YOLO bounding boxes
 *  - Shows navigation state prompt (e.g., "Move phone to scan floor")
 *  - Shows turn-by-turn direction and distance when navigating
 */
public class NavigationOverlayView extends View {

    /** Bounding box detection from YOLO inference. */
    public static class Detection {
        public final RectF  box;     // normalized [0..1]
        public final float  score;
        public final int    classId;
        public final String label;

        public Detection(RectF box, float score, int classId, String label) {
            this.box     = box;
            this.score   = score;
            this.classId = classId;
            this.label   = label;
        }
    }

    // ── State ─────────────────────────────────────────────────────────────────

    private List<Detection> detections   = new ArrayList<>();
    private String          statePrompt  = "";
    private String          directionText = "";
    private String          distanceText  = "";
    private boolean         showNavHud   = false;

    // ── Paints ────────────────────────────────────────────────────────────────

    private final Paint boxPaint;
    private final Paint boxLabelBgPaint;
    private final Paint boxLabelTextPaint;

    private final Paint promptBgPaint;
    private final Paint promptTextPaint;

    private final Paint directionPaint;
    private final Paint distancePaint;
    private final Paint hudBgPaint;

    public NavigationOverlayView(Context context) {
        this(context, null);
    }

    public NavigationOverlayView(Context context, AttributeSet attrs) {
        super(context, attrs);
        setWillNotDraw(false);

        boxPaint = new Paint();
        boxPaint.setColor(Color.RED);
        boxPaint.setStrokeWidth(4f);
        boxPaint.setStyle(Paint.Style.STROKE);

        boxLabelBgPaint = new Paint();
        boxLabelBgPaint.setColor(Color.argb(200, 200, 0, 0));
        boxLabelBgPaint.setStyle(Paint.Style.FILL);

        boxLabelTextPaint = new Paint();
        boxLabelTextPaint.setColor(Color.WHITE);
        boxLabelTextPaint.setTextSize(36f);
        boxLabelTextPaint.setStyle(Paint.Style.FILL);

        promptBgPaint = new Paint();
        promptBgPaint.setColor(Color.argb(160, 0, 0, 0));
        promptBgPaint.setStyle(Paint.Style.FILL);

        promptTextPaint = new Paint();
        promptTextPaint.setColor(Color.WHITE);
        promptTextPaint.setTextSize(42f);
        promptTextPaint.setTextAlign(Paint.Align.CENTER);
        promptTextPaint.setStyle(Paint.Style.FILL);

        directionPaint = new Paint();
        directionPaint.setColor(Color.WHITE);
        directionPaint.setTextSize(72f);
        directionPaint.setTextAlign(Paint.Align.CENTER);
        directionPaint.setFakeBoldText(true);
        directionPaint.setStyle(Paint.Style.FILL);

        distancePaint = new Paint();
        distancePaint.setColor(Color.YELLOW);
        distancePaint.setTextSize(48f);
        distancePaint.setTextAlign(Paint.Align.CENTER);
        distancePaint.setStyle(Paint.Style.FILL);

        hudBgPaint = new Paint();
        hudBgPaint.setColor(Color.argb(180, 0, 0, 0));
        hudBgPaint.setStyle(Paint.Style.FILL);
    }

    // ── Public update API (call from UI thread) ───────────────────────────────

    public void setDetections(List<Detection> detections) {
        this.detections = detections != null ? detections : new ArrayList<>();
        invalidate();
    }

    public void setStatePrompt(String prompt) {
        this.statePrompt = prompt != null ? prompt : "";
        invalidate();
    }

    public void setNavigationHud(String direction, String distance) {
        this.directionText = direction != null ? direction : "";
        this.distanceText  = distance  != null ? distance  : "";
        this.showNavHud    = !directionText.isEmpty();
        invalidate();
    }

    public void hideNavigationHud() {
        showNavHud = false;
        directionText = "";
        distanceText  = "";
        invalidate();
    }

    // ── Drawing ───────────────────────────────────────────────────────────────

    @Override
    protected void onDraw(Canvas canvas) {
        super.onDraw(canvas);
        int w = getWidth();
        int h = getHeight();

        // YOLO bounding boxes
        for (Detection det : detections) {
            float left   = det.box.left   * w;
            float top    = det.box.top    * h;
            float right  = det.box.right  * w;
            float bottom = det.box.bottom * h;

            canvas.drawRect(left, top, right, bottom, boxPaint);

            String text     = det.label + " " + String.format("%.0f%%", det.score * 100);
            float  textH    = boxLabelTextPaint.getTextSize();
            float  textW    = boxLabelTextPaint.measureText(text);
            canvas.drawRect(left, top - textH - 8, left + textW + 8, top, boxLabelBgPaint);
            canvas.drawText(text, left + 4, top - 6, boxLabelTextPaint);
        }

        // Navigation HUD (bottom bar)
        if (showNavHud) {
            float hudH     = 180f;
            float startY   = h - hudH;
            canvas.drawRect(0, startY, w, h, hudBgPaint);

            canvas.drawText(directionText, w / 2f, startY + 100f, directionPaint);
            canvas.drawText(distanceText,  w / 2f, startY + 155f, distancePaint);
        }
    }
}
