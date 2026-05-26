<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue';
import { getCompanionSummary, getPetState, sendPetEvent } from '../api';

const petState = ref(null);
const companion = ref(null);
let timer = null;

const refreshPetState = async () => {
  try {
    const { data } = await getPetState();
    petState.value = data;
  } catch {
    petState.value = {
      activity: 'error',
      mood: 'offline',
      message: 'Backend unavailable.',
    };
  }
};

const refreshCompanion = async () => {
  try {
    const { data } = await getCompanionSummary();
    companion.value = data;
  } catch {
    companion.value = null;
  }
};

onMounted(async () => {
  await Promise.all([refreshPetState(), refreshCompanion()]);
  timer = window.setInterval(() => {
    refreshPetState();
    refreshCompanion();
  }, 3000);
});

onUnmounted(() => {
  if (timer) window.clearInterval(timer);
});

const activity = computed(() => petState.value?.activity || 'idle');
const mood = computed(() => petState.value?.mood || 'calm');
const display = computed(() => petState.value?.display || {});
const message = computed(() => petState.value?.message || 'Ready.');
const allowedEvents = computed(() => petState.value?.allowed_events || []);
const affinity = computed(() => companion.value?.affinity ?? 0);
const petName = computed(() => companion.value?.pet_name || 'Maple');
const faceClass = computed(() => {
  if (activity.value === 'celebrating') return 'face-excited';
  if (activity.value === 'awaiting_approval') return 'face-careful';
  if (activity.value === 'executing') return 'face-working';
  if (activity.value === 'sleeping') return 'face-sleepy';
  if (activity.value === 'error' || mood.value === 'worried' || mood.value === 'offline') return 'face-worried';
  if (activity.value === 'thinking' || activity.value === 'planning') return 'face-thinking';
  if (activity.value === 'listening') return 'face-curious';
  if (activity.value === 'speaking') return 'face-happy';
  if (activity.value === 'reminding' || mood.value === 'warm') return 'face-warm';
  return 'face-calm';
});

const wakePet = async () => {
  const eventName = allowedEvents.value.includes('wake') ? 'wake' : 'recover';
  try {
    const { data } = await sendPetEvent(eventName);
    petState.value = data;
  } catch {
    await refreshPetState();
  }
};

const openConsole = () => {
  window.myAgentDesktop?.toggleMain?.();
};

const closePet = () => {
  window.myAgentDesktop?.close?.();
};
</script>

<template>
  <main class="floating-pet" :class="`state-${activity}`">
    <button class="pet-control close" title="Hide" @click="closePet">x</button>
    <button class="pet-control console" title="Console" @click="openConsole">A</button>

    <div class="pet-drag-zone" @dblclick="openConsole">
      <div class="bubble-preview">{{ message }}</div>
      <div class="pet-orb" :class="faceClass" @click="wakePet">
        <div class="bond-glow" :style="{ opacity: Math.min(0.65, affinity / 140) }"></div>
        <div class="pet-antenna"></div>
        <div class="pet-signal"></div>
        <div class="pet-face">
          <span class="eye left"></span>
          <span class="eye right"></span>
          <span class="mouth"></span>
        </div>
      </div>
      <div class="pet-shadow"></div>
      <p class="pet-state">{{ petName }} / {{ display.label || activity }} / Lv.{{ companion?.level || 1 }}</p>
    </div>
  </main>
</template>

<style scoped>
.floating-pet {
  width: 100vw;
  height: 100vh;
  position: relative;
  overflow: hidden;
  background: transparent;
  color: #18232b;
  user-select: none;
}

.pet-drag-zone {
  position: absolute;
  inset: 12px;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  flex-direction: column;
  -webkit-app-region: drag;
}

.pet-control {
  position: absolute;
  z-index: 10;
  width: 26px;
  height: 26px;
  border-radius: 50%;
  border: 1px solid rgba(255, 255, 255, 0.74);
  background: rgba(255, 255, 255, 0.72);
  color: #52616a;
  font-size: 12px;
  font-weight: 900;
  cursor: pointer;
  -webkit-app-region: no-drag;
}

.pet-control:hover {
  background: #0f766e;
  color: white;
}

.pet-control.close {
  top: 12px;
  right: 12px;
}

.pet-control.console {
  top: 12px;
  left: 12px;
}

.bubble-preview {
  width: min(205px, calc(100vw - 28px));
  min-height: 48px;
  max-height: 78px;
  margin-bottom: 10px;
  padding: 10px 12px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.82);
  border: 1px solid rgba(214, 226, 224, 0.9);
  box-shadow: 0 10px 26px rgba(25, 44, 48, 0.08);
  color: #52616a;
  font-size: 12px;
  line-height: 1.45;
  text-align: left;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
  -webkit-app-region: no-drag;
}

