<script setup>
import { computed, ref } from 'vue';

const props = defineProps({
  queue: Object,
  busyId: String,
});

const emit = defineEmits(['approve', 'reject', 'run', 'refresh']);
const expandedId = ref('');

const actions = computed(() => props.queue?.actions || []);
const pendingActions = computed(() => actions.value.filter((action) => action.status === 'pending_approval'));
const activeActions = computed(() => actions.value.filter((action) => ['approved', 'running'].includes(action.status)));
const recentActions = computed(() => actions.value.filter((action) => !['pending_approval', 'approved', 'running'].includes(action.status)).slice(0, 5));

const statusLabel = (status) => status.replaceAll('_', ' ');
const toggleExpand = (id) => {
  expandedId.value = expandedId.value === id ? '' : id;
};
</script>

<template>
  <section class="action-panel glass">
    <div class="action-header">
      <div>
        <span class="label-xs">Permission</span>
        <h2>Action Queue</h2>
      </div>
      <button class="btn-ghost compact" @click="emit('refresh')">Refresh</button>
    </div>

    <div class="queue-stats">
      <div>
        <span class="status-value">{{ props.queue?.pending_count ?? 0 }}</span>
        <span class="status-label">Pending</span>
      </div>
      <div>
        <span class="status-value">{{ props.queue?.running_count ?? 0 }}</span>
        <span class="status-label">Running</span>
      </div>
      <div>
        <span class="status-value">{{ props.queue?.recent_count ?? 0 }}</span>
        <span class="status-label">Recent</span>
      </div>
    </div>

    <div v-if="pendingActions.length" class="action-list pending-list">
      <article v-for="action in pendingActions" :key="action.id" class="action-item pending">
        <div class="action-title-row" @click="toggleExpand(action.id)">
          <span class="risk-pill" :class="`risk-${action.risk}`">{{ action.risk }}</span>
          <strong>{{ action.title }}</strong>
        </div>
        <p class="tool-name">{{ action.tool_name }}</p>
        <p v-if="action.reason" class="reason-text">{{ action.reason }}</p>
        <pre v-if="expandedId === action.id" class="args-preview">{{ JSON.stringify(action.arguments, null, 2) }}</pre>
        <div class="action-buttons">
          <button class="btn-primary mini" :disabled="props.busyId === action.id" @click="emit('approve', action.id)">
            Approve
          </button>
          <button class="btn-ghost mini" :disabled="props.busyId === action.id" @click="emit('reject', action.id)">
            Reject
          </button>
        </div>
      </article>
    </div>

    <div v-if="activeActions.length" class="action-list">
      <article v-for="action in activeActions" :key="action.id" class="action-item active">
        <div class="action-title-row">
          <span class="status-chip">{{ statusLabel(action.status) }}</span>
          <strong>{{ action.title }}</strong>
        </div>
        <button
          v-if="action.status === 'approved'"
          class="btn-ghost mini run-btn"
          :disabled="props.busyId === action.id"
          @click="emit('run', action.id)"
        >
          Run
        </button>
      </article>
    </div>

    <div v-if="recentActions.length" class="recent-actions">
      <div v-for="action in recentActions" :key="action.id" class="recent-row" :class="action.status">
        <span>{{ statusLabel(action.status) }}</span>
        <strong>{{ action.title }}</strong>
      </div>
    </div>

    <p v-if="!actions.length" class="empty-actions">No queued actions yet.</p>
  </section>
</template>

<style scoped>
.action-panel {
  width: 100%;
  padding: 16px;
}

.action-header {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
}

.action-header h2 {
  margin-top: 4px;
  font-size: 17px;
  line-height: 1.2;
}

.compact {
  padding: 6px 10px;
  font-size: 12px;
}

.queue-stats {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
  margin: 14px 0;
}

.queue-stats > div {
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
  color: var(--text-primary);
  font-size: 13px;
  font-weight: 800;
}

.status-label {
  color: var(--text-muted);
  font-size: 10px;
  margin-top: 2px;
}

.action-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 8px;
}

.pending-list {
  max-height: 250px;
  overflow-y: auto;
}

.action-item {
  padding: 10px;
  border-radius: var(--radius-md);
  background: rgba(255,255,255,0.56);
  border: 1px solid rgba(255,255,255,0.72);
}

.action-item.pending {
  box-shadow: inset 3px 0 0 var(--accent-warm);
}

.action-title-row {
  display: flex;
  align-items: center;
  gap: 7px;
  min-width: 0;
  cursor: pointer;
}

.action-title-row strong {
  color: var(--text-primary);
  font-size: 12px;
  line-height: 1.3;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.risk-pill,
.status-chip {
  flex-shrink: 0;
  padding: 2px 7px;
  border-radius: var(--radius-pill);
  font-size: 10px;
  font-weight: 900;
  text-transform: uppercase;
}

.risk-low {
  color: var(--accent);
  background: rgba(15, 118, 110, 0.1);
}

.risk-medium {
  color: #a16207;
  background: rgba(234, 179, 8, 0.16);
}

.risk-high {
  color: #c2410c;
  background: rgba(241, 122, 62, 0.16);
}

.status-chip {
  color: var(--accent);
  background: rgba(15, 118, 110, 0.1);
}

.tool-name,
.reason-text {
  margin-top: 5px;
  color: var(--text-muted);
  font-size: 11px;
  line-height: 1.35;
  word-break: break-word;
}

.args-preview {
  margin-top: 8px;
  max-height: 130px;
  overflow: auto;
  border-radius: var(--radius-md);
  background: rgba(24, 35, 43, 0.92);
  color: #e8f2f1;
  padding: 9px;
  font-size: 10px;
  line-height: 1.5;
}

.action-buttons {
  display: flex;
  gap: 8px;
  margin-top: 9px;
}

.mini {
  flex: 1;
  min-height: 30px;
  padding: 0 10px;
  font-size: 11px;
  border-radius: var(--radius-md);
}

.run-btn {
  width: 100%;
  margin-top: 8px;
}

.recent-actions {
  display: flex;
  flex-direction: column;
  gap: 7px;
  margin-top: 10px;
}

.recent-row {
  display: grid;
  grid-template-columns: 74px minmax(0, 1fr);
  gap: 8px;
  align-items: center;
  color: var(--text-muted);
  font-size: 11px;
}

.recent-row span {
  text-transform: capitalize;
  font-weight: 800;
}

.recent-row.succeeded span {
  color: var(--accent);
}

.recent-row.failed span,
.recent-row.rejected span {
  color: var(--accent-warm);
}

.recent-row strong {
  color: var(--text-secondary);
  font-size: 11px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.empty-actions {
  color: var(--text-muted);
  font-size: 12px;
}
</style>
