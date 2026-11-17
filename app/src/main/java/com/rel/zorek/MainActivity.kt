package com.rel.zorek

import android.Manifest
import android.app.Activity
import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.graphics.Typeface
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.os.Environment
import android.os.Handler
import android.os.Looper
import android.provider.Settings
import android.text.InputType
import android.view.Gravity
import android.widget.Button
import android.widget.CheckBox
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.Switch
import android.widget.TextView
import com.chaquo.python.Python
import java.io.File

class MainActivity : Activity() {
    companion object {
        fun configFile(c: Context) = File(c.filesDir, "shares.json")

        /** Directory watched for shares_*.json when the "watch Downloads" switch is on, else null. */
        fun importDir(c: Context): String? =
            if (c.getSharedPreferences("zorek", MODE_PRIVATE).getBoolean("watch_downloads", false))
                Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOWNLOADS).absolutePath
            else null

        fun backend() = Python.getInstance().getModule("zorek_backend")
    }

    private val ui = Handler(Looper.getMainLooper())

    private fun field(hint: String, type: Int = InputType.TYPE_CLASS_TEXT, text: String = "") =
        EditText(this).apply { this.hint = hint; inputType = type; setText(text); setSingleLine() }

    override fun onCreate(b: Bundle?) {
        super.onCreate(b)
        requestPermissions(arrayOf(Manifest.permission.POST_NOTIFICATIONS), 1)
        val prefs = getSharedPreferences("zorek", MODE_PRIVATE)
        val cfg = configFile(this)
        if (!cfg.exists()) cfg.writeText("{\n  \"shares\": []\n}\n")
        val mono = Typeface.MONOSPACE

        fun title(t: String) = TextView(this).apply { text = t; textSize = 18f; setPadding(0, 32, 0, 8) }

        val status = TextView(this).apply { typeface = mono; text = "starting..." }

        // --- new URL ---------------------------------------------------------------------------------------------
        val token = field("zrok enable token", InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_PASSWORD)
        val ip = field("target IP (emulator host: 10.0.2.2)", text = "127.0.0.1")
        val port = field("target port", InputType.TYPE_CLASS_NUMBER, "8000")
        val name = field("public name (optional)")
        val https = CheckBox(this).apply { text = "target speaks https" }
        val result = TextView(this)
        val create = Button(this).apply {
            text = "Create URL"
            setOnClickListener {
                isEnabled = false
                result.text = "creating..."
                Thread {
                    val msg = try {
                        val url = backend().callAttr(
                            "create_url", cfg.absolutePath, token.text.toString(), ip.text.toString(),
                            port.text.toString(), if (https.isChecked) "https" else "http", name.text.toString()
                        ).toString()
                        (getSystemService(CLIPBOARD_SERVICE) as ClipboardManager)
                            .setPrimaryClip(ClipData.newPlainText("url", url))
                        "created $url (copied)"
                    } catch (e: Exception) {
                        "failed: ${e.message}"
                    }
                    runOnUiThread { result.text = msg; isEnabled = true; reloadEditor() }
                }.start()
            }
        }

        // --- Downloads watch -------------------------------------------------------------------------------------
        val watch = Switch(this).apply {
            text = "Import shares_*.json from Downloads"
            isChecked = prefs.getBoolean("watch_downloads", false)
            setOnCheckedChangeListener { _, on ->
                prefs.edit().putBoolean("watch_downloads", on).apply()
                if (on && !Environment.isExternalStorageManager()) {  // reading other apps' files in Downloads
                    startActivity(
                        Intent(Settings.ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION, Uri.parse("package:$packageName"))
                    )
                }
                if (Python.isStarted()) backend().callAttr("set_import_dir", importDir(this@MainActivity))
            }
        }

        // --- config editor ---------------------------------------------------------------------------------------
        val edit = EditText(this).apply {
            setText(cfg.readText())
            typeface = mono
            textSize = 12f
            inputType = InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_FLAG_MULTI_LINE
            gravity = Gravity.TOP
            minLines = 8
        }
        val save = Button(this).apply {
            text = "Save config"
            setOnClickListener { cfg.writeText(edit.text.toString()) }  // backend re-reads the file every 2s
        }
        reloadEditor = { edit.setText(cfg.readText()) }

        setContentView(ScrollView(this).apply {
            addView(LinearLayout(this@MainActivity).apply {
                orientation = LinearLayout.VERTICAL
                setPadding(32, 48, 32, 32)
                addView(title("Tunnels")); addView(status)
                addView(title("New public URL"))
                listOf(token, ip, port, name, https, create, result).forEach { addView(it) }
                addView(title("Folder import")); addView(watch)
                addView(title("Config (shares.json)")); addView(edit); addView(save)
            })
        })

        startForegroundService(Intent(this, TunnelService::class.java))
        object : Runnable {
            override fun run() {
                status.text = if (Python.isStarted()) backend().callAttr("status").toString() else "starting..."
                ui.postDelayed(this, 2000)
            }
        }.run()
    }

    private var reloadEditor: () -> Unit = {}
}
