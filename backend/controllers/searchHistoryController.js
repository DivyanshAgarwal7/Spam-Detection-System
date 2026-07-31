const SearchHistory = require('../models/searchHistory');
const logger = require('../utils/logger');

function isValidDate(dateString) {
  if (!dateString || typeof dateString !== 'string') return false;
  const date = new Date(dateString);
  return date instanceof Date && !isNaN(date.getTime());
}

function validateDateRange(startDate, endDate) {
  const errors = [];

  if (startDate) {
    if (!isValidDate(startDate)) {
      errors.push({
        field: 'startDate',
        value: startDate,
        message: 'Invalid startDate format. Use ISO 8601 date format (YYYY-MM-DD or YYYY-MM-DDTHH:mm:ss.sssZ)'
      });
    }
  }

  if (endDate) {
    if (!isValidDate(endDate)) {
      errors.push({
        field: 'endDate',
        value: endDate,
        message: 'Invalid endDate format. Use ISO 8601 date format (YYYY-MM-DD or YYYY-MM-DDTHH:mm:ss.sssZ)'
      });
    }
  }

  if (startDate && endDate && isValidDate(startDate) && isValidDate(endDate)) {
    const start = new Date(startDate);
    const end = new Date(endDate);
    if (start > end) {
      errors.push({
        field: 'dateRange',
        value: `${startDate} to ${endDate}`,
        message: 'startDate must be before or equal to endDate'
      });
    }
  }

  return errors;
}

const searchHistory = async (req, res) => {
  try {
    const { userId, startDate, endDate, limit = 20, page = 1 } = req.query;

    const dateErrors = validateDateRange(startDate, endDate);
    if (dateErrors.length > 0) {
      logger.warn('Date validation failed', { userId, startDate, endDate, errors: dateErrors });
      return res.status(400).json({
        success: false,
        error: 'Invalid date parameters',
        details: dateErrors,
        validFormats: [
          'YYYY-MM-DD (e.g., 2024-01-01)',
          'YYYY-MM-DDTHH:mm:ss.sssZ (e.g., 2024-01-01T00:00:00.000Z)'
        ]
      });
    }

    const query = { userId };

    if (startDate) {
      query.createdAt = query.createdAt || {};
      query.createdAt.$gte = new Date(startDate);
    }

    if (endDate) {
      query.createdAt = query.createdAt || {};
      query.createdAt.$lte = new Date(endDate);
    }

    const limitNum = Math.min(parseInt(limit) || 20, 100);
    const pageNum = Math.max(parseInt(page) || 1, 1);
    const skip = (pageNum - 1) * limitNum;

    const [results, total] = await Promise.all([
      SearchHistory.find(query)
        .sort({ createdAt: -1 })
        .skip(skip)
        .limit(limitNum)
        .lean(),
      SearchHistory.countDocuments(query)
    ]);

    logger.info('Search history retrieved', {
      userId,
      startDate,
      endDate,
      total,
      page: pageNum,
      limit: limitNum
    });

    res.status(200).json({
      success: true,
      data: results,
      pagination: {
        total,
        page: pageNum,
        limit: limitNum,
        totalPages: Math.ceil(total / limitNum),
        hasNextPage: pageNum * limitNum < total,
        hasPrevPage: pageNum > 1
      },
      filters: {
        startDate: startDate || null,
        endDate: endDate || null
      }
    });
  } catch (error) {
    logger.error('Error in searchHistory:', error);
    res.status(500).json({
      success: false,
      error: 'Internal server error',
      message: process.env.NODE_ENV === 'development' ? error.message : undefined
    });
  }
};

