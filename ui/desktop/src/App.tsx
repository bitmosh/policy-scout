import { useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import "./App.css";
import { CliJsonResponse } from "./types";
import { BoundaryNote } from "./components/BoundaryNote";
import { DoctorStatusCard } from "./components/DoctorStatusCard";
import { DataStatusCard } from "./components/DataStatusCard";
import { ReportsListCard } from "./components/ReportsListCard";
import { AuditStatsCard } from "./components/AuditStatsCard";

function App() {
  const [doctorStatus, setDoctorStatus] = useState<CliJsonResponse | null>(null);
  const [dataStatus, setDataStatus] = useState<CliJsonResponse | null>(null);
  const [reportsList, setReportsList] = useState<CliJsonResponse | null>(null);
  const [auditStats, setAuditStats] = useState<CliJsonResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function fetchAllStatus() {
    setLoading(true);
    setError(null);
    try {
      const [doctor, data, reports, audit] = await Promise.all([
        invoke<CliJsonResponse>("get_doctor_status"),
        invoke<CliJsonResponse>("get_data_status"),
        invoke<CliJsonResponse>("list_reports"),
        invoke<CliJsonResponse>("get_audit_stats"),
      ]);
      setDoctorStatus(doctor);
      setDataStatus(data);
      setReportsList(reports);
      setAuditStats(audit);
      if (!doctor.ok) {
        setError(doctor.error || "Unknown error");
      }
      if (!data.ok) {
        setError(data.error || "Unknown error");
      }
      if (!reports.ok) {
        setError(reports.error || "Unknown error");
      }
      if (!audit.ok) {
        setError(audit.error || "Unknown error");
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
      <BoundaryNote />

      <div className="cards-container">
        {loading && <p className="status-message">Loading status...</p>}

        {error && (
          <div className="error-message">
            <p>Error: {error}</p>
          </div>
        )}

        <DoctorStatusCard doctorStatus={doctorStatus} loading={loading} onRefresh={fetchAllStatus} />
        <DataStatusCard dataStatus={dataStatus} />
        <ReportsListCard reportsList={reportsList} />
        <AuditStatsCard auditStats={auditStats} />
      </div>
    </main>
  );
}

export default App;
