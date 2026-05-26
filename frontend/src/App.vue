<script setup>
import { onMounted, onUnmounted, ref } from 'vue';
import Sidebar from './components/Sidebar.vue';
import ChatWindow from './components/ChatWindow.vue';
import PetStage from './components/PetStage.vue';
import McpPanel from './components/McpPanel.vue';
import PetFloating from './components/PetFloating.vue';
import ActionQueuePanel from './components/ActionQueuePanel.vue';
import SettingsPanel from './components/SettingsPanel.vue';
import {
  approveAction,
  getChatHistory,
  getCompanionSummary,
  getActionQueue,
  getMcpStatus,
  getPetState,
  rejectAction,
  reloadMcp,
  runAction,
  sendCompanionCheckIn,
  sendPetEvent,
} from './api';

const chatMessages = ref([]);
const petState = ref(null);
const mcpStatus = ref(null);
const backendStatus = ref(null);
const companion = ref(null);
const actionQueue = ref(null);
const actionBusyId = ref('');
const windowMode = new URLSearchParams(window.location.search).get('window') || 'console';
document.body.dataset.window = windowMode;
let petTimer = null;
let queueTimer = null;
let unsubscribeBackendStatus = null;

const refreshPetState = async () => {
  try {
    const { data } = await getPetState();
    petState.value = data;
  } catch {
    const backendState = backendStatus.value?.state;
    const isStarting = backendState === 'starting' || backendState === 'unknown';
    petState.value = {
      activity: isStarting ? 'booting' : 'error',
      mood: isStarting ? 'starting' : 'offline',
      message: isStarting
        ? 'Backend is starting. First launch may take a little while.'
        : 'Backend connection is unavailable.',
    };
  }
};

const refreshMcpStatus = async () => {
  try {
    const { data } = await getMcpStatus();
    mcpStatus.value = data;
  } catch {
    mcpStatus.value = {
      enabled: false,
      sdk_available: false,
      server_count: 0,
      tool_count: 0,
      active_tool_count: 0,
      tools: [],
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

const refreshActionQueue = async () => {
  try {
    const { data } = await getActionQueue();
    actionQueue.value = data;
  } catch {
    actionQueue.value = null;
  }
};

const refreshBackendStatus = async () => {
  if (!window.myAgentDesktop?.getBackendStatus) {
    backendStatus.value = null;
    return;
  }

  try {
    backendStatus.value = await window.myAgentDesktop.getBackendStatus();
  } catch {
    backendStatus.value = {
      state: 'unknown',
      managed: false,
      lastError: 'Desktop shell status unavailable.',
    };
  }
};

onMounted(async () => {
  if (windowMode === 'pet') {
    return;
  }

  if (window.myAgentDesktop?.onBackendStatus) {
    unsubscribeBackendStatus = window.myAgentDesktop.onBackendStatus((status) => {
      backendStatus.value = status;
      if (status?.state === 'running' || status?.state === 'external') {
        Promise.all([
          refreshPetState(),
          refreshMcpStatus(),
          refreshCompanion(),
          refreshActionQueue(),
        ]);
      }
    });
  }

  try {
    const { data } = await getChatHistory();
    if (data?.messages) chatMessages.value = data.messages;
  } catch {
    chatMessages.value = [];
  }

  await Promise.all([
    refreshPetState(),
    refreshMcpStatus(),
    refreshBackendStatus(),
    refreshCompanion(),
    refreshActionQueue(),
  ]);
  petTimer = window.setInterval(refreshPetState, 2500);
  queueTimer = window.setInterval(refreshActionQueue, 4000);
  window.setTimeout(() => {
    refreshMcpStatus();
    refreshCompanion();
    refreshActionQueue();
  }, 3500);
});

onUnmounted(() => {
  if (petTimer) window.clearInterval(petTimer);
  if (queueTimer) window.clearInterval(queueTimer);
  if (unsubscribeBackendStatus) unsubscribeBackendStatus();
});

const handleNewMessage = (msg) => {
  chatMessages.value.push(msg);
  refreshPetState();
  if (msg.role === 'assistant') refreshCompanion();
};

const handleChatCleared = () => {
  chatMessages.value = [];
};

const handlePetEvent = async (event) => {
  try {
    const { data } = await sendPetEvent(event);
    petState.value = data;
  } catch {
    await refreshPetState();
  }
};

const handleCheckIn = async (payload) => {
  try {
    const { data } = await sendCompanionCheckIn(payload?.mood || '', payload?.note || '');
    companion.value = data;
    await refreshPetState();
  } catch {
    await refreshCompanion();
  }
};

const handleMcpReload = async () => {
  try {
    const { data } = await reloadMcp();
    mcpStatus.value = data;
  } catch {
    await refreshMcpStatus();
  }
};

const handleApproveAction = async (actionId) => {
  actionBusyId.value = actionId;
  try {
    await approveAction(actionId, true);
    await Promise.all([refreshActionQueue(), refreshPetState(), refreshCompanion()]);
  } finally {
    actionBusyId.value = '';
  }
};

const handleRejectAction = async (actionId) => {
  actionBusyId.value = actionId;
  try {
    await rejectAction(actionId);
    await Promise.all([refreshActionQueue(), refreshPetState(), refreshCompanion()]);
  } finally {
    actionBusyId.value = '';
  }
};

const handleRunAction = async (actionId) => {
  actionBusyId.value = actionId;
  try {
    await runAction(actionId);
    await Promise.all([refreshActionQueue(), refreshPetState(), refreshCompanion()]);
  } finally {
    actionBusyId.value = '';
  }
};
</script>

<template>
  <PetFloating v-if="windowMode === 'pet'" />

  <main v-else class="desktop-console">
    <aside class="pet-column">
      <PetStage
        :state="petState"
        :mcp="mcpStatus"
        :backend="backendStatus"
        :companion="companion"
        @check-in="handleCheckIn"
        @pet-event="handlePetEvent"
      />
    </aside>

    <section class="conversation-column">
      <ChatWindow
        :messages="chatMessages"
        @message-added="handleNewMessage"
        @message-cleared="handleChatCleared"
      />
    </section>

    <aside class="control-column">
      <Sidebar />
      <ActionQueuePanel
        :queue="actionQueue"
        :busy-id="actionBusyId"
        @approve="handleApproveAction"
        @reject="handleRejectAction"
        @run="handleRunAction"
        @refresh="refreshActionQueue"
      />
      <McpPanel :status="mcpStatus" @reload="handleMcpReload" />
      <SettingsPanel />
    </aside>
  </main>
</template>

<style scoped>
.desktop-console {
  display: grid;
  grid-template-columns: minmax(260px, 310px) minmax(440px, 1fr) minmax(280px, 322px);
  height: 100%;
  gap: 14px;
}

.pet-column,
.conversation-column,
.control-column {
  min-height: 0;
  min-width: 0;
}

.conversation-column {
  display: flex;
}

.control-column {
  display: flex;
  flex-direction: column;
  gap: 12px;
  overflow-y: auto;
  padding-right: 2px;
}

.control-column :deep(.sidebar) {
  width: 100%;
  min-width: 0;
  flex: none;
  max-height: 520px;
}

@media (max-width: 1180px) {
  .desktop-console {
    grid-template-columns: minmax(240px, 290px) 1fr;
  }

  .control-column {
    display: none;
  }
}

@media (max-width: 760px) {
  .desktop-console {
    grid-template-columns: 1fr;
    overflow-y: auto;
  }

  .pet-column {
    min-height: 520px;
  }

  .conversation-column {
    min-height: 620px;
  }
}
</style>
