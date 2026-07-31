const mongoose = require('mongoose');

// Mock dependencies
jest.mock('../models/History', () => ({
  find: jest.fn(),
  deleteMany: jest.fn(),
}));

jest.mock('../models/HistoryArchive', () => ({
  bulkWrite: jest.fn(),
  insertMany: jest.fn()
}));

jest.mock('node-cron', () => ({
  schedule: jest.fn(),
}));

const cron = require('node-cron');
const History = require('../models/History');
const HistoryArchive = require('../models/HistoryArchive');

// Save the original env variable if it existed
const originalSchedule = process.env.ARCHIVAL_CRON_SCHEDULE;
process.env.ARCHIVAL_CRON_SCHEDULE = '0 5 * * *';
const { archivalJob, schedule } = require('../jobs/archivalCron');

describe('Archival Cron Job', () => {
  let consoleLogSpy;
  let consoleErrorSpy;

  beforeEach(() => {
    jest.clearAllMocks();
    consoleLogSpy = jest.spyOn(console, 'log').mockImplementation(() => {});
    consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
  });

  afterEach(() => {
    consoleLogSpy.mockRestore();
    consoleErrorSpy.mockRestore();
  });

  it('should use the environment variable for cron schedule', () => {
    expect(schedule).toBe('0 5 * * *');
  });

  it('should successfully archive records (normal archival)', async () => {
    const mockRecord = {
      _id: new mongoose.Types.ObjectId(),
      user: new mongoose.Types.ObjectId(),
      query: 'test spam',
      prediction: 'spam',
      confidence: 99,
      createdAt: new Date('2023-01-01')
    };

    // First call returns 1 record, second call returns empty array to break the loop
    const chainableFind = {
      limit: jest.fn().mockReturnThis(),
      lean: jest.fn().mockResolvedValueOnce([mockRecord]).mockResolvedValueOnce([])
    };
    History.find.mockReturnValue(chainableFind);

    HistoryArchive.bulkWrite.mockResolvedValue({ modifiedCount: 1 });
    History.deleteMany.mockResolvedValue({ deletedCount: 1 });

    await archivalJob();

    // Verify find
    expect(History.find).toHaveBeenCalledTimes(2);
    // Verify bulkWrite
    expect(HistoryArchive.bulkWrite).toHaveBeenCalledTimes(1);
    const bulkOps = HistoryArchive.bulkWrite.mock.calls[0][0];
    expect(bulkOps.length).toBe(1);
    expect(bulkOps[0].updateOne.filter._id).toBe(mockRecord._id);
    expect(bulkOps[0].updateOne.upsert).toBe(true);
    expect(bulkOps[0].updateOne.update.$setOnInsert.message).toBe('test spam');
    expect(bulkOps[0].updateOne.update.$setOnInsert._id).toBe(mockRecord._id);

    // Verify deleteMany
    expect(History.deleteMany).toHaveBeenCalledTimes(1);
    expect(History.deleteMany).toHaveBeenCalledWith({ _id: { $in: [mockRecord._id] } });
  });

  it('should handle archive write failure by preventing source deletion', async () => {
    const mockRecord = { _id: '123' };
    const chainableFind = {
      limit: jest.fn().mockReturnThis(),
      lean: jest.fn().mockResolvedValueOnce([mockRecord]).mockResolvedValueOnce([])
    };
    History.find.mockReturnValue(chainableFind);

    HistoryArchive.bulkWrite.mockRejectedValue(new Error('Write Failed'));

    await archivalJob();

    expect(HistoryArchive.bulkWrite).toHaveBeenCalled();
    expect(History.deleteMany).not.toHaveBeenCalled();
    expect(consoleErrorSpy).toHaveBeenCalledWith(expect.stringContaining('Failed to write archival records batch to HistoryArchive'), expect.any(Error));
  });

  it('should handle source deletion failure safely', async () => {
    const mockRecord = { _id: '123' };
    const chainableFind = {
      limit: jest.fn().mockReturnThis(),
      lean: jest.fn().mockResolvedValueOnce([mockRecord]).mockResolvedValueOnce([])
    };
    History.find.mockReturnValue(chainableFind);

    HistoryArchive.bulkWrite.mockResolvedValue({ ok: 1 });
    History.deleteMany.mockRejectedValue(new Error('Delete Failed'));

    await archivalJob();

    expect(HistoryArchive.bulkWrite).toHaveBeenCalled();
    expect(History.deleteMany).toHaveBeenCalled();
    expect(consoleErrorSpy).toHaveBeenCalledWith(expect.stringContaining('Failed to delete archived records batch from History'), expect.any(Error));
  });
  
  it('should behave idempotently for already-archived records (successful retry)', async () => {
    // If a record is already archived, bulkWrite with upsert:true simply does nothing for that document,
    // but the promise resolves successfully. Then deleteMany cleans it up.
    const mockRecord = { _id: '123' };
    const chainableFind = {
      limit: jest.fn().mockReturnThis(),
      lean: jest.fn().mockResolvedValueOnce([mockRecord]).mockResolvedValueOnce([])
    };
    History.find.mockReturnValue(chainableFind);

    // Simulate bulkWrite succeeding (which it does even if $setOnInsert finds an existing doc)
    HistoryArchive.bulkWrite.mockResolvedValue({ upsertedCount: 0, modifiedCount: 0 });
    History.deleteMany.mockResolvedValue({ deletedCount: 1 });

    await archivalJob();

    expect(HistoryArchive.bulkWrite).toHaveBeenCalled();
    expect(History.deleteMany).toHaveBeenCalled();
  });
});
