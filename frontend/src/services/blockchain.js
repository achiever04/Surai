import api from './api';

export const blockchainService = {
  async getEvidenceProvenance(eventId) {
    return await api.post('/blockchain/provenance', { event_id: eventId });
  },

  async verifyEvidence(eventId, currentHash) {
    return await api.post(`/blockchain/verify/${eventId}`, { current_hash: currentHash });
  },

  async getTransactions(filters = {}) {
    return await api.get('/blockchain/transactions', { params: filters });
  },

  async getBlockchainStats() {
    return await api.get('/blockchain/stats');
  }
};

export default blockchainService;