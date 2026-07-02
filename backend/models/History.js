const mongoose = require("mongoose");

const historySchema = new mongoose.Schema(
  {
    user: {
      type: mongoose.Schema.Types.ObjectId,
      ref: "User",
      required: true,
    },
    query: {
      type: String,
      required: true,
      trim: true,
    },
    prediction: {
      type: String,
      required: true,
    },
    type: {
      type: String,
      required: true,
      enum: ["sms", "email", "url", "message"],
    },
    confidence: {
      type: Number,
    },
  },
  { timestamps: true }
);



// 1. Time-Series Index: Optimizes getTrends (filtering by user & sorting by date)
// Drastically improves performance for dashboard time-series charts.
historySchema.index({ user: 1, createdAt: -1 }, { background: true });

// 2. Categorical Index: Optimizes getSummary & getPersonalSummary
// Speeds up aggregation pipelines where we group spam vs. ham for a specific user.
historySchema.index({ user: 1, prediction: 1 }, { background: true });

// 3. Type Index: Optimizes breakdown by payload type
historySchema.index({ user: 1, type: 1 }, { background: true });

module.exports = mongoose.model("History", historySchema);