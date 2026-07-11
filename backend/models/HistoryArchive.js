const mongoose = require('mongoose');

// Assuming your original History model has similar fields. Adjust if needed!
const historyArchiveSchema = new mongoose.Schema({
    userId: {
        type: mongoose.Schema.Types.ObjectId,
        ref: 'User',
        required: [true, 'User ID is required']
    },
    message: {
        type: String,
        required: [true, 'Message is required'],
        trim: true
    },
    prediction: {
        type: String,
        required: [true, 'Prediction is required'],
        trim: true,
        enum: {
            values: ['spam', 'ham'],
            message: '{VALUE} is not a valid prediction'
        }
    },
    confidenceScore: {
        type: Number,
        min: [0, 'Confidence score cannot be less than 0'],
        max: [100, 'Confidence score cannot exceed 100']
    }
}, {
    timestamps: true,
    collection: 'history_archive' // Explicitly naming the cold storage collection
});

module.exports = mongoose.model('HistoryArchive', historyArchiveSchema);