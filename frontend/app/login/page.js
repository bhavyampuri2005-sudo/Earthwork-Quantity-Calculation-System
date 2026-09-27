'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { setAuth } from '../../lib/auth';

const BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError('');
    setLoading(true);

    const body = new URLSearchParams();
    body.append('username', username);
    body.append('password', password);

    try {
      const res = await fetch(`${BASE_URL}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body,
      });

      if (!res.ok) {
        setError(res.status === 401 ? 'Incorrect username or password.' : 'Login failed.');
        setLoading(false);
        return;
      }

      const data = await res.json();
      setAuth(data.access_token, data.role);
      router.push('/');
    } catch (err) {
      setError('Could not reach the server.');
      setLoading(false);
    }
  }

  return (
    <div className="login-page">
      <form onSubmit={handleSubmit} className="login-form">
        <h1>Sign in</h1>
        <label>
          Username
          <input type="text" value={username} onChange={(e) => setUsername(e.target.value)} required />
        </label>
        <label>
          Password
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
        </label>
        {error && <p className="login-error">{error}</p>}
        <button type="submit" disabled={loading}>{loading ? 'Signing in...' : 'Sign in'}</button>
      </form>
    </div>
  );
}
