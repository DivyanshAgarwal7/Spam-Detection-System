import axios from 'axios';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

class EmailService {
  async getEmails(params = {}) {
    const {
      page = 1,
      limit = 20,
      search = '',
      sort_by = 'created_at',
      sort_order = 'desc',
      is_spam = null
    } = params;

    const queryParams = new URLSearchParams({
      page,
      limit,
      sort_by,
      sort_order
    });

    if (search) queryParams.append('search', search);
    if (is_spam !== null) queryParams.append('is_spam', is_spam);

    const response = await axios.get(`${API_URL}/api/emails?${queryParams}`, {
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('token')}`
      }
    });

    return response.data;
  }
}

export default new EmailService();