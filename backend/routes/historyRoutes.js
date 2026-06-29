const express = require("express");
const router = express.Router();

const {
  getHistory,
  deleteHistoryItem,
  clearHistory,
} = require("../controllers/historyController");

const { protect } = require("../middleware/authMiddleware");

// Get logged-in user's history
router.get("/", protect, getHistory);

// Bulk delete history items
router.delete("/bulk-delete", protect, async (req, res) => {
  try {
    const { ids } = req.body; // Expecting an array of IDs in the request body
    
    if (!ids || !Array.isArray(ids) || ids.length === 0) {
      return res.status(400).json({ 
        success: false, 
        message: "Invalid request. 'ids' must be a non-empty array." 
      });
    }

    const result = await History.deleteMany({ 
      _id: { $in: ids }, 
      user: req.user.id 
    });

    res.json({
      success: true,
      deletedCount: result.deletedCount,
      message: `${result.deletedCount} items deleted successfully`
    });

  } catch (error) {
    res.status(500).json({ 
      success: false, 
      message: error.message 
    });
  }
});

// Delete one history item
router.delete("/:id", protect, deleteHistoryItem);

// Clear all history
router.delete("/", protect, clearHistory);

module.exports = router;