<script setup>
import { computed, onMounted, ref } from 'vue';
import {
  generateDailyReport,
  getAppSettings,
  getRecentLogs,
  getReminderStatus,
  getTodayDailyReport,
  saveAppSettings,
} from '../api';

const settings = ref(null);
const dailyReport = ref(null);
const reminders = ref(null);
const logs = ref({ app: [], electron_backend: [] });
const activeTab = ref('settings');
const isSaving = ref(false);
const isGenerating = ref(false);
const savedMessage = ref('');
const autoLaunch = ref(false);

const mcpServers = computed(() => settings.value?.mcp?.servers || []);

const fetchAll = async () => {
  try {
    const [settingsRes, reportRes, reminderRes, logsRes] = await Promise.all([
      getAppSettings(),
      getTodayDailyReport(),
      getReminderStatus(),
      getRecentLogs(120),
    ]);
    settings.value = settingsRes.data;
    dailyReport.value = reportRes.data;
    reminders.value = reminderRes.data;
    logs.value = logsRes.data;
  } catch {
    savedMessage.value = 'Settings service is unavailable.';
  }

  try {
    const result = await window.myAgentDesktop?.getAutoLaunch?.();
    autoLaunch.value = Boolean(result?.openAtLogin);
  } catch {
    autoLaunch.value = false;
  }
};

onMounted(fetchAll);

const saveSettings = async () => {
  if (!settings.value) return;
  isSaving.value = true;
  savedMessage.value = '';
  try {
    const { data } = await saveAppSettings(settings.value);
    settings.value = data;
    if (window.myAgentDesktop?.setAutoLaunch) {
      await window.myAgentDesktop.setAutoLaunch(autoLaunch.value);
    }
    savedMessage.value = 'Saved. Model and embedding changes may need a backend restart.';
  } catch (error) {
    savedMessage.value = error?.response?.data?.detail || 'Save failed.';
  } finally {
    isSaving.value = false;
  }
};

const createReport = async () => {
  isGenerating.value = true;
  try {
    const { data } = await generateDailyReport();
    dailyReport.value = data;
    const reminderRes = await getReminderStatus();
    reminders.value = reminderRes.data;
  } finally {
    isGenerating.value = false;
  }
};

const refreshLogs = async () => {
  const { data } = await getRecentLogs(180);
  logs.value = data;
};
</script>

<template>
  <section class="settings-panel glass">
    <div class="settings-header">
      <div>
        <span class="label-xs">Product</span>
        <h2>Settings</h2>
      </div>
      <button class="btn-ghost compact" @click="fetchAll">Sync</button>
    </div>

    <div class="settings-tabs">
      <button :class="{ active: activeTab === 'settings' }" @click="activeTab = 'settings'">Config</button>
      <button :class="{ active: activeTab === 'reports' }" @click="activeTab = 'reports'">Reports</button>
      <button :class="{ active: activeTab === 'logs' }" @click="activeTab = 'logs'">Logs</button>
    </div>

    <div v-if="settings && activeTab === 'settings'" class="settings-body">
      <section class="settings-group">
        <span class="group-title">Model</span>
        <label>
          <span>Ollama URL</span>
          <input v-model="settings.model.ollama_base_url" />
        </label>
        <label>
          <span>Chat Model</span>
          <input v-model="settings.model.ollama_model" />
        </label>
        <label>
          <span>Vision Model</span>
          <input v-model="settings.model.ollama_vision_model" />
        </label>
        <div class="field-grid">
          <label>
            <span>Temperature</span>
            <input v-model.number="settings.model.temperature" type="number" min="0" max="2" step="0.1" />
          </label>
          <label>
            <span>Max Tokens</span>
            <input v-model.number="settings.model.max_tokens" type="number" min="128" max="8192" />
          </label>
        </div>
      </section>

      <section class="settings-group">
        <span class="group-title">Knowledge</span>
        <div class="field-grid">
          <label>
            <span>Chunk Size</span>
            <input v-model.number="settings.knowledge.chunk_size" type="number" min="100" />
          </label>
          <label>
            <span>Overlap</span>
            <input v-model.number="settings.knowledge.chunk_overlap" type="number" min="0" />
          </label>
        </div>
        <div class="field-grid">
          <label>
            <span>Top K</span>
            <input v-model.number="settings.knowledge.retriever_top_k" type="number" min="1" />
          </label>
          <label>
            <span>Max MB</span>
            <input v-model.number="settings.knowledge.max_file_size_mb" type="number" min="1" />
          </label>
        </div>
        <label class="toggle-row">
          <input v-model="settings.knowledge.enable_mmr" type="checkbox" />
          <span>MMR retrieval</span>
        </label>
      </section>

      <section class="settings-group">
        <span class="group-title">Pet</span>
        <label>
          <span>Name</span>
          <input v-model="settings.pet.name" />
        </label>
        <label>
          <span>Persona</span>
          <textarea v-model="settings.pet.persona" rows="3"></textarea>
        </label>
        <div class="field-grid">
          <label>
            <span>Tone</span>
            <input v-model="settings.pet.tone" />
          </label>
          <label>
            <span>Theme</span>
            <select v-model="settings.pet.theme">
              <option value="mint">Mint</option>
              <option value="sunrise">Sunrise</option>
              <option value="mono">Mono</option>
            </select>
          </label>
        </div>
        <div class="field-grid">
          <label>
            <span>Quiet Start</span>
            <input v-model="settings.pet.quiet_hours_start" />
          </label>
          <label>
            <span>Quiet End</span>
            <input v-model="settings.pet.quiet_hours_end" />
          </label>
        </div>
        <label class="toggle-row">
          <input v-model="settings.pet.proactive_reminders" type="checkbox" />
          <span>Proactive reminders</span>
        </label>
        <label class="toggle-row">
          <input v-model="settings.pet.daily_report_auto" type="checkbox" />
          <span>Auto daily report</span>
        </label>
        <label class="toggle-row">
          <input v-model="autoLaunch" type="checkbox" />
          <span>Start at Windows login</span>
        </label>
      </section>

      <section class="settings-group">
        <span class="group-title">MCP Servers</span>
        <div v-for="server in mcpServers" :key="server.name" class="server-row">
          <label class="toggle-row">
            <input v-model="server.enabled" type="checkbox" />
            <span>{{ server.name }}</span>
          </label>
          <div class="tool-toggles">
            <label v-for="tool in server.tools || []" :key="tool.name">
              <input v-model="tool.enabled" type="checkbox" />
              <span>{{ tool.name }}</span>
            </label>
          </div>
        </div>
      </section>

      <button class="btn-primary save-btn" :disabled="isSaving" @click="saveSettings">
        {{ isSaving ? 'Saving...' : 'Save Settings' }}
      </button>
      <p v-if="savedMessage" class="save-message">{{ savedMessage }}</p>
    </div>

    <div v-if="activeTab === 'reports'" class="settings-body">
      <section class="settings-group">
        <div class="report-head">
          <span class="group-title">Daily Report</span>
          <button class="btn-ghost compact" :disabled="isGenerating" @click="createReport">
            {{ isGenerating ? 'Generating...' : 'Generate' }}
          </button>
        </div>
        <pre class="report-preview">{{ dailyReport?.content || 'No report yet.' }}</pre>
      </section>

      <section class="settings-group">
        <span class="group-title">Active Reminders</span>
        <p class="quiet-line">
          Quiet hours: {{ reminders?.quiet_hours?.start || '--' }} - {{ reminders?.quiet_hours?.end || '--' }}
        </p>
        <ul class="reminder-list">
          <li v-for="item in reminders?.next_suggestions || []" :key="item">{{ item }}</li>
        </ul>
      </section>
    </div>

    <div v-if="activeTab === 'logs'" class="settings-body">
      <div class="report-head">
        <span class="group-title">Recent Logs</span>
        <button class="btn-ghost compact" @click="refreshLogs">Refresh</button>
      </div>
      <pre class="log-preview">{{ [...(logs.app || []), '', ...(logs.electron_backend || [])].join('\n') || 'No logs yet.' }}</pre>
    </div>
  </section>
