package com.google.ar.core.examples.java.computervision;

import android.content.Context;
import android.graphics.Bitmap;
import android.graphics.RectF;
import android.util.Log;

import org.tensorflow.lite.DataType;
import org.tensorflow.lite.Interpreter;
import org.tensorflow.lite.support.common.FileUtil;

import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.MappedByteBuffer;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * TensorFlow Lite YOLO11 object detector.
 * Adapted from hello_ar_java; uses {@link NavigationOverlayView.Detection} as the result type.
 */
public class ObjectDetectorHelper {

    private static final String TAG = "YOLO";

    private static final String MODEL_FILE  = "yolo11.tflite";
    private static final float  CONF_THRESH = 0.40f;
    private static final float  IOU_THRESH  = 0.45f;

    private static final String[] LABELS = {
            "person","bicycle","car","motorcycle","airplane","bus","train","truck","boat",
            "traffic light","fire hydrant","stop sign","parking meter","bench","bird","cat",
            "dog","horse","sheep","cow","elephant","bear","zebra","giraffe","backpack",
            "umbrella","handbag","tie","suitcase","frisbee","skis","snowboard","sports ball",
            "kite","baseball bat","baseball glove","skateboard","surfboard","tennis racket",
            "bottle","wine glass","cup","fork","knife","spoon","bowl","banana","apple",
            "sandwich","orange","broccoli","carrot","hot dog","pizza","donut","cake","chair",
            "couch","potted plant","bed","dining table","toilet","tv","laptop","mouse",
            "remote","keyboard","cell phone","microwave","oven","toaster","sink","refrigerator",
            "book","clock","vase","scissors","teddy bear","hair drier","toothbrush","door"
    };

    private static final int FORMAT_STANDARD = 0;
    private static final int FORMAT_SPLIT_2  = 1;
    private static final int FORMAT_AI_HUB_3 = 2;

    private final Interpreter interpreter;
    private final int         inputSize;
    private final int         numBoxes;
    private final int         modelFormat;
    private final int         numClasses;
    private final boolean     channelFirst;
    private final boolean     inputUint8; // true if model expects UINT8 input (not FLOAT32)
    private int               runCount = 0;

    public ObjectDetectorHelper(Context context) throws IOException {
        MappedByteBuffer model = FileUtil.loadMappedFile(context, MODEL_FILE);

        Interpreter.Options options = new Interpreter.Options();
        options.setNumThreads(4);
        interpreter = new Interpreter(model, options);

        int[] inShape = interpreter.getInputTensor(0).shape();
        inputSize = inShape[1];
        inputUint8 = interpreter.getInputTensor(0).dataType() == DataType.UINT8;
        Log.d(TAG, "Input shape: " + Arrays.toString(inShape) + " type=" + interpreter.getInputTensor(0).dataType());

        int outputCount = interpreter.getOutputTensorCount();
        Log.d(TAG, "Output tensor count: " + outputCount);
        for (int i = 0; i < outputCount; i++) {
            Log.d(TAG, "  output[" + i + "] shape="
                    + Arrays.toString(interpreter.getOutputTensor(i).shape()));
        }

        int[] s0 = interpreter.getOutputTensor(0).shape();

        if (outputCount == 3
                && s0.length == 3
                && interpreter.getOutputTensor(1).shape().length == 2
                && interpreter.getOutputTensor(2).shape().length == 2) {
            modelFormat  = FORMAT_AI_HUB_3;
            numBoxes     = s0[1];
            numClasses   = -1;
            channelFirst = false;
        } else if (outputCount >= 2) {
            int[] s1 = interpreter.getOutputTensor(1).shape();
            modelFormat = FORMAT_SPLIT_2;
            if (s0.length == 3 && s0[1] == 4) {
                channelFirst = true;
                numBoxes     = s0[2];
                numClasses   = (s1.length >= 3) ? s1[1] : LABELS.length;
            } else if (s0.length == 3 && s0[2] == 4) {
                channelFirst = false;
                numBoxes     = s0[1];
                numClasses   = (s1.length >= 3) ? s1[2] : LABELS.length;
            } else {
                channelFirst = true;
                numBoxes     = Math.max(s0[1], s0[2]);
                numClasses   = LABELS.length;
            }
        } else {
            modelFormat = FORMAT_STANDARD;
            if (s0.length == 3 && s0[1] < s0[2]) {
                channelFirst = true;
                numClasses   = s0[1] - 4;
                numBoxes     = s0[2];
            } else {
                channelFirst = false;
                numBoxes     = s0[1];
                numClasses   = s0[2] - 4;
            }
        }
    }

