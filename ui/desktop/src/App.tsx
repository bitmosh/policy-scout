import { useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import "./App.css";

interface DoctorResponse {
  ok: boolean;
  exit_code: number;
  data: any;
  error: string | null;
  stderr_summary: string | null;
}

function App() {
  const [doctorStatus, setDoctorStatus] = useState<DoctorResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function fetchDoctorStatus() {
    setLoading(true);
    setError(null);
    try {
      const response = await invoke<DoctorResponse>("get_doctor_status");
      setDoctorStatus(response);
      if (!response.ok) {
        setError(response.error || "Unknown error");
      }
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="container">
      <h1>Policy Scout</h1>
      <p className="boundary-note">
        Read-only preview. Policy Scout CLI remains the authority.
      </p>

      <div className="doctor-card">
        <div className="card-header">
          <h2>Doctor Status</h2>
          <button onClick={fetchDoctorStatus} disabled={loading}>
            {loading ? "Loading..." : "Refresh"}
          </button>
        </div>

        {loading && <p className="status-message">Loading doctor status...</p>}

        {error && (
          <div className="error-message">
            <p>Error: {error}</p>
          </div>
        )}

        {doctorStatus && doctorStatus.ok && doctorStatus.data && (
          <div className="doctor-data">
            <div className="info-row">
              <span className="label">Version:</span>
              <span className="value">{doctorStatus.data.policy_scout_version}</span>
            </div>
            <div className="info-row">
              <span className="label">Python:</span>
              <span className="value">{doctorStatus.data.python_version}</span>
            </div>
            <div className="info-row">
              <span className="label">Platform:</span>
              <span className="value">{doctorStatus.data.platform?.system}</span>
            </div>

            <h3>Checks</h3>
            {doctorStatus.data.checks && (
              <div className="checks-list">
                {Object.entries(doctorStatus.data.checks).map(([key, check]: [string, any]) => (
                  <div key={key} className={`check-item ${check.status}`}>
                    <span className="check-name">{key}</span>
                    <span className={`check-status ${check.status}`}>{check.status}</span>
                    <span className="check-message">{check.message}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </main>
  );
}

export default App;
