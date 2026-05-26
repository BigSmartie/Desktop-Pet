<script setup>
import { computed, ref } from 'vue';

const props = defineProps({
  state: Object,
  mcp: Object,
  backend: Object,
  companion: Object,
});

const emit = defineEmits(['pet-event', 'check-in']);
const checkInMood = ref('steady');
const checkInNote = ref('');

const activity = computed(() => props.state?.activity || 'idle');
const mood = computed(() => props.state?.mood || 'calm');
const message = computed(() => props.state?.message || 'Ready to help.');
const display = computed(() => props.state?.display || {});
const allowedEvents = computed(() => props.state?.allowed_events || []);
const canWake = computed(() => allowedEvents.value.includes('wake'));
const canSleep = computed(() => allowedEvents.value.includes('sleep'));
const canListen = computed(() => allowedEvents.value.includes('listen'));
const canRecover = computed(() => allowedEvents.value.includes('recover'));
const affinity = computed(() => props.companion?.affinity ?? 0);
const level = computed(() => props.companion?.level ?? 1);
const checkedInToday = computed(() => Boolean(props.companion?.checked_in_today));
const recentMoments = computed(() => props.companion?.recent_moments || []);
const petName = computed(() => props.companion?.pet_name || 'Maple');
const petPersona = computed(() => props.companion?.pet_persona || 'Local companion mode is ready.');

const statusLine = computed(() => {
  const activityText = display.value.label || activity.value.replaceAll('_', ' ');
  const moodText = mood.value.replaceAll('_', ' ');
  return `${activityText} / ${moodText}`;
});

const faceClass = computed(() => {
  if (activity.value === 'celebrating') return 'face-excited';
  if (activity.value === 'awaiting_approval') return 'face-careful';
  if (activity.value === 'executing') return 'face-working';
  if (activity.value === 'sleeping') return 'face-sleepy';
  if (activity.value === 'error' || mood.value === 'worried' || mood.value === 'offline') return 'face-worried';
  if (activity.value === 'thinking' || activity.value === 'planning') return 'face-thinking';
  if (activity.value === 'listening') return 'face-curious';
  if (activity.value === 'speaking' || mood.value === 'engaged') return 'face-happy';
  if (activity.value === 'reminding' || mood.value === 'warm') return 'face-warm';
  return 'face-calm';
});

const auraClass = computed(() => {
  if (activity.value === 'celebrating') return 'aura-celebrate';
  if (activity.value === 'awaiting_approval') return 'aura-approval';
  if (activity.value === 'executing') return 'aura-execute';
  if (activity.value === 'error') return 'aura-alert';
  if (activity.value === 'sleeping') return 'aura-sleep';
  if (activity.value === 'thinking' || activity.value === 'listening') return 'aura-focus';
  if (activity.value === 'reminding') return 'aura-warm';
  return 'aura-ready';
});

const mcpLine = computed(() => {
  if (!props.mcp) return 'MCP bridge loading';
  if (!props.mcp.enabled) return 'MCP bridge prepared';
  return `${props.mcp.active_tool_count || 0} MCP tools active`;
});

const backendValue = computed(() => {
  const state = props.backend?.state;
  if (!state) return 'Web';
  if (state === 'external') return 'External';
  if (state === 'running') return 'Running';
  if (state === 'starting') return 'Starting';
  if (state === 'disabled') return 'Manual';
  if (state === 'error') return 'Error';
  return state;
});

const backendLine = computed(() => {
  if (!props.backend) return 'Running in browser preview mode.';
  if (props.backend.lastError) return props.backend.lastError;
  if (props.backend.managed && props.backend.pid) {
    return `Electron is managing FastAPI on pid ${props.backend.pid}.`;
  }
  if (props.backend.state === 'external') {
    return 'FastAPI is already running outside Electron.';
  }
  return `Backend endpoint: ${props.backend.baseUrl || 'http://127.0.0.1:8000'}`;
});

