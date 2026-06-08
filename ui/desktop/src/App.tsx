import { useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import "./App.css";

interface CliJsonResponse {
  ok: boolean;
  exit_code: number;
  data: any;
  error: string | null;
  stderr_summary: string | null;
}

function App() {
  const [doctorStatus, setDoctorStatus] = useState<CliJsonResponse | null>(null);
  const [dataStatus, setDataStatus] = useState<CliJsonResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function fetchAllStatus() {
    setLoading(true);
    setError(null);
    try {
      const [doctor, data] = await Promise.all([
        invoke<CliJsonResponse>("get_doctor_status"),
        invoke<CliJsonResponse>("get_data_status"),
      ]);
      setDoctorStatus(doctor);
      setDataStatus(data);
      if (!doctor.ok) {
        setError(doctor.error || "Unknown error");
      }
      if (!data.ok) {
        setError(data.error || "Unknown error");
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

      <div className="cards-container">
        <div className="doctor-card">
          <div className="card-header">
            <h2>Doctor Status</h2>
            <button onClick={fetchAllStatus} disabled={loading}>
              {loading ? "Loading..." : "Refresh"}
            </button>
          </div>

          {loading && <p className="status-message">Loading status...</p>}

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

        <div className="data-card">
          <div className="card-header">
            <h2>Data Status</h2>
          </div>

          {dataStatus && dataStatus.ok && dataStatus.data && (
            <div className="data-data">
              <div className="info-row">
                <span className="label">Data Root:</span>
                <span className="value">{dataStatus.data.data_root}</span>
              </div>

              <h3>Counts</h3>
              {dataStatus.data.counts && (
                <div className="counts-list">
                  {Object.entries(dataStatus.data.counts).map(([key, value]: [string, any]) => (
                    <div key={key} className="count-item">
                      <span className="count-name">{key}</span>
                      <span className="count-value">{value}</span>
                    </div>
                  ))}
                </div>
              )}

              <h3>Paths</h3>
              {dataStatus.data.paths && (
                <div className="paths-list">
                  {Object.entries(dataStatus.data.paths).map(([key, path]: [string, any]) => (
                    <div key={key} className={`path-item ${path.exists ? "exists" : "missing"}`}>
                      <span className="path-name">{key}</span>
                      <span className={`path-status ${path.exists ? "exists" : "missing"}`}>
                        {path.exists ? "exists" : "missing"}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </main>
  );
}

export default App;
