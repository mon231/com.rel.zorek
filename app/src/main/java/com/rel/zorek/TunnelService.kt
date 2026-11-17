package com.rel.zorek

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Intent
import android.content.pm.ServiceInfo
import android.os.Build
import android.os.Handler
import android.os.HandlerThread
import android.os.IBinder
import com.chaquo.python.Python
import com.chaquo.python.android.AndroidPlatform
import org.json.JSONObject

/**
 * "Service mode": keeps the Python backend (and so every tunnel in shares.json) alive in the background and shows an
 * ongoing notification with the live state of every tunnel.
 */
class TunnelService : Service() {
    companion object {
        const val ACTION_STOP = "com.rel.zorek.STOP"
        private const val CHANNEL = "tunnels"
        private const val ID = 1
    }

    // Python calls can block (e.g. while libziti loads a broken identity): never on the main thread
    private val thread = HandlerThread("zorek-status").apply { start() }
    private val handler = Handler(thread.looper)
    private var lastShown: String? = null

    private val refresh = object : Runnable {
        override fun run() {
            show()
            handler.postDelayed(this, 3000)
        }
    }

    override fun onBind(i: Intent?): IBinder? = null

    override fun onStartCommand(i: Intent?, flags: Int, startId: Int): Int {
        if (i?.action == ACTION_STOP) {
            // the user pressed Stop in the notification: stop the tunnels and leave service mode
            handler.removeCallbacks(refresh)
            handler.post { if (Python.isStarted()) MainActivity.backend().callAttr("stop") }
            MainActivity.prefs(this).edit().putBoolean("service_mode", false).putBoolean("start_on_boot", false).apply()
            stopForeground(STOP_FOREGROUND_REMOVE)
            stopSelf()
            return START_NOT_STICKY
        }
        getSystemService(NotificationManager::class.java)
            .createNotificationChannel(NotificationChannel(CHANNEL, "Tunnel status", NotificationManager.IMPORTANCE_LOW))
        val first = build("Zorek", "Starting tunnels...", null)
        // dataSync services are time-limited on Android 15 and cannot start from BOOT_COMPLETED: use specialUse (API 34+)
        if (Build.VERSION.SDK_INT >= 34) startForeground(ID, first, ServiceInfo.FOREGROUND_SERVICE_TYPE_SPECIAL_USE)
        else startForeground(ID, first)
        MainActivity.ensureBackend(this)
        handler.removeCallbacks(refresh)
        refresh.run()
        return START_STICKY
    }

    override fun onDestroy() {
        handler.removeCallbacks(refresh)
        thread.quitSafely()
        super.onDestroy()
    }

    private fun intent(action: String?) = PendingIntent.getService(
        this, 1, Intent(this, TunnelService::class.java).setAction(action),
        PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT
    )

    private fun build(title: String, text: String, big: String?): Notification {
        val open = PendingIntent.getActivity(
            this, 0, Intent(this, MainActivity::class.java), PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT
        )
        val p = MainActivity.prefs(this)
        val flags = listOf(
            "boot start " + if (p.getBoolean("start_on_boot", false)) "on" else "off",
            "Downloads import " + if (p.getBoolean("watch_downloads", false)) "on" else "off"
        ).joinToString(" · ")
        return Notification.Builder(this, CHANNEL)
            .setSmallIcon(android.R.drawable.stat_sys_upload)
            .setContentTitle(title).setContentText(text).setSubText(flags)
            .apply { if (big != null) setStyle(Notification.BigTextStyle().bigText(big)) }
            .setContentIntent(open)
            .addAction(Notification.Action.Builder(null, "Stop", intent(ACTION_STOP)).build())
            .setOngoing(true).setOnlyAlertOnce(true).setShowWhen(false)
            .build()
    }

    /** Title "2 of 3 tunnels up", one expanded line per tunnel (url, target, state), config/import error on top. */
    private fun show() {
        val st = try {
            JSONObject(MainActivity.backend().callAttr("status_json").toString())
        } catch (e: Exception) {
            return
        }
        val tunnels = st.getJSONObject("tunnels")
        val lines = mutableListOf<String>()
        var up = 0
        if (!st.isNull("error")) lines.add("! " + st.getString("error"))
        for (k in tunnels.keys()) {
            val t = tunnels.getJSONObject(k)
            val ok = t.getString("state") == "running"
            if (ok) up++
            val host = t.getString("url").removePrefix("https://")
            val state = t.getString("state")
            val mark = if (ok) "up   " else if (state == "connecting") "...  " else "DOWN "
            lines.add(mark + host + " -> " + t.getString("target").substringAfter("://") + (if (ok) "" else "  ($state)"))
        }
        val n = tunnels.length()
        val title = when {
            n == 0 -> "No tunnels configured"
            up == n -> if (n == 1) "Tunnel up" else "All $n tunnels up"
            else -> "$up of $n tunnels up"
        }
        val text = when {
            n == 0 -> "Create a URL in the app"
            n == 1 -> lines.last().trim()
            else -> "Pull down for each tunnel's URL and state"
        }
        val big = lines.joinToString("\n")
        if (title + text + big + lastFlags() == lastShown) return  // nothing changed: do not re-post
        lastShown = title + text + big + lastFlags()
        getSystemService(NotificationManager::class.java).notify(ID, build(title, text, big.ifEmpty { null }))
    }

    private fun lastFlags(): String = MainActivity.prefs(this).all.toString()
}