const submitCheckIn = () => {
  emit('check-in', {
    mood: checkInMood.value,
    note: checkInNote.value,
  });
  checkInNote.value = '';
};
</script>

<template>
  <section class="pet-stage glass">
    <div class="pet-window-frame">
      <div class="window-dot"></div>
      <span>Desktop Pet Preview</span>
    </div>

    <div class="pet-canvas" :class="[`state-${activity}`, auraClass]">
      <div class="ambient-line line-one"></div>
      <div class="ambient-line line-two"></div>
      <div class="approval-pulse"></div>
      <div class="spark spark-one"></div>
      <div class="spark spark-two"></div>
      <div class="pet-shadow"></div>
      <div class="pet-body" :class="faceClass">
        <div class="pet-antenna"></div>
        <div class="pet-signal"></div>
        <div class="pet-face">
          <span class="eye left"></span>
          <span class="eye right"></span>
          <span class="mouth"></span>
        </div>
      </div>
      <div class="thought-ring"></div>
    </div>

    <div class="pet-status">
      <span class="label-xs">Pet State</span>
      <h1>{{ petName }}</h1>
      <p class="status-line">{{ statusLine }}</p>
      <p class="status-description">{{ display.description || 'Standing by.' }}</p>
      <p class="persona-line">{{ petPersona }}</p>
      <p class="pet-message">{{ message }}</p>
    </div>

    <div v-if="props.companion" class="companion-strip">
      <div>
        <span class="metric-value">{{ props.companion.days_together }}</span>
        <span class="metric-label">Days</span>
      </div>
      <div>
        <span class="metric-value">Lv.{{ level }}</span>
        <span class="metric-label">Bond</span>
      </div>
      <div>
        <span class="metric-value">{{ affinity }}%</span>
        <span class="metric-label">Affinity</span>
      </div>
      <div>
        <span class="metric-value">{{ props.companion.checkin_streak }}</span>
        <span class="metric-label">Streak</span>
      </div>
    </div>

    <section v-if="props.companion" class="companion-card">
      <p class="companion-greeting">{{ props.companion.greeting }}</p>
      <div class="bond-meter">
        <span :style="{ width: `${Math.min(100, affinity)}%` }"></span>
      </div>
      <div v-if="props.companion.nudges?.length" class="nudge-list">
        <p v-for="item in props.companion.nudges" :key="item">{{ item }}</p>
      </div>

      <div class="checkin-box">
        <select v-model="checkInMood" :disabled="checkedInToday">
          <option value="steady">Steady</option>
          <option value="focused">Focused</option>
          <option value="tired">Tired</option>
          <option value="curious">Curious</option>
          <option value="stuck">Stuck</option>
        </select>
        <input
          v-model="checkInNote"
          :disabled="checkedInToday"
          placeholder="Today's quick note"
          @keydown.enter.prevent="submitCheckIn"
        />
        <button class="btn-ghost compact-action" :disabled="checkedInToday" @click="submitCheckIn">
          {{ checkedInToday ? 'Saved' : 'Check in' }}
        </button>
      </div>
    </section>

    <div class="pet-actions">
      <button class="btn-primary" :disabled="!canWake" @click="emit('pet-event', 'wake')">Wake</button>
      <button class="btn-ghost" :disabled="!canListen" @click="emit('pet-event', 'listen')">Listen</button>
      <button class="btn-ghost" :disabled="!canSleep" @click="emit('pet-event', 'sleep')">Rest</button>
      <button v-if="canRecover" class="btn-ghost" @click="emit('pet-event', 'recover')">Recover</button>
    </div>

    <div class="pet-metrics">
      <div>
        <span class="metric-value">{{ props.mcp?.server_count ?? 0 }}</span>
        <span class="metric-label">Servers</span>
      </div>
      <div>
        <span class="metric-value">{{ props.mcp?.tool_count ?? 0 }}</span>
        <span class="metric-label">Tools</span>
      </div>
      <div>
        <span class="metric-value">{{ backendValue }}</span>
        <span class="metric-label">Backend</span>
      </div>
    </div>

    <p class="mcp-line">{{ mcpLine }}</p>
    <p class="mcp-line">{{ backendLine }}</p>
    <div v-if="recentMoments.length" class="moment-list">
      <span v-for="moment in recentMoments.slice(-3)" :key="`${moment.time}-${moment.type}`">
        {{ moment.type.replaceAll('_', ' ') }}
      </span>
    </div>
  </section>
