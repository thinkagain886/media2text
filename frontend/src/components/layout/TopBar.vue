<template>
  <a-layout-header class="topbar">
    <div class="left">
      <span class="logo-dot" />
      <span class="title">媒体转文本</span>
      <span class="badge">v2</span>
    </div>
    <div class="right">
      <a-button type="text" class="btn" @click="$emit('history')">
        <template #icon><history-outlined /></template>
        历史记录
      </a-button>
      <a-button type="text" class="btn" @click="$emit('settings')">
        <template #icon><setting-outlined /></template>
        设置
      </a-button>
    </div>
  </a-layout-header>
</template>

<script setup>
import { HistoryOutlined, SettingOutlined } from '@ant-design/icons-vue'

defineEmits(['history', 'settings'])
</script>

<style scoped>
.topbar {
  height: 48px;
  line-height: 48px;
  padding: 0 20px;
  background: linear-gradient(90deg, #1e1b4b 0%, #312e81 42%, #4c1d95 100%);
  color: #fff;
  display: flex;
  justify-content: space-between;
  align-items: center;
  box-shadow: 0 4px 20px rgba(30, 27, 75, 0.35);
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}
.left {
  display: flex;
  align-items: center;
  gap: 10px;
}
.logo-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: linear-gradient(135deg, #a5b4fc, #c4b5fd);
  box-shadow: 0 0 12px rgba(165, 180, 252, 0.9);
}
.title {
  font-size: 17px;
  font-weight: 700;
  letter-spacing: 0.03em;
}
.badge {
  font-size: 11px;
  padding: 0 7px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.12);
  color: rgba(255, 255, 255, 0.85);
  line-height: 20px;
}
.right {
  display: flex;
  gap: 4px;
}
.btn {
  color: rgba(255, 255, 255, 0.92) !important;
}
.btn:hover {
  background: rgba(255, 255, 255, 0.08) !important;
  color: #fff !important;
}
</style>
