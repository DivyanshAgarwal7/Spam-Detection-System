const express = require("express");
const router = express.Router();

const {
  getHistory,
  searchHistory,
  deleteHistoryItem,
  clearHistory,
  bulkDeleteHistory,
  getHistoryCount,
} = require("../controllers/historyController");

const History = require("../models/History");
const { protect } = require("../middleware/authMiddleware");

router.use(protect);

// Get logged-in user's history
router.get("/", getHistory);

// Search user's history
router.get("/search", searchHistory);

// Bulk delete history items
router.delete("/bulk-delete", bulkDeleteHistory);

// Delete one history item
router.delete("/:id", deleteHistoryItem);

// Clear all history
router.delete("/", clearHistory);

router.get('/count', getHistoryCount);

router.get('/recent', protect, async (req, res) => {
  try {
    const predictions = await History.find({ user: req.user.id })
      .sort({ createdAt: -1 })
      .limit(10)
      .select('query prediction createdAt');

    res.json(predictions);
  } catch (error) {
    res.status(500).json({ error: 'Failed to fetch recent activity' });
  }
});

module.exports = router;