</template>

<style scoped>
.pet-stage {
  width: 100%;
  min-height: 100%;
  display: flex;
  flex-direction: column;
  padding: 18px;
  overflow: hidden;
}

.pet-window-frame {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--text-muted);
  font-size: 12px;
  font-weight: 600;
  margin-bottom: 18px;
}

.window-dot {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  background: var(--accent-warm);
  box-shadow: 0 0 0 4px rgba(241, 122, 62, 0.12);
}

.pet-canvas {
  position: relative;
  min-height: 230px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-xl);
  background:
    radial-gradient(circle at 50% 92%, rgba(56, 189, 248, 0.16), transparent 28%),
    linear-gradient(180deg, rgba(255,255,255,0.65), rgba(247,250,252,0.42));
  border: 1px solid rgba(255,255,255,0.72);
}

.ambient-line {
  position: absolute;
  border-radius: 50%;
  border: 1px solid rgba(15, 118, 110, 0.12);
  pointer-events: none;
}

.line-one {
  width: 78%;
  height: 54%;
  transform: rotate(-8deg);
}

.line-two {
  width: 58%;
  height: 72%;
  transform: rotate(14deg);
}

.aura-ready {
  background:
    radial-gradient(circle at 50% 90%, rgba(56, 189, 248, 0.14), transparent 30%),
    linear-gradient(180deg, rgba(255,255,255,0.7), rgba(247,250,252,0.46));
}

.aura-focus {
  background:
    radial-gradient(circle at 50% 34%, rgba(15, 118, 110, 0.14), transparent 34%),
    linear-gradient(180deg, rgba(255,255,255,0.72), rgba(230, 252, 247, 0.54));
}

.aura-warm {
  background:
    radial-gradient(circle at 50% 90%, rgba(241, 122, 62, 0.16), transparent 32%),
    linear-gradient(180deg, rgba(255,255,255,0.7), rgba(255, 247, 237, 0.58));
}

.aura-approval {
  background:
    radial-gradient(circle at 50% 50%, rgba(241, 122, 62, 0.13), transparent 34%),
    linear-gradient(180deg, rgba(255,255,255,0.72), rgba(255, 247, 237, 0.6));
}

.aura-execute {
  background:
    radial-gradient(circle at 50% 52%, rgba(15, 118, 110, 0.2), transparent 34%),
    linear-gradient(180deg, rgba(255,255,255,0.72), rgba(220, 252, 231, 0.52));
}

.aura-celebrate {
  background:
    radial-gradient(circle at 44% 46%, rgba(241, 122, 62, 0.2), transparent 30%),
    radial-gradient(circle at 65% 70%, rgba(15, 118, 110, 0.16), transparent 30%),
    linear-gradient(180deg, rgba(255,255,255,0.75), rgba(255, 251, 235, 0.58));
}

.aura-alert {
  background:
    radial-gradient(circle at 50% 88%, rgba(241, 122, 62, 0.18), transparent 34%),
    linear-gradient(180deg, rgba(255,247,237,0.78), rgba(255, 237, 213, 0.5));
}

.aura-sleep {
  background:
    radial-gradient(circle at 50% 90%, rgba(125, 145, 164, 0.12), transparent 32%),
    linear-gradient(180deg, rgba(255,255,255,0.62), rgba(238, 242, 247, 0.52));
}

