const EmailHeaderAnalyzer = require('../services/emailHeaderAnalyzer');

const MAX_EMAIL_SIZE = 5 * 1024 * 1024; // 5MB

class EmailHeaderController {
    static async verifyHeaders(req, res) {
        try {
            const { email_content } = req.body;

            if (!email_content || typeof email_content !== 'string') {
                return res.status(400).json({
                    success: false,
                    error: 'Email content is required and must be a string'
                });
            }

            const emailSize = Buffer.byteLength(email_content, 'utf8');

            if (emailSize > MAX_EMAIL_SIZE) {
                return res.status(413).json({
                    success: false,
                    error: `Email content exceeds maximum size of ${MAX_EMAIL_SIZE / (1024 * 1024)}MB. Current size: ${(emailSize / (1024 * 1024)).toFixed(2)}MB`,
                    code: 'PAYLOAD_TOO_LARGE'
                });
            }

            const result = await EmailHeaderAnalyzer.analyze(email_content);

            return res.status(200).json({
                success: true,
                data: result
            });

        } catch (error) {
            console.error('Email header analysis error:', error);

            return res.status(500).json({
                success: false,
                error: 'Failed to analyze email headers',
                details: 'Internal server error'
            });
        }
    }
}

module.exports = EmailHeaderController;