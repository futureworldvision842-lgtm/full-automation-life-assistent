/**
 * avatar.js — Cybernetic Animated J.A.R.V.I.S. Arc Reactor HUD & Face
 * Interactive Canvas Avatar responding to IDLE, LISTENING, THINKING, SPEAKING states.
 */

class JarvisAvatar {
  constructor(canvasId) {
    this.canvas = document.getElementById(canvasId);
    if (!this.canvas) return;
    this.ctx = this.canvas.getContext('2d');
    this.state = 'idle'; // 'idle' | 'listening' | 'thinking' | 'speaking'
    this.audioLevel = 0.0; // 0.0 to 1.0
    this.rotationOuter = 0;
    this.rotationInner = 0;
    this.pulsePhase = 0;
    this.particles = [];
    this.numParticles = 40;
    this.lastTimestamp = performance.now();
    this.stateText = 'SYSTEM ACTIVE — STANDBY';

    this.initParticles();
    this.bindEvents();
    this.startAnimation();
  }

  initParticles() {
    this.particles = [];
    for (let i = 0; i < this.numParticles; i++) {
      this.particles.push({
        angle: (i / this.numParticles) * Math.PI * 2,
        radiusOffset: (Math.random() - 0.5) * 24,
        speed: 0.008 + Math.random() * 0.015,
        size: 1.5 + Math.random() * 2.5,
        alpha: 0.3 + Math.random() * 0.7,
        pulseSpeed: 0.03 + Math.random() * 0.04
      });
    }
  }

  bindEvents() {
    if (!this.canvas) return;
    this.canvas.addEventListener('click', () => {
      if (this.state === 'idle') {
        if (window.jarvisApp && window.jarvisApp.startVoiceInput) {
          window.jarvisApp.startVoiceInput();
        } else {
          this.setState('listening');
        }
      } else if (this.state === 'listening') {
        this.setState('thinking');
      } else if (this.state === 'thinking') {
        this.setState('speaking');
      } else {
        this.setState('idle');
      }
    });
  }

  setState(newState) {
    const validStates = ['idle', 'listening', 'thinking', 'speaking'];
    if (!validStates.includes(newState)) return;
    this.state = newState;

    const labelEl = document.getElementById('avatarStateText');
    switch (this.state) {
      case 'idle':
        this.stateText = 'SYSTEM ACTIVE — STANDBY';
        if (labelEl) labelEl.textContent = '🟢 IDLE / LISTENING FOR "COMPUTER"';
        break;
      case 'listening':
        this.stateText = 'AUDIO INGESTION — AURA ACTIVE';
        if (labelEl) labelEl.textContent = '🎙️ LISTENING... (Urdu / English)';
        break;
      case 'thinking':
        this.stateText = 'NEURAL QUANTUM REASONING';
        if (labelEl) labelEl.textContent = '⚡ THINKING / REASONING...';
        break;
      case 'speaking':
        this.stateText = 'SYNTHESIS AUDIO BROADCAST';
        if (labelEl) labelEl.textContent = '🔊 J.A.R.V.I.S. SPEAKING...';
        break;
    }
  }

  getState() {
    return this.state;
  }

  setAudioLevel(level) {
    this.audioLevel = Math.max(0, Math.min(1.0, level));
  }

  startAnimation() {
    const animate = (timestamp) => {
      const dt = Math.min((timestamp - this.lastTimestamp) / 1000, 0.1);
      this.lastTimestamp = timestamp;
      this.update(dt);
      this.render();
      requestAnimationFrame(animate);
    };
    requestAnimationFrame(animate);
  }

  update(dt) {
    this.pulsePhase += dt * (this.state === 'thinking' ? 6 : (this.state === 'speaking' ? 4.5 : 2.0));

    // Rotation speeds based on state
    let outerSpeed = 0.4;
    let innerSpeed = -0.6;
    if (this.state === 'thinking') {
      outerSpeed = 2.4;
      innerSpeed = -3.2;
    } else if (this.state === 'listening') {
      outerSpeed = 0.8;
      innerSpeed = -1.2;
    } else if (this.state === 'speaking') {
      outerSpeed = 1.0;
      innerSpeed = -1.5;
    }

    this.rotationOuter += outerSpeed * dt;
    this.rotationInner += innerSpeed * dt;

    // Update particle constellation
    for (let p of this.particles) {
      p.angle += p.speed * (this.state === 'thinking' ? 3.0 : 1.0);
      p.alpha = 0.4 + 0.4 * Math.sin(this.pulsePhase * p.pulseSpeed * 10);
    }
  }

