import axios from 'axios';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080/api';

export const getToken = () => {
  if (typeof window === 'undefined') return '';
  return localStorage.getItem('token') || '';
};

export const setToken = (t: string) => {
  if (typeof window === 'undefined') return;
  localStorage.setItem('token', t);
};

export const ensureDemoUser = async () => {
  if (typeof window === 'undefined') return;
  const token = getToken();
  if (token) return;
  const email = `demo_${Math.random().toString(36).slice(2,8)}@example.com`;
  const password = 'password123';
  const { data } = await axios.post(`${API}/auth/register`, { email, password, name: 'Demo User' });
  setToken(data.data.token);
};
