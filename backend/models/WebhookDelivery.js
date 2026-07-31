const mongoose = require('mongoose');

const webhookDeliverySchema = new mongoose.Schema(
  {
    userId: {
      type: mongoose.Schema.Types.ObjectId,
      ref: 'User',
      required: true,
    },
    url: {
      type: String,
      required: true,
      trim: true,
    },
    payload: {
      type: mongoose.Schema.Types.Mixed,
      required: true,
    },
    status: {
      type: String,
      enum: ['pending', 'processing', 'failed', 'success', 'max_attempts_exceeded', 'rejected'],
      default: 'pending',
    },
    attempts: {
      type: Number,
      default: 0,
    },
    maxAttempts: {
      type: Number,
      default: 5,
    },
    nextRetry: {
      type: Date,
      default: Date.now,
    },
    lastError: {
      type: String,
      default: null,
    },
    lockedAt: {
      type: Date,
      default: null,
    },
  },
  {
    timestamps: true,
  }
);

// Indexes to speed up the cron job query
webhookDeliverySchema.index({ status: 1, nextRetry: 1 });
webhookDeliverySchema.index({ status: 1, lockedAt: 1 });

module.exports = mongoose.model('WebhookDelivery', webhookDeliverySchema);