    public List<NavigationOverlayView.Detection> detect(Bitmap bitmap) {
        Bitmap resized = Bitmap.createScaledBitmap(bitmap, inputSize, inputSize, true);

        int bytesPerPixel = inputUint8 ? 1 : 4;
        ByteBuffer inputBuffer = ByteBuffer.allocateDirect(1 * inputSize * inputSize * 3 * bytesPerPixel);
        inputBuffer.order(ByteOrder.nativeOrder());

        int[] pixels = new int[inputSize * inputSize];
        resized.getPixels(pixels, 0, inputSize, 0, 0, inputSize, inputSize);
        for (int px : pixels) {
            if (inputUint8) {
                inputBuffer.put((byte) ((px >> 16) & 0xFF));
                inputBuffer.put((byte) ((px >>  8) & 0xFF));
                inputBuffer.put((byte) ( px        & 0xFF));
            } else {
                inputBuffer.putFloat(((px >> 16) & 0xFF) / 255.0f);
                inputBuffer.putFloat(((px >>  8) & 0xFF) / 255.0f);
                inputBuffer.putFloat(( px        & 0xFF) / 255.0f);
            }
        }
        inputBuffer.rewind();

        List<NavigationOverlayView.Detection> results;
        if      (modelFormat == FORMAT_AI_HUB_3) results = runAiHub3(inputBuffer);
        else if (modelFormat == FORMAT_SPLIT_2)  results = runSplit2(inputBuffer);
        else                                      results = runStandard(inputBuffer);

        return nms(results);
    }

    // ── Inference runners ─────────────────────────────────────────────────────

