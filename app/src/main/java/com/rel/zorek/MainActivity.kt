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
import android.provider.Settings
import android.text.InputType
import android.view.Gravity
import android.view.View
import android.widget.Button
import android.widget.CheckBox
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.Switch
import android.widget.TextView
import com.chaquo.python.Python
import com.chaquo.python.android.AndroidPlatform
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

        fun prefs(c: Context) = c.getSharedPreferences("zorek", MODE_PRIVATE)

        /** Service mode: tunnels run in a foreground service (with a status notification), also with the app closed. */
        fun serviceMode(c: Context) = prefs(c).getBoolean("service_mode", true)

        fun startOnBoot(c: Context) = prefs(c).getBoolean("start_on_boot", false)

        /** Starts Python and the tunnel backend once per process. */
        @Synchronized
        fun ensureBackend(c: Context) {
            if (!Python.isStarted()) Python.start(AndroidPlatform(c))
            backend().callAttr("start", configFile(c).absolutePath, c.filesDir.absolutePath, importDir(c))
        }
    }


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

        fun openUrl(u: String) = startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(u)))
        val help = TextView(this).apply {
            text = "No token yet? Sign up free at myzrok.io, click the zrok icon in the sidebar, then " +
                "\"CLICK HERE TO GET STARTED!\" and copy the account token from step 2."
            textSize = 13f
        }
        val consoleBtn = Button(this).apply {
            text = "Open zrok console (token, environments, shares)"
            setOnClickListener { openUrl("https://api-v2.zrok.io/") }
        }

        // --- service mode / boot ---------------------------------------------------------------------------------
        var syncing = false
        val svc = Switch(this).apply { text = "Service mode (keep tunnels running, status notification)" }
        val boot = Switch(this).apply { text = "Start service mode on boot" }
        fun syncSwitches() {
            syncing = true
            svc.isChecked = serviceMode(this@MainActivity)
            boot.isChecked = startOnBoot(this@MainActivity)
            syncing = false
        }
        svc.setOnCheckedChangeListener { _, on ->
            if (syncing) return@setOnCheckedChangeListener
            prefs.edit().putBoolean("service_mode", on).apply()
            if (on) startForegroundService(Intent(this, TunnelService::class.java))
            else {  // tunnels keep running while the app process lives, the notification goes away
                stopService(Intent(this, TunnelService::class.java))
                prefs.edit().putBoolean("start_on_boot", false).apply()
                syncSwitches()
            }
        }
        boot.setOnCheckedChangeListener { _, on ->
            if (syncing) return@setOnCheckedChangeListener
            prefs.edit().putBoolean("start_on_boot", on).apply()
            if (on && !serviceMode(this)) {
                prefs.edit().putBoolean("service_mode", true).apply()
                startForegroundService(Intent(this, TunnelService::class.java))
                syncSwitches()
            }
        }
        syncSwitches()
        resync = ::syncSwitches

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

        @Suppress("DEPRECATION") window.decorView.run { systemUiVisibility = systemUiVisibility or View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR }
        actionBar?.hide()  // edge-to-edge (targetSdk 35): the bar would cover the top of the page
        setContentView(ScrollView(this).apply {
            fitsSystemWindows = true  // keep clear of the status and navigation bars
            addView(LinearLayout(this@MainActivity).apply {
                orientation = LinearLayout.VERTICAL
                setPadding(32, 48, 32, 32)
                addView(TextView(this@MainActivity).apply { text = "Zorek"; textSize = 26f })
                addView(title("Tunnels")); addView(status)
                addView(title("Background"))
                addView(svc); addView(boot)
                addView(title("New public URL"))
                listOf(help, consoleBtn, token, ip, port, name, https, create, result).forEach { addView(it) }
                addView(title("Folder import")); addView(watch)
                addView(title("Config (shares.json)")); addView(edit); addView(save)
            })
        })

        if (serviceMode(this)) startForegroundService(Intent(this, TunnelService::class.java)) else ensureBackend(this)
        // Python can block (broken identity while libziti loads): poll on a worker thread, never on the UI thread
        Thread {
            while (!isDestroyed) {
                val text = try {
                    if (Python.isStarted()) backend().callAttr("status").toString() else "starting..."
                } catch (e: Exception) {
                    "status failed: ${e.message}"
                }
                runOnUiThread { status.text = text }
                Thread.sleep(2000)
            }
        }.start()
    }

    private var reloadEditor: () -> Unit = {}
    private var resync: () -> Unit = {}

    /** The notification's Stop button changes the switches while the app is in the background. */
    override fun onResume() {
        super.onResume()
        resync()
    }
}
