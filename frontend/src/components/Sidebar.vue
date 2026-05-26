<script setup>
import { onMounted, ref } from 'vue';
import { deleteDocument, getDocuments, getProfile, getTasks, uploadDocument } from '../api';

const profile = ref(null);
const tasks = ref([]);
const docs = ref([]);
const isUploading = ref(false);
const uploadError = ref('');
const acceptedFileTypes = '.pdf,.txt,.md';

const fetchData = async () => {
  try {
    const [profileRes, taskRes, docRes] = await Promise.all([
      getProfile(),
      getTasks(),
      getDocuments(),
    ]);
    profile.value = profileRes.data;
    tasks.value = taskRes.data;
    docs.value = docRes.data;
  } catch {
    profile.value = profile.value || null;
  }
};

onMounted(fetchData);

const onFileSelect = async (e) => {
  const file = e.target.files[0];
  if (!file) return;

  uploadError.value = '';
  isUploading.value = true;

  try {
    await uploadDocument(file);
    await fetchData();
  } catch (error) {
    uploadError.value = error?.response?.data?.detail || 'Upload failed.';
  } finally {
    isUploading.value = false;
    e.target.value = '';
  }
};

const removeDoc = async (id) => {
  if (!confirm('Remove this document from the knowledge base?')) return;
  await deleteDocument(id);
  await fetchData();
};

const activeTasks = () => tasks.value.filter((task) => task.status !== 'done');
const doneTasks = () => tasks.value.filter((task) => task.status === 'done');
</script>

<template>
  <aside class="sidebar glass">
    <section class="section profile-section">
      <div class="profile-banner">
        <div class="profile-ring">
          <div class="profile-inner">
            <span>{{ (profile?.name || 'A')[0].toUpperCase() }}</span>
          </div>
        </div>
        <div class="profile-text">
          <div class="profile-name">{{ profile?.name || 'My Agent' }}</div>
          <div class="profile-role">{{ profile?.preferred_style || 'Personal assistant' }}</div>
        </div>
      </div>

      <div v-if="profile?.interests?.length" class="tag-cloud">
        <span v-for="tag in profile.interests.slice(0, 4)" :key="tag" class="tag">{{ tag }}</span>
      </div>

      <p v-if="profile?.persona_notes" class="persona-note">{{ profile.persona_notes }}</p>
    </section>

    <div class="divider"></div>

    <section class="section">
      <div class="section-header">
        <span class="label-xs">Active Tasks</span>
        <span class="count-badge">{{ activeTasks().length }}</span>
      </div>

      <ul v-if="activeTasks().length" class="task-list">
        <li v-for="task in activeTasks()" :key="task.id" class="task-item">
          <div class="task-dot pending"></div>
          <span>{{ task.content }}</span>
        </li>
      </ul>
      <p v-else class="empty-label">No active tasks</p>

      <template v-if="doneTasks().length">
        <div class="section-header compact-top">
          <span class="label-xs">Completed</span>
        </div>
        <ul class="task-list">
          <li v-for="task in doneTasks()" :key="task.id" class="task-item done">
            <div class="task-dot done"></div>
            <span>{{ task.content }}</span>
          </li>
        </ul>
      </template>
    </section>

    <div class="divider"></div>

    <section class="section knowledge-section">
      <div class="section-header">
        <span class="label-xs">Knowledge Base</span>
        <span class="count-badge">{{ docs.length }}</span>
      </div>

      <ul v-if="docs.length" class="doc-list">
        <li v-for="doc in docs" :key="doc.doc_id" class="doc-item">
          <div class="doc-info">
            <span class="doc-name">{{ doc.source_file }}</span>
            <span class="doc-meta">{{ doc.chunk_count }} chunks</span>
          </div>
          <button class="del-btn" @click="removeDoc(doc.doc_id)" title="Remove">x</button>
        </li>
      </ul>
      <p v-else class="empty-label">No documents ingested</p>

      <p v-if="uploadError" class="upload-error">{{ uploadError }}</p>

      <input
        id="file-upload"
        type="file"
        class="file-input"
        :accept="acceptedFileTypes"
        :disabled="isUploading"
        @change="onFileSelect"
      />
      <label for="file-upload" class="btn-primary upload-label" :class="{ loading: isUploading }">
        {{ isUploading ? 'Uploading...' : 'Upload Document' }}
      </label>
    </section>
  </aside>
</template>

<style scoped>
.sidebar {
  width: var(--sidebar-width);
  min-width: var(--sidebar-width);
  display: flex;
  flex-direction: column;
  padding: 0;
  overflow-y: auto;
  overflow-x: hidden;
}

.section {
  padding: 16px;
}

.profile-banner {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.profile-ring {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  padding: 2px;
  background: linear-gradient(135deg, var(--accent), var(--accent-warm));
  flex-shrink: 0;
}

.profile-inner {
  width: 100%;
  height: 100%;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.92);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 19px;
  font-weight: 900;
  color: var(--accent);
}

.profile-name {
  font-weight: 800;
  font-size: 16px;
  color: var(--text-primary);
}

.profile-role {
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 2px;
}

.tag-cloud {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.tag {
  font-size: 11px;
  font-weight: 700;
  padding: 3px 9px;
  border-radius: var(--radius-pill);
  background: rgba(15, 118, 110, 0.1);
  color: var(--accent);
  border: 1px solid rgba(15, 118, 110, 0.14);
}

.persona-note {
  margin-top: 10px;
  font-size: 12px;
  color: var(--text-muted);
  line-height: 1.5;
}

.divider {
  height: 1px;
  background: rgba(214, 226, 224, 0.82);
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}

.compact-top {
  margin-top: 12px;
}

.count-badge {
  font-size: 11px;
  font-weight: 800;
  padding: 2px 8px;
  border-radius: var(--radius-pill);
  background: var(--accent-glow-sm);
  color: var(--accent);
}

.task-list,
.doc-list {
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 7px;
}

.task-item {
  display: flex;
  align-items: flex-start;
  gap: 9px;
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.45;
}

.task-item.done {
  opacity: 0.55;
  text-decoration: line-through;
}

.task-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
  margin-top: 5px;
}

.task-dot.pending {
  background: var(--accent);
  box-shadow: 0 0 6px var(--accent-glow);
}

.task-dot.done {
  background: var(--accent-warm);
}

.empty-label {
  font-size: 12px;
  color: var(--text-muted);
}

.knowledge-section {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.doc-list {
  margin-bottom: 14px;
}

.doc-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 9px 10px;
  border-radius: var(--radius-md);
  background: rgba(255, 255, 255, 0.52);
  border: 1px solid rgba(214, 226, 224, 0.78);
}

.doc-info {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.doc-name {
  font-size: 12px;
  font-weight: 700;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 190px;
}

.doc-meta {
  font-size: 11px;
  color: var(--text-muted);
  margin-top: 1px;
}

.del-btn {
  width: 24px;
  height: 24px;
  border: none;
  border-radius: 50%;
  cursor: pointer;
  color: var(--text-muted);
  background: rgba(33, 55, 61, 0.06);
  flex-shrink: 0;
  font-weight: 800;
}

.del-btn:hover {
  color: white;
  background: var(--accent-warm);
}

.file-input {
  display: none;
}

.upload-label {
  margin-top: auto;
  width: 100%;
  cursor: pointer;
}

.upload-label.loading {
  opacity: 0.6;
  cursor: not-allowed;
}

.upload-error {
  font-size: 12px;
  color: #c2410c;
  margin-bottom: 8px;
}
</style>
