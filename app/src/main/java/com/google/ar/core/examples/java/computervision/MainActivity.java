package com.google.ar.core.examples.java.computervision;

import android.content.Intent;
import android.os.Bundle;
import androidx.appcompat.app.AppCompatActivity;
import android.widget.Button;

/**
 * Home screen activity. Presents "Begin Navigating" and "How to Use" options
 * before launching into the AR experience.
 */
public class MainActivity extends AppCompatActivity {

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_landing);

        Button btnBegin = findViewById(R.id.btn_begin_navigating);
        btnBegin.setOnClickListener(v ->
                startActivity(new Intent(this, ComputerVisionActivity.class)));

        Button btnHowTo = findViewById(R.id.btn_how_to_use);
        btnHowTo.setOnClickListener(v ->
                startActivity(new Intent(this, HowToUseActivity.class)));
    }
}
