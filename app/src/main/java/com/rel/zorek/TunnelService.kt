package com.rel.zorek

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.Intent
import android.content.pm.ServiceInfo
import android.os.IBinder
import com.chaquo.python.Python
import com.chaquo.python.android.AndroidPlatform

/** Keeps the Python backend (and so every tunnel in shares.json) alive while the app is in the background. */
class TunnelService : Service() {
    override fun onBind(i: Intent?): IBinder? = null

    override fun onStartCommand(i: Intent?, flags: Int, startId: Int): Int {
        val nm = getSystemService(NotificationManager::class.java)
        nm.createNotificationChannel(NotificationChannel("tunnels", "Tunnels", NotificationManager.IMPORTANCE_LOW))
        startForeground(
            1,
            Notification.Builder(this, "tunnels").setContentTitle("Zorek").setContentText("Tunnels running")
                .setSmallIcon(android.R.drawable.stat_sys_upload).build(),
            ServiceInfo.FOREGROUND_SERVICE_TYPE_DATA_SYNC
        )
        if (!Python.isStarted()) Python.start(AndroidPlatform(this))
        Python.getInstance().getModule("zorek_backend")
            .callAttr("start", MainActivity.configFile(this).absolutePath, filesDir.absolutePath, MainActivity.importDir(this))
        return START_STICKY
    }
}
