const { generatePdfReport } = require("../utils/pdfGenerator");
const History = require("../models/History");

const exportPdfReport = async (req, res) => {
  try {
    const [analytics] = await History.aggregate([
      {
        $match: {
          user: req.user.id,
        },
      },
      {
        $group: {
          _id: null,

          total: {
            $sum: 1,
          },

          spam: {
            $sum: {
              $cond: [
                {
                  $in: [
                    "$prediction",
                    ["spam", "smishing", "malicious"],
                  ],
                },
                1,
                0,
              ],
            },
          },

          nonSpam: {
            $sum: {
              $cond: [
                {
                  $in: [
                    "$prediction",
                    ["ham", "safe"],
                  ],
                },
                1,
                0,
              ],
            },
          },
        },
      },
    ]);

    const total = analytics?.total || 0;
    const spam = analytics?.spam || 0;
    const nonSpam = analytics?.nonSpam || 0;

    const spamPercentage =
      total > 0 ? (spam / total) * 100 : 0;

    const analyticsData = {
      total,
      spam,
      nonSpam,
      spamPercentage,
    };

    await generatePdfReport(req, res, analyticsData);
  } catch (error) {
    console.error("Export PDF Error:", error);
    res.status(500).json({
      error: "Server error while generating PDF report",
    });
  }
};

module.exports = {
  exportPdfReport,
};