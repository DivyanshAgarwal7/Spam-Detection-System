/**
 * Federation Service - Integration with prediction pipeline
 */

const FederationManager = require('../federation/federationManager');

let federationInstance = null;

function getFederationInstance() {
    if (!federationInstance) {
        federationInstance = new FederationManager();
    }
    return federationInstance;
}

/**
 * Enhance prediction with federation intelligence
 */
async function enhancePrediction(text, localResult) {
    try {
        const federation = getFederationInstance();
        
        // Query federation
        const threats = await federation.queryFederation(text);
        
        // If federation has this as threat
        if (threats.length > 0) {
            const isSpam = threats.some(t => t.label === 'spam');
            if (isSpam && localResult.confidence < 0.7) {
                // Boost confidence from federation intel
                localResult.confidence = Math.min(localResult.confidence + 0.2, 0.95);
                localResult.federation_boost = true;
                localResult.federation_source = threats.map(t => t.sourceOrgId || 'federation');
            }
        }
        
        return localResult;
    } catch (error) {
        console.error('Federation enhancement failed:', error);
        return localResult;
    }
}

module.exports = {
    getFederationInstance,
    enhancePrediction
};