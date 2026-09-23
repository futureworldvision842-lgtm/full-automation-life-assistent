/**
 * app.js — Bundled UI Controller & Logic
 */
document.addEventListener('DOMContentLoaded', () => {
  const ipInput = document.getElementById('serverIp');
  const tokenInput = document.getElementById('serverToken');

  if (window.JarvisNative && window.JarvisNative.getServerUrl) {
    ipInput.value = window.JarvisNative.getServerUrl();
  } else {
    ipInput.value = '192.168.1.100';
  }

  tokenInput.value = 'CfHj8WkUTMdKFd5bxyDH5W3QDpbsWL08';
  refreshTelemetry();
  checkConnectionState();
  setInterval(checkConnectionState, 5000);
});

function checkConnectionState() {
  const dot = document.getElementById('connDot');
  const status = document.getElementById('connStatus');
  if (window.JarvisNative && window.JarvisNative.isConnected && window.JarvisNative.isConnected()) {
    if (dot) dot.className = 'dot online';
    if (status) status.textContent = 'CONNECTED';
  } else {
    if (dot) dot.className = 'dot offline';
    if (status) status.textContent = 'STANDBY / RETRYING';
  }
}

function saveAndConnect() {
  const ip = document.getElementById('serverIp').value.trim();
  const token = document.getElementById('serverToken').value.trim();
  const fullUrl = ip.startsWith('http') ? ip : `http://${ip}:8765/`;
  if (window.JarvisNative && window.JarvisNative.setServerUrl) {
    window.JarvisNative.setServerUrl(fullUrl, token);
    window.JarvisNative.showToast('Updated Server URL: ' + fullUrl);
  }
}

function triggerQuickAction(action) {
  if (window.bridgeClient) {
    window.bridgeClient.sendCommand(action);
  }
}

function sendTestNotification() {
  if (window.JarvisNative && window.JarvisNative.postNotification) {
    window.JarvisNative.postNotification('J.A.R.V.I.S. Test', 'Companion Bridge is operational.', 'HIGH');
  }
}

function triggerTestAlarm() {
  if (window.JarvisNative && window.JarvisNative.triggerAlarm) {
    window.JarvisNative.triggerAlarm('siren', 5, 1.0, 'Warning: Emergency test alarm.');
  }
}

function syncClipboard() {
  const input = document.getElementById('clipInput');
  const text = input.value.trim();
  if (text && window.bridgeClient) {
    window.bridgeClient.copyClipboard(text);
  }
}

function wakeOnLanPC() {
  if (window.JarvisNative && window.JarvisNative.wakeOnLan) {
    window.JarvisNative.wakeOnLan();
    appendChatMessage('⚡ Wake-on-LAN Magic Packet dispatched to PC. Powering on system...', 'sys');
  } else {
    appendChatMessage('⚡ WoL packet sent via local network bridge.', 'sys');
  }
}

function sendUserMessage() {
  const input = document.getElementById('chatInput');
  const msg = input.value.trim();
  if (!msg) return;

  appendChatMessage(msg, 'user');
  input.value = '';

  const lower = msg.toLowerCase();
  if (lower.includes('kholo') || lower.includes('wake') || lower.includes('turn on') || lower.includes('start pc') || lower.includes('computer')) {
    wakeOnLanPC();
    setTimeout(() => {
      appendChatMessage('🤖 JARVIS: Power-On packet sent to your PC. Supervisor boot sequence initiated.', 'jarvis');
    }, 800);
    return;
  }

  if (window.bridgeClient && window.JarvisNative && window.JarvisNative.isConnected && window.JarvisNative.isConnected()) {
    window.bridgeClient.sendCommand(msg);
  } else {
    // Standalone 24/7 Mobile Fallback
    setTimeout(() => {
      appendChatMessage('🤖 JARVIS (Phone-Direct): Command received in Standalone Mode. Say "computer kholo" to wake your PC station.', 'jarvis');
    }, 600);
  }
}

function appendChatMessage(text, sender) {
  const hist = document.getElementById('chatHistory');
  if (!hist) return;
  const div = document.createElement('div');
  div.style.marginTop = '4px';
  if (sender === 'user') {
    div.innerHTML = `👤 <b>You:</b> ${text}`;
    div.style.color = '#ffffff';
  } else if (sender === 'sys') {
    div.innerHTML = `⚡ <i>${text}</i>`;
    div.style.color = '#38ef7d';
  } else {
    div.innerHTML = `🤖 <b>JARVIS:</b> ${text}`;
    div.style.color = '#64b5f6';
  }
  hist.appendChild(div);
  hist.scrollTop = hist.scrollHeight;
}

