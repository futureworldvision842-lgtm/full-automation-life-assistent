package com.jarvis.app;

import android.content.Context;
import android.content.SharedPreferences;
import android.os.Handler;
import android.os.Looper;
import android.webkit.JavascriptInterface;
import android.widget.Toast;

import org.json.JSONObject;

/**
 * JarvisBridgeInterface — Native JavaScript Bridge
 * Injected into WebView as `window.JarvisNative`.
 */
public class JarvisBridgeInterface {
    private final Context context;
    private final MainActivity activity;
    private final Handler mainHandler;

    public JarvisBridgeInterface(MainActivity activity) {
        this.activity = activity;
        this.context = activity.getApplicationContext();
        this.mainHandler = new Handler(Looper.getMainLooper());
    }

    @JavascriptInterface
    public void postNotification(String title, String message, String priority) {
        if (activity.getBridgeService() != null) {
            activity.getBridgeService().showNotification(title, message, priority);
        }
    }

    @JavascriptInterface
    public void triggerAlarm(String tone, int durationSec, float volume, String ttsMessage) {
        if (activity.getBridgeService() != null) {
            activity.getBridgeService().playAlarm(tone, durationSec, volume, ttsMessage);
        }
    }

    @JavascriptInterface
    public void copyToClipboard(String text) {
        mainHandler.post(() -> {
            android.content.ClipboardManager cm = (android.content.ClipboardManager)
                    context.getSystemService(Context.CLIPBOARD_SERVICE);
            if (cm != null) {
                android.content.ClipData clip = android.content.ClipData.newPlainText("JARVIS", text);
                cm.setPrimaryClip(clip);
                Toast.makeText(context, "Copied to mobile clipboard", Toast.LENGTH_SHORT).show();
            }
        });
    }

    @JavascriptInterface
    public String getClipboardText() {
        android.content.ClipboardManager cm = (android.content.ClipboardManager)
                context.getSystemService(Context.CLIPBOARD_SERVICE);
        if (cm != null && cm.hasPrimaryClip() && cm.getPrimaryClip() != null) {
            if (cm.getPrimaryClip().getItemCount() > 0) {
                CharSequence text = cm.getPrimaryClip().getItemAt(0).getText();
                return text != null ? text.toString() : "";
            }
        }
        return "";
    }

    @JavascriptInterface
    public String getTelemetryJson() {
        return TelemetryReporter.collectTelemetryJson(context);
    }

    @JavascriptInterface
    public void sendCommand(String cmdJson) {
        if (activity.getBridgeService() != null) {
            activity.getBridgeService().sendWebSocketMessage(cmdJson);
        }
    }

    @JavascriptInterface
    public boolean isConnected() {
        if (activity.getBridgeService() != null) {
            return activity.getBridgeService().isWebSocketConnected();
        }
        return false;
    }

    @JavascriptInterface
    public String getServerUrl() {
        SharedPreferences prefs = context.getSharedPreferences("jarvis_config", Context.MODE_PRIVATE);
        return prefs.getString("server_url", "http://192.168.1.100:8765/");
    }

    @JavascriptInterface
    public void setServerUrl(String url, String token) {
        SharedPreferences prefs = context.getSharedPreferences("jarvis_config", Context.MODE_PRIVATE);
        prefs.edit().putString("server_url", url).putString("token", token).apply();
        if (activity.getBridgeService() != null) {
            activity.getBridgeService().reconnectWithNewConfig(url, token);
        }
    }

    @JavascriptInterface
    public void wakeOnLan() {
        WakeOnLanManager.wakeAllConfiguredAdapters();
        showToast("⚡ Wake-on-LAN Magic Packet sent to PC!");
    }

    @JavascriptInterface
    public void showToast(String message) {
        mainHandler.post(() -> Toast.makeText(context, message, Toast.LENGTH_SHORT).show());
    }
}
