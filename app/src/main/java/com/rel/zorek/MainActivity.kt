package com.rel.zorek

import android.Manifest
import android.app.Activity
import android.content.Context
import android.content.Intent
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.text.InputType
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.TextView
import com.chaquo.python.Python
import java.io.File

class MainActivity : Activity() {
    companion object {
        fun configFile(c: Context) = File(c.filesDir, "shares.json")
    }

    private val ui = Handler(Looper.getMainLooper())

    override fun onCreate(b: Bundle?) {
        super.onCreate(b)
        requestPermissions(arrayOf(Manifest.permission.POST_NOTIFICATIONS), 1)
        val f = configFile(this)
        if (!f.exists()) f.writeText("{\n  \"shares\": []\n}\n")

        val edit = EditText(this).apply {
            setText(f.readText())
            typeface = android.graphics.Typeface.MONOSPACE
            inputType = InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_FLAG_MULTI_LINE
            gravity = android.view.Gravity.TOP
        }
        val status = TextView(this).apply { typeface = android.graphics.Typeface.MONOSPACE }
        val save = Button(this).apply {
            text = "Save config"
            setOnClickListener { f.writeText(edit.text.toString()) }  // backend re-reads the file every 2s
        }
        setContentView(LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(24, 48, 24, 24)
            addView(save)
            addView(edit, LinearLayout.LayoutParams(-1, 0, 1f))
            addView(status)
        })

        startForegroundService(Intent(this, TunnelService::class.java))
        object : Runnable {
            override fun run() {
                status.text = if (Python.isStarted())
                    Python.getInstance().getModule("zorek_backend").callAttr("status").toString() else "starting..."
                ui.postDelayed(this, 2000)
            }
        }.run()
    }
}
