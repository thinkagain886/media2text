import { defineStore } from 'pinia'
import * as api from '@/api/index.js'

let _id = 0
function nid() {
  _id += 1
  return String(_id)
}

export const useFilesStore = defineStore('files', {
  state: () => ({
    fileList: [],
  }),
  actions: {
    addFiles(rawFiles) {
      const incoming = Array.from(rawFiles || [])
      for (const f of incoming) {
        const dup = this.fileList.some((x) => x.filename === f.name && x.size === f.size)
        if (dup) continue
        this.fileList.push({
          id: nid(),
          file: f,
          filename: f.name,
          size: f.size,
          file_type: null,
          temp_path: null,
        })
      }
    },
    removeFile(id) {
      this.fileList = this.fileList.filter((x) => x.id !== id)
    },
    clearAll() {
      this.fileList = []
    },
    async uploadAll() {
      const files = this.fileList.map((x) => x.file).filter(Boolean)
      if (!files.length) return
      const res = await api.uploadFiles(files)
      let j = 0
      this.fileList = this.fileList.map((row) => {
        if (!row.file) return row
        const hit = res[j]
        j += 1
        if (!hit) return row
        return {
          ...row,
          file_type: hit.file_type,
          temp_path: hit.temp_path,
        }
      })
    },
  },
})