    private List<NavigationOverlayView.Detection> runAiHub3(ByteBuffer inputBuffer) {
        // Use ByteBuffer outputs — accepted for any tensor type (FLOAT32 or UINT8).
        ByteBuffer buf0 = ByteBuffer.allocateDirect(interpreter.getOutputTensor(0).numBytes())
                .order(ByteOrder.nativeOrder());
        ByteBuffer buf1 = ByteBuffer.allocateDirect(interpreter.getOutputTensor(1).numBytes())
                .order(ByteOrder.nativeOrder());
        ByteBuffer buf2 = ByteBuffer.allocateDirect(interpreter.getOutputTensor(2).numBytes())
                .order(ByteOrder.nativeOrder());

        Map<Integer, Object> outputs = new HashMap<>();
        outputs.put(0, buf0);
        outputs.put(1, buf1);
        outputs.put(2, buf2);
        interpreter.runForMultipleInputsOutputs(new Object[]{inputBuffer}, outputs);

        buf0.rewind(); buf1.rewind(); buf2.rewind();

        boolean float0 = interpreter.getOutputTensor(0).dataType() == DataType.FLOAT32;
        boolean float1 = interpreter.getOutputTensor(1).dataType() == DataType.FLOAT32;
        boolean float2 = interpreter.getOutputTensor(2).dataType() == DataType.FLOAT32;

        // ── One-time diagnostic ────────────────────────────────────────────────
        // Inspect the first 3 valid boxes to determine coordinate space and format.
        // Check logcat tag "YOLO" for "boxN" lines to confirm the fix is correct.
        if (runCount++ == 0) {
            Log.d(TAG, "out0 type=" + interpreter.getOutputTensor(0).dataType()
                    + " out1 type=" + interpreter.getOutputTensor(1).dataType()
                    + " out2 type=" + interpreter.getOutputTensor(2).dataType()
                    + " inputSize=" + inputSize + " numBoxes=" + numBoxes);
            buf0.mark(); buf1.mark(); buf2.mark();
            for (int di = 0; di < Math.min(3, numBoxes); di++) {
                if (float0) {
                    float v0=buf0.getFloat(), v1=buf0.getFloat(),
                          v2=buf0.getFloat(), v3=buf0.getFloat();
                    Log.d(TAG, "box" + di + " raw_float=[" + v0 + "," + v1 + "," + v2 + "," + v3 + "]");
                } else {
                    int v0=buf0.get()&0xFF, v1=buf0.get()&0xFF,
                        v2=buf0.get()&0xFF, v3=buf0.get()&0xFF;
                    Log.d(TAG, "box" + di + " raw_uint8=[" + v0 + "," + v1 + "," + v2 + "," + v3 + "]");
                }
                float sc = float1 ? buf1.getFloat() : (buf1.get()&0xFF) / 255.0f;
                int cl = float2 ? (int) buf2.getFloat() : (buf2.get() & 0xFF);
                Log.d(TAG, "  score=" + sc + " class=" + cl);
            }
            buf0.reset(); buf1.reset(); buf2.reset();
        }

        // ── Coordinate format detection ───────────────────────────────────────
        // AI Hub YOLO11 3-tensor format outputs boxes as xyxy.
        // FLOAT32: values are in pixel space [0, inputSize] → divide by inputSize.
        // UINT8:   quantised so that pixel [0, inputSize] maps to [0, 255].
        //          (byte & 0xFF) / 255.0f already gives the correct [0-1] value.
        //
        // Previous bug: values were read without / inputSize for FLOAT32, then treated
        // as xywh — producing boxes of the form {clamp(x1 - x2/2), ...} where x1 is
        // small and x2 is large (pixel), collapsing everything to {0, 0, 1, 1}.

        List<NavigationOverlayView.Detection> results = new ArrayList<>();
        for (int i = 0; i < numBoxes; i++) {
            // Read raw box values (4 floats per box)
            float v0, v1, v2, v3;
            if (float0) {
                v0 = buf0.getFloat(); v1 = buf0.getFloat();
                v2 = buf0.getFloat(); v3 = buf0.getFloat();
                // Pixel space → normalize to [0, 1]
                v0 /= inputSize; v1 /= inputSize; v2 /= inputSize; v3 /= inputSize;
            } else {
                v0 = (buf0.get() & 0xFF) / 255.0f; v1 = (buf0.get() & 0xFF) / 255.0f;
                v2 = (buf0.get() & 0xFF) / 255.0f; v3 = (buf0.get() & 0xFF) / 255.0f;
            }

            float score   = float1 ? buf1.getFloat() : (buf1.get() & 0xFF) / 255.0f;
            int   classId = float2 ? (int) buf2.getFloat() : (buf2.get() & 0xFF);

            if (score < CONF_THRESH) continue;

            // Interpret as xyxy (AI Hub post-processed format).
            // If the box looks like xywh (i.e., v0 >= v2 meaning x1 >= x2 in xyxy) try
            // falling back to xywh→xyxy conversion so the code is robust to both.
            float x1, y1, x2, y2;
            if (v2 > v0 && v3 > v1) {
                // xyxy: values are already x_min, y_min, x_max, y_max
                x1 = v0; y1 = v1; x2 = v2; y2 = v3;
            } else {
                // xywh fallback: v0=cx, v1=cy, v2=w, v3=h
                x1 = v0 - v2 / 2f; y1 = v1 - v3 / 2f;
                x2 = v0 + v2 / 2f; y2 = v1 + v3 / 2f;
            }

            x1 = clamp(x1); y1 = clamp(y1); x2 = clamp(x2); y2 = clamp(y2);

            float area = (x2 - x1) * (y2 - y1);
            if (area < 0.0001f || area > 0.80f) continue; // skip degenerate or full-frame boxes

            String label = (classId >= 0 && classId < LABELS.length)
                    ? LABELS[classId] : "class_" + classId;
            results.add(new NavigationOverlayView.Detection(
                    new RectF(x1, y1, x2, y2), score, classId, label));
        }
        return results;
    }