</template>

<style scoped>
.settings-panel {
  width: 100%;
  padding: 16px;
}

.settings-header,
.report-head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
}

.settings-header h2 {
  margin-top: 4px;
  font-size: 17px;
  line-height: 1.2;
}

.compact {
  padding: 6px 10px;
  font-size: 12px;
}

.settings-tabs {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 6px;
  margin: 14px 0;
}

.settings-tabs button {
  height: 30px;
  border: 1px solid rgba(33, 55, 61, 0.08);
  border-radius: var(--radius-md);
  background: rgba(255,255,255,0.42);
  color: var(--text-muted);
  font: inherit;
  font-size: 12px;
  font-weight: 800;
  cursor: pointer;
}

.settings-tabs button.active {
  color: white;
  background: var(--accent);
}

.settings-body {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.settings-group {
  padding: 11px;
  border-radius: var(--radius-md);
  background: rgba(255,255,255,0.5);
  border: 1px solid rgba(255,255,255,0.72);
}

.group-title {
  display: block;
  margin-bottom: 8px;
  color: var(--text-primary);
  font-size: 12px;
  font-weight: 900;
}

.settings-group label {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-top: 8px;
}

.settings-group label span,
.quiet-line,
.reminder-list {
  color: var(--text-muted);
  font-size: 11px;
  line-height: 1.4;
}

.settings-group input,
.settings-group textarea,
.settings-group select {
  width: 100%;
  min-width: 0;
  border: 1px solid rgba(33, 55, 61, 0.08);
  border-radius: var(--radius-md);
  background: rgba(255,255,255,0.72);
  color: var(--text-secondary);
  font: inherit;
  font-size: 12px;
  outline: none;
  padding: 7px 8px;
}

.field-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}

.toggle-row {
  flex-direction: row !important;
  align-items: center;
}

.toggle-row input {
  width: 15px;
  height: 15px;
}

.server-row {
  margin-top: 8px;
}

.tool-toggles {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-left: 23px;
}

.tool-toggles label {
  flex-direction: row;
  align-items: center;
  margin-top: 0;
}

.tool-toggles input {
  width: 13px;
  height: 13px;
}

.save-btn {
  width: 100%;
  border-radius: var(--radius-md);
}

.save-message {
  color: var(--text-muted);
  font-size: 11px;
  line-height: 1.4;
}

.report-preview,
.log-preview {
  max-height: 320px;
  overflow: auto;
  border-radius: var(--radius-md);
  background: rgba(24, 35, 43, 0.92);
  color: #e8f2f1;
  padding: 10px;
  white-space: pre-wrap;
  font-size: 11px;
  line-height: 1.55;
}

.log-preview {
  max-height: 460px;
}

.reminder-list {
  padding-left: 16px;
}
</style>