.pet-body {
  position: relative;
  width: 132px;
  height: 142px;
  border-radius: 42% 42% 36% 36%;
  background: linear-gradient(155deg, #ffffff 0%, #dff8f6 48%, #b9f0e9 100%);
  border: 1px solid rgba(20, 184, 166, 0.3);
  box-shadow: 0 18px 40px rgba(22, 124, 121, 0.18);
  animation: petFloat 3.2s ease-in-out infinite;
  z-index: 2;
}

.pet-antenna {
  position: absolute;
  top: -28px;
  left: 63px;
  width: 2px;
  height: 32px;
  background: #16a39a;
  transform-origin: bottom center;
}

.pet-antenna::after {
  content: '';
  position: absolute;
  top: -10px;
  left: -6px;
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: var(--accent-warm);
}

.pet-signal {
  position: absolute;
  top: -48px;
  left: 50%;
  width: 48px;
  height: 48px;
  border-radius: 50%;
  border: 1px solid rgba(15, 118, 110, 0.14);
  transform: translateX(-50%);
  opacity: 0;
  pointer-events: none;
}

.pet-face {
  position: absolute;
  inset: 38px 24px 34px;
  border-radius: 28px;
  background: rgba(255,255,255,0.72);
  border: 1px solid rgba(255,255,255,0.82);
}

.eye {
  position: absolute;
  top: 26px;
  width: 12px;
  height: 18px;
  border-radius: 50%;
  background: #172033;
  animation: blink 4.8s infinite;
}

.eye.left { left: 24px; }
.eye.right { right: 24px; }

.mouth {
  position: absolute;
  left: 50%;
  bottom: 20px;
  width: 28px;
  height: 12px;
  border-bottom: 3px solid #172033;
  border-radius: 0 0 20px 20px;
  transform: translateX(-50%);
}

.face-happy .mouth,
.face-warm .mouth {
  width: 34px;
  height: 15px;
  border-bottom-width: 4px;
}

.face-thinking .eye {
  height: 14px;
}

.face-thinking .mouth {
  width: 20px;
  height: 4px;
  border-bottom-width: 3px;
}

.face-working .eye {
  height: 15px;
}

.face-working .mouth {
  width: 26px;
  height: 8px;
  border-bottom-width: 3px;
  animation: workMouth 0.9s ease-in-out infinite;
}

.face-careful .eye {
  height: 12px;
}

.face-careful .mouth {
  width: 24px;
  height: 2px;
  border-bottom-width: 3px;
}

.face-excited .eye {
  height: 22px;
}

.face-excited .mouth {
  width: 36px;
  height: 18px;
  border-bottom-width: 4px;
  animation: happyBounce 0.9s ease-in-out infinite;
}

.face-curious .eye.left {
  height: 22px;
}

.face-curious .mouth {
  width: 18px;
  height: 18px;
  border: 3px solid #172033;
  border-top-width: 0;
}

.face-worried .eye {
  height: 10px;
  transform: rotate(8deg);
}

.face-worried .eye.right {
  transform: rotate(-8deg);
}

.face-worried .mouth {
  bottom: 18px;
  border-top: 3px solid #172033;
  border-bottom: 0;
  border-radius: 20px 20px 0 0;
}

.face-sleepy .eye {
  height: 2px;
  top: 34px;
  border-radius: 8px;
  animation: none;
}

.face-sleepy .mouth {
  width: 18px;
}

.pet-shadow {
  position: absolute;
  width: 124px;
  height: 22px;
  bottom: 36px;
  border-radius: 50%;
  background: rgba(39, 87, 96, 0.16);
  filter: blur(4px);
}

.thought-ring {
  position: absolute;
  width: 168px;
  height: 168px;
  border-radius: 50%;
  border: 1px dashed rgba(20, 184, 166, 0.24);
  opacity: 0;
}

.approval-pulse {
  position: absolute;
  width: 184px;
  height: 184px;
  border-radius: 50%;
  border: 1px solid rgba(241, 122, 62, 0.26);
  opacity: 0;
}

.spark {
  position: absolute;
  width: 9px;
  height: 9px;
  border-radius: 50%;
  background: var(--accent-warm);
  opacity: 0;
}

.spark-one {
  top: 52px;
  left: 54px;
}

.spark-two {
  right: 58px;
  bottom: 64px;
  background: var(--accent);
}

.state-thinking .thought-ring,
.state-planning .thought-ring,
.state-speaking .thought-ring,
.state-listening .thought-ring,
.state-reminding .thought-ring,
.state-executing .thought-ring {
  opacity: 1;
  animation: ringSpin 7s linear infinite;
}

.state-awaiting_approval .approval-pulse {
  opacity: 1;
  animation: approvalPulse 1.8s ease-in-out infinite;
}

.state-executing .pet-body {
  animation: petWork 1.1s ease-in-out infinite;
}

.state-celebrating .spark {
  opacity: 1;
  animation: sparkPop 1.2s ease-in-out infinite;
}

.state-celebrating .spark-two {
  animation-delay: 0.35s;
}

.state-celebrating .pet-body {
  box-shadow: 0 18px 40px rgba(241, 122, 62, 0.22), 0 0 0 12px rgba(241, 122, 62, 0.08);
}

.state-listening .pet-signal {
  opacity: 1;
  animation: signalPulse 1.8s ease-in-out infinite;
}

.state-speaking .mouth {
  height: 16px;
  border-bottom-width: 4px;
  animation: talkMouth 0.7s ease-in-out infinite;
}

.state-thinking .pet-antenna {
  animation: antennaThink 1.2s ease-in-out infinite;
}

.state-planning .pet-antenna,
.state-executing .pet-antenna {
  animation: antennaThink 0.9s ease-in-out infinite;
}

.state-reminding .pet-body {
  box-shadow: 0 18px 40px rgba(241, 122, 62, 0.2), 0 0 0 10px rgba(241, 122, 62, 0.08);
}

.state-error .pet-body {
  background: linear-gradient(155deg, #fff7ed, #ffd9c2);
  border-color: rgba(241, 122, 62, 0.45);
}

.state-sleeping .pet-body {
  animation-duration: 5s;
  opacity: 0.76;
}

.state-booting .pet-body {
  opacity: 0.86;
}

.pet-status {
  margin-top: 18px;
}

.pet-status h1 {
  font-size: 24px;
  line-height: 1.1;
  margin: 6px 0;
  color: var(--text-primary);
}

.status-line {
  color: var(--accent-strong);
  font-size: 13px;
  font-weight: 700;
  text-transform: capitalize;
}

.status-description {
  margin-top: 6px;
  color: var(--text-muted);
  font-size: 12px;
  line-height: 1.4;
}

.persona-line {
  margin-top: 8px;
  color: var(--text-secondary);
  font-size: 12px;
  line-height: 1.45;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.pet-message {
  margin-top: 12px;
  min-height: 72px;
  color: var(--text-secondary);
  font-size: 13px;
  line-height: 1.6;
  display: -webkit-box;
  -webkit-line-clamp: 4;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.companion-strip {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
  margin-top: 14px;
}

.companion-strip > div,
.companion-card {
  border-radius: var(--radius-md);
  background: rgba(255,255,255,0.58);
  border: 1px solid rgba(255,255,255,0.72);
}

.companion-strip > div {
  padding: 10px 8px;
}

.companion-card {
  margin-top: 10px;
  padding: 12px;
}

.companion-greeting {
  color: var(--text-secondary);
  font-size: 12px;
  line-height: 1.45;
}

.bond-meter {
  height: 7px;
  border-radius: var(--radius-pill);
  background: rgba(15, 118, 110, 0.1);
  overflow: hidden;
  margin-top: 10px;
}

.bond-meter span {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, var(--accent), var(--accent-warm));
}

.nudge-list {
  display: flex;
  flex-direction: column;
  gap: 5px;
  margin-top: 10px;
}

.nudge-list p {
  color: var(--text-muted);
  font-size: 11px;
  line-height: 1.35;
}

.checkin-box {
  display: grid;
  grid-template-columns: 88px minmax(0, 1fr) 78px;
  gap: 6px;
  margin-top: 10px;
}

.checkin-box select,
.checkin-box input {
  min-width: 0;
  height: 32px;
  border: 1px solid rgba(33, 55, 61, 0.08);
  border-radius: var(--radius-md);
  background: rgba(255,255,255,0.68);
  color: var(--text-secondary);
  font: inherit;
  font-size: 11px;
  outline: none;
  padding: 0 8px;
}

.checkin-box select:disabled,
.checkin-box input:disabled {
  opacity: 0.58;
}

.compact-action {
  height: 32px;
  padding: 0 9px;
  font-size: 11px;
  border-radius: var(--radius-md);
}

.pet-actions {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  margin-top: auto;
}

.pet-actions button {
  flex: 1;
}

.pet-metrics {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
  margin-top: 14px;
}

.pet-metrics > div {
  padding: 12px;
  border-radius: var(--radius-md);
  background: rgba(255,255,255,0.58);
  border: 1px solid rgba(255,255,255,0.72);
}

.metric-value,
.metric-label {
  display: block;
}

.metric-value {
  color: var(--text-primary);
  font-size: 15px;
  font-weight: 800;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.metric-label {
  color: var(--text-muted);
  font-size: 11px;
  margin-top: 2px;
}

.mcp-line {
  margin-top: 12px;
  color: var(--text-muted);
  font-size: 12px;
}

.moment-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 10px;
}

.moment-list span {
  max-width: 100%;
  padding: 3px 8px;
  border-radius: var(--radius-pill);
  background: rgba(15, 118, 110, 0.08);
  color: var(--accent);
  font-size: 10px;
  font-weight: 800;
  text-transform: capitalize;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

@media (max-width: 520px) {
  .companion-strip {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .checkin-box {
    grid-template-columns: 1fr;
  }
}

@keyframes petFloat {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-10px); }
}

@keyframes blink {
  0%, 92%, 100% { transform: scaleY(1); }
  95% { transform: scaleY(0.15); }
}

@keyframes ringSpin {
  to { transform: rotate(360deg); }
}

@keyframes signalPulse {
  0%, 100% { transform: translateX(-50%) scale(0.8); opacity: 0.2; }
  50% { transform: translateX(-50%) scale(1.18); opacity: 0.8; }
}

@keyframes talkMouth {
  0%, 100% { transform: translateX(-50%) scaleY(0.75); }
  50% { transform: translateX(-50%) scaleY(1.1); }
}

@keyframes antennaThink {
  0%, 100% { transform: rotate(0); }
  50% { transform: rotate(8deg); }
}

@keyframes approvalPulse {
  0%, 100% { transform: scale(0.88); opacity: 0.25; }
  50% { transform: scale(1.1); opacity: 0.8; }
}

@keyframes petWork {
  0%, 100% { transform: translateY(0) rotate(-1deg); }
  50% { transform: translateY(-6px) rotate(1deg); }
}

@keyframes sparkPop {
  0%, 100% { transform: translateY(8px) scale(0.5); opacity: 0; }
  40% { transform: translateY(-6px) scale(1); opacity: 1; }
}

@keyframes workMouth {
  0%, 100% { transform: translateX(-50%) scaleX(0.7); }
  50% { transform: translateX(-50%) scaleX(1.12); }
}

@keyframes happyBounce {
  0%, 100% { transform: translateX(-50%) scaleY(0.9); }
  50% { transform: translateX(-50%) scaleY(1.16); }
}
</style>
