<script setup>
import { computed } from 'vue';

const props = defineProps({
  status: Object,
});

const emit = defineEmits(['reload']);

const tools = computed(() => props.status?.tools || []);
const enabledTools = computed(() => tools.value.filter((tool) => tool.enabled));
const disabledTools = computed(() => tools.value.filter((tool) => !tool.enabled));
const bridgeState = computed(() => {
  if (!props.status) return 'Loading';
  if (!props.status.sdk_available) return 'SDK Missing';
  return props.status.enabled ? 'Online' : 'Configured';
});
</script>

<template>
  <section class="mcp-panel glass">
    <div class="mcp-header">
      <div>
        <span class="label-xs">Tool Mesh</span>
        <h2>MCP Bridge</h2>
      </div>
      <button class="btn-ghost compact" @click="emit('reload')">Reload</button>
    </div>

    <div class="mcp-status-grid">
      <div>
        <span class="status-value">{{ bridgeState }}</span>
        <span class="status-label">Bridge</span>
      </div>
      <div>
        <span class="status-value">{{ props.status?.server_count ?? 0 }}</span>
        <span class="status-label">Servers</span>
      </div>
      <div>
        <span class="status-value">{{ props.status?.active_tool_count ?? 0 }}</span>
        <span class="status-label">Active</span>
      </div>
      <div>
        <span class="status-value">{{ props.status?.tool_count ?? 0 }}</span>
        <span class="status-label">Total</span>
      </div>
    </div>

    <div class="tool-summary">
      <span>{{ enabledTools.length }} enabled</span>
      <span>{{ disabledTools.length }} disabled</span>
    </div>

    <div class="tool-list">
      <div
        v-for="tool in tools"
        :key="tool.name"
        class="tool-row"
        :class="{ disabled: !tool.enabled }"
      >
        <span class="tool-dot"></span>
        <div class="tool-main">
          <strong>{{ tool.tool }}</strong>
          <span class="tool-meta">
            {{ tool.server }}
            <span v-if="tool.requires_approval" class="approval-chip">{{ tool.risk || 'approval' }}</span>
          </span>
          <span v-if="tool.description" class="tool-desc">{{ tool.description }}</span>
        </div>
      </div>
      <p v-if="!tools.length" class="empty-tools">No MCP tools configured.</p>
    </div>
  </section>
</template>

<style scoped>
.mcp-panel {
  width: 100%;
  padding: 16px;
}

.mcp-header {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
}

.mcp-header h2 {
  margin-top: 4px;
  font-size: 17px;
  line-height: 1.2;
}

.compact {
  padding: 6px 10px;
  font-size: 12px;
}

.mcp-status-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
  margin: 14px 0;
}

.mcp-status-grid > div {
  padding: 10px;
  border-radius: var(--radius-md);
  background: rgba(255,255,255,0.58);
  border: 1px solid rgba(255,255,255,0.72);
}

.status-value,
.status-label {
  display: block;
}

.status-value {
  font-size: 13px;
  font-weight: 800;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.status-label {
  color: var(--text-muted);
  font-size: 10px;
  margin-top: 2px;
}

.tool-summary {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
  color: var(--text-muted);
  font-size: 11px;
  font-weight: 700;
}

.tool-summary span {
  padding: 3px 8px;
  border-radius: var(--radius-pill);
  background: rgba(255,255,255,0.56);
  border: 1px solid rgba(255,255,255,0.72);
}

.tool-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 250px;
  overflow-y: auto;
}

.tool-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 10px;
  border-radius: var(--radius-md);
  background: rgba(255,255,255,0.5);
  border: 1px solid rgba(255,255,255,0.62);
}

.tool-row.disabled {
  opacity: 0.55;
}

.tool-main {
  min-width: 0;
}

.tool-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--accent-strong);
  flex-shrink: 0;
}

.tool-row.disabled .tool-dot {
  background: var(--text-muted);
}

.tool-row strong,
.tool-meta,
.tool-desc {
  display: block;
}

.tool-row strong {
  font-size: 12px;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.tool-meta {
  font-size: 11px;
  color: var(--text-muted);
}

.approval-chip {
  display: inline-flex;
  margin-left: 5px;
  padding: 1px 6px;
  border-radius: var(--radius-pill);
  color: var(--accent-warm);
  background: rgba(241, 122, 62, 0.12);
  font-size: 9px;
  font-weight: 900;
  text-transform: uppercase;
}

.tool-desc {
  margin-top: 2px;
  color: var(--text-muted);
  font-size: 11px;
  line-height: 1.35;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.empty-tools {
  color: var(--text-muted);
  font-size: 12px;
}
</style>
