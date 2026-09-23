package com.jarvis.app;

import android.annotation.SuppressLint;
import android.app.Activity;
import android.content.ComponentName;
import android.content.Context;
import android.content.Intent;
import android.content.ServiceConnection;
import android.content.SharedPreferences;
import android.os.Build;
import android.os.Bundle;
import android.os.IBinder;
import android.view.WindowManager;
import android.webkit.PermissionRequest;
import android.webkit.WebChromeClient;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;

public class MainActivity extends Activity {
    private WebView webView;
    private JarvisBridgeService bridgeService;
    private boolean isBound = false;

    private final ServiceConnection serviceConnection = new ServiceConnection() {
        @Override
        public void onServiceConnected(ComponentName className, IBinder binder) {
            JarvisBridgeService.LocalBinder localBinder = (JarvisBridgeService.LocalBinder) binder;
            bridgeService = localBinder.getService();
            isBound = true;
        }

        @Override
        public void onServiceDisconnected(ComponentName arg0) {
            bridgeService = null;
            isBound = false;
        }
    };

    @SuppressLint({"SetJavaScriptEnabled", "AddJavascriptInterface"})
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);

        // Start & bind background bridge service
        Intent serviceIntent = new Intent(this, JarvisBridgeService.class);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            startForegroundService(serviceIntent);
        } else {
            startService(serviceIntent);
        }
        bindService(serviceIntent, serviceConnection, Context.BIND_AUTO_CREATE);

        // Initialize WebView Container
        webView = new WebView(this);
        setContentView(webView);

        WebSettings settings = webView.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setDatabaseEnabled(true);
        settings.setMediaPlaybackRequiresUserGesture(false);
        settings.setLoadWithOverviewMode(true);
        settings.setUseWideViewPort(true);
        settings.setAllowFileAccess(true);
        settings.setAllowContentAccess(true);
        settings.setCacheMode(WebSettings.LOAD_DEFAULT);

        // Inject Native Bridge Interface
        webView.addJavascriptInterface(new JarvisBridgeInterface(this), "JarvisNative");

        webView.setWebViewClient(new WebViewClient() {
            @Override
            public void onReceivedError(WebView view, int errorCode, String description, String failingUrl) {
                // Fallback to local offline assets if server is unreachable
                if (!failingUrl.startsWith("file:///android_asset/")) {
                    view.loadUrl("file:///android_asset/www/index.html");
                }
            }
        });

        webView.setWebChromeClient(new WebChromeClient() {
            @Override
            public void onPermissionRequest(final PermissionRequest request) {
                request.grant(request.getResources());
            }
        });

        // Load configured server endpoint or bundled offline app
        SharedPreferences prefs = getSharedPreferences("jarvis_config", Context.MODE_PRIVATE);
        String host = prefs.getString("server_host", "192.168.1.100");
        String port = prefs.getString("server_port", "8765");
        String token = prefs.getString("token", "CfHj8WkUTMdKFd5bxyDH5W3QDpbsWL08");
        String initialUrl = "http://" + host + ":" + port + "/?token=" + token;

        webView.loadUrl(initialUrl);
    }

    public JarvisBridgeService getBridgeService() {
        return bridgeService;
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        if (isBound) {
            unbindService(serviceConnection);
            isBound = false;
        }
    }

    @Override
    public void onBackPressed() {
        if (webView != null && webView.canGoBack()) {
            webView.goBack();
        } else {
            super.onBackPressed();
        }
    }
}
