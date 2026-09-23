package com.jarvis.app;

import android.content.Context;
import android.util.Log;
import java.net.DatagramPacket;
import java.net.DatagramSocket;
import java.net.InetAddress;

/**
 * WakeOnLanManager.java — Autonomous Remote PC Power-On & Wake-on-LAN Dispatcher.
 * Allows the J.A.R.V.I.S. Mobile Companion App to wake up and power on the PC remotely
 * even when the PC is completely shut down or asleep.
 */
public class WakeOnLanManager {
    private static final String TAG = "JarvisWoL";
    private static final int WOL_PORT = 9;

    // Configured MAC addresses for host PC (Wi-Fi and Ethernet adapters)
    public static final String DEFAULT_WIFI_MAC = "E8:B1:FC:0E:51:32";
    public static final String DEFAULT_ETH_MAC = "54:EE:75:2C:AC:86";
    public static final String DEFAULT_BROADCAST_IP = "192.168.100.255";

    public static boolean sendWakeOnLan(String macAddress, String broadcastIp) {
        try {
            if (macAddress == null || macAddress.trim().isEmpty()) {
                macAddress = DEFAULT_WIFI_MAC;
            }
            if (broadcastIp == null || broadcastIp.trim().isEmpty()) {
                broadcastIp = DEFAULT_BROADCAST_IP;
            }

            byte[] macBytes = getMacBytes(macAddress);
            byte[] bytes = new byte[6 + 16 * macBytes.length];
            for (int i = 0; i < 6; i++) {
                bytes[i] = (byte) 0xFF;
            }
            for (int i = 6; i < bytes.length; i += macBytes.length) {
                System.arraycopy(macBytes, 0, bytes, i, macBytes.length);
            }

            InetAddress address = InetAddress.getByName(broadcastIp);
            DatagramPacket packet = new DatagramPacket(bytes, bytes.length, address, WOL_PORT);
            
            DatagramSocket socket = new DatagramSocket();
            socket.setBroadcast(true);
            socket.send(packet);
            socket.close();

            Log.i(TAG, "✅ Wake-on-LAN Magic Packet sent successfully to " + macAddress + " via " + broadcastIp);

            // Also broadcast to 255.255.255.255 for global subnet coverage
            try {
                InetAddress globalBroadcast = InetAddress.getByName("255.255.255.255");
                DatagramPacket globalPacket = new DatagramPacket(bytes, bytes.length, globalBroadcast, WOL_PORT);
                DatagramSocket globalSocket = new DatagramSocket();
                globalSocket.setBroadcast(true);
                globalSocket.send(globalPacket);
                globalSocket.close();
            } catch (Exception e) {
                Log.d(TAG, "Global broadcast packet notice: " + e.getMessage());
            }

            return true;
        } catch (Exception e) {
            Log.e(TAG, "[-] Failed to send Wake-on-LAN packet: " + e.getMessage(), e);
            return false;
        }
    }

    public static void wakeAllConfiguredAdapters() {
        new Thread(new Runnable() {
            @Override
            public void run() {
                sendWakeOnLan(DEFAULT_WIFI_MAC, DEFAULT_BROADCAST_IP);
                sendWakeOnLan(DEFAULT_ETH_MAC, DEFAULT_BROADCAST_IP);
            }
        }).start();
    }

    private static byte[] getMacBytes(String macStr) throws IllegalArgumentException {
        String[] hex = macStr.split("(\\:|\\-)");
        if (hex.length != 6) {
            throw new IllegalArgumentException("Invalid MAC address length: " + macStr);
        }
        byte[] bytes = new byte[6];
        for (int i = 0; i < 6; i++) {
            bytes[i] = (byte) Integer.parseInt(hex[i], 16);
        }
        return bytes;
    }
}
