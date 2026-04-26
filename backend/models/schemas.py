# -*- coding: utf-8 -*-
"""请求/响应模型、Process 配置默认值（与 frontend/src/stores/config.js 一致）"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

DEFAULT_PROMPTS_DICT: Dict[str, str] = {
    "默认总结": "请对下列内容做简明总结：",
}

DEFAULT_CONFIG_DICT: Dict[str, Any] = {
    "category": "默认分类",
    "save_audio_local": True,
    "save_audio_oss": False,
    "transcribe_enabled": False,
    "subtitle_priority": False,
    "asr_engine": "funasr",
    "transcript_save_local": False,
    "transcript_save_oss": False,
    "batch_mode": "separate",
    "merge_title": "",
    "summary_enabled": False,
    "summary_model": "qwen",
    "summary_prompt_title": "默认总结",
    "save_to_db": False,
    "dashscope_api_key": "",
    "qwen_api_key": "",
    "oss_access_key_id": "",
    "oss_access_key_secret": "",
    "oss_bucket_name": "",
    "oss_endpoint": "",
    "audio_local_base_path": "./output",
    "transcript_local_base_path": "./output",
    "temp_dir": "./temp",
    "push_notion_enabled": False,
    "push_feishu_enabled": False,
    "notion_integration_token": "",
    "notion_database_id": "",
    "feishu_app_id": "",
    "feishu_app_secret": "",
    "feishu_bitable_app_token": "",
    "feishu_table_id": "",
    "db_engine": "sqlite",
    "sqlite_path": "",
    "supabase_url": "",
    "supabase_key": "",
    "supabase_table": "records",
    "filename_clean_regex": "",
    "filename_temp_rules": [],
    "filename_regex_library": [],
    "filename_selected_regex_ids": [],
}


def merge_config(
    base: Dict[str, Any],
    override: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    out = dict(base)
    if override:
        out.update(override)
    return out


class ProcessConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")

    category: str = "默认分类"
    save_audio_local: bool = True
    save_audio_oss: bool = False
    transcribe_enabled: bool = False
    subtitle_priority: bool = False
    asr_engine: str = "funasr"
    transcript_save_local: bool = False
    transcript_save_oss: bool = False
    batch_mode: str = "separate"
    merge_title: str = ""
    summary_enabled: bool = False
    summary_model: str = "qwen"
    summary_prompt_title: str = "默认总结"
    save_to_db: bool = False
    dashscope_api_key: str = ""
    qwen_api_key: str = ""
    oss_access_key_id: str = ""
    oss_access_key_secret: str = ""
    oss_bucket_name: str = ""
    oss_endpoint: str = ""
    audio_local_base_path: str = "./output"
    transcript_local_base_path: str = "./output"
    temp_dir: str = "./temp"
    push_notion_enabled: bool = False
    push_feishu_enabled: bool = False
    notion_integration_token: str = ""
    notion_database_id: str = ""
    feishu_app_id: str = ""
    feishu_app_secret: str = ""
    feishu_bitable_app_token: str = ""
    feishu_table_id: str = ""
    db_engine: str = "sqlite"
    sqlite_path: str = ""
    supabase_url: str = ""
    supabase_key: str = ""
    supabase_table: str = "records"
    filename_clean_regex: str = ""
    filename_temp_rules: List[str] = Field(default_factory=list)
    filename_regex_library: List[Dict[str, Any]] = Field(default_factory=list)
    filename_selected_regex_ids: List[str] = Field(default_factory=list)


def process_config_from_merged(merged: Dict[str, Any]) -> ProcessConfig:
    filled = dict(DEFAULT_CONFIG_DICT)
    filled.update(merged)
    return ProcessConfig.model_validate(filled)


class SourceFile(BaseModel):
    model_config = ConfigDict(extra="ignore")

    filename: str
    original_filename: str
    audio_local_path: Optional[str] = None
    audio_oss_url: Optional[str] = None
    caption_local_path: Optional[str] = None
    caption_oss_url: Optional[str] = None


class ProcessResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    title: str
    source_files: List[SourceFile] = Field(default_factory=list)
    captions: Optional[str] = None
    summary: Optional[str] = None
    status: str
    recognition_type: Optional[str] = None
    record_uuid: Optional[str] = None
    record_id: Optional[int] = None
    error_msg: Optional[str] = None


class BatchFileItem(BaseModel):
    model_config = ConfigDict(extra="ignore")

    filename: str
    temp_path: str


class BatchProcessRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    config: Optional[Dict[str, Any]] = None
    files: List[BatchFileItem] = Field(default_factory=list)
