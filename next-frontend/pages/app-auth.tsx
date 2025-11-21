import { useEffect, useState } from 'react';
import axios from 'axios';
import { ensureDemoUser, getToken } from '../utils/auth';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080/api';

export default function AppAuth() {
  const [pkg, setPkg] = useState('');
  const [issuer, setIssuer] = useState('Bank Authority');
  const [list, setList] = useState<any[]>([]);

  const refresh = async () => {
    const { data } = await axios.get(`${API}/app/official`);
    setList(data.data || []);
  };

  useEffect(() => { ensureDemoUser(); refresh(); }, []);

  const add = async () => {
    await axios.post(`${API}/app/official`, { packageName: pkg, issuer });
    setPkg('');
    refresh();
  };

  return (
    <main className="p-6 max-w-xl mx-auto">
      <h1 className="text-2xl font-bold mb-4">App Authenticity</h1>
      <div className="flex gap-2">
        <input value={pkg} onChange={e=>setPkg(e.target.value)} placeholder="com.bank.app" className="flex-1 border rounded p-2" />
        <input value={issuer} onChange={e=>setIssuer(e.target.value)} placeholder="Issuer" className="flex-1 border rounded p-2" />
        <button onClick={add} className="px-4 py-2 bg-blue-600 text-white rounded">Add Official</button>
      </div>
      <h2 className="mt-6 font-semibold">Official Registry</h2>
      <ul className="mt-2 list-disc pl-6">
        {list.map(item => <li key={item._id}>{item.packageName} — {item.issuer}</li>)}
      </ul>
    </main>
  );
}
