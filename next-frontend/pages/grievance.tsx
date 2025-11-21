import { useEffect, useState } from 'react';
import axios from 'axios';
import { ensureDemoUser, getToken } from '../utils/auth';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080/api';

export default function Grievance() {
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [list, setList] = useState<any[]>([]);

  const load = async () => {
    const token = getToken();
    const { data } = await axios.get(`${API}/grievance`, { headers: { Authorization: `Bearer ${token}` } });
    setList(data.data || []);
  };

  useEffect(() => { ensureDemoUser(); load(); }, []);

  const submit = async () => {
    const token = getToken();
    await axios.post(`${API}/grievance`, { title, description }, { headers: { Authorization: `Bearer ${token}` } });
    setTitle(''); setDescription('');
    load();
  };

  return (
    <main className="p-6 max-w-xl mx-auto">
      <h1 className="text-2xl font-bold mb-4">File a Grievance</h1>
      <input value={title} onChange={e=>setTitle(e.target.value)} placeholder="Title" className="w-full border rounded p-2 mb-2" />
      <textarea value={description} onChange={e=>setDescription(e.target.value)} placeholder="Describe the issue" className="w-full border rounded p-2" rows={5} />
      <button onClick={submit} className="mt-3 px-4 py-2 bg-blue-600 text-white rounded">Submit</button>
      <h2 className="mt-6 font-semibold">My Grievances</h2>
      <ul className="mt-2 list-disc pl-6">
        {list.map(g => <li key={g._id}>{g.title} — <span className="italic">{g.category}</span></li>)}
      </ul>
    </main>
  );
}
