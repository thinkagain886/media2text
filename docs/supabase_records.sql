-- =============================================================================
-- media2text：Supabase 历史表 `public.records` 建表脚本
-- -----------------------------------------------------------------------------
-- 在 Supabase 控制台：SQL Editor → New query，粘贴后执行。
-- 应用里「设置 → 数据库」中表名默认为 records；若改表名，请同步改 SQL 与配置。
-- 后端使用 service_role 密钥时可绕过 RLS；若仅 anon key，需自行添加 RLS 策略（见末尾说明）。
-- =============================================================================

CREATE TABLE IF NOT EXISTS public.records (
    id BIGSERIAL PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    record_uuid TEXT NOT NULL,
    task_id TEXT NOT NULL DEFAULT '',
    category TEXT NOT NULL DEFAULT '默认分类',
    batch_mode TEXT NOT NULL DEFAULT '单数据',
    title TEXT NOT NULL DEFAULT '',

    -- JSON 数组字符串，如 [{"filename":"...","audio_oss_url":...}]
    source_files TEXT NOT NULL DEFAULT '[]',

    captions TEXT,
    summary TEXT,
    status TEXT NOT NULL DEFAULT 'success',

    transcript_on_oss BOOLEAN NOT NULL DEFAULT false,
    has_summary BOOLEAN NOT NULL DEFAULT false,
    notion_pushed BOOLEAN NOT NULL DEFAULT false,
    feishu_pushed BOOLEAN NOT NULL DEFAULT false,

    CONSTRAINT records_record_uuid_key UNIQUE (record_uuid)
);

-- 与 SQLite 中按时间、分页使用习惯一致
CREATE INDEX IF NOT EXISTS idx_records_created_at ON public.records (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_records_task_id ON public.records (task_id);

-- 任意列更新时刷新 updated_at（与 SQLite 侧多处显式写 updated_at 行为对齐）
CREATE OR REPLACE FUNCTION public.set_records_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $fn$
BEGIN
    NEW.updated_at := now();
    RETURN NEW;
END;
$fn$;

DROP TRIGGER IF EXISTS tr_records_updated_at ON public.records;
CREATE TRIGGER tr_records_updated_at
    BEFORE UPDATE ON public.records
    FOR EACH ROW
    EXECUTE PROCEDURE public.set_records_updated_at();

-- ---------------------------------------------------------------------------
-- Row Level Security（按你的密钥类型二选一）
-- ---------------------------------------------------------------------------
-- 1）后端使用 Project Settings → API → service_role 密钥：可保持关闭 RLS，或开启并添加放行策略。
-- 2）若从前端用 anon 直连：必须配置 policy。

ALTER TABLE public.records ENABLE ROW LEVEL SECURITY;

-- 示例：仅允许 service_role 全表（适合自建后端用 service key；按实际安全需求收紧）
-- CREATE POLICY "service_role_all_records"
--     ON public.records
--     FOR ALL
--     TO service_role
--     USING (true)
--     WITH CHECK (true);

-- 若需关闭 RLS（仅本机/可信环境，不推荐生产裸奔）：
-- ALTER TABLE public.records DISABLE ROW LEVEL SECURITY;

COMMENT ON TABLE public.records IS 'media2text 历史记录；与 db_supabase / SQLite records 列一致。';
