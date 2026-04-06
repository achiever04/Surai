import api from './api';

export const authService = {
  async login(username, password) {
    const formData = new URLSearchParams();
    formData.append('username', username);
    formData.append('password', password);

    const response = await api.post('/auth/login', formData, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
    });

    if (response.data.access_token) {
      sessionStorage.setItem('access_token', response.data.access_token);
    }

    return response.data;
  },

  async logout() {
    try {
      await api.post('/auth/logout');
    } finally {
      sessionStorage.removeItem('access_token');
    }
  },

  async getCurrentUser() {
    return await api.get('/auth/me');
  },

  getToken() {
    return sessionStorage.getItem('access_token');
  },

  isAuthenticated() {
    return !!this.getToken();
  }
};

export default authService;