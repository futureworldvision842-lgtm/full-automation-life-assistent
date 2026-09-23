package com.jarvis.app;

import android.content.ClipData;
import android.content.ClipboardManager;
import android.content.Context;
import android.os.Handler;
import android.os.Looper;

import org.json.JSONObject;

/**
 * ClipboardSyncManager — Monitors Android primary clipboard changes
 * and synchronizes text bi-directionally with Master PC.
 */
public class ClipboardSyncManager {
    private final Context context;
    private final WebSocketClientManager wsManager;
    private final ClipboardManager clipboardManager;
    private final Handler mainHandler;
    private String lastSyncedText = "";
    private boolean isListening = false;

    public ClipboardSyncManager(Context context, WebSocketClientManager wsManager) {
        this.context = context;
        this.wsManager = wsManager;
        this.clipboardManager = (ClipboardManager) context.getSystemService(Context.CLIPBOARD_SERVICE);
        this.mainHandler = new Handler(Looper.getMainLooper());
    }

    private final ClipboardManager.OnPrimaryClipChangedListener clipListener = new ClipboardManager.OnPrimaryClipChangedListener() {
        @Override
        public void onPrimaryClipChanged() {
            if (clipboardManager != null && clipboardManager.hasPrimaryClip()) {
                ClipData clipData = clipboardManager.getPrimaryClip();
                if (clipData != null && clipData.getItemCount() > 0) {
                    CharSequence text = clipData.getItemAt(0).getText();
                    if (text != null) {
                        String current = text.toString().trim();
                        if (!current.isEmpty() && !current.equals(lastSyncedText)) {
                            lastSyncedText = current;
                            sendClipboardPushToServer(current);
                        }
                    }
                }
            }
        }
    };

    public void startListening() {
        if (isListening || clipboardManager == null) return;
        mainHandler.post(() -> {
            try {
                clipboardManager.addPrimaryClipChangedListener(clipListener);
                isListening = true;
            } catch (Exception ignored) {}
        });
    }

    public void stopListening() {
        if (!isListening || clipboardManager == null) return;
        mainHandler.post(() -> {
            try {
                clipboardManager.removePrimaryClipChangedListener(clipListener);
                isListening = false;
            } catch (Exception ignored) {}
        });
    }

    public void updateFromRemote(String remoteText) {
        if (remoteText == null || remoteText.isEmpty() || remoteText.equals(lastSyncedText)) return;
        lastSyncedText = remoteText;
        mainHandler.post(() -> {
            if (clipboardManager != null) {
                ClipData clip = ClipData.newPlainText("JARVIS_SYNC", remoteText);
                clipboardManager.setPrimaryClip(clip);
            }
        });
    }

    private void sendClipboardPushToServer(String text) {
        try {
            JSONObject json = new JSONObject();
            json.put("type", "CLIPBOARD_PUSH");
            json.put("content", text);
            json.put("timestamp", System.currentTimeMillis() / 1000.0);
            json.put("source", "android_mobile");
            wsManager.sendMessage(json.toString());
        } catch (Exception ignored) {}
    }
}
