// src/utils/dispatchWebhook.js
const net = require('net');
const User = require('../models/User');
const WebhookDelivery = require('../models/WebhookDelivery');

/**
 * Checks if a webhook URL is safe from SSRF attacks.
 * @param {string} webhookUrl - The webhook URL to validate.
 * @returns {boolean} - True if the URL is safe, false otherwise.
 */
const isSafeWebhookUrl = (webhookUrl) => {
  try {
    const parsed = new URL(webhookUrl);
    if (!['http:', 'https:'].includes(parsed.protocol)) return false;

    const host = parsed.hostname.toLowerCase();
    if (host === 'localhost') return false;

    if (net.isIP(host)) {
      if (host.startsWith('127.') || host.startsWith('10.') || host.startsWith('192.168.') || host.startsWith('169.254.')) return false;
      const parts = host.split('.');
      if (parts.length === 4) {
        const first = parseInt(parts[0], 10);
        const second = parseInt(parts[1], 10);
        if (first === 172 && second >= 16 && second <= 31) return false;
        if (first === 0) return false;
      }
      if (host === '::1' || host.startsWith('fe80:') || host.startsWith('fc00:') || host.startsWith('fd00:')) return false;
    }
    return true;
  } catch (e) {
    return false;
  }
};

/**
 * Enqueues a high-risk threat alert for reliable webhook delivery.
 * @param {string} userId - The ID of the user to send the webhook for.
 * @param {Object} payload - The threat details payload.
 */
const dispatchWebhook = async (userId, payload) => {
  try {
    const user = await User.findById(userId);
    if (user && user.webhookUrl) {
      if (!isSafeWebhookUrl(user.webhookUrl)) {
        console.warn(`[Webhook Blocked] SSRF protection prevented queueing request to: ${user.webhookUrl}`);
        return;
      }

      console.log(`[Webhook] Enqueueing threat alert to: ${user.webhookUrl}`);

      // Insert into retry queue (processed by webhookRetryCron)
      await WebhookDelivery.create({
        userId: user._id,
        url: user.webhookUrl,
        payload: {
          event: 'high_risk_threat_detected',
          timestamp: new Date().toISOString(),
          threat_details: payload
        }
      });
    }
  } catch (err) {
    console.error('[Webhook Error] Error enqueuing webhook:', err.message);
  }
};

module.exports = dispatchWebhook;