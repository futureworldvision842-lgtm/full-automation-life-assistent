package com.jarvis.app;

import android.content.Context;
import android.os.Handler;
import android.os.Looper;

import org.json.JSONObject;

import java.util.concurrent.TimeUnit;

import okhttp3.OkHttpClient;
import okhttp3.Request;
import okhttp3.Response;
import okhttp3.WebSocket;
import okhttp3.WebSocketListener;

/**
 * WebSocketClientManager — Low-latency OkHttp WebSocket client
 * with auto-reconnect backoff, token handshake, and packet routing.
 */
public class WebSocketClientManager {
    public interface MessageListener {
        void onAuthenticated();
        void onNotification(String title, String body, String priority, String channelId);
        void onAlarm(String tone, int durationSec, float volume, String ttsMessage);
        void onClipboardPush(String content);
        void onCommandResult(String output, boolean ok);
        void onConnectionStateChanged(boolean connected);
    }

    private final Context context;
    private final MessageListener listener;
    private final Handler handler;
    private OkHttpClient httpClient;
    private WebSocket webSocket;
    private String serverWsUrl;
    private String authToken;
    private boolean isConnected = false;
    private boolean isAuthenticated = false;
    private int reconnectAttempts = 0;
    private boolean isClosedIntentionally = false;

    public WebSocketClientManager(Context context, String serverWsUrl, String authToken, MessageListener listener) {
        this.context = context;
        this.serverWsUrl = serverWsUrl;
        this.authToken = authToken;
        this.listener = listener;
        this.handler = new Handler(Looper.getMainLooper());
        initHttpClient();
    }

    private void initHttpClient() {
        this.httpClient = new OkHttpClient.Builder()
                .pingInterval(15, TimeUnit.SECONDS)
                .connectTimeout(10, TimeUnit.SECONDS)
                .readTimeout(0, TimeUnit.MILLISECONDS)
                .retryOnConnectionFailure(true)
                .build();
    }

    public synchronized void connect() {
        isClosedIntentionally = false;
        if (webSocket != null) {
            webSocket.close(1000, "Reconnecting");
            webSocket = null;
        }

        String targetUrl = serverWsUrl;
        if (!targetUrl.contains("token=") && authToken != null && !authToken.isEmpty()) {
            targetUrl += (targetUrl.contains("?") ? "&" : "?") + "token=" + authToken;
        }

        Request request = new Request.Builder()
                .url(targetUrl)
                .build();

        webSocket = httpClient.newWebSocket(request, new WebSocketListener() {
            @Override
            public void onOpen(WebSocket ws, Response response) {
                isConnected = true;
                reconnectAttempts = 0;
                notifyStateChanged(true);
                sendAuthHandshake();
            }

            @Override
            public void onMessage(WebSocket ws, String text) {
                handleIncomingMessage(text);
            }

            @Override
            public void onClosing(WebSocket ws, int code, String reason) {
                ws.close(1000, null);
            }

            @Override
            public void onClosed(WebSocket ws, int code, String reason) {
                isConnected = false;
                isAuthenticated = false;
                notifyStateChanged(false);
                scheduleReconnect();
            }

            @Override
            public void onFailure(WebSocket ws, Throwable t, Response response) {
                isConnected = false;
                isAuthenticated = false;
                notifyStateChanged(false);
                scheduleReconnect();
            }
        });
    }

    public synchronized void disconnect() {
        isClosedIntentionally = true;
        if (webSocket != null) {
            webSocket.close(1000, "App closed");
            webSocket = null;
        }
        isConnected = false;
        isAuthenticated = false;
        notifyStateChanged(false);
    }

    public boolean sendMessage(String jsonText) {
        if (webSocket != null && isConnected) {
            return webSocket.send(jsonText);
        }
        return false;
    }

    private void sendAuthHandshake() {
        try {
            JSONObject auth = new JSONObject();
            auth.put("type", "AUTH");
            auth.put("token", authToken);
            JSONObject dev = new JSONObject();
            dev.put("model", android.os.Build.MODEL);
            dev.put("os", "Android " + android.os.Build.VERSION.RELEASE);
            dev.put("app_version", "2.5.0");
            dev.put("client_type", "native_apk");
            auth.put("device_info", dev);
            sendMessage(auth.toString());
        } catch (Exception ignored) {}
    }

    private void handleIncomingMessage(String text) {
        try {
            JSONObject json = new JSONObject(text);
            String type = json.optString("type", "").toUpperCase();

            if ("AUTH_OK".equals(type)) {
                isAuthenticated = true;
                handler.post(listener::onAuthenticated);
            } else if ("PUSH_NOTIFICATION".equals(type)) {
                String title = json.optString("title", "J.A.R.V.I.S. Alert");
                String body = json.optString("body", "");
                String priority = json.optString("priority", "HIGH");
                String channelId = json.optString("channel_id", "jarvis_general");
                handler.post(() -> listener.onNotification(title, body, priority, channelId));
            } else if ("AUDIO_ALARM".equals(type)) {
                String tone = json.optString("tone", "defcon_siren");
                int duration = json.optInt("duration_sec", 10);
                float volume = (float) json.optDouble("volume", 1.0);
                String tts = json.optString("tts_message", "");
                handler.post(() -> listener.onAlarm(tone, duration, volume, tts));
            } else if ("CLIPBOARD_PUSH".equals(type)) {
                String content = json.optString("content", "");
                handler.post(() -> listener.onClipboardPush(content));
            } else if ("CMD_RESULT".equals(type)) {
                String output = json.optString("output", "");
                boolean ok = json.optBoolean("ok", true);
                handler.post(() -> listener.onCommandResult(output, ok));
            }
        } catch (Exception ignored) {}
    }

    private void scheduleReconnect() {
        if (isClosedIntentionally) return;
        reconnectAttempts++;
        long delay = Math.min(30000, (long) Math.pow(2, Math.min(reconnectAttempts, 5)) * 1000);
        handler.postDelayed(this::connect, delay);
    }

    private void notifyStateChanged(boolean connected) {
        handler.post(() -> listener.onConnectionStateChanged(connected));
    }

    public void updateConfig(String newUrl, String newToken) {
        this.serverWsUrl = newUrl;
        this.authToken = newToken;
        connect();
    }

    public boolean isConnected() {
        return isConnected;
    }

    public boolean isAuthenticated() {
        return isAuthenticated;
    }
}
