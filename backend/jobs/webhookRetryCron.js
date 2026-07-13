const cron = require('node-cron');
const axios = require('axios');
const WebhookDelivery = require('../models/WebhookDelivery');
const net = require('net');

/**
 * Checks if a webhook URL is safe from SSRF attacks.
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

const processWebhooks = async () => {
  try {
    while (true) {
      const now = new Date();
      const leaseTimeout = new Date(now.getTime() - 5 * 60 * 1000); // 5 minutes ago

      // Atomic claim
      const job = await WebhookDelivery.findOneAndUpdate(
        {
          $or: [
            { status: { $in: ['pending', 'failed'] }, nextRetry: { $lte: now } },
            { status: 'processing', lockedAt: { $lt: leaseTimeout } }
          ]
        },
        {
          $set: {
            status: 'processing',
            lockedAt: now
          }
        },
        { new: true, sort: { nextRetry: 1 } }
      );

      // If no jobs are eligible, exit the loop
      if (!job) {
        break;
      }

      // Check SSRF immediately before delivery
      if (!isSafeWebhookUrl(job.url)) {
        console.warn(`[Webhook Blocked] SSRF validation failed for job ${job._id} right before delivery.`);
        job.status = 'rejected';
        job.lastError = 'SSRF validation failed immediately prior to delivery';
        job.lockedAt = null;
        await job.save();
        continue; // process next job
      }

      // Attempt to dispatch
      try {
        await axios.post(job.url, job.payload, { timeout: 10000 }); // 10s timeout
        
        // Success
        job.status = 'success';
        job.attempts += 1;
        job.lastError = null;
        job.lockedAt = null;
        await job.save();
        
      } catch (err) {
        // Failure
        job.attempts += 1;
        job.lastError = err.message;
        job.lockedAt = null;
        
        if (job.attempts >= job.maxAttempts) {
          job.status = 'max_attempts_exceeded';
        } else {
          job.status = 'failed';
          // Exponential backoff: 2^(attempts-1) minutes
          // attempts = 1 -> 1 min
          // attempts = 2 -> 2 min
          // attempts = 3 -> 4 min
          // attempts = 4 -> 8 min
          const delayMs = (2 ** (job.attempts - 1)) * 60 * 1000;
          job.nextRetry = new Date(Date.now() + delayMs);
        }
        await job.save();
      }
    }
  } catch (err) {
    console.error('[Webhook Cron] Error processing webhooks:', err.message);
  }
};

// Schedule job to run every minute
cron.schedule('* * * * *', () => {
  processWebhooks();
});

module.exports = { processWebhooks, isSafeWebhookUrl }; // Exported for testing
