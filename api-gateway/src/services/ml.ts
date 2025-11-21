import axios from 'axios';

export const identityPredict = async (payload: any) => {
  const base = process.env.IDENTITY_SERVICE_URL || '';
  try {
    const { data } = await axios.post(`${base}/predict`, payload, { timeout: 5000 });
    return { success: true, data };
  } catch (e) {
    return { success: false, data: { status: 'fallback', approved: true, score: 0.5 } };
  }
};

export const grievanceCategorize = async (payload: any) => {
  const base = process.env.GRIEVANCE_SERVICE_URL || '';
  try {
    const { data } = await axios.post(`${base}/categorize`, payload, { timeout: 5000 });
    return { success: true, data };
  } catch (e) {
    return { success: false, data: { category: 'general', confidence: 0.3, status: 'fallback' } };
  }
};
