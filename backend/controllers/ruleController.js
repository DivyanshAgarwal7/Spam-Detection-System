const Rule = require("../models/Rule");
const { validateKeywordPattern } = require("../utils/keywordRules");
const { getPaginationParams } = require("../utils/pagination");
const mongoose = require("mongoose");

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

const validatePattern = (pattern) => {
  if (!pattern || typeof pattern !== 'string') {
    return { valid: false, error: 'Pattern must be a non-empty string' };
  }

  const trimmed = pattern.trim();
  
  if (trimmed.length === 0) {
    return { valid: false, error: 'Pattern cannot be empty' };
  }

  if (trimmed.length > MAX_PATTERN_LENGTH) {
    return { 
      valid: false, 
      error: `Pattern cannot exceed ${MAX_PATTERN_LENGTH} characters` 
    };
  }

  if (trimmed.includes(' ')) {
    return { valid: false, error: 'Email or domain cannot contain spaces' };
  }

  if (trimmed.startsWith('*.')) {
    const domainPart = trimmed.slice(2);
    if (!domainPart || domainPart.length < 3) {
      return { valid: false, error: 'Invalid wildcard domain format. Use *.domain.com' };
    }
    if (!validateDomain(trimmed)) {
      return { valid: false, error: 'Invalid wildcard domain format. Use *.domain.com' };
    }
    return { valid: true, value: trimmed.toLowerCase() };
  }

  if (trimmed.startsWith('@')) {
    const domainPart = trimmed.slice(1);
    if (!domainPart || domainPart.length < 3) {
      return { valid: false, error: 'Invalid domain format. Use @domain.com' };
    }
    if (!validateDomain(trimmed)) {
      return { valid: false, error: 'Invalid domain format. Use @domain.com' };
    }
    return { valid: true, value: trimmed.toLowerCase() };
  }

  if (trimmed.includes('@')) {
    if (!validateEmail(trimmed)) {
      return { valid: false, error: 'Invalid email format. Use user@domain.com' };
    }
    return { valid: true, value: trimmed.toLowerCase() };
  }

  if (validateDomain(trimmed)) {
    return { valid: true, value: trimmed.toLowerCase() };
  }

  return { 
    valid: false, 
    error: 'Pattern must be a valid email (user@domain.com), domain (domain.com or @domain.com), or wildcard (*.domain.com)' 
  };
};

const checkRuleConflict = async (userId, type, pattern, category) => {
  const trimmedPattern = pattern.toLowerCase().trim();
  
  if (type === 'blacklist') {
    const conflict = await Rule.findOne({
      user: userId,
      ruleCategory: category,
      type: 'whitelist',
      pattern: { $regex: new RegExp('^' + trimmedPattern + '$', 'i') }
    });
    if (conflict) {
      return { 
        hasConflict: true, 
        message: 'This pattern already exists in your whitelist. Remove it from whitelist first.' 
      };
    }
  }

  if (type === 'whitelist') {
    const conflict = await Rule.findOne({
      user: userId,
      ruleCategory: category,
      type: 'blacklist',
      pattern: { $regex: new RegExp('^' + trimmedPattern + '$', 'i') }
    });
    if (conflict) {
      return { 
        hasConflict: true, 
        message: 'This pattern already exists in your blacklist. Remove it from blacklist first.' 
      };
    }
  }

  return { hasConflict: false };
};

const getRules = async (req, res) => {
  try {
    const { page, safeLimit, skip } = getPaginationParams(req.query, 100, 100);

    const total = await Rule.countDocuments({ user: req.user.id });
    const rules = await Rule.find({ user: req.user.id })
      .sort({ createdAt: -1 })
      .skip(skip)
      .limit(safeLimit);

    res.json({
      success: true,
      data: rules,
      pagination: {
        total,
        page,
        limit: safeLimit,
        totalPages: Math.ceil(total / safeLimit),
      }
    });
  } catch (err) {
    console.error("Get rules error:", err);
    res.status(500).json({ error: "Server error" });
  }
};

const addRule = async (req, res) => {
  try {
    const { type, pattern, ruleCategory } = req.body;

    if (!type || !pattern) {
      return res.status(400).json({ error: "Type and pattern are required" });
    }

    const lowerType = type.toLowerCase();
    if (lowerType !== "blacklist" && lowerType !== "whitelist") {
      return res.status(400).json({ error: "Type must be either blacklist or whitelist" });
    }

    const category = (ruleCategory || "sender").toLowerCase();
    if (category !== "sender" && category !== "keyword") {
      return res.status(400).json({ error: "ruleCategory must be either sender or keyword" });
    }

    let trimmedPattern;
    if (category === "keyword") {
      const result = validateKeywordPattern(pattern);
      if (!result.valid) {
        return res.status(400).json({ error: result.error });
      }
      trimmedPattern = result.value;
    } else {
      const validation = validatePattern(pattern);
      if (!validation.valid) {
        return res.status(400).json({ error: validation.error });
      }
      trimmedPattern = validation.value;
    }

    const ruleCount = await Rule.countDocuments({ user: req.user.id });
    if (ruleCount >= 500) {
      return res.status(400).json({ error: "Maximum rule limit reached (500). Please delete some old rules before adding new ones." });
    }

    const existingRule = await Rule.findOne({
      user: req.user.id,
      ruleCategory: category,
      type: lowerType,
      pattern: { $regex: new RegExp('^' + trimmedPattern + '$', 'i') }
    });

    if (existingRule) {
      return res.status(400).json({ error: "This rule already exists" });
    }

    const conflict = await checkRuleConflict(req.user.id, lowerType, trimmedPattern, category);
    if (conflict.hasConflict) {
      return res.status(409).json({ error: conflict.message });
    }

    const newRule = await Rule.create({
      user: req.user.id,
      ruleCategory: category,
      type: lowerType,
      pattern: trimmedPattern,
    });
    
    res.status(201).json({
      success: true,
      data: newRule,
    });
  } catch (err) {
    console.error("Add rule error:", err);
    res.status(500).json({ error: "Server error" });
  }
};

const deleteRule = async (req, res) => {
  if (!mongoose.Types.ObjectId.isValid(req.params.id)) {
    return res.status(400).json({ error: "Invalid rule id" });
  }

  try {
    const rule = await Rule.findOneAndDelete({
      _id: req.params.id,
      user: req.user.id,
    });

    if (!rule) {
      return res.status(404).json({ error: "Rule not found" });
    }

    res.json({
      success: true,
      message: "Rule deleted successfully",
    });
  } catch (err) {
    console.error("Delete rule error:", err);
    res.status(500).json({ error: "Server error" });
  }
};

module.exports = {
  getRules,
  addRule,
  deleteRule,
};