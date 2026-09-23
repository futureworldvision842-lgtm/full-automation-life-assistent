/**
 * bridge_client.js — Mobile Client WebSocket & Native Bridge Wrapper
 */
class JarvisMobileBridge {
  constructor() {
    this.ws = null;
    this.connected = false;
    this.token = '';
    this.serverUrl = '';
  }

  init(serverUrl, token) {
    this.serverUrl = serverUrl || 'http://192.168.1.100:8765';
    this.token = token || 'CfHj8WkUTMdKFd5bxyDH5W3QDpbsWL08';
    
    if (window.JarvisNative && window.JarvisNative.setServerUrl) {
      window.JarvisNative.setServerUrl(this.serverUrl, this.token);
    }
  }

  sendCommand(cmd) {
    const payload = JSON.stringify({
      type: 'CMD_EXEC',
      id: 'cmd_' + Date.now(),
      command: cmd
    });
    if (window.JarvisNative && window.JarvisNative.sendCommand) {
      window.JarvisNative.sendCommand(payload);
    }
  }

  copyClipboard(text) {
    if (window.JarvisNative && window.JarvisNative.copyToClipboard) {
      window.JarvisNative.copyToClipboard(text);
    }
  }

  getTelemetry() {
    if (window.JarvisNative && window.JarvisNative.getTelemetryJson) {
      try {
        return JSON.parse(window.JarvisNative.getTelemetryJson());
      } catch(e) {
        return {};
      }
    }
    return {};
  }
}

window.bridgeClient = new JarvisMobileBridge();
