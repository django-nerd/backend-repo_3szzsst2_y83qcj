import { useEffect, useState } from 'react';
import { getToken, ensureDemoUser } from '../utils/auth';
import axios from 'axios';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080/api';

export default function Identity() {
  const [video, setVideo] = useState<string>('');
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => { ensureDemoUser(); }, []);

  const submit = async () => {
    setLoading(true);
    try {
      const token = getToken();
      const { data } = await axios.post(`${API}/identity/verify`, { livenessVideo: video }, { headers: { Authorization: `Bearer ${token}` } });
      setResult(data.data);
    } catch (e) {
      setResult({ error: 'failed' });
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="p-6 max-w-xl mx-auto">
      <h1 className="text-2xl font-bold mb-4">Identity Verification</h1>
      <textarea className="w-full border rounded p-2" rows={6} placeholder="paste base64 of liveness video" value={video} onChange={e=>setVideo(e.target.value)} />
      <button onClick={submit} className="mt-4 px-4 py-2 bg-blue-600 text-white rounded" disabled={loading}>{loading ? 'Submitting...' : 'Submit'}</button>
      {result && <pre className="mt-4 bg-gray-100 p-2 rounded text-sm">{JSON.stringify(result, null, 2)}</pre>}
    </main>
  );
}
