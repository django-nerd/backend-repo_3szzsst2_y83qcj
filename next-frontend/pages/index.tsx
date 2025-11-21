import Link from 'next/link';

export default function Home() {
  return (
    <main className="min-h-screen flex flex-col items-center justify-center gap-6 p-8">
      <h1 className="text-3xl font-bold">TrustGuard</h1>
      <p className="text-gray-600">Secure banking platform demo (Next.js)</p>
      <nav className="flex gap-4">
        <Link href="/identity" className="text-blue-600 underline">Identity</Link>
        <Link href="/app-auth" className="text-blue-600 underline">App Auth</Link>
        <Link href="/grievance" className="text-blue-600 underline">Grievance</Link>
        <Link href="/dashboard" className="text-blue-600 underline">Dashboard</Link>
      </nav>
    </main>
  );
}