  render() {
    const ctx = this.ctx;
    const w = this.canvas.width;
    const h = this.canvas.height;
    const cx = w / 2;
    const cy = h / 2;
    const baseRadius = Math.min(cx, cy) * 0.72;

    ctx.clearRect(0, 0, w, h);

    // Color palettes per state
    let primary = '#00F0FF';
    let secondary = '#0088FF';
    let glow = 'rgba(0, 240, 255, ';
    if (this.state === 'thinking') {
      primary = '#FFB800';
      secondary = '#FF6600';
      glow = 'rgba(255, 184, 0, ';
    } else if (this.state === 'listening') {
      primary = '#00FFCC';
      secondary = '#00AAFF';
      glow = 'rgba(0, 255, 204, ';
    } else if (this.state === 'speaking') {
      primary = '#00FF88';
      secondary = '#00F0FF';
      glow = 'rgba(0, 255, 136, ';
    }

    // 1. Outer Holographic Ambient Glow
    const pulseMod = Math.sin(this.pulsePhase) * 0.08 + (this.audioLevel * 0.2);
    const grad = ctx.createRadialGradient(cx, cy, baseRadius * 0.2, cx, cy, baseRadius * 1.35);
    grad.addColorStop(0, glow + '0.25)');
    grad.addColorStop(0.5, glow + '0.08)');
    grad.addColorStop(1, 'rgba(3, 8, 17, 0)');
    ctx.fillStyle = grad;
    ctx.beginPath();
    ctx.arc(cx, cy, baseRadius * 1.35, 0, Math.PI * 2);
    ctx.fill();

    // 2. Outer Rotating Degree Ring & Ticks
    ctx.save();
    ctx.translate(cx, cy);
    ctx.rotate(this.rotationOuter);
    ctx.strokeStyle = glow + '0.35)';
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.arc(0, 0, baseRadius, 0, Math.PI * 2);
    ctx.stroke();

    // Outer ticks
    const tickCount = 36;
    for (let i = 0; i < tickCount; i++) {
      const angle = (i / tickCount) * Math.PI * 2;
      const isMajor = i % 4 === 0;
      const r1 = baseRadius;
      const r2 = baseRadius + (isMajor ? 8 : 4);
      ctx.beginPath();
      ctx.strokeStyle = isMajor ? primary : glow + '0.4)';
      ctx.lineWidth = isMajor ? 2.0 : 1.0;
      ctx.moveTo(Math.cos(angle) * r1, Math.sin(angle) * r1);
      ctx.lineTo(Math.cos(angle) * r2, Math.sin(angle) * r2);
      ctx.stroke();
    }
    ctx.restore();

    // 3. Middle Segmented Reactor Ring (Counter-Rotating)
    ctx.save();
    ctx.translate(cx, cy);
    ctx.rotate(this.rotationInner);
    const midRadius = baseRadius * 0.78;
    const segments = 6;
    const segSpan = (Math.PI * 2) / segments;
    ctx.lineWidth = 3.5;
    for (let s = 0; s < segments; s++) {
      ctx.beginPath();
      ctx.strokeStyle = (s % 2 === 0) ? primary : secondary;
      ctx.arc(0, 0, midRadius, s * segSpan + 0.12, (s + 1) * segSpan - 0.12);
      ctx.stroke();
    }
    ctx.restore();

    // 4. Particle Constellation Aura
    for (let p of this.particles) {
      const pr = baseRadius * 0.88 + p.radiusOffset;
      const px = cx + Math.cos(p.angle) * pr;
      const py = cy + Math.sin(p.angle) * pr;
      ctx.beginPath();
      ctx.fillStyle = glow + p.alpha + ')';
      ctx.arc(px, py, p.size, 0, Math.PI * 2);
      ctx.fill();
    }

    // 5. Dynamic Audio Wave / Harmonic Frequency Visualizer
    ctx.save();
    ctx.translate(cx, cy);
    const waveRadius = baseRadius * 0.52;
    const wavePoints = 48;
    ctx.beginPath();
    ctx.strokeStyle = primary;
    ctx.lineWidth = 2.0;

    const waveAmp = (this.state === 'speaking' || this.state === 'listening')
      ? (12 + this.audioLevel * 28)
      : (4 + Math.sin(this.pulsePhase * 2) * 3);

    for (let i = 0; i <= wavePoints; i++) {
      const a = (i / wavePoints) * Math.PI * 2;
      const harmonic = Math.sin(a * 6 + this.pulsePhase * 3) * Math.cos(a * 3 - this.pulsePhase);
      const r = waveRadius + harmonic * waveAmp;
      const wx = Math.cos(a) * r;
      const wy = Math.sin(a) * r;
      if (i === 0) ctx.moveTo(wx, wy);
      else ctx.lineTo(wx, wy);
    }
    ctx.closePath();
    ctx.stroke();
    ctx.restore();

    // 6. Cybernetic Inner Core / Arc Reactor Heart
    const coreRadius = baseRadius * (0.32 + pulseMod);
    const coreGrad = ctx.createRadialGradient(cx, cy, coreRadius * 0.1, cx, cy, coreRadius);
    coreGrad.addColorStop(0, '#FFFFFF');
    coreGrad.addColorStop(0.3, primary);
    coreGrad.addColorStop(0.8, secondary);
    coreGrad.addColorStop(1, glow + '0.1)');

    ctx.fillStyle = coreGrad;
    ctx.beginPath();
    ctx.arc(cx, cy, coreRadius, 0, Math.PI * 2);
    ctx.fill();

    // Core border
    ctx.strokeStyle = '#FFFFFF';
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.arc(cx, cy, coreRadius * 0.4, 0, Math.PI * 2);
    ctx.stroke();

    // Central Triangular Arc Reactor Emblem
    ctx.save();
    ctx.translate(cx, cy);
    ctx.rotate(this.pulsePhase * 0.5);
    ctx.strokeStyle = '#FFFFFF';
    ctx.lineWidth = 1.8;
    const triR = coreRadius * 0.55;
    ctx.beginPath();
    for (let t = 0; t < 3; t++) {
      const ta = (t * 2 * Math.PI / 3) - Math.PI / 2;
      const tx = Math.cos(ta) * triR;
      const ty = Math.sin(ta) * triR;
      if (t === 0) ctx.moveTo(tx, ty);
      else ctx.lineTo(tx, ty);
    }
    ctx.closePath();
    ctx.stroke();
    ctx.restore();
  }
}

window.JarvisAvatar = JarvisAvatar;
