package com.rel.zorek

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent

/** Starts service mode after a reboot when the "start on boot" switch is on. */
class BootReceiver : BroadcastReceiver() {
    override fun onReceive(c: Context, i: Intent) {
        if (i.action == Intent.ACTION_BOOT_COMPLETED && MainActivity.startOnBoot(c)) {
            c.startForegroundService(Intent(c, TunnelService::class.java))
        }
    }
}
