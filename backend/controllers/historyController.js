const History = require("../models/History");
const mongoose = require("mongoose");

// Utility function to sanitize NoSQL inputs
const sanitizeInput = (v) => {
  if (v instanceof Object) {
    for (let key in v) {
      if (/^\$/.test(key)) {
        delete v[key];
      } else {
        sanitizeInput(v[key]);
      }
    }
  }
  return v;
};

// Get logged-in user's history
const getHistory = async (req, res) => {
  try {
    // Sanitize user ID to prevent NoSQL injection payload
    const safeUserId = sanitizeInput(req.user.id);

    //Get pagination parameters from query
    const page = Math.max(1, parseInt(req.query.page) || 1);
    const limit = parseInt(req.query.limit) || 10;
    const safeLimit = Math.min(limit, 100); // Limit to 100 items per page
    const skip = (page - 1) * safeLimit;

    //Get total count and Paginated data using sanitized ID
    const total = await History.countDocuments({ user: safeUserId });
    const history = await History.find({ user: safeUserId })
      .sort({ createdAt: -1 })
      .skip(skip)
      .limit(safeLimit);

    const totalPages = Math.ceil(total / safeLimit);

    res.json({
      success: true,
      data: history,
      pagination: {
        total,
        page,
        limit: safeLimit,
        totalPages,
        hasNextPage: page < totalPages,
        hasPrevPage: page > 1,
      },
    });
  } catch (err) {
    res.status(500).json({
      error: {
        code: "INTERNAL_SERVER_ERROR",
        message: "Server error",
      },
    });
  }
};

// Delete a single history item
const deleteHistoryItem = async (req, res) => {
  if (!mongoose.Types.ObjectId.isValid(req.params.id)) {
    return res.status(400).json({
      error: "Invalid history id",
    });
  }
  
  try {
    // Sanitize parameters
    const safeHistoryId = sanitizeInput(req.params.id);
    const safeUserId = sanitizeInput(req.user.id);

    const historyItem = await History.findOneAndDelete({
      _id: safeHistoryId,
      user: safeUserId,
    });

    if (!historyItem) {
      return res.status(404).json({ error: "History item not found" });
    }

    res.json({ message: "History item deleted" });
  } catch (err) {
    console.error("Delete history error:", err);
    res.status(500).json({ error: "Server error" });
  }
};

// Clear all history for logged-in user
const clearHistory = async (req, res) => {
  try {
    // Sanitize user ID before bulk delete
    const safeUserId = sanitizeInput(req.user.id);
    await History.deleteMany({ user: safeUserId });

    res.json({ message: "History cleared successfully" });
  } catch (err) {
    console.error("Clear history error:", err);
    res.status(500).json({ error: "Server error" });
  }
};

module.exports = {
  getHistory,
  deleteHistoryItem,
  clearHistory,
};