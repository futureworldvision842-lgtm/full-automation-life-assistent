package com.jarvis.app;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.media.AudioAttributes;
import android.media.AudioManager;
import android.media.MediaPlayer;
import android.media.RingtoneManager;
import android.net.Uri;
import android.os.Binder;
import android.os.Build;
import android.os.Handler;
import android.os.IBinder;
import android.os.Looper;
import android.os.PowerManager;
import android.speech.tts.TextToSpeech;

import androidx.core.app.NotificationCompat;

import org.json.JSONObject;

import java.util.Locale;

/**
 * JarvisBridgeService — Android Foreground Service maintaining persistent
 * bi-directional communication, push notifications, siren/alarm playback,
 * clipboard sync, and periodic telemetry streaming.
 */
public class JarvisBridgeService extends Service implements WebSocketClientManager.MessageListener {

    public class LocalBinder extends Binder {
        public JarvisBridgeService getService() {
            return JarvisBridgeService.this;
        }
    }

    private final IBinder binder = new LocalBinder();
    private static final int FOREGROUND_NOTIFICATION_ID = 84201;
    public static final String CHANNEL_CRITICAL = "jarvis_critical";
    public static final String CHANNEL_GENERAL = "jarvis_general";
    public static final String CHANNEL_FOREGROUND = "jarvis_foreground";

    private WebSocketClientManager wsManager;
    private ClipboardSyncManager clipManager;
    private NotificationManager notificationManager;
    private TextToSpeech tts;
    private MediaPlayer alarmPlayer;
    private Handler telemetryHandler;
    private PowerManager.WakeLock wakeLock;
    private boolean isTtsReady = false;

    @Override
    public void onCreate() {
        super.onCreate();
        notificationManager = (NotificationManager) getSystemService(Context.NOTIFICATION_SERVICE);
        createNotificationChannels();
        startForeground(FOREGROUND_NOTIFICATION_ID, buildForegroundNotification("Connecting to JARVIS..."));

        initWakeLock();
        initTextToSpeech();

        SharedPreferences prefs = getSharedPreferences("jarvis_config", Context.MODE_PRIVATE);
        String host = prefs.getString("server_host", "192.168.1.100");
        String port = prefs.getString("server_port", "8765");
        String token = prefs.getString("token", "CfHj8WkUTMdKFd5bxyDH5W3QDpbsWL08");
        String wsUrl = "ws://" + host + ":" + port + "/ws/mobile?token=" + token;

        wsManager = new WebSocketClientManager(this, wsUrl, token, this);
        clipManager = new ClipboardSyncManager(this, wsManager);

        wsManager.connect();
        clipManager.startListening();

        startTelemetryLoop();
    }

