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
  pattern: {
    type: String,
    required: true,
    trim: true,
    lowercase: true
  }
}, { timestamps: true });

// Prevent duplicate rules for the same user
ruleSchema.index({ user: 1, type: 1, pattern: 1 }, { unique: true });

module.exports = mongoose.model('Rule', ruleSchema);
