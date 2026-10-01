import { useEffect, useState } from 'react';
import './App.css';

interface HealthStatus {
  status: string;
  [key: string]: unknown;
}

function App() {
  const [aiStatus, setAiStatus] = useState<HealthStatus | null>(null);
  const [backendStatus, setBackendStatus] = useState<HealthStatus | null>(null);
  const [aiError, setAiError] = useState<string | null>(null);
  const [backendError, setBackendError] = useState<string | null>(null);

  useEffect(() => {
    fetch('http://localhost:8000/health')
      .then((res) => res.json())
      .then((data) => setAiStatus(data))
      .catch((err) => setAiError(err.message));

    fetch('http://localhost:4000/health')
      .then((res) => res.json())
      .then((data) => setBackendStatus(data))
      .catch((err) => setBackendError(err.message));
  }, []);

  return (
    <div style={{ padding: '2rem', fontFamily: 'system-ui, sans-serif' }}>
      <h1>Border AI Platform - Day 1 Health Check</h1>
      <div style={{ marginTop: '1.5rem', display: 'flex', gap: '2rem' }}>
        <div style={{ border: '1px solid #ccc', padding: '1rem', borderRadius: '8px', minWidth: '280px' }}>
          <h3>AI Engine (:8000)</h3>
          {aiError && <p style={{ color: 'red' }}>Error: {aiError}</p>}
          {aiStatus ? (
            <pre>{JSON.stringify(aiStatus, null, 2)}</pre>
          ) : !aiError && <p>Checking...</p>}
        </div>
        <div style={{ border: '1px solid #ccc', padding: '1rem', borderRadius: '8px', minWidth: '280px' }}>
          <h3>Backend (:4000)</h3>
          {backendError && <p style={{ color: 'red' }}>Error: {backendError}</p>}
          {backendStatus ? (
            <pre>{JSON.stringify(backendStatus, null, 2)}</pre>
          ) : !backendError && <p>Checking...</p>}
        </div>
      </div>
    </div>
  );
}

export default App;