.pet-orb {
  position: relative;
  width: 136px;
  height: 146px;
  border-radius: 42% 42% 36% 36%;
  background: linear-gradient(155deg, #ffffff 0%, #dff8f6 48%, #b9f0e9 100%);
  border: 1px solid rgba(20, 184, 166, 0.3);
  box-shadow: 0 18px 40px rgba(22, 124, 121, 0.2);
  animation: petFloat 3.2s ease-in-out infinite;
  cursor: pointer;
  -webkit-app-region: no-drag;
}

.bond-glow {
  position: absolute;
  inset: -14px;
  border-radius: inherit;
  background: radial-gradient(circle, rgba(241, 122, 62, 0.3), transparent 66%);
  filter: blur(10px);
  z-index: -1;
  pointer-events: none;
}

.pet-antenna {
  position: absolute;
  top: -30px;
  left: 66px;
  width: 2px;
  height: 34px;
  background: #16a39a;
}

.pet-antenna::after {
  content: '';
  position: absolute;
  top: -10px;
  left: -6px;
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: #f17a3e;
}

.pet-signal {
  position: absolute;
  top: -50px;
  left: 50%;
  width: 52px;
  height: 52px;
  border-radius: 50%;
  border: 1px solid rgba(15, 118, 110, 0.16);
  transform: translateX(-50%);
  opacity: 0;
  pointer-events: none;
}

.pet-face {
  position: absolute;
  inset: 40px 24px 36px;
  border-radius: 28px;
  background: rgba(255, 255, 255, 0.74);
  border: 1px solid rgba(255, 255, 255, 0.86);
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
  width: 126px;
  height: 22px;
  margin-top: 6px;
  border-radius: 50%;
  background: rgba(39, 87, 96, 0.16);
  filter: blur(4px);
}

.pet-state {
  margin-top: 2px;
  padding: 3px 10px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.72);
  color: #0f766e;
  font-size: 11px;
  font-weight: 800;
  text-transform: capitalize;
  max-width: calc(100vw - 36px);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.state-thinking .pet-orb,
.state-speaking .pet-orb {
  box-shadow: 0 18px 44px rgba(15, 118, 110, 0.3), 0 0 0 10px rgba(15, 118, 110, 0.08);
}

.state-listening .pet-signal {
  opacity: 1;
  animation: signalPulse 1.8s ease-in-out infinite;
}

.state-speaking .mouth {
  animation: talkMouth 0.7s ease-in-out infinite;
}

.state-thinking .pet-antenna {
  animation: antennaThink 1.2s ease-in-out infinite;
}

.state-planning .pet-antenna,
.state-executing .pet-antenna {
  animation: antennaThink 0.9s ease-in-out infinite;
}

.state-awaiting_approval .pet-orb {
  box-shadow: 0 18px 44px rgba(241, 122, 62, 0.22), 0 0 0 10px rgba(241, 122, 62, 0.08);
}

.state-executing .pet-orb {
  animation: petWork 1.1s ease-in-out infinite;
}

.state-celebrating .pet-orb {
  box-shadow: 0 18px 44px rgba(241, 122, 62, 0.28), 0 0 0 13px rgba(241, 122, 62, 0.1);
}

.state-reminding .pet-orb {
  box-shadow: 0 18px 44px rgba(241, 122, 62, 0.26), 0 0 0 10px rgba(241, 122, 62, 0.08);
}

.state-error .pet-orb {
  background: linear-gradient(155deg, #fff7ed, #ffd9c2);
  border-color: rgba(241, 122, 62, 0.45);
}

.state-sleeping .pet-orb {
  opacity: 0.72;
  animation-duration: 5s;
}

@keyframes petFloat {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-9px); }
}

@keyframes blink {
  0%, 92%, 100% { transform: scaleY(1); }
  95% { transform: scaleY(0.15); }
}

@keyframes signalPulse {
  0%, 100% { transform: translateX(-50%) scale(0.8); opacity: 0.2; }
  50% { transform: translateX(-50%) scale(1.18); opacity: 0.8; }
}

@keyframes talkMouth {
  0%, 100% { transform: translateX(-50%) scaleY(0.72); }
  50% { transform: translateX(-50%) scaleY(1.12); }
}

@keyframes antennaThink {
  0%, 100% { transform: rotate(0); }
  50% { transform: rotate(8deg); }
}

@keyframes petWork {
  0%, 100% { transform: translateY(0) rotate(-1deg); }
  50% { transform: translateY(-6px) rotate(1deg); }
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
