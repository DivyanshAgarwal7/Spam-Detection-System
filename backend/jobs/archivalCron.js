const cron = require('node-cron');
const mongoose = require('mongoose');
const History = require('../models/History'); // Ensure this path matches your existing History model
const HistoryArchive = require('../models/HistoryArchive');

// Schedule job to run at 3:00 AM every day
// Run every minute for testing
    cron.schedule('* * * * *', async () => {
    console.log('📦 [Cron] Starting data archival process for records older than 90 days...');
    
    // Start a transaction session for safe data migration
    const session = await mongoose.startSession();
    session.startTransaction();
    
    try {
        // Calculate the date 90 days ago
        const ninetyDaysAgo = new Date();
        ninetyDaysAgo.setDate(ninetyDaysAgo.getDate() - 90);

        // 1. Find all records older than 90 days
        const oldRecords = await History.find({ createdAt: { $lt: ninetyDaysAgo } }).session(session);

        if (oldRecords.length > 0) {
            // Map the old records to the new schema
            const mappedRecords = oldRecords.map(record => ({
                userId: record.user,
                message: record.query,
                prediction: record.prediction,
                confidenceScore: record.confidence,
                createdAt: record.createdAt
            }));

            // 2. Bulk insert them into the Archive collection
            await HistoryArchive.insertMany(mappedRecords, { session });
            
            // 3. Bulk delete them from the main History collection
            await History.deleteMany({ createdAt: { $lt: ninetyDaysAgo } }, { session });
            
            console.log(`✅ [Cron] Successfully archived ${oldRecords.length} records.`);
        } else {
            console.log('ℹ️ [Cron] No old records to archive today.');
        }

        // Commit transaction if both insert and delete succeed
        await session.commitTransaction();
    } catch (error) {
        // Abort if anything fails so we don't lose data!
        await session.abortTransaction();
        console.error('❌ [Cron] Archival process failed, rolling back changes:', error);
    } finally {
        session.endSession();
    }
});