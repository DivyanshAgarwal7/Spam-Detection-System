const Rule = require("../models/Rule");

// Get all rules for the logged-in user
const getRules = async (req, res) => {
  try {
    const page = parseInt(req.query.page) || 1;
    const limit = parseInt(req.query.limit) || 100;
    const safeLimit = Math.min(limit, 100);
    const skip = (page - 1) * safeLimit;

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

// Add a new rule
const addRule = async (req, res) => {
  try {
    const { type, pattern } = req.body;
    
    if (!type || !pattern) {
      return res.status(400).json({ error: "Type and pattern are required" });
    }
    
    const lowerType = type.toLowerCase();
    if (lowerType !== "blacklist" && lowerType !== "whitelist") {
      return res.status(400).json({ error: "Type must be either blacklist or whitelist" });
    }
    
    const trimmedPattern = pattern.trim().toLowerCase();
    if (!trimmedPattern) {
      return res.status(400).json({ error: "Pattern cannot be empty" });
    }
    
    // Validate pattern: check if it's a valid email or domain
    const isValidEmail = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(trimmedPattern);
    const isValidDomain = /^(?:@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)|(?:[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)$/.test(trimmedPattern);
    
    if (!isValidEmail && !isValidDomain) {
      return res.status(400).json({ error: "Pattern must be a valid email address (e.g. user@domain.com) or domain (e.g. @domain.com or domain.com)" });
    }

    // Check if the rule already exists
    const existingRule = await Rule.findOne({
      user: req.user.id,
      type: lowerType,
      pattern: trimmedPattern,
    });
    
    if (existingRule) {
      return res.status(400).json({ error: "This rule already exists" });
    }

    const newRule = await Rule.create({
      user: req.user.id,
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

// Delete a rule
const deleteRule = async (req, res) => {
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
