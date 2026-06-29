const History = require("../models/History");
const mongoose = require("mongoose");

// Get logged-in user's history
const getHistory = async (req, res) => {
  try {
    //Get pagination parameters from query
    const page = Math.max(1, parseInt(req.query.page) || 1);
    const limit = parseInt(req.query.limit) || 10;
    const safeLimit = Math.min(limit, 100); // Limit to 100 items per page
    const skip = (page - 1) * safeLimit;

    //Get total count and Paginated data
    const total = await History.countDocuments({ user: req.user.id });
    const history = await History.find({ user: req.user.id })
      .sort({ createdAt: -1 })
      .skip(skip)
      .limit(safeLimit);

    const totalPages = Math.ceil(total / safeLimit);

    res.json({
      success: true,
      data:history,
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
    const historyItem = await History.findOneAndDelete({
      _id: req.params.id,
      user: req.user.id,
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
    await History.deleteMany({ user: req.user.id });

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