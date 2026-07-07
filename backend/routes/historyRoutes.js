const express = require("express");
const router = express.Router();

const {
  getHistory,
  searchHistory,
  deleteHistoryItem,
  clearHistory,
  bulkDeleteHistory,
} = require("../controllers/historyController");

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

router.get('/count', protect, async (req, res) => {
  try {
    const count = await History.countDocuments({ user: req.user.id });
    res.json({ success: true, count });
  } catch (error) {
    console.error('Count error:', error.message);
    res.status(500).json({ success: false, error: error.message });
  }
});
module.exports = router;