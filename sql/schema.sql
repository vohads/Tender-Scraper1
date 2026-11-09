-- Namibia Public Enterprises Tender Scraper
-- MySQL schema

CREATE DATABASE IF NOT EXISTS namibia_tenders
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE namibia_tenders;

CREATE TABLE IF NOT EXISTS entities (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    name          VARCHAR(150) NOT NULL,
    short_name    VARCHAR(50)  NOT NULL UNIQUE,
    base_url      VARCHAR(255) NOT NULL,
    tender_url    VARCHAR(255) DEFAULT NULL,
    is_active     TINYINT(1)   NOT NULL DEFAULT 1,
    created_at    TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    updated_at    TIMESTAMP    DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS tenders (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    entity_id       INT          NOT NULL,
    title           VARCHAR(500) NOT NULL,
    reference       VARCHAR(150) DEFAULT NULL,
    description     TEXT         DEFAULT NULL,
    closing_date    DATE         DEFAULT NULL,
    closing_time    VARCHAR(20)  DEFAULT NULL,
    status          ENUM('open','closed','cancelled','under_evaluation','unknown') NOT NULL DEFAULT 'unknown',
    document_url    VARCHAR(500) DEFAULT NULL,
    source_url      VARCHAR(500) NOT NULL,
    scraped_at      TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    first_seen_at   TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_seen_at    TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    is_active       TINYINT(1)   NOT NULL DEFAULT 1,

    UNIQUE KEY uq_entity_ref_title (entity_id, reference(100), title(200)),
    KEY idx_closing_date (closing_date),
    KEY idx_status (status),
    KEY idx_entity_status (entity_id, status),
    CONSTRAINT fk_tenders_entity FOREIGN KEY (entity_id) REFERENCES entities(id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS scrape_runs (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    started_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    finished_at     TIMESTAMP NULL,
    entities_scraped INT      DEFAULT 0,
    tenders_found   INT      DEFAULT 0,
    tenders_new     INT      DEFAULT 0,
    errors          INT      DEFAULT 0,
    status          ENUM('running','success','partial','failed') DEFAULT 'running',
    notes           TEXT
) ENGINE=InnoDB;

-- Seed the entities we care about
INSERT INTO entities (name, short_name, base_url, tender_url) VALUES
('Agricultural Bank of Namibia', 'Agribank', 'https://www.agribank.com.na/', 'https://agribank.com.na/page/bidders'),
('Development Bank of Namibia', 'DBN', 'https://www.dbn.com.na/', 'https://www.dbn.com.na/invitation-of-bids-clarifications/'),
('Environmental Investment Fund of Namibia', 'EIF', 'https://www.eifnamibia.com/', NULL),
('Game Products Trust Fund', 'GPTF', 'https://www.gptf.org.na/', NULL),
('Namibia National Reinsurance Corporation', 'NamibRe', 'https://namibre.com/', NULL),
('National Housing Enterprise', 'NHE', 'https://www.nhe.com.na/', 'https://www.nhe.com.na/open-bids/'),
('Road Fund Administration', 'RFA', 'https://www.rfanam.com.na/', NULL),
('Social Security Commission', 'SSC', 'https://www.ssc.org.na/', NULL),
('Epangelo Mining Company', 'Epangelo', 'https://www.epangelomining.na/', NULL),
('Meat Corporation of Namibia', 'Meatco', 'https://www.meatco.com.na/', NULL),
('Mobile Telecommunications Limited', 'MTC', 'https://www.mtc.com.na/', 'https://www.mtc.com.na/procurement/tenders'),
('Namibia Airports Company', 'NAC', 'https://www.airports.com.na/', NULL),
('Namib Desert Diamonds', 'Namdia', 'https://namdia.na/', NULL),
('Namibia Industrial Development Agency', 'NIDA', 'https://www.nida.com.na/', NULL),
('Namibia Post Limited', 'NamPost', 'https://www.nampost.com.na/', NULL)
ON DUPLICATE KEY UPDATE
  name = VALUES(name),
  base_url = VALUES(base_url),
  tender_url = VALUES(tender_url);