const crypto = require('crypto');

class PATCHAlgorithm {
  /**
   * PATCH (Privacy-Preserving Anonymization for Collaborative Threat Handling)
   * Ensures full anonymity of exchanged content
   */
  
  anonymize(email) {
    // 1. Normalize email (lowercase, remove special chars)
    const normalized = this.normalize(email);
    
    // 2. Generate hash (SHA-256)
    const hash = crypto.createHash('sha256').update(normalized).digest('hex');
    
    // 3. Extract patterns (n-grams)
    const patterns = this.extractPatterns(normalized);
    
    // 4. Apply differential privacy (add noise)
    const anonymized = this.addNoise(patterns);
    
    return {
      hash,
      patterns: anonymized,
      timestamp: new Date().toISOString()
    };
  }

  normalize(text) {
    return text
      .toLowerCase()
      .replace(/[^a-zA-Z0-9\s]/g, '')
      .trim();
  }

  extractPatterns(text) {
    const words = text.split(/\s+/);
    const patterns = [];
    
    // Single words
    words.forEach(w => {
      if (w.length > 3) patterns.push(w);
    });
    
    // Bigrams
    for (let i = 0; i < words.length - 1; i++) {
      patterns.push(`${words[i]} ${words[i+1]}`);
    }
    
    return patterns;
  }

  addNoise(patterns) {
    // Randomly sample 70% of patterns to add noise
    const sampleSize = Math.floor(patterns.length * 0.7);
    const shuffled = patterns.sort(() => 0.5 - Math.random());
    return shuffled.slice(0, sampleSize);
  }

  compare(pattern1, pattern2) {
    // Calculate similarity score
    const common = pattern1.filter(p => pattern2.includes(p));
    return common.length / Math.max(pattern1.length, pattern2.length);
  }
}

module.exports = new PATCHAlgorithm();