const getSearchHistory = async (req, res) => {
  try {
    const { userId, startDate, endDate, limit = 10, page = 1 } = req.query;

    if (!userId) {
      return res.status(400).json({
        success: false,
        error: 'userId is required'
      });
    }

    const dateErrors = validateDateRange(startDate, endDate);
    if (dateErrors.length > 0) {
      return res.status(400).json({
        success: false,
        error: 'Invalid date parameters',
        details: dateErrors
      });
    }

    const query = { userId };

    if (startDate) {
      query.timestamp = query.timestamp || {};
      query.timestamp.$gte = new Date(startDate);
    }

    if (endDate) {
      query.timestamp = query.timestamp || {};
      query.timestamp.$lte = new Date(endDate);
    }

    const limitNum = Math.min(parseInt(limit) || 10, 50);
    const pageNum = Math.max(parseInt(page) || 1, 1);
    const skip = (pageNum - 1) * limitNum;

    const [results, total] = await Promise.all([
      SearchHistory.find(query)
        .sort({ timestamp: -1 })
        .skip(skip)
        .limit(limitNum)
        .lean(),
      SearchHistory.countDocuments(query)
    ]);

    res.status(200).json({
      success: true,
      data: results,
      pagination: {
        total,
        page: pageNum,
        limit: limitNum,
        totalPages: Math.ceil(total / limitNum),
        hasNextPage: pageNum * limitNum < total,
        hasPrevPage: pageNum > 1
      }
    });
  } catch (error) {
    logger.error('Error in getSearchHistory:', error);
    res.status(500).json({
      success: false,
      error: 'Internal server error',
      message: process.env.NODE_ENV === 'development' ? error.message : undefined
    });
  }
};

const clearSearchHistory = async (req, res) => {
  try {
    const { userId } = req.params;

    if (!userId) {
      return res.status(400).json({
        success: false,
        error: 'userId is required'
      });
    }

    const result = await SearchHistory.deleteMany({ userId });

    logger.info('Search history cleared', { userId, deletedCount: result.deletedCount });

    res.status(200).json({
      success: true,
      message: 'Search history cleared successfully',
      deletedCount: result.deletedCount
    });
  } catch (error) {
    logger.error('Error in clearSearchHistory:', error);
    res.status(500).json({
      success: false,
      error: 'Internal server error',
      message: process.env.NODE_ENV === 'development' ? error.message : undefined
    });
  }
};

const deleteSearchHistoryItem = async (req, res) => {
  try {
    const { userId, historyId } = req.params;

    if (!userId) {
      return res.status(400).json({
        success: false,
        error: 'userId is required'
      });
    }

    if (!historyId) {
      return res.status(400).json({
        success: false,
        error: 'historyId is required'
      });
    }

    const result = await SearchHistory.findOneAndDelete({
      _id: historyId,
      userId: userId
    });

    if (!result) {
      return res.status(404).json({
        success: false,
        error: 'Search history item not found'
      });
    }

    logger.info('Search history item deleted', { userId, historyId });

    res.status(200).json({
      success: true,
      message: 'Search history item deleted successfully'
    });
  } catch (error) {
    logger.error('Error in deleteSearchHistoryItem:', error);
    res.status(500).json({
      success: false,
      error: 'Internal server error',
      message: process.env.NODE_ENV === 'development' ? error.message : undefined
    });
  }
};

const getSearchHistoryStats = async (req, res) => {
  try {
    const { userId } = req.query;

    if (!userId) {
      return res.status(400).json({
        success: false,
        error: 'userId is required'
      });
    }

    const [total, recent] = await Promise.all([
      SearchHistory.countDocuments({ userId }),
      SearchHistory.find({ userId })
        .sort({ timestamp: -1 })
        .limit(5)
        .lean()
    ]);

    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const todayCount = await SearchHistory.countDocuments({
      userId,
      timestamp: { $gte: today }
    });

    res.status(200).json({
      success: true,
      data: {
        totalSearches: total,
        todaySearches: todayCount,
        recentSearches: recent
      }
    });
  } catch (error) {
    logger.error('Error in getSearchHistoryStats:', error);
    res.status(500).json({
      success: false,
      error: 'Internal server error',
      message: process.env.NODE_ENV === 'development' ? error.message : undefined
    });
  }
};

module.exports = {
  searchHistory,
  getSearchHistory,
  clearSearchHistory,
  deleteSearchHistoryItem,
  getSearchHistoryStats,
  isValidDate,
  validateDateRange
};