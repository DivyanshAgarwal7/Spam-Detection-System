/**
 * CyberDART - Collaborative Spam Detection Federation
 * Enables organizations to share anonymized threat intelligence
 */

const crypto = require('crypto');
const axios = require('axios');

class FederationManager {
    constructor() {
        this.members = new Map();
        this.sharedThreats = [];
        this.threatCache = new Map();
        this.federationId = crypto.randomUUID();
        this.config = {
            minMembersForConsensus: 3,
            threatTTL: 7 * 24 * 60 * 60 * 1000, // 7 days
            syncInterval: 60 * 60 * 1000, // 1 hour
            maxThreatsPerShare: 100
        };
    }

    /**
     * Register a new member in the federation
     */
    registerMember(memberData) {
        const { orgId, orgName, endpoint, publicKey, trustScore = 50 } = memberData;
        
        if (!orgId || !orgName || !endpoint || !publicKey) {
            throw new Error('Missing required member data');
        }

        const member = {
            orgId,
            orgName,
            endpoint,
            publicKey,
            trustScore,
            joinedAt: new Date().toISOString(),
            lastSync: null,
            threatsShared: 0,
            threatsReceived: 0,
            status: 'active'
        };

        this.members.set(orgId, member);
        
        // Start background sync
        this.scheduleSync(orgId);
        
        return member;
    }

    /**
     * Remove a member from federation
     */
    unregisterMember(orgId) {
        if (!this.members.has(orgId)) {
            throw new Error('Member not found');
        }
        this.members.delete(orgId);
        return { success: true };
    }

    /**
     * Share a threat anonymously using PATCH algorithm
     */
    async shareThreat(threatData) {
        const { text, label, confidence, sourceOrgId } = threatData;
        
        // Validate
        if (!text || !label) {
            throw new Error('Threat text and label required');
        }

        // Anonymize using PATCH algorithm
        const anonymized = this.patchAnonymize(text);
        
        // Calculate threat hash for deduplication
        const threatHash = this.generateThreatHash(anonymized);

        // Check if already exists
        const existing = this.sharedThreats.find(t => t.hash === threatHash);
        if (existing) {
            // Increment occurrence count
            existing.occurrences += 1;
            existing.lastSeen = new Date().toISOString();
            return { shared: false, duplicate: true };
        }

        const threat = {
            id: crypto.randomUUID(),
            hash: threatHash,
            anonymizedText: anonymized,
            originalText: text.slice(0, 100), // Store preview for verification
            label,
            confidence,
            sourceOrgId,
            occurrences: 1,
            createdAt: new Date().toISOString(),
            lastSeen: new Date().toISOString(),
            verified: false,
            verificationCount: 0
        };

        this.sharedThreats.push(threat);
        
        // Broadcast to all members
        await this.broadcastThreat(threat);

        // Update member stats
        const member = this.members.get(sourceOrgId);
        if (member) {
            member.threatsShared += 1;
        }

        return { shared: true, threatId: threat.id };
    }

    /**
     * PATCH Anonymization Algorithm
     * Privacy-Preserving Anonymization for Collaborative Threat Sharing
     */
    patchAnonymize(text) {
        // Step 1: Remove personal identifiable information (PII)
        let anonymized = text
            .replace(/\b\d{3}[-.]?\d{3}[-.]?\d{4}\b/g, '[PHONE]') // Phone numbers
            .replace(/\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b/g, '[EMAIL]') // Emails
            .replace(/\bhttps?:\/\/[^\s]+\b/g, '[URL]') // URLs
            .replace(/\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b/g, '[IP]'); // IP addresses

        // Step 2: Normalize case
        anonymized = anonymized.toLowerCase();

        // Step 3: Remove stop words (common words)
        const stopWords = new Set(['the', 'a', 'an', 'of', 'for', 'on', 'at', 'to', 'in', 'is', 'it', 'and', 'or', 'but', 'with', 'from', 'by', 'as', 'was', 'are', 'were', 'been']);
        anonymized = anonymized.split(' ')
            .filter(word => !stopWords.has(word))
            .join(' ');

        // Step 4: Apply differential privacy - add minimal noise
        // (This is a simplified version - real DP adds calibrated noise)
        const words = anonymized.split(' ');
        if (words.length > 3) {
            // Randomly replace 5% of words with placeholders
            const replaceCount = Math.max(1, Math.floor(words.length * 0.05));
            for (let i = 0; i < replaceCount; i++) {
                const idx = Math.floor(Math.random() * words.length);
                words[idx] = '[REDACTED]';
            }
        }

        // Step 5: Generate n-gram signature
        const result = words.join(' ');
        return result;
    }

    /**
     * Generate a unique hash for a threat
     */
    generateThreatHash(text) {
        return crypto
            .createHash('sha256')
            .update(text)
            .digest('hex')
            .slice(0, 16);
    }

