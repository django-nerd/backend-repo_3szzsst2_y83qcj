import { useEffect, useState } from 'react';
import axios from 'axios';
import { ensureDemoUser, getToken } from '../utils/auth';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080/api';

export default function Dashboard() {
  const [analytics, setAnalytics] = useState<any[]>([]);
  const [official, setOfficial] = useState<any[]>([]);
  const [suspicious, setSuspicious] = useState<any[]>([]);

  const load = async () => {
    const token = getToken();
    const a = await axios.get(`${API}/grievance/analytics`, { headers: { Authorization: `Bearer ${token}` } });
    const o = await axios.get(`${API}/app/official`);
    const s = await axios.get(`${API}/app/suspicious`);
    setAnalytics(a.data.data || []);
    setOfficial(o.data.data || []);
    setSuspicious(s.data.data || []);
  };

  useEffect(() => { ensureDemoUser(); load(); }, []);

  return (
    <main className="p-6 max-w-4xl mx-auto">
      <h1 className="text-2xl font-bold mb-4">Operations Dashboard</h1>
      <section className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="border rounded p-4">
          <h2 className="font-semibold mb-2">Grievance Analytics</h2>
          <ul>{analytics.map((x:any)=> <li key={x.category}>{x.category}: {x.count}</li>)}</ul>
        </div>
        <div className="border rounded p-4">
          <h2 className="font-semibold mb-2">Official Apps</h2>
          <ul>{official.map((x:any)=> <li key={x._id}>{x.packageName} — {x.issuer}</li>)}</ul>
        </div>
        <div className="border rounded p-4">
          <h2 className="font-semibold mb-2">Suspicious Apps</h2>
          <ul>{suspicious.map((x:any)=> <li key={x._id}>{x.packageName} — {x.reason}</li>)}</ul>
        </div>
      </section>
    </main>
  );
}