    private List<NavigationOverlayView.Detection> runSplit2(ByteBuffer inputBuffer) {
        float[][][] coordsOut;
        float[][][] scoresOut;
        if (channelFirst) {
            coordsOut = new float[1][4][numBoxes];
            scoresOut = new float[1][numClasses][numBoxes];
        } else {
            coordsOut = new float[1][numBoxes][4];
            scoresOut = new float[1][numBoxes][numClasses];
        }
        Map<Integer, Object> out = new HashMap<>();
        out.put(0, coordsOut);
        out.put(1, scoresOut);
        interpreter.runForMultipleInputsOutputs(new Object[]{inputBuffer}, out);

        List<NavigationOverlayView.Detection> results = new ArrayList<>();
        for (int i = 0; i < numBoxes; i++) {
            float cx, cy, w, h;
            float[] cls = new float[numClasses];
            if (channelFirst) {
                cx = coordsOut[0][0][i]; cy = coordsOut[0][1][i];
                w  = coordsOut[0][2][i]; h  = coordsOut[0][3][i];
                for (int c = 0; c < numClasses; c++) cls[c] = scoresOut[0][c][i];
            } else {
                cx = coordsOut[0][i][0]; cy = coordsOut[0][i][1];
                w  = coordsOut[0][i][2]; h  = coordsOut[0][i][3];
                for (int c = 0; c < numClasses; c++) cls[c] = scoresOut[0][i][c];
            }
            int bestClass = 0; float bestLogit = Float.NEGATIVE_INFINITY;
            for (int c = 0; c < numClasses; c++) {
                if (cls[c] > bestLogit) { bestLogit = cls[c]; bestClass = c; }
            }
            float bestScore = 1.0f / (1.0f + (float) Math.exp(-bestLogit));
            if (bestScore < CONF_THRESH) continue;

            float x1 = clamp(cx - w / 2f), y1 = clamp(cy - h / 2f);
            float x2 = clamp(cx + w / 2f), y2 = clamp(cy + h / 2f);
            String label = bestClass < LABELS.length ? LABELS[bestClass] : "class_" + bestClass;
            results.add(new NavigationOverlayView.Detection(
                    new RectF(x1, y1, x2, y2), bestScore, bestClass, label));
        }
        return results;
    }

    private List<NavigationOverlayView.Detection> runStandard(ByteBuffer inputBuffer) {
        float[][][] raw = channelFirst
                ? new float[1][4 + numClasses][numBoxes]
                : new float[1][numBoxes][4 + numClasses];
        interpreter.run(inputBuffer, raw);

        List<NavigationOverlayView.Detection> results = new ArrayList<>();
        for (int i = 0; i < numBoxes; i++) {
            float cx, cy, w, h;
            float[] cls = new float[numClasses];
            if (channelFirst) {
                cx = raw[0][0][i]; cy = raw[0][1][i];
                w  = raw[0][2][i]; h  = raw[0][3][i];
                for (int c = 0; c < numClasses; c++) cls[c] = raw[0][4 + c][i];
            } else {
                cx = raw[0][i][0]; cy = raw[0][i][1];
                w  = raw[0][i][2]; h  = raw[0][i][3];
                for (int c = 0; c < numClasses; c++) cls[c] = raw[0][i][4 + c];
            }
            int bestClass = 0; float bestScore = 0f;
            for (int c = 0; c < numClasses; c++) {
                if (cls[c] > bestScore) { bestScore = cls[c]; bestClass = c; }
            }
            if (bestScore < CONF_THRESH) continue;

            float x1 = clamp((cx - w / 2f) / inputSize);
            float y1 = clamp((cy - h / 2f) / inputSize);
            float x2 = clamp((cx + w / 2f) / inputSize);
            float y2 = clamp((cy + h / 2f) / inputSize);
            String label = bestClass < LABELS.length ? LABELS[bestClass] : "class_" + bestClass;
            results.add(new NavigationOverlayView.Detection(
                    new RectF(x1, y1, x2, y2), bestScore, bestClass, label));
        }
        return results;
    }

    // ── NMS ───────────────────────────────────────────────────────────────────

    private List<NavigationOverlayView.Detection> nms(List<NavigationOverlayView.Detection> dets) {
        dets.sort((a, b) -> Float.compare(b.score, a.score));
        List<NavigationOverlayView.Detection> kept = new ArrayList<>();
        boolean[] suppressed = new boolean[dets.size()];
        for (int i = 0; i < dets.size(); i++) {
            if (suppressed[i]) continue;
            kept.add(dets.get(i));
            for (int j = i + 1; j < dets.size(); j++) {
                if (!suppressed[j] && dets.get(i).classId == dets.get(j).classId
                        && iou(dets.get(i).box, dets.get(j).box) > IOU_THRESH) {
                    suppressed[j] = true;
                }
            }
        }
        return kept;
    }

    private float iou(RectF a, RectF b) {
        float interLeft   = Math.max(a.left,   b.left);
        float interTop    = Math.max(a.top,    b.top);
        float interRight  = Math.min(a.right,  b.right);
        float interBottom = Math.min(a.bottom, b.bottom);
        float interArea   = Math.max(0, interRight - interLeft)
                * Math.max(0, interBottom - interTop);
        if (interArea == 0) return 0f;
        float aArea = (a.right - a.left) * (a.bottom - a.top);
        float bArea = (b.right - b.left) * (b.bottom - b.top);
        return interArea / (aArea + bArea - interArea);
    }

    private static float clamp(float v) {
        return Math.max(0f, Math.min(1f, v));
    }
}
