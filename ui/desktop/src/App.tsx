import { useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import "./App.css";
import { CliJsonResponse } from "./types";
import { BoundaryNote } from "./components/BoundaryNote";
import { OverviewStatusStrip } from "./components/OverviewStatusStrip";
import { DoctorStatusCard } from "./components/DoctorStatusCard";
import { DataStatusCard } from "./components/DataStatusCard";
import { ReportsListCard } from "./components/ReportsListCard";
import { AuditStatsCard } from "./components/AuditStatsCard";
import { AuditEventsListCard } from "./components/AuditEventsListCard";
import { AuditEventDetailCard } from "./components/AuditEventDetailCard";
import { CleanupDryRunCard } from "./components/CleanupDryRunCard";
import { EvalResultsCard } from "./components/EvalResultsCard";
import { QuickSweepCard } from "./components/QuickSweepCard";
import { ProjectSweepCard } from "./components/ProjectSweepCard";
import { ReportDetailCard } from "./components/ReportDetailCard";

function App() {
  const [doctorStatus, setDoctorStatus] = useState<CliJsonResponse | null>(null);
  const [dataStatus, setDataStatus] = useState<CliJsonResponse | null>(null);
  const [reportsList, setReportsList] = useState<CliJsonResponse | null>(null);
  const [auditStats, setAuditStats] = useState<CliJsonResponse | null>(null);
  const [auditEventsList, setAuditEventsList] = useState<CliJsonResponse | null>(null);
  const [demoCleanup, setDemoCleanup] = useState<CliJsonResponse | null>(null);
  const [sandboxCleanup, setSandboxCleanup] = useState<CliJsonResponse | null>(null);
  const [sandboxResultsCleanup, setSandboxResultsCleanup] = useState<CliJsonResponse | null>(null);
  const [evalResults, setEvalResults] = useState<CliJsonResponse | null>(null);
  const [quickSweep, setQuickSweep] = useState<CliJsonResponse | null>(null);
  const [sweepLoading, setSweepLoading] = useState(false);
  const [projectSweep, setProjectSweep] = useState<CliJsonResponse | null>(null);
  const [projectSweepLoading, setProjectSweepLoading] = useState(false);
  const [selectedReportId, setSelectedReportId] = useState<string | null>(null);
  const [reportDetail, setReportDetail] = useState<CliJsonResponse | null>(null);
  const [reportDetailLoading, setReportDetailLoading] = useState(false);
  const [selectedAuditEventId, setSelectedAuditEventId] = useState<string | null>(null);
  const [auditEventDetail, setAuditEventDetail] = useState<CliJsonResponse | null>(null);
  const [auditEventDetailLoading, setAuditEventDetailLoading] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function fetchAllStatus() {
    setLoading(true);
    setError(null);
    try {
      const [doctor, data, reports, audit, auditEvents, demo, sandbox, sandboxResults, evalResult] = await Promise.all([
        invoke<CliJsonResponse>("get_doctor_status"),
        invoke<CliJsonResponse>("get_data_status"),
        invoke<CliJsonResponse>("list_reports"),
        invoke<CliJsonResponse>("get_audit_stats"),
        invoke<CliJsonResponse>("list_audit_events"),
        invoke<CliJsonResponse>("get_cleanup_dry_run_demo"),
        invoke<CliJsonResponse>("get_cleanup_dry_run_sandbox"),
        invoke<CliJsonResponse>("get_cleanup_dry_run_sandbox_results"),
        invoke<CliJsonResponse>("run_eval"),
      ]);
      setDoctorStatus(doctor);
      setDataStatus(data);
      setReportsList(reports);
      setAuditStats(audit);
      setAuditEventsList(auditEvents);
      setDemoCleanup(demo);
      setSandboxCleanup(sandbox);
      setSandboxResultsCleanup(sandboxResults);
      setEvalResults(evalResult);
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
      if (!auditEvents.ok) {
        setError(auditEvents.error || "Unknown error");
      }
      if (!demo.ok) {
        setError(demo.error || "Unknown error");
      }
      if (!sandbox.ok) {
        setError(sandbox.error || "Unknown error");
      }
      if (!sandboxResults.ok) {
        setError(sandboxResults.error || "Unknown error");
      }
      if (!evalResult.ok) {
        setError(evalResult.error || "Unknown error");
      }
    } catch (e) {
      const errorStr = String(e);
      // Detect Tauri invoke error (occurs in browser preview without Tauri runtime)
      if (errorStr.includes("invoke") || errorStr.includes("undefined")) {
        setError("Tauri runtime unavailable. Launch with `npm run tauri dev` to load live Policy Scout data.");
      } else {
        setError(errorStr);
      }
    } finally {
      setLoading(false);
    }
  }

  async function runQuickSweep() {
    setSweepLoading(true);
    try {
      const result = await invoke<CliJsonResponse>("run_sweep_quick");
      setQuickSweep(result);
    } catch (e) {
      const errorStr = String(e);
      if (errorStr.includes("invoke") || errorStr.includes("undefined")) {
        setError("Tauri runtime unavailable. Launch with `npm run tauri dev` to load live Policy Scout data.");
      } else {
        setError(errorStr);
      }
    } finally {
      setSweepLoading(false);
    }
  }

  async function runProjectSweep() {
    setProjectSweepLoading(true);
    try {
      const result = await invoke<CliJsonResponse>("run_sweep_project");
      setProjectSweep(result);
    } catch (e) {
      const errorStr = String(e);
      if (errorStr.includes("invoke") || errorStr.includes("undefined")) {
        setError("Tauri runtime unavailable. Launch with `npm run tauri dev` to load live Policy Scout data.");
      } else {
        setError(errorStr);
      }
    } finally {
      setProjectSweepLoading(false);
    }
  }

  async function handleReportClick(reportId: string) {
    setSelectedReportId(reportId);
    setReportDetail(null);
    setReportDetailLoading(true);
    try {
      const result = await invoke<CliJsonResponse>("show_report", { reportId });
      setReportDetail(result);
    } catch (e) {
      const errorStr = String(e);
      if (errorStr.includes("invoke") || errorStr.includes("undefined")) {
        setError("Tauri runtime unavailable. Launch with `npm run tauri dev` to load live Policy Scout data.");
      } else {
        setError(errorStr);
      }
    } finally {
      setReportDetailLoading(false);
    }
  }

  function handleCloseReportDetail() {
    setSelectedReportId(null);
    setReportDetail(null);
  }

  async function handleAuditEventClick(eventId: string) {
    setSelectedAuditEventId(eventId);
    setAuditEventDetail(null);
    setAuditEventDetailLoading(true);
    try {
      const result = await invoke<CliJsonResponse>("show_audit_event", { eventId });
      setAuditEventDetail(result);
    } catch (e) {
      const errorStr = String(e);
      if (errorStr.includes("invoke") || errorStr.includes("undefined")) {
        setError("Tauri runtime unavailable. Launch with `npm run tauri dev` to load live Policy Scout data.");
      } else {
        setError(errorStr);
      }
    } finally {
      setAuditEventDetailLoading(false);
    }
  }

  function handleCloseAuditEventDetail() {
    setSelectedAuditEventId(null);
    setAuditEventDetail(null);
  }

  return (
    <main className="container">
      <h1>Policy Scout</h1>
      <BoundaryNote />
      <OverviewStatusStrip
        doctorStatus={doctorStatus}
        reportsList={reportsList}
        auditStats={auditStats}
        demoCleanup={demoCleanup}
        sandboxCleanup={sandboxCleanup}
        sandboxResultsCleanup={sandboxResultsCleanup}
        evalResults={evalResults}
        quickSweep={quickSweep}
      />

      <div className="cards-container">
        {loading && <p className="status-message">Loading status...</p>}

        {error && (
          <div className="error-message">
            <p>Error: {error}</p>
          </div>
        )}

        {selectedReportId ? (
          <ReportDetailCard
            reportDetail={reportDetail}
            loading={reportDetailLoading}
            selectedId={selectedReportId}
            onClose={handleCloseReportDetail}
          />
        ) : selectedAuditEventId ? (
          <AuditEventDetailCard
            auditEventDetail={auditEventDetail}
            loading={auditEventDetailLoading}
            selectedId={selectedAuditEventId}
            onClose={handleCloseAuditEventDetail}
          />
        ) : (
          <>
            <DoctorStatusCard doctorStatus={doctorStatus} loading={loading} onRefresh={fetchAllStatus} />
            <DataStatusCard dataStatus={dataStatus} />
            <ReportsListCard reportsList={reportsList} onReportClick={handleReportClick} />
            <AuditStatsCard auditStats={auditStats} />
            <AuditEventsListCard auditEventsList={auditEventsList} onEventClick={handleAuditEventClick} />
            <CleanupDryRunCard
              demoCleanup={demoCleanup}
              sandboxCleanup={sandboxCleanup}
              sandboxResultsCleanup={sandboxResultsCleanup}
            />
            <EvalResultsCard evalResults={evalResults} />
            <QuickSweepCard
              quickSweep={quickSweep}
              loading={sweepLoading}
              onRunSweep={runQuickSweep}
            />
            <ProjectSweepCard
              projectSweep={projectSweep}
              loading={projectSweepLoading}
              onRunSweep={runProjectSweep}
            />
          </>
        )}
      </div>
    </main>
  );
}

export default App;
