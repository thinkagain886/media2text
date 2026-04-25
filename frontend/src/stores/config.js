import { defineStore } from 'pinia'
import * as api from '@/api/index.js'

const defaultState = () => ({
  category: '默认分类',
  save_audio_local: true,
  save_audio_oss: false,
  transcribe_enabled: false,
  asr_engine: 'funasr',
  transcript_save_local: false,
  transcript_save_oss: false,
  batch_mode: 'separate',
  merge_title: '',
  summary_enabled: false,
  summary_model: 'qwen',
  summary_prompt_title: '默认总结',
  save_to_db: false,
  dashscope_api_key: '',
  qwen_api_key: '',
  oss_access_key_id: '',
  oss_access_key_secret: '',
  oss_bucket_name: '',
  oss_endpoint: '',
  audio_local_base_path: './output',
  transcript_local_base_path: './output',
  temp_dir: './temp',
  push_notion_enabled: false,
  push_feishu_enabled: false,
  notion_integration_token: '',
  notion_database_id: '',
  feishu_app_id: '',
  feishu_app_secret: '',
  feishu_bitable_app_token: '',
  feishu_table_id: '',
  db_engine: 'sqlite',
  sqlite_path: '',
  supabase_url: '',
  supabase_key: '',
  supabase_table: 'records',
  categories: [],
  prompts: [],
})

export const useConfigStore = defineStore('config', {
  state: defaultState,
  actions: {
    async loadConfig() {
      const d = await api.getConfig()
      const def = defaultState()
      Object.keys(def).forEach((k) => {
        if (k === 'categories' || k === 'prompts') return
        this[k] = d[k] !== undefined ? d[k] : def[k]
      })
    },
    async saveConfig(partial) {
      await api.putConfig(partial)
      Object.assign(this, partial)
    },
    async loadCategories() {
      this.categories = await api.getCategories()
    },
    async addCategory(name) {
      await api.addCategory(name)
      await this.loadCategories()
    },
    async deleteCategory(name) {
      await api.deleteCategory(name)
      await this.loadCategories()
      if (this.category === name) {
        this.category = '默认分类'
        await this.persistMainPageToRedis()
      }
    },
    async loadPrompts() {
      this.prompts = await api.getPrompts()
    },
    async addPrompt(title, content) {
      await api.addPrompt(title, content)
      await this.loadPrompts()
    },
    /** 主页（非设置弹窗）控制的选项，用于实时同步到 Redis */
    buildMainPageRedisPayload() {
      return {
        category: this.category,
        save_audio_local: this.save_audio_local,
        save_audio_oss: this.save_audio_oss,
        transcribe_enabled: this.transcribe_enabled,
        asr_engine: this.asr_engine || 'funasr',
        dashscope_api_key: this.dashscope_api_key,
        transcript_save_local: this.transcript_save_local,
        transcript_save_oss: this.transcript_save_oss,
        batch_mode: this.batch_mode,
        merge_title: this.merge_title,
        summary_enabled: this.summary_enabled,
        summary_model: this.summary_model,
        summary_prompt_title: this.summary_prompt_title,
        push_notion_enabled: this.push_notion_enabled,
        push_feishu_enabled: this.push_feishu_enabled,
      }
    },
    async persistMainPageToRedis() {
      await api.putConfig(this.buildMainPageRedisPayload())
    },
    buildProcessPayload() {
      return {
        category: this.category,
        save_audio_local: this.save_audio_local,
        save_audio_oss: this.save_audio_oss,
        transcribe_enabled: this.transcribe_enabled,
        asr_engine: this.asr_engine || 'funasr',
        transcript_save_local: this.transcript_save_local,
        transcript_save_oss: this.transcript_save_oss,
        batch_mode: this.batch_mode,
        merge_title: this.merge_title,
        summary_enabled: this.summary_enabled,
        summary_model: this.summary_model,
        summary_prompt_title: this.summary_prompt_title,
        save_to_db: this.save_to_db,
        dashscope_api_key: this.dashscope_api_key,
        qwen_api_key: this.qwen_api_key,
        oss_access_key_id: this.oss_access_key_id,
        oss_access_key_secret: this.oss_access_key_secret,
        oss_bucket_name: this.oss_bucket_name,
        oss_endpoint: this.oss_endpoint,
        audio_local_base_path: this.audio_local_base_path,
        transcript_local_base_path: this.transcript_local_base_path,
        temp_dir: this.temp_dir,
        push_notion_enabled: this.push_notion_enabled,
        push_feishu_enabled: this.push_feishu_enabled,
        notion_integration_token: this.notion_integration_token,
        notion_database_id: this.notion_database_id,
        feishu_app_id: this.feishu_app_id,
        feishu_app_secret: this.feishu_app_secret,
        feishu_bitable_app_token: this.feishu_bitable_app_token,
        feishu_table_id: this.feishu_table_id,
        db_engine: this.db_engine,
        sqlite_path: this.sqlite_path,
        supabase_url: this.supabase_url,
        supabase_key: this.supabase_key,
        supabase_table: this.supabase_table,
      }
    },
  },
})
