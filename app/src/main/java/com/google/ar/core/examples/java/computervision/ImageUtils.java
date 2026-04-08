package com.google.ar.core.examples.java.computervision;

import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.graphics.ImageFormat;
import android.graphics.Rect;
import android.graphics.YuvImage;
import android.media.Image;

import java.io.ByteArrayOutputStream;
import java.nio.ByteBuffer;

/** Converts ARCore camera images (YUV_420_888) to Bitmap for TFLite inference. */
public class ImageUtils {

    /**
     * Converts an Android {@link Image} (YUV_420_888) to a {@link Bitmap}.
     *
     * @param image           Camera image acquired from ARCore.
     * @param rotationDegrees Clockwise rotation to apply so the bitmap matches the display
     *                        orientation (0 / 90 / 180 / 270).
     */
    public static Bitmap imageToBitmap(Image image, int rotationDegrees) {

        Image.Plane[] planes = image.getPlanes();
        int width  = image.getWidth();
        int height = image.getHeight();

        // Y plane (luma)
        ByteBuffer yBuffer    = planes[0].getBuffer();
        int        yRowStride = planes[0].getRowStride();
        byte[]     nv21       = new byte[width * height * 3 / 2];

        if (yRowStride == width) {
            yBuffer.get(nv21, 0, width * height);
        } else {
            for (int row = 0; row < height; row++) {
                yBuffer.position(row * yRowStride);
                yBuffer.get(nv21, row * width, width);
            }
        }

        // UV planes – handle both packed (pixelStride=1) and interleaved (pixelStride=2) layouts
        ByteBuffer vBuffer       = planes[2].getBuffer();
        ByteBuffer uBuffer       = planes[1].getBuffer();
        int        uvPixelStride = planes[1].getPixelStride();
        int        uvRowStride   = planes[1].getRowStride();
        int        ySize         = width * height;

        for (int row = 0; row < height / 2; row++) {
            for (int col = 0; col < width / 2; col++) {
                int uvIndex = row * uvRowStride + col * uvPixelStride;
                nv21[ySize + row * width + col * 2]     = vBuffer.get(uvIndex);
                nv21[ySize + row * width + col * 2 + 1] = uBuffer.get(uvIndex);
            }
        }

        // Decode NV21 → JPEG → Bitmap
        YuvImage yuvImage = new YuvImage(nv21, ImageFormat.NV21, width, height, null);
        ByteArrayOutputStream out = new ByteArrayOutputStream();
        yuvImage.compressToJpeg(new Rect(0, 0, width, height), 100, out);
        byte[] imageBytes = out.toByteArray();
        Bitmap bitmap = BitmapFactory.decodeByteArray(imageBytes, 0, imageBytes.length);

        // Rotate to match display orientation
        if (rotationDegrees != 0) {
            android.graphics.Matrix m = new android.graphics.Matrix();
            m.postRotate(rotationDegrees);
            bitmap = Bitmap.createBitmap(
                    bitmap, 0, 0, bitmap.getWidth(), bitmap.getHeight(), m, true);
        }

        return bitmap;
    }
}
