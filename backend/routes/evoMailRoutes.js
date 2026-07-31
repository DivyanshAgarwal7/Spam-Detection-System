const express = require('express');
const router = express.Router();
const { protect } = require('../middleware/authMiddleware');
const { checkPermission } = require('../middleware/zeroTrust');

// Import Python EvoMail module
const { spawn } = require('child_process');
const path = require('path');

// Path to EvoMail Python script
const EVOMAIL_SCRIPT = path.join(__dirname, '../evo_mail.py');

/**
 * @route   POST /api/evomail/evolve
 * @desc    Force evolution of the cognitive agent
 * @access  Private (Admin)
 */
router.post('/evolve', protect, checkPermission('system_config'), async (req, res) => {
    try {
        const { force = true, data = [] } = req.body;
        
        // Run evolution
        const result = await runEvoMailCommand('evolve', { force, data });
        
        res.json({
            success: true,
            message: 'Evolution completed successfully',
            result
        });
    } catch (error) {
        res.status(500).json({
            success: false,
            error: error.message
        });
    }
});

/**
 * @route   POST /api/evomail/detect
 * @desc    Detect spam using cognitive agent
 * @access  Private
 */
router.post('/detect', protect, async (req, res) => {
    try {
        const { text } = req.body;
        
        if (!text) {
            return res.status(400).json({
                success: false,
                error: 'Text is required'
            });
        }
        
        const result = await runEvoMailCommand('detect', { text });
        
        res.json({
            success: true,
            ...result
        });
    } catch (error) {
        res.status(500).json({
            success: false,
            error: error.message
        });
    }
});

/**
 * @route   GET /api/evomail/stats
 * @desc    Get cognitive agent statistics
 * @access  Private (Admin)
 */
router.get('/stats', protect, checkPermission('view_logs'), async (req, res) => {
    try {
        const stats = await runEvoMailCommand('stats', {});
        
        res.json({
            success: true,
            stats
        });
    } catch (error) {
        res.status(500).json({
            success: false,
            error: error.message
        });
    }
});

/**
 * @route   POST /api/evomail/schedule
 * @desc    Configure evolution schedule
 * @access  Private (Admin)
 */
router.post('/schedule', protect, checkPermission('system_config'), async (req, res) => {
    try {
        const { intervalHours, enabled } = req.body;
        
        // Update schedule
        const result = await runEvoMailCommand('schedule', { intervalHours, enabled });
        
        res.json({
            success: true,
            message: 'Schedule updated successfully',
            result
        });
    } catch (error) {
        res.status(500).json({
            success: false,
            error: error.message
        });
    }
});

/**
 * Helper: Run EvoMail Python script
 */
function runEvoMailCommand(command, params = {}) {
    return new Promise((resolve, reject) => {
        const python = spawn('python', [
            EVOMAIL_SCRIPT,
            '--command', command,
            '--params', JSON.stringify(params)
        ]);
        
        let output = '';
        let errorOutput = '';
        
        python.stdout.on('data', (data) => {
            output += data.toString();
        });
        
        python.stderr.on('data', (data) => {
            errorOutput += data.toString();
        });
        
        python.on('close', (code) => {
            if (code !== 0) {
                reject(new Error(errorOutput || `Process exited with code ${code}`));
            } else {
                try {
                    resolve(JSON.parse(output));
                } catch (e) {
                    resolve({ output, raw: true });
                }
            }
        });
        
        python.on('error', (err) => {
            reject(err);
        });
    });
}

module.exports = router;