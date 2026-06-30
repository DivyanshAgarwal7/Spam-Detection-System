const mongoose = require('mongoose');

const ruleSchema = new mongoose.Schema({
  user: {
    type: mongoose.Schema.Types.ObjectId,
    ref: 'User',
    required: true
  },
  type: {
    type: String,
    enum: ['blacklist', 'whitelist'],
    required: true
  },
  // Distinguishes sender-based rules (email/domain) from keyword/phrase rules
  // that match message content. Defaults to 'sender' so existing rules and
  // older API clients keep working unchanged.
  ruleCategory: {
    type: String,
    enum: ['sender', 'keyword'],
    default: 'sender',
    required: true
  },
  pattern: {
    type: String,
    required: true,
    trim: true,
    lowercase: true
  }
}, { timestamps: true });

// Prevent duplicate rules for the same user (scoped per category)
ruleSchema.index({ user: 1, ruleCategory: 1, type: 1, pattern: 1 }, { unique: true });

module.exports = mongoose.model('Rule', ruleSchema);
