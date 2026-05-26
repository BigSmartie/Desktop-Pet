<script setup>
import { nextTick, ref, watch } from 'vue';
import { marked } from 'marked';
import DOMPurify from 'dompurify';
import { clearChat, sendMessage } from '../api';

marked.setOptions({ breaks: true, gfm: true });

const renderMd = (text) => DOMPurify.sanitize(marked.parse(text || ''));

const props = defineProps({ messages: Array });
const emit = defineEmits(['message-added', 'message-cleared']);

const inputMessage = ref('');
const imageBase64 = ref('');
const isSending = ref(false);
const chatContainer = ref(null);

watch(
  () => props.messages,
  () => nextTick(() => {
    if (chatContainer.value) {
      chatContainer.value.scrollTop = chatContainer.value.scrollHeight;
    }
  }),
  { deep: true }
);

const submitMessage = async () => {
  if ((!inputMessage.value.trim() && !imageBase64.value) || isSending.value) return;

  const text = inputMessage.value.trim();
  const imgData = imageBase64.value;
  emit('message-added', { role: 'user', content: text, image: imgData });

  inputMessage.value = '';
  imageBase64.value = '';
  isSending.value = true;

  try {
    const { data } = await sendMessage(text, 'default', imgData);
    if (data?.answer) {
      emit('message-added', { role: 'assistant', content: data.answer, plan: data.thought_plan });
    }
  } catch {
    emit('message-added', { role: 'assistant', content: 'Connection failed. Please check the backend service.' });
  } finally {
    isSending.value = false;
  }
};

const handlePaste = (e) => {
  const items = e.clipboardData?.items;
  if (!items) return;

  for (const item of items) {
    if (item.type.startsWith('image/')) {
      const file = item.getAsFile();
      const reader = new FileReader();
      reader.onload = (evt) => {
        imageBase64.value = evt.target.result;
      };
      reader.readAsDataURL(file);
      e.preventDefault();
      break;
    }
  }
};

const removeImage = () => {
  imageBase64.value = '';
};

const triggerClear = async () => {
  if (!confirm('Clear the current session?')) return;
  await clearChat();
  emit('message-cleared');
};

const handleKeydown = (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    submitMessage();
  }
};
</script>

<template>
  <div class="chat-shell glass">
    <header class="chat-header">
      <div class="header-left">
        <div class="agent-avatar">A</div>
        <div class="header-info">
          <span class="agent-name">Agent Core</span>
          <span class="agent-status">
            <span class="status-dot" :class="{ active: !isSending }"></span>
            {{ isSending ? 'Thinking...' : 'Ready' }}
          </span>
        </div>
      </div>
      <button class="btn-ghost" @click="triggerClear">Clear</button>
    </header>

    <div class="message-feed" ref="chatContainer">
      <div v-if="!messages?.length" class="empty-hint">
        <div class="empty-mark">AI</div>
        <p class="greeting-title">Start a desktop pet session</p>
        <div class="feature-grid">
          <div class="feat-card">
            <span class="feat-icon">WX</span>
            <span class="feat-text">Weather</span>
          </div>
          <div class="feat-card">
            <span class="feat-icon">SE</span>
            <span class="feat-text">Web Search</span>
          </div>
          <div class="feat-card">
            <span class="feat-icon">VI</span>
            <span class="feat-text">Vision Input</span>
          </div>
          <div class="feat-card">
            <span class="feat-icon">KB</span>
            <span class="feat-text">Doc Q&A</span>
          </div>
        </div>
      </div>

      <div
        v-for="(msg, i) in messages"
        :key="i"
        class="msg-row"
        :class="msg.role"
      >
        <div v-if="msg.role === 'assistant'" class="msg-avatar bot-avatar">
          <span>A</span>
        </div>

        <div class="bubble-wrap">
          <div class="bubble" :class="msg.role">
            <img v-if="msg.image" :src="msg.image" class="bubble-img" />
            <div v-html="renderMd(msg.content)"></div>
          </div>
        </div>

        <div v-if="msg.role === 'user'" class="msg-avatar user-avatar">
          <span>U</span>
        </div>
      </div>

      <div v-if="isSending" class="msg-row assistant typing-row">
        <div class="msg-avatar bot-avatar"><span>A</span></div>
        <div class="bubble assistant typing-bubble">
          <span class="dot"></span>
          <span class="dot"></span>
          <span class="dot"></span>
        </div>
      </div>
    </div>

    <div class="input-shell">
      <div v-if="imageBase64" class="image-preview">
        <img :src="imageBase64" alt="pasted preview" />
        <button class="remove-img" @click="removeImage">x</button>
      </div>
      <div class="input-card glass">
        <textarea
          v-model="inputMessage"
          placeholder="Message your pet agent or paste an image..."
          :disabled="isSending"
          @keydown="handleKeydown"
          @paste="handlePaste"
          rows="1"
        ></textarea>
        <button class="send-btn btn-primary" :disabled="isSending || (!inputMessage.trim() && !imageBase64)" @click="submitMessage">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <line x1="22" y1="2" x2="11" y2="13"/>
            <polygon points="22 2 15 22 11 13 2 9 22 2"/>
          </svg>
        </button>
      </div>
      <p class="input-hint">Enter to send, Shift+Enter for new line, Ctrl+V to paste image.</p>
    </div>
  </div>
</template>

<style scoped>
.chat-shell {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-width: 0;
}

.chat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 18px;
  border-bottom: 1px solid rgba(214, 226, 224, 0.8);
  flex-shrink: 0;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.agent-avatar {
  width: 38px;
  height: 38px;
  border-radius: 50%;
  background: var(--accent);
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-weight: 800;
  font-size: 14px;
  box-shadow: 0 4px 14px var(--accent-glow);
}