    /**
     * Broadcast threat to all federation members
     */
    async broadcastThreat(threat) {
        const broadcastPromises = [];
        
        for (const [orgId, member] of this.members) {
            if (orgId === threat.sourceOrgId) continue; // Skip source
            
            const payload = {
                type: 'THREAT_SHARE',
                threatId: threat.id,
                hash: threat.hash,
                anonymizedText: threat.anonymizedText,
                label: threat.label,
                confidence: threat.confidence,
                timestamp: new Date().toISOString()
            };

            broadcastPromises.push(
                this.sendToMember(orgId, payload)
                    .catch(err => console.error(`Failed to send to ${orgId}:`, err))
            );
        }

        await Promise.allSettled(broadcastPromises);
    }

    /**
     * Send data to a specific member
     */
    async sendToMember(orgId, payload) {
        const member = this.members.get(orgId);
        if (!member) {
            throw new Error(`Member ${orgId} not found`);
        }

        // Add signature for verification
        const signature = crypto
            .createSign('sha256')
            .update(JSON.stringify(payload))
            .sign(process.env.FEDERATION_PRIVATE_KEY || 'default-key')
            .toString('base64');

        const response = await axios.post(
            `${member.endpoint}/api/federation/receive`,
            { ...payload, signature },
            {
                headers: {
                    'Content-Type': 'application/json',
                    'X-Federation-Id': this.federationId
                },
                timeout: 10000
            }
        );

        if (member) {
            member.threatsReceived += 1;
            member.lastSync = new Date().toISOString();
        }

        return response.data;
    }

    /**
     * Query federation for threats matching a text
     */
    async queryFederation(text) {
        const anonymized = this.patchAnonymize(text);
        const hash = this.generateThreatHash(anonymized);
        
        // Check local cache first
        if (this.threatCache.has(hash)) {
            return this.threatCache.get(hash);
        }

        // Query all members
        const queryPromises = [];
        for (const [orgId, member] of this.members) {
            queryPromises.push(
                this.queryMember(orgId, { hash })
                    .then(result => ({ orgId, result }))
                    .catch(() => ({ orgId, result: null }))
            );
        }

        const results = await Promise.allSettled(queryPromises);
        
        // Aggregate results
        const threats = [];
        for (const r of results) {
            if (r.status === 'fulfilled' && r.value.result) {
                threats.push(r.value.result);
            }
        }

        // Cache results
        if (threats.length > 0) {
            this.threatCache.set(hash, threats);
            setTimeout(() => this.threatCache.delete(hash), 60000); // Cache for 1 minute
        }

        return threats;
    }

    /**
     * Query a specific member
     */
    async queryMember(orgId, query) {
        const member = this.members.get(orgId);
        if (!member) {
            throw new Error(`Member ${orgId} not found`);
        }

        const response = await axios.post(
            `${member.endpoint}/api/federation/query`,
            query,
            {
                headers: {
                    'Content-Type': 'application/json',
                    'X-Federation-Id': this.federationId
                },
                timeout: 5000
            }
        );

        return response.data;
    }

    /**
     * Get federation statistics
     */
    getStats() {
        return {
            federationId: this.federationId,
            totalMembers: this.members.size,
            activeMembers: Array.from(this.members.values()).filter(m => m.status === 'active').length,
            totalThreats: this.sharedThreats.length,
            threatsLast24h: this.sharedThreats.filter(
                t => new Date(t.createdAt) > new Date(Date.now() - 24 * 60 * 60 * 1000)
            ).length,
            members: Array.from(this.members.entries()).map(([id, m]) => ({
                id,
                name: m.orgName,
                trustScore: m.trustScore,
                threatsShared: m.threatsShared,
                threatsReceived: m.threatsReceived,
                status: m.status
            }))
        };
    }

    /**
     * Schedule background sync with members
     */
    scheduleSync(orgId) {
        setInterval(async () => {
            try {
                const member = this.members.get(orgId);
                if (!member) return;

                const response = await this.queryMember(orgId, { sync: true });
                // Process sync response
                if (response.threats) {
                    for (const threat of response.threats) {
                        const existing = this.sharedThreats.find(t => t.hash === threat.hash);
                        if (!existing) {
                            this.sharedThreats.push({
                                ...threat,
                                receivedAt: new Date().toISOString()
                            });
                        }
                    }
                }
            } catch (err) {
                console.error(`Sync failed for ${orgId}:`, err);
            }
        }, this.config.syncInterval);
    }

    /**
     * Verify a threat (consensus-based)
     */
    verifyThreat(threatId) {
        const threat = this.sharedThreats.find(t => t.id === threatId);
        if (!threat) {
            throw new Error('Threat not found');
        }

        threat.verificationCount += 1;
        
        // 3 verifications = verified
        if (threat.verificationCount >= 3) {
            threat.verified = true;
        }

        return threat;
    }
}

module.exports = FederationManager;