const mongoose = require('mongoose');

const FederationMemberSchema = new mongoose.Schema({
  name: { type: String, required: true },
  apiUrl: { type: String, required: true },
  apiKey: { type: String, required: true },
  status: { 
    type: String, 
    enum: ['active', 'inactive', 'pending'], 
    default: 'pending' 
  },
  joinedAt: { type: Date, default: Date.now },
  lastSync: { type: Date },
  threatCount: { type: Number, default: 0 },
  trustScore: { type: Number, default: 50, min: 0, max: 100 }
});

module.exports = mongoose.model('FederationMember', FederationMemberSchema);