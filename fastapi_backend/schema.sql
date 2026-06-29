-- Spam Detection System — MySQL Schema (Issue #13)
-- Run this in your MySQL client before starting the server

CREATE DATABASE IF NOT EXISTS spam_detection;
USE spam_detection;

CREATE TABLE IF NOT EXISTS emails (
    email_id  INT AUTO_INCREMENT PRIMARY KEY,
    subject   VARCHAR(255) NOT NULL,
    sender    VARCHAR(255) NOT NULL,
    is_spam   BOOLEAN      NOT NULL DEFAULT FALSE,
    timestamp DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Sample data for testing
INSERT INTO emails (subject, sender, is_spam) VALUES
    ('Win a FREE iPhone now!!!',    'promo@spam.com',        TRUE),
    ('Team standup at 10am',        'manager@company.com',   FALSE),
    ('You have won $1,000,000!',    'lucky@winner.net',      TRUE),
    ('Project update for Q3',       'colleague@company.com', FALSE),
    ('URGENT: Verify your account', 'noreply@phish.com',     TRUE),
    ('Lunch plans tomorrow?',       'friend@gmail.com',      FALSE);

-- Useful queries
-- All spam emails:
SELECT * FROM emails WHERE is_spam = TRUE ORDER BY timestamp DESC;

-- All legitimate emails:
SELECT * FROM emails WHERE is_spam = FALSE ORDER BY timestamp DESC;

-- Count spam:
SELECT COUNT(*) AS total_spam FROM emails WHERE is_spam = TRUE;

-- Count legitimate:
SELECT COUNT(*) AS total_legitimate FROM emails WHERE is_spam = FALSE;