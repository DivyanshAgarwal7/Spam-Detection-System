const mongoose = require('mongoose');

const MAX_PATTERN_LENGTH = 255;

const validateEmail = (email) => {
  return /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/.test(email);
};

const validateDomain = (domain) => {
  if (domain.startsWith('*.')) {
    const domainPart = domain.slice(2);
    return /^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/.test(domainPart);
  }
  if (domain.startsWith('@')) {
    const domainPart = domain.slice(1);
    return /^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/.test(domainPart);
  }
  return /^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/.test(domain);
};

const validatePattern = (value, ruleCategory) => {
  if (!value || typeof value !== 'string') {
    throw new Error('Pattern must be a non-empty string');
  }

  const trimmed = value.trim();
  if (trimmed.length === 0) {
    throw new Error('Pattern cannot be empty');
  }

  if (trimmed.length > MAX_PATTERN_LENGTH) {
    throw new Error(`Pattern cannot exceed ${MAX_PATTERN_LENGTH} characters`);
  }

  if (ruleCategory === 'keyword') {
    if (trimmed.length < 2) {
      throw new Error('Keyword must be at least 2 characters');
    }
    if (!/^[a-zA-Z0-9\s.,!?'"()-]+$/.test(trimmed)) {
      throw new Error('Keyword contains invalid characters');
    }
    return trimmed.toLowerCase();
  }

  if (trimmed.includes(' ')) {
    throw new Error('Email or domain cannot contain spaces');
  }

  if (trimmed.startsWith('*.')) {
    const domainPart = trimmed.slice(2);
    if (!domainPart || domainPart.length < 3) {
      throw new Error('Invalid wildcard domain format. Use *.domain.com');
    }
    if (!validateDomain(trimmed)) {
      throw new Error('Invalid wildcard domain format. Use *.domain.com');
    }
    return trimmed.toLowerCase();
  }

  if (trimmed.startsWith('@')) {
    const domainPart = trimmed.slice(1);
    if (!domainPart || domainPart.length < 3) {
      throw new Error('Invalid domain format. Use @domain.com');
    }
    if (!validateDomain(trimmed)) {
      throw new Error('Invalid domain format. Use @domain.com');
    }
    return trimmed.toLowerCase();
  }

  if (trimmed.includes('@')) {
    if (!validateEmail(trimmed)) {
      throw new Error('Invalid email format. Use user@domain.com');
    }
    return trimmed.toLowerCase();
  }

  if (validateDomain(trimmed)) {
    return trimmed.toLowerCase();
  }

  throw new Error('Pattern must be a valid email (user@domain.com), domain (domain.com or @domain.com), or wildcard (*.domain.com)');
};

const ruleSchema = new mongoose.Schema({
  user: {
    type: mongoose.Schema.Types.ObjectId,
    ref: 'User',
    required: [true, "User is required."]
  },
  type: {
    type: String,
    enum: {
      values: ['blacklist', 'whitelist'],
      message: "Type must be either 'blacklist' or 'whitelist'."
    },
    required: [true, "Type is required."]
  },
  ruleCategory: {
    type: String,
    enum: {
      values: ['sender', 'keyword'],
      message: "Rule category must be either 'sender' or 'keyword'."
    },
    default: 'sender',
    required: [true, "Rule category is required."]
  },
  pattern: {
    type: String,
    required: [true, "Pattern is required."],
    trim: true,
    lowercase: true,
    validate: {
      validator: function(value) {
        try {
          validatePattern(value, this.ruleCategory);
          return true;
        } catch (error) {
          return false;
        }
      },
      message: function(props) {
        try {
          validatePattern(props.value, this.ruleCategory);
          return 'Validation passed';
        } catch (error) {
          return error.message;
        }
      }
    }
  }
}, { timestamps: true });

ruleSchema.index({ user: 1, ruleCategory: 1, type: 1, pattern: 1 }, { unique: true });

module.exports = mongoose.model('Rule', ruleSchema);