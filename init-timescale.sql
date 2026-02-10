-- 自動啟用 TimescaleDB 擴展
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- OCR 任務狀態機
DROP TABLE IF EXISTS ocr_tasks CASCADE;
DROP TABLE IF EXISTS ocr_front_results CASCADE;
DROP TABLE IF EXISTS ocr_back_results CASCADE;
DROP TABLE IF EXISTS stores CASCADE;

CREATE TABLE ocr_tasks (
    id SERIAL PRIMARY KEY,
    file_id VARCHAR(255) NOT NULL,
    file_name VARCHAR(500) NOT NULL,
    store_name VARCHAR(255),
    side VARCHAR(10),
    business_folder VARCHAR(255),
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    error_message TEXT,
    image_path VARCHAR(500),
    modified_time TIMESTAMPTZ,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT uq_ocr_tasks_file_modified UNIQUE (file_id, modified_time)
);

COMMENT ON TABLE ocr_tasks IS 'OCR 任務狀態機';
COMMENT ON COLUMN ocr_tasks.status IS 'pending → downloaded → processing → completed → failed';

CREATE INDEX IF NOT EXISTS idx_ocr_tasks_status ON ocr_tasks (status);

-- 店家主檔

CREATE TABLE stores (
    store_name VARCHAR(255) NOT NULL,
    business_folder VARCHAR(255),
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT stores_pk PRIMARY KEY (store_name)
);

COMMENT ON TABLE stores IS '店家主檔';
COMMENT ON COLUMN stores.store_name IS '店名（從檔名解析）';
COMMENT ON COLUMN stores.business_folder IS '所屬業務目錄';

-- 身分證正面 OCR 結果
CREATE TABLE ocr_front_results (
    file_name VARCHAR(500) NOT NULL,
    time TIMESTAMPTZ NOT NULL,
    file_id VARCHAR(255),
    store_name VARCHAR(255) NOT NULL,

    name VARCHAR(100),
    id_number VARCHAR(20),
    birthday VARCHAR(20),
    gender VARCHAR(10),
    issue_date VARCHAR(20),
    issue_type VARCHAR(20),
    issue_location VARCHAR(50),

    confidence NUMERIC(5, 2),
    raw_text TEXT,
    update_ts TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    create_ts TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT ocr_front_results_pk PRIMARY KEY (file_name, time),
    CONSTRAINT fk_front_store FOREIGN KEY (store_name) REFERENCES stores(store_name)
);

COMMENT ON TABLE ocr_front_results IS '身分證正面 OCR 結果';
COMMENT ON COLUMN ocr_front_results.file_name IS '檔名';
COMMENT ON COLUMN ocr_front_results.time IS 'Google Drive 檔案修改時間';
COMMENT ON COLUMN ocr_front_results.file_id IS 'Google Drive File ID';
COMMENT ON COLUMN ocr_front_results.store_name IS '店名';
COMMENT ON COLUMN ocr_front_results.name IS '負責人姓名';
COMMENT ON COLUMN ocr_front_results.id_number IS '身分證字號';
COMMENT ON COLUMN ocr_front_results.birthday IS '出生日期';
COMMENT ON COLUMN ocr_front_results.gender IS '性別';
COMMENT ON COLUMN ocr_front_results.issue_date IS '發證日期';
COMMENT ON COLUMN ocr_front_results.issue_type IS '發證類型（初發/換發/補發）';
COMMENT ON COLUMN ocr_front_results.issue_location IS '發證地點';
COMMENT ON COLUMN ocr_front_results.confidence IS 'OCR 辨識信心度';
COMMENT ON COLUMN ocr_front_results.raw_text IS 'OCR 原始辨識文字';

SELECT create_hypertable('ocr_front_results', 'time',
                        chunk_time_interval => INTERVAL '7 days',
                        if_not_exists => TRUE);

CREATE INDEX IF NOT EXISTS idx_front_store_time
ON ocr_front_results (store_name, time DESC);

-- 身分證反面 OCR 結果
CREATE TABLE ocr_back_results (
    file_name VARCHAR(500) NOT NULL,
    time TIMESTAMPTZ NOT NULL,
    file_id VARCHAR(255),
    store_name VARCHAR(255) NOT NULL,

    father VARCHAR(100),
    mother VARCHAR(100),
    spouse VARCHAR(100),
    military_service VARCHAR(100),
    birthplace VARCHAR(100),
    address TEXT,

    confidence NUMERIC(5, 2),
    raw_text TEXT,
    update_ts TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    create_ts TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT ocr_back_results_pk PRIMARY KEY (file_name, time),
    CONSTRAINT fk_back_store FOREIGN KEY (store_name) REFERENCES stores(store_name)
);

COMMENT ON TABLE ocr_back_results IS '身分證反面 OCR 結果';
COMMENT ON COLUMN ocr_back_results.file_name IS '檔名';
COMMENT ON COLUMN ocr_back_results.time IS 'Google Drive 檔案修改時間';
COMMENT ON COLUMN ocr_back_results.file_id IS 'Google Drive File ID';
COMMENT ON COLUMN ocr_back_results.store_name IS '店名';
COMMENT ON COLUMN ocr_back_results.father IS '父';
COMMENT ON COLUMN ocr_back_results.mother IS '母';
COMMENT ON COLUMN ocr_back_results.spouse IS '配偶';
COMMENT ON COLUMN ocr_back_results.military_service IS '役別';
COMMENT ON COLUMN ocr_back_results.birthplace IS '出生地';
COMMENT ON COLUMN ocr_back_results.address IS '戶籍地址';
COMMENT ON COLUMN ocr_back_results.confidence IS 'OCR 辨識信心度';
COMMENT ON COLUMN ocr_back_results.raw_text IS 'OCR 原始辨識文字';

SELECT create_hypertable('ocr_back_results', 'time',
                        chunk_time_interval => INTERVAL '7 days',
                        if_not_exists => TRUE);

CREATE INDEX IF NOT EXISTS idx_back_store_time
ON ocr_back_results (store_name, time DESC);
