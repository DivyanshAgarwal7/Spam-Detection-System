const express = require("express");
const router = express.Router();

const {
  getHistory,
  searchHistory,
  deleteHistoryItem,
  clearHistory,
} = require("../controllers/historyController");

const { protect } = require("../middleware/authMiddleware");

router.use(protect);
// Get logged-in user's history
router.get("/", getHistory);

// Search user's history
router.get("/search", searchHistory);

// Bulk delete history items
router.delete("/bulk-delete", async (req, res) => {
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
    console.error("Bulk delete histoy error: ", error);
    res.status(500).json({ 
      success: false, 
      message: "Internal server error"
    });
  }
});

// Delete one history item
router.delete("/:id", deleteHistoryItem);

// Clear all history
router.delete("/", clearHistory);

module.exports = router;