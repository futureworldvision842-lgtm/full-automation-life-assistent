package com.jarvis.companion;

import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.net.ConnectivityManager;
import android.net.NetworkCapabilities;
import android.net.NetworkInfo;
import android.net.wifi.WifiInfo;
import android.net.wifi.WifiManager;
import android.os.BatteryManager;
import android.os.Build;
import android.os.PowerManager;

import org.json.JSONObject;

/**
 * TelemetryReporter — Gathers live device health, battery status, Wi-Fi RSSI,
 * network link quality, and screen state.
 */
public class TelemetryReporter {

    public static JSONObject collectTelemetry(Context context) {
        JSONObject json = new JSONObject();
        try {
            // 1. Battery Information
            IntentFilter ifilter = new IntentFilter(Intent.ACTION_BATTERY_CHANGED);
            Intent batteryStatus = context.registerReceiver(null, ifilter);
            int level = -1;
            int scale = -1;
            boolean isCharging = false;
            if (batteryStatus != null) {
                level = batteryStatus.getIntExtra(BatteryManager.EXTRA_LEVEL, -1);
                scale = batteryStatus.getIntExtra(BatteryManager.EXTRA_SCALE, -1);
                int status = batteryStatus.getIntExtra(BatteryManager.EXTRA_STATUS, -1);
                isCharging = (status == BatteryManager.BATTERY_STATUS_CHARGING ||
                              status == BatteryManager.BATTERY_STATUS_FULL);
            }
            float batteryPct = (level >= 0 && scale > 0) ? ((float) level / (float) scale) * 100.0f : 100.0f;
            json.put("battery_level", Math.round(batteryPct));
            json.put("is_charging", isCharging);

            // 2. Network Connectivity & Wi-Fi RSSI
            ConnectivityManager cm = (ConnectivityManager) context.getSystemService(Context.CONNECTIVITY_SERVICE);
            String networkType = "UNKNOWN";
            int wifiRssi = -50;
            String wifiSsid = "UNKNOWN";

            if (cm != null) {
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
                    android.net.Network activeNet = cm.getActiveNetwork();
                    if (activeNet != null) {
                        NetworkCapabilities caps = cm.getNetworkCapabilities(activeNet);
                        if (caps != null) {
                            if (caps.hasTransport(NetworkCapabilities.TRANSPORT_WIFI)) {
                                networkType = "WIFI";
                            } else if (caps.hasTransport(NetworkCapabilities.TRANSPORT_CELLULAR)) {
                                networkType = "CELLULAR";
                            } else if (caps.hasTransport(NetworkCapabilities.TRANSPORT_ETHERNET)) {
                                networkType = "ETHERNET";
                            }
                        }
                    }
                } else {
                    NetworkInfo info = cm.getActiveNetworkInfo();
                    if (info != null && info.isConnected()) {
                        networkType = info.getTypeName();
                    }
                }
            }

            if ("WIFI".equals(networkType)) {
                WifiManager wm = (WifiManager) context.getApplicationContext().getSystemService(Context.WIFI_SERVICE);
                if (wm != null) {
                    WifiInfo wifiInfo = wm.getConnectionInfo();
                    if (wifiInfo != null) {
                        wifiRssi = wifiInfo.getRssi();
                        wifiSsid = wifiInfo.getSSID() != null ? wifiInfo.getSSID().replace("\"", "") : "WIFI";
                    }
                }
            }

            json.put("network_type", networkType);
            json.put("wifi_ssid", wifiSsid);
            json.put("wifi_rssi_dbm", wifiRssi);

            // 3. Screen State
            PowerManager pm = (PowerManager) context.getSystemService(Context.POWER_SERVICE);
            boolean isScreenOn = pm != null && (Build.VERSION.SDK_INT >= Build.VERSION_CODES.KITKAT_WATCH ?
                    pm.isInteractive() : pm.isScreenOn());
            json.put("screen_on", isScreenOn);

            // 4. Device Meta
            json.put("device_model", Build.MANUFACTURER + " " + Build.MODEL);
            json.put("android_version", Build.VERSION.RELEASE);
            json.put("api_level", Build.VERSION.SDK_INT);
            json.put("timestamp", System.currentTimeMillis() / 1000.0);

        } catch (Exception e) {
            try {
                json.put("error", e.getMessage());
            } catch (Exception ignored) {}
        }
        return json;
    }

    public static String collectTelemetryJson(Context context) {
        return collectTelemetry(context).toString();
    }
}
