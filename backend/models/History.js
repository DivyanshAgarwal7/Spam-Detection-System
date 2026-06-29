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

historySchema.index({ user: 1, createdAt: -1 });
historySchema.index({ user: 1, prediction: 1 });
historySchema.index({ user: 1, type: 1 });

module.exports = mongoose.model("History", historySchema);