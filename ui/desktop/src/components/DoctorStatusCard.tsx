// SPDX-License-Identifier: Apache-2.0
import { CliJsonResponse, DoctorStatusData } from "../types";

interface DoctorStatusCardProps {
  doctorStatus: CliJsonResponse<DoctorStatusData> | null;
  loading: boolean;
  onRefresh: () => void;
}

export function DoctorStatusCard({ doctorStatus, loading, onRefresh }: DoctorStatusCardProps) {
  return (
    <div className="doctor-card">
      <div className="card-header">
        <h2>Doctor Status</h2>
        <button onClick={onRefresh} disabled={loading}>
          {loading ? "Loading..." : "Refresh"}
        </button>
      </div>

      {loading && <p className="status-message">Loading status...</p>}

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
  );
}