    private void initWakeLock() {
        try {
            PowerManager pm = (PowerManager) getSystemService(Context.POWER_SERVICE);
            if (pm != null) {
                wakeLock = pm.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "JARVIS:BridgeServiceWakeLock");
                wakeLock.acquire(10 * 60 * 1000L); // 10 min auto release safety
            }
        } catch (Exception ignored) {}
    }

    private void initTextToSpeech() {
        tts = new TextToSpeech(this, status -> {
            if (status == TextToSpeech.SUCCESS) {
                tts.setLanguage(Locale.US);
                isTtsReady = true;
            }
        });
    }

    private void createNotificationChannels() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O && notificationManager != null) {
            // Foreground ongoing service channel
            NotificationChannel fgChannel = new NotificationChannel(
                    CHANNEL_FOREGROUND,
                    "JARVIS Bridge Status",
                    NotificationManager.IMPORTANCE_LOW
            );
            fgChannel.setDescription("Persistent service state");
            notificationManager.createNotificationChannel(fgChannel);

            // Critical alerts & sirens channel
            NotificationChannel critChannel = new NotificationChannel(
                    CHANNEL_CRITICAL,
                    "JARVIS Critical Alerts",
                    NotificationManager.IMPORTANCE_HIGH
            );
            critChannel.setDescription("Trading, DEFCON, and Workstation critical notifications");
            critChannel.enableVibration(true);
            critChannel.setVibrationPattern(new long[]{0, 300, 150, 300});
            notificationManager.createNotificationChannel(critChannel);

            // General telemetry channel
            NotificationChannel genChannel = new NotificationChannel(
                    CHANNEL_GENERAL,
                    "JARVIS General",
                    NotificationManager.IMPORTANCE_DEFAULT
            );
            genChannel.setDescription("Standard updates and clipboard sync");
            notificationManager.createNotificationChannel(genChannel);
        }
    }

    private Notification buildForegroundNotification(String statusText) {
        Intent launchIntent = new Intent(this, MainActivity.class);
        PendingIntent pendingIntent = PendingIntent.getActivity(
                this, 0, launchIntent,
                PendingIntent.FLAG_UPDATE_CURRENT | (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M ? PendingIntent.FLAG_IMMUTABLE : 0)
        );

        return new NotificationCompat.Builder(this, CHANNEL_FOREGROUND)
                .setContentTitle("J.A.R.V.I.S. Bridge Service")
                .setContentText(statusText)
                .setSmallIcon(R.drawable.ic_stat_jarvis)
                .setContentIntent(pendingIntent)
                .setOngoing(true)
                .setPriority(NotificationCompat.PRIORITY_LOW)
                .build();
    }

    private void startTelemetryLoop() {
        telemetryHandler = new Handler(Looper.getMainLooper());
        Runnable telemetryRunnable = new Runnable() {
            @Override
            public void run() {
                if (wsManager != null && wsManager.isConnected()) {
                    try {
                        JSONObject envelope = new JSONObject();
                        envelope.put("type", "MOBILE_TELEMETRY");
                        envelope.put("payload", TelemetryReporter.collectTelemetry(JarvisBridgeService.this));
                        envelope.put("timestamp", System.currentTimeMillis() / 1000.0);
                        wsManager.sendMessage(envelope.toString());
                    } catch (Exception ignored) {}
                }
                telemetryHandler.postDelayed(this, 15000); // Every 15 seconds
            }
        };
        telemetryHandler.postDelayed(telemetryRunnable, 5000);
    }

    public void showNotification(String title, String message, String priority) {
        String channelId = "HIGH".equalsIgnoreCase(priority) ? CHANNEL_CRITICAL : CHANNEL_GENERAL;
        int notifPriority = "HIGH".equalsIgnoreCase(priority) ?
                NotificationCompat.PRIORITY_HIGH : NotificationCompat.PRIORITY_DEFAULT;

        Intent intent = new Intent(this, MainActivity.class);
        PendingIntent pendingIntent = PendingIntent.getActivity(
                this, (int) System.currentTimeMillis(), intent,
                PendingIntent.FLAG_UPDATE_CURRENT | (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M ? PendingIntent.FLAG_IMMUTABLE : 0)
        );

        Notification notif = new NotificationCompat.Builder(this, channelId)
                .setContentTitle(title)
                .setContentText(message)
                .setStyle(new NotificationCompat.BigTextStyle().bigText(message))
                .setSmallIcon(R.drawable.ic_stat_jarvis)
                .setPriority(notifPriority)
                .setAutoCancel(true)
                .setContentIntent(pendingIntent)
                .build();

        if (notificationManager != null) {
            notificationManager.notify((int) (System.currentTimeMillis() % 100000), notif);
        }
    }

    public void playAlarm(String tone, int durationSec, float volume, String ttsMessage) {
        try {
            if (alarmPlayer != null) {
                alarmPlayer.stop();
                alarmPlayer.release();
                alarmPlayer = null;
            }

            Uri alarmUri = RingtoneManager.getDefaultUri(RingtoneManager.TYPE_ALARM);
            if (alarmUri == null) {
                alarmUri = RingtoneManager.getDefaultUri(RingtoneManager.TYPE_NOTIFICATION);
            }

            alarmPlayer = new MediaPlayer();
            alarmPlayer.setDataSource(this, alarmUri);
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {
                alarmPlayer.setAudioAttributes(new AudioAttributes.Builder()
                        .setUsage(AudioAttributes.USAGE_ALARM)
                        .setContentType(AudioAttributes.CONTENT_TYPE_SONIFICATION)
                        .build());
            } else {
                alarmPlayer.setAudioStreamType(AudioManager.STREAM_ALARM);
            }
            alarmPlayer.setVolume(volume, volume);
            alarmPlayer.setLooping(true);
            alarmPlayer.prepare();
            alarmPlayer.start();

            // Auto stop after duration
            new Handler(Looper.getMainLooper()).postDelayed(() -> {
                try {
                    if (alarmPlayer != null && alarmPlayer.isPlaying()) {
                        alarmPlayer.stop();
                        alarmPlayer.release();
                        alarmPlayer = null;
                    }
                } catch (Exception ignored) {}
            }, durationSec * 1000L);

            // Optional Voice / TTS speech
            if (isTtsReady && ttsMessage != null && !ttsMessage.isEmpty()) {
                tts.speak(ttsMessage, TextToSpeech.QUEUE_FLUSH, null, "jarvis_alarm_tts");
            }
        } catch (Exception ignored) {}
    }

    public void sendWebSocketMessage(String json) {
        if (wsManager != null) {
            wsManager.sendMessage(json);
        }
    }

    public boolean isWebSocketConnected() {
        return wsManager != null && wsManager.isConnected();
    }

    public void reconnectWithNewConfig(String host, String token) {
        if (wsManager != null) {
            String wsUrl = host.replace("http://", "ws://").replace("https://", "wss://");
            if (!wsUrl.endsWith("/ws/mobile")) {
                wsUrl = wsUrl.replaceAll("/+$", "") + "/ws/mobile";
            }
            wsManager.updateConfig(wsUrl, token);
        }
    }

    // MessageListener Callbacks
    @Override
    public void onAuthenticated() {
        updateForegroundStatus("Connected to Master Station (Online)");
    }

    @Override
    public void onNotification(String title, String body, String priority, String channelId) {
        showNotification(title, body, priority);
    }

    @Override
    public void onAlarm(String tone, int durationSec, float volume, String ttsMessage) {
        playAlarm(tone, durationSec, volume, ttsMessage);
    }

    @Override
    public void onClipboardPush(String content) {
        if (clipManager != null) {
            clipManager.updateFromRemote(content);
        }
    }

    @Override
    public void onCommandResult(String output, boolean ok) {}

    @Override
    public void onConnectionStateChanged(boolean connected) {
        updateForegroundStatus(connected ? "Bridge Online" : "Reconnecting to Station...");
    }

    private void updateForegroundStatus(String text) {
        Notification notif = buildForegroundNotification(text);
        if (notificationManager != null) {
            notificationManager.notify(FOREGROUND_NOTIFICATION_ID, notif);
        }
    }

    @Override
    public IBinder onBind(Intent intent) {
        return binder;
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        return START_STICKY;
    }

    @Override
    public void onDestroy() {
        super.onDestroy();
        if (telemetryHandler != null) {
            telemetryHandler.removeCallbacksAndMessages(null);
        }
        if (clipManager != null) {
            clipManager.stopListening();
        }
        if (wsManager != null) {
            wsManager.disconnect();
        }
        if (alarmPlayer != null) {
            alarmPlayer.release();
        }
        if (tts != null) {
            tts.shutdown();
        }
        if (wakeLock != null && wakeLock.isHeld()) {
            wakeLock.release();
        }
    }
}
