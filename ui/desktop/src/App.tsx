import { useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import "./App.css";
import { CliJsonResponse, ReportTypeFilter, AuditEventTypeFilter, CleanupTarget } from "./types";
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
import { SandboxResultsListCard } from "./components/SandboxResultsListCard";
import { SandboxResultDetailCard } from "./components/SandboxResultDetailCard";
import { DecisionCheckCard } from "./components/DecisionCheckCard";

function App() {
  const [doctorStatus, setDoctorStatus] = useState<CliJsonResponse | null>(null);
  const [dataStatus, setDataStatus] = useState<CliJsonResponse | null>(null);
  const [reportsList, setReportsList] = useState<CliJsonResponse | null>(null);
  const [auditStats, setAuditStats] = useState<CliJsonResponse | null>(null);
  const [auditEventsList, setAuditEventsList] = useState<CliJsonResponse | null>(null);
  const [cleanupResult, setCleanupResult] = useState<CliJsonResponse | null>(null);
  const [cleanupTarget, setCleanupTarget] = useState<CleanupTarget>("demo");
  const [cleanupLoading, setCleanupLoading] = useState(false);
  const [evalResults, setEvalResults] = useState<CliJsonResponse | null>(null);
  const [sandboxResultsList, setSandboxResultsList] = useState<CliJsonResponse | null>(null);
  const [selectedSandboxResultId, setSelectedSandboxResultId] = useState<string | null>(null);
  const [sandboxResultDetail, setSandboxResultDetail] = useState<CliJsonResponse | null>(null);
  const [sandboxResultDetailLoading, setSandboxResultDetailLoading] = useState(false);
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
  const [reportLimit, setReportLimit] = useState<number>(5);
  const [reportType, setReportType] = useState<ReportTypeFilter>("");
  const [reportsLoading, setReportsLoading] = useState(false);
  const [auditEventType, setAuditEventType] = useState<AuditEventTypeFilter>("all");
  const [auditEventsLoading, setAuditEventsLoading] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function fetchAllStatus() {
    setLoading(true);
    setError(null);
    try {
      const [doctor, data, reports, audit, auditEvents, cleanup, evalResult, sbxList] = await Promise.all([
        invoke<CliJsonResponse>("get_doctor_status"),
        invoke<CliJsonResponse>("get_data_status"),
        invoke<CliJsonResponse>("list_reports_filtered", { limit: reportLimit, reportType: reportType || null }),
        invoke<CliJsonResponse>("get_audit_stats"),
        invoke<CliJsonResponse>("list_audit_events_filtered", { event_type: auditEventType === "all" ? null : auditEventType }),
        invoke<CliJsonResponse>("get_cleanup_dry_run", { target: cleanupTarget }),
        invoke<CliJsonResponse>("run_eval"),
        invoke<CliJsonResponse>("list_sandbox_results"),
      ]);
      setDoctorStatus(doctor);
      setDataStatus(data);
      setReportsList(reports);
      setAuditStats(audit);
      setAuditEventsList(auditEvents);
      setCleanupResult(cleanup);
      setEvalResults(evalResult);
      setSandboxResultsList(sbxList);
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
      if (!cleanup.ok) {
        setError(cleanup.error || "Unknown error");
      }
      if (!evalResult.ok) {
        setError(evalResult.error || "Unknown error");
      }
      if (!sbxList.ok) {
        setError(sbxList.error || "Unknown error");
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

  async function fetchReports(limit: number, type: ReportTypeFilter) {
    setReportsLoading(true);
    try {
      const result = await invoke<CliJsonResponse>("list_reports_filtered", {
        limit,
        reportType: type || null,
      });
      setReportsList(result);
      if (!result.ok) {
        setError(result.error || "Unknown error");
      }
    } catch (e) {
      const errorStr = String(e);
      if (errorStr.includes("invoke") || errorStr.includes("undefined")) {
        setError("Tauri runtime unavailable. Launch with `npm run tauri dev` to load live Policy Scout data.");
      } else {
        setError(errorStr);
      }
    } finally {
      setReportsLoading(false);
    }
  }

  async function fetchCleanupDryRun(target: CleanupTarget) {
    setCleanupLoading(true);
    try {
      const result = await invoke<CliJsonResponse>("get_cleanup_dry_run", { target });
      setCleanupResult(result);
      if (!result.ok) {
        setError(result.error || "Unknown error");
      }
    } catch (e) {
      const errorStr = String(e);
      if (errorStr.includes("invoke") || errorStr.includes("undefined")) {
        setError("Tauri runtime unavailable. Launch with `npm run tauri dev` to load live Policy Scout data.");
      } else {
        setError(errorStr);
      }
    } finally {
      setCleanupLoading(false);
    }
  }

  function handleCleanupTargetChange(target: CleanupTarget) {
    setCleanupTarget(target);
    fetchCleanupDryRun(target);
  }

  function handleReportLimitChange(limit: number) {
    setReportLimit(limit);
    fetchReports(limit, reportType);
  }

  async function fetchAuditEvents(type: AuditEventTypeFilter) {
    setAuditEventsLoading(true);
    try {
      const result = await invoke<CliJsonResponse>("list_audit_events_filtered", {
        event_type: type === "all" ? null : type,
      });
      setAuditEventsList(result);
      if (!result.ok) {
        setError(result.error || "Unknown error");
      }
    } catch (e) {
      const errorStr = String(e);
      if (errorStr.includes("invoke") || errorStr.includes("undefined")) {
        setError("Tauri runtime unavailable. Launch with `npm run tauri dev` to load live Policy Scout data.");
      } else {
        setError(errorStr);
      }
    } finally {
      setAuditEventsLoading(false);
    }
  }

  function handleAuditEventTypeChange(type: AuditEventTypeFilter) {
    setAuditEventType(type);
    if (selectedAuditEventId) {
      setSelectedAuditEventId(null);
      setAuditEventDetail(null);
    }
    fetchAuditEvents(type);
  }

  function handleReportTypeChange(type: ReportTypeFilter) {
    setReportType(type);
    if (selectedReportId) {
      setSelectedReportId(null);
      setReportDetail(null);
    }
    fetchReports(reportLimit, type);
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

  async function handleSandboxResultClick(reportId: string) {
    setSelectedSandboxResultId(reportId);
    setSandboxResultDetail(null);
    setSandboxResultDetailLoading(true);
    try {
      const result = await invoke<CliJsonResponse>("show_sandbox_result", { reportId });
      setSandboxResultDetail(result);
    } catch (e) {
      const errorStr = String(e);
      if (errorStr.includes("invoke") || errorStr.includes("undefined")) {
        setError("Tauri runtime unavailable. Launch with `npm run tauri dev` to load live Policy Scout data.");
      } else {
        setError(errorStr);
      }
    } finally {
      setSandboxResultDetailLoading(false);
    }
  }

  function handleCloseSandboxResultDetail() {
    setSelectedSandboxResultId(null);
    setSandboxResultDetail(null);
  }

  return (
    <main className="container">
      <h1>Policy Scout</h1>
      <BoundaryNote />
      <OverviewStatusStrip
        doctorStatus={doctorStatus}
        reportsList={reportsList}
        auditStats={auditStats}
        cleanupResult={cleanupResult}
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

        <DecisionCheckCard />

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
        ) : selectedSandboxResultId ? (
          <SandboxResultDetailCard
            sandboxResultDetail={sandboxResultDetail}
            loading={sandboxResultDetailLoading}
            selectedId={selectedSandboxResultId}
            onClose={handleCloseSandboxResultDetail}
          />
        ) : (
          <>
            <DoctorStatusCard doctorStatus={doctorStatus} loading={loading} onRefresh={fetchAllStatus} />
            <DataStatusCard dataStatus={dataStatus} />
            <ReportsListCard
              reportsList={reportsList}
              onReportClick={handleReportClick}
              limit={reportLimit}
              reportType={reportType}
              onLimitChange={handleReportLimitChange}
              onTypeChange={handleReportTypeChange}
              loading={reportsLoading}
            />
            <AuditStatsCard auditStats={auditStats} />
            <AuditEventsListCard
              auditEventsList={auditEventsList}
              onEventClick={handleAuditEventClick}
              auditEventType={auditEventType}
              onTypeChange={handleAuditEventTypeChange}
              loading={auditEventsLoading}
            />
            <CleanupDryRunCard
              cleanupResult={cleanupResult}
              cleanupTarget={cleanupTarget}
              onTargetChange={handleCleanupTargetChange}
              loading={cleanupLoading}
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
            <SandboxResultsListCard sandboxResults={sandboxResultsList} onResultClick={handleSandboxResultClick} />
          </>
        )}
      </div>
    </main>
  );
}

export default App;
