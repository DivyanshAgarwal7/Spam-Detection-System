const express = require('express');
const router = express.Router();
const { protect } = require('../middleware/authMiddleware');
const { checkPermission } = require('../middleware/zeroTrust');
const FederationManager = require('../federation/federationManager');

// Singleton instance
const federation = new FederationManager();

/**
 * @route   POST /api/federation/register
 * @desc    Register a new member in the federation
 * @access  Private (Admin)
 */
router.post('/register', protect, checkPermission('system_config'), async (req, res) => {
    try {
        const { orgId, orgName, endpoint, publicKey, trustScore } = req.body;
        
        const member = federation.registerMember({
            orgId,
            orgName,
            endpoint,
            publicKey,
            trustScore
        });

        res.json({
            success: true,
            message: 'Member registered successfully',
            member
        });
    } catch (error) {
        res.status(400).json({
            success: false,
            error: error.message
        });
    }
});

/**
 * @route   POST /api/federation/unregister/:orgId
 * @desc    Remove a member from federation
 * @access  Private (Admin)
 */
router.delete('/unregister/:orgId', protect, checkPermission('system_config'), async (req, res) => {
    try {
        const result = federation.unregisterMember(req.params.orgId);
        res.json({
            success: true,
            ...result
        });
    } catch (error) {
        res.status(400).json({
            success: false,
            error: error.message
        });
    }
});

/**
 * @route   POST /api/federation/share
 * @desc    Share a threat with the federation
 * @access  Private (User)
 */
router.post('/share', protect, async (req, res) => {
    try {
        const { text, label, confidence } = req.body;
        
        if (!text || !label) {
            return res.status(400).json({
                success: false,
                error: 'Threat text and label required'
            });
        }

        const result = await federation.shareThreat({
            text,
            label,
            confidence: confidence || 0.8,
            sourceOrgId: req.user.orgId || req.user._id
        });

        res.json({
            success: true,
            ...result
        });
    } catch (error) {
        res.status(400).json({
            success: false,
            error: error.message
        });
    }
});

/**
 * @route   POST /api/federation/query
 * @desc    Query federation for threats
 * @access  Private
 */
router.post('/query', protect, async (req, res) => {
    try {
        const { text } = req.body;
        
        if (!text) {
            return res.status(400).json({
                success: false,
                error: 'Query text required'
            });
        }

        const threats = await federation.queryFederation(text);
        
        res.json({
            success: true,
            threats: threats,
            count: threats.length
        });
    } catch (error) {
        res.status(400).json({
            success: false,
            error: error.message
        });
    }
});

/**
 * @route   POST /api/federation/receive
 * @desc    Receive threat from federation member (public endpoint)
 * @access  Public (Internal)
 */
router.post('/receive', async (req, res) => {
    try {
        const { threatId, hash, anonymizedText, label, confidence, timestamp, signature } = req.body;
        
        // Verify signature
        // (Simplified - in production, verify with member's public key)
        
        // Store locally
        const threat = {
            id: threatId,
            hash,
            anonymizedText,
            label,
            confidence,
            receivedAt: new Date().toISOString(),
            source: 'federation'
        };

        federation.sharedThreats.push(threat);
        
        res.json({
            success: true,
            message: 'Threat received and stored'
        });
    } catch (error) {
        res.status(400).json({
            success: false,
            error: error.message
        });
    }
});

/**
 * @route   GET /api/federation/stats
 * @desc    Get federation statistics
 * @access  Private (Admin)
 */
router.get('/stats', protect, checkPermission('view_logs'), async (req, res) => {
    try {
        const stats = federation.getStats();
        res.json({
            success: true,
            stats
        });
    } catch (error) {
        res.status(400).json({
            success: false,
            error: error.message
        });
    }
});

/**
 * @route   POST /api/federation/verify/:threatId
 * @desc    Verify a threat (consensus)
 * @access  Private (User)
 */
router.post('/verify/:threatId', protect, async (req, res) => {
    try {
        const threat = federation.verifyThreat(req.params.threatId);
        res.json({
            success: true,
            threat
        });
    } catch (error) {
        res.status(400).json({
            success: false,
            error: error.message
        });
    }
});

module.exports = router;