.agent-name {
  display: block;
  font-weight: 800;
  font-size: 15px;
  color: var(--text-primary);
}

.agent-status {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--text-muted);
}

.status-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--text-muted);
  transition: background 0.4s;
}

.status-dot.active {
  background: var(--accent-soft);
  box-shadow: 0 0 6px var(--accent-glow);
}

.message-feed {
  flex: 1;
  overflow-y: auto;
  padding: 20px 18px;
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.empty-hint {
  margin: auto;
  text-align: center;
  color: var(--text-muted);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 14px;
}

.empty-mark {
  width: 58px;
  height: 58px;
  border-radius: 16px;
  background: var(--accent);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 900;
  box-shadow: 0 12px 28px var(--accent-glow);
}

.greeting-title {
  font-size: 19px;
  font-weight: 800;
  color: var(--text-primary);
}

.feature-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  width: min(360px, 100%);
}

.feat-card {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px;
  background: rgba(255, 255, 255, 0.54);
  border: 1px solid rgba(214, 226, 224, 0.82);
  border-radius: var(--radius-lg);
}

.feat-icon {
  width: 28px;
  height: 28px;
  border-radius: 7px;
  background: rgba(15, 118, 110, 0.1);
  color: var(--accent);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 900;
}

.feat-text {
  font-size: 13px;
  font-weight: 700;
  color: var(--text-secondary);
}

.msg-row {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  animation: fadeSlideUp 0.28s ease-out both;
}

.msg-row.user {
  flex-direction: row-reverse;
}

.msg-avatar {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 800;
  flex-shrink: 0;
}

.bot-avatar {
  background: var(--accent);
  color: white;
  box-shadow: 0 2px 10px var(--accent-glow);
}

.user-avatar {
  background: rgba(33, 55, 61, 0.08);
  color: var(--text-secondary);
}

.bubble-wrap {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-width: 74%;
}

.bubble {
  padding: 12px 15px;
  border-radius: var(--radius-lg);
  font-size: 14px;
  line-height: 1.65;
  word-break: break-word;
}

.bubble.assistant {
  background: var(--bot-bubble-bg);
  border: 1px solid var(--bot-bubble-border);
  color: var(--text-primary);
  backdrop-filter: blur(8px);
  border-bottom-left-radius: 4px;
  box-shadow: 0 2px 10px rgba(25, 44, 48, 0.04);
}

.bubble.user {
  background: var(--user-bubble-bg);
  color: white;
  border-bottom-right-radius: 4px;
  box-shadow: 0 4px 18px var(--accent-glow);
}

.typing-bubble {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 14px 18px;
}

.dot {
  display: inline-block;
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--accent);
  animation: pulse-dot 1.4s ease-in-out infinite;
}

.dot:nth-child(2) { animation-delay: 0.2s; }
.dot:nth-child(3) { animation-delay: 0.4s; }

.input-shell {
  padding: 10px 16px 12px;
  border-top: 1px solid rgba(214, 226, 224, 0.8);
  flex-shrink: 0;
}

.input-card {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 8px 6px 16px;
  border-radius: var(--radius-lg) !important;
  background: rgba(255, 255, 255, 0.76) !important;
}

.input-card:focus-within {
  box-shadow: var(--glass-shadow), 0 0 0 3px var(--accent-glow-sm);
}

.input-card textarea {
  flex: 1;
  background: transparent;
  border: none;
  outline: none;
  font-family: inherit;
  font-size: 14px;
  color: var(--text-primary);
  resize: none;
  min-height: 24px;
  max-height: 120px;
  line-height: 1.6;
  padding: 2px 0;
  overflow-y: auto;
}

.input-card textarea::placeholder {
  color: var(--text-muted);
}

.send-btn {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  padding: 0;
  flex-shrink: 0;
}

.input-hint {
  text-align: center;
  font-size: 11px;
  color: var(--text-muted);
  margin-top: 6px;
}

.bubble-img {
  max-width: 220px;
  max-height: 160px;
  display: block;
  border-radius: var(--radius-md);
  margin-bottom: 8px;
  object-fit: contain;
}

.image-preview {
  display: inline-block;
  position: relative;
  margin-bottom: 10px;
  margin-left: 4px;
}

.image-preview img {
  height: 60px;
  border-radius: var(--radius-md);
  border: 2px solid var(--accent-glow);
  box-shadow: var(--glass-shadow);
  object-fit: contain;
}

.remove-img {
  position: absolute;
  top: -8px;
  right: -8px;
  width: 20px;
  height: 20px;
  border: none;
  border-radius: 50%;
  background: var(--accent-warm);
  color: white;
  cursor: pointer;
  font-size: 12px;
  font-weight: 800;
}

.bubble :deep(p) { margin: 0 0 0.6em; }
.bubble :deep(p:last-child) { margin-bottom: 0; }
.bubble :deep(ul),
.bubble :deep(ol) {
  padding-left: 1.4em;
  margin: 0.5em 0;
}
.bubble :deep(li) { margin: 0.25em 0; }
.bubble :deep(code) {
  font-family: 'JetBrains Mono', 'Fira Code', 'Cascadia Code', monospace;
  font-size: 0.85em;
  padding: 2px 6px;
  border-radius: 5px;
  background: rgba(15, 118, 110, 0.1);
  color: var(--accent);
}
.bubble :deep(pre) {
  margin: 0.7em 0;
  border-radius: var(--radius-md);
  overflow: auto;
  background: rgba(24, 35, 43, 0.92) !important;
}
.bubble :deep(pre code) {
  display: block;
  padding: 14px 18px;
  background: transparent !important;
  color: #e8f2f1;
  line-height: 1.7;
}
</style>
