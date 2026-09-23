# ProGuard rules for J.A.R.V.I.S. Android Companion
-keep class com.jarvis.companion.** { *; }
-keepclassmembers class * {
    @android.webkit.JavascriptInterface <methods>;
}
