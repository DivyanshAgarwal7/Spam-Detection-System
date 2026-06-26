const { generatePdfReport } = require('../utils/pdfGenerator');
const History = require('../models/History');

const exportPdfReport = async (req, res) => {
  try {
    // Get analytics data to include in the report
    const total = await History.countDocuments({ user: req.user.id });
    const spam = await History.countDocuments({ user: req.user.id, prediction: { $in: ['spam', 'smishing', 'malicious'] } });
    const nonSpam = await History.countDocuments({ user: req.user.id, prediction: { $in: ['ham', 'safe'] } });
    
    let spamPercentage = 0;
    if (total > 0) {
      spamPercentage = (spam / total) * 100;
    }

    const analyticsData = {
      total,
      spam,
      nonSpam,
      spamPercentage
    };

    await generatePdfReport(req, res, analyticsData);
  } catch (error) {
    console.error('Export PDF Error:', error);
    res.status(500).json({ error: 'Server error while generating PDF report' });
  }
};

module.exports = {
  exportPdfReport
};
