import { useState, useEffect } from "react";
import { invoke } from "@tauri-apps/api/core";
import "./App.css";
import {
  CliJsonResponse, ReportTypeFilter, AuditEventTypeFilter, CleanupTarget,
  DoctorStatusData, DataStatusData, AuditStatsData, CleanupDryRunData,
  EvalRunData, SweepData, ReportListData, ReportDetailData,
  AuditEventListData, AuditEventDetailData, SandboxResultListItem, SandboxResultDetailData,
  PolicyOverviewData, PolicyValidateData,
} from "./types";
import doctorStatusMock from "./mocks/doctor_status.json";
import dataStatusMock from "./mocks/data_status.json";
import auditStatsMock from "./mocks/audit_stats.json";
import cleanupDryRunMock from "./mocks/cleanup_dry_run.json";
import evalResultsMock from "./mocks/eval_results.json";
import sweepDataMock from "./mocks/sweep_data.json";
import reportListMockRaw from "./mocks/report_list.json";
import reportDetailMock from "./mocks/report_detail.json";
import auditEventsListMock from "./mocks/audit_events_list.json";
import auditEventDetailMock from "./mocks/audit_event_detail.json";
import sandboxResultListMock from "./mocks/sandbox_result_list.json";
import sandboxResultDetailMock from "./mocks/sandbox_result_detail.json";
import policyOverviewMock from "./mocks/policy_overview.json";
import policyValidateMock from "./mocks/policy_validate.json";

function mockResponse<T>(data: T): CliJsonResponse<T> {
  return { ok: true, exit_code: 0, data, error: null, stderr_summary: null };
}
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
import { PolicyOverviewCard } from "./components/PolicyOverviewCard";
import { PolicyValidateCard } from "./components/PolicyValidateCard";

function App() {
  const [doctorStatus, setDoctorStatus] = useState<CliJsonResponse<DoctorStatusData> | null>(null);
  const [dataStatus, setDataStatus] = useState<CliJsonResponse<DataStatusData> | null>(null);
  const [reportsList, setReportsList] = useState<CliJsonResponse<ReportListData> | null>(null);
  const [reportsOffset, setReportsOffset] = useState<number>(0);
  const [auditStats, setAuditStats] = useState<CliJsonResponse<AuditStatsData> | null>(null);
  const [auditEventsList, setAuditEventsList] = useState<CliJsonResponse<AuditEventListData> | null>(null);
  const [cleanupResult, setCleanupResult] = useState<CliJsonResponse<CleanupDryRunData> | null>(null);
  const [cleanupTarget, setCleanupTarget] = useState<CleanupTarget>("demo");
  const [cleanupLoading, setCleanupLoading] = useState(false);
  const [evalResults, setEvalResults] = useState<CliJsonResponse<EvalRunData> | null>(null);
  const [sandboxResultsList, setSandboxResultsList] = useState<CliJsonResponse<SandboxResultListItem[]> | null>(null);
  const [selectedSandboxResultId, setSelectedSandboxResultId] = useState<string | null>(null);
  const [sandboxResultDetail, setSandboxResultDetail] = useState<CliJsonResponse<SandboxResultDetailData> | null>(null);
  const [sandboxResultDetailLoading, setSandboxResultDetailLoading] = useState(false);
  const [quickSweep, setQuickSweep] = useState<CliJsonResponse<SweepData> | null>(null);
  const [sweepLoading, setSweepLoading] = useState(false);
  const [projectSweep, setProjectSweep] = useState<CliJsonResponse<SweepData> | null>(null);
  const [projectSweepLoading, setProjectSweepLoading] = useState(false);
  const [selectedReportId, setSelectedReportId] = useState<string | null>(null);
  const [reportDetail, setReportDetail] = useState<CliJsonResponse<ReportDetailData> | null>(null);
  const [reportDetailLoading, setReportDetailLoading] = useState(false);
  const [selectedAuditEventId, setSelectedAuditEventId] = useState<string | null>(null);
  const [auditEventDetail, setAuditEventDetail] = useState<CliJsonResponse<AuditEventDetailData> | null>(null);
  const [auditEventDetailLoading, setAuditEventDetailLoading] = useState(false);
  const [policyOverview, setPolicyOverview] = useState<CliJsonResponse<PolicyOverviewData> | null>(null);
  const [policyValidate, setPolicyValidate] = useState<CliJsonResponse<PolicyValidateData> | null>(null);
  const [policyValidateLoading, setPolicyValidateLoading] = useState(false);
  const [reportLimit, setReportLimit] = useState<number>(5);
  const [reportType, setReportType] = useState<ReportTypeFilter>("");
  const [reportsLoading, setReportsLoading] = useState(false);
  const [auditEventType, setAuditEventType] = useState<AuditEventTypeFilter>("all");
  const [auditEventsLoading, setAuditEventsLoading] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load audit events on mount and when filter changes
  useEffect(() => {
    fetchAuditEvents(auditEventType);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [auditEventType]);

  async function fetchAllStatus() {
    setLoading(true);
    setError(null);
    try {
      const [doctor, data, reports, audit, cleanup, evalResult, sbxList, policyOv] = await Promise.all([
        invoke<CliJsonResponse<DoctorStatusData>>("get_doctor_status"),
        invoke<CliJsonResponse<DataStatusData>>("get_data_status"),
        invoke<CliJsonResponse<ReportListData>>("list_reports_filtered", { limit: reportLimit, reportType: reportType || null }),
        invoke<CliJsonResponse<AuditStatsData>>("get_audit_stats"),
        invoke<CliJsonResponse<CleanupDryRunData>>("get_cleanup_dry_run", { target: cleanupTarget }),
        invoke<CliJsonResponse<EvalRunData>>("run_eval"),
        invoke<CliJsonResponse<SandboxResultListItem[]>>("list_sandbox_results"),
        invoke<CliJsonResponse<PolicyOverviewData>>("get_policy_overview"),
      ]);
      setDoctorStatus(doctor);
      setDataStatus(data);
      setReportsList(reports);
      setAuditStats(audit);
      setCleanupResult(cleanup);
      setPolicyOverview(policyOv);
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
      if (errorStr.includes("invoke") || errorStr.includes("undefined") || errorStr.includes("not been defined")) {
        setDoctorStatus(mockResponse(doctorStatusMock as DoctorStatusData));
        setDataStatus(mockResponse(dataStatusMock as DataStatusData));
        setReportsList(mockResponse(reportListMockRaw as ReportListData));
        setAuditStats(mockResponse(auditStatsMock as AuditStatsData));
        setCleanupResult(mockResponse(cleanupDryRunMock as CleanupDryRunData));
        setEvalResults(mockResponse(evalResultsMock as EvalRunData));
        setSandboxResultsList(mockResponse(sandboxResultListMock as SandboxResultListItem[]));
        setPolicyOverview(mockResponse(policyOverviewMock as PolicyOverviewData));
      } else {
        setError(errorStr);
      }
    } finally {
      setLoading(false);
    }
  }

  async function fetchReports(limit: number, type: ReportTypeFilter, offset: number = 0) {
    setReportsLoading(true);
    setReportsOffset(offset);
    try {
      const result = await invoke<CliJsonResponse<ReportListData>>("list_reports_filtered", {
        limit,
        reportType: type || null,
        offset,
      });
      setReportsList(result);
      if (!result.ok) {
        setError(result.error || "Unknown error");
      }
    } catch (e) {
      const errorStr = String(e);
      if (errorStr.includes("invoke") || errorStr.includes("undefined") || errorStr.includes("not been defined")) {
        setReportsList(mockResponse(reportListMockRaw as ReportListData));
      } else {
        setError(errorStr);
      }
    } finally {
      setReportsLoading(false);
    }
  }

  function handleReportPagePrev() {
    const newOffset = Math.max(0, reportsOffset - reportLimit);
    fetchReports(reportLimit, reportType, newOffset);
  }

  function handleReportPageNext() {
    const totalCount = reportsList?.data?.total_count ?? 0;
    const newOffset = reportsOffset + reportLimit;
    if (newOffset < totalCount) {
      fetchReports(reportLimit, reportType, newOffset);
    }
  }

  async function fetchCleanupDryRun(target: CleanupTarget) {
    setCleanupLoading(true);
    try {
      const result = await invoke<CliJsonResponse<CleanupDryRunData>>("get_cleanup_dry_run", { target });
      setCleanupResult(result);
      if (!result.ok) {
        setError(result.error || "Unknown error");
      }
    } catch (e) {
      const errorStr = String(e);
      if (errorStr.includes("invoke") || errorStr.includes("undefined") || errorStr.includes("not been defined")) {
        setCleanupResult(mockResponse(cleanupDryRunMock as CleanupDryRunData));
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
      const result = await invoke<CliJsonResponse<AuditEventListData>>("list_audit_events_filtered", {
        event_type: type === "all" ? null : type,
      });
      setAuditEventsList(result);
      if (!result.ok) {
        setError(result.error || "Unknown error");
      }
    } catch (e) {
      const errorStr = String(e);
      if (errorStr.includes("invoke") || errorStr.includes("undefined") || errorStr.includes("not been defined")) {
        setAuditEventsList(mockResponse(auditEventsListMock as AuditEventListData));
      } else {
        setError(errorStr);
      }
    } finally {
      setAuditEventsLoading(false);
    }
  }

  function handleAuditEventTypeChange(type: AuditEventTypeFilter) {
    setAuditEventType(type);
    setSelectedAuditEventId(null);
    setAuditEventDetail(null);
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
      const result = await invoke<CliJsonResponse<SweepData>>("run_sweep_quick");
      setQuickSweep(result);
    } catch (e) {
      const errorStr = String(e);
      if (errorStr.includes("invoke") || errorStr.includes("undefined") || errorStr.includes("not been defined")) {
        setQuickSweep(mockResponse(sweepDataMock as SweepData));
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
      const result = await invoke<CliJsonResponse<SweepData>>("run_sweep_project");
      setProjectSweep(result);
    } catch (e) {
      const errorStr = String(e);
      if (errorStr.includes("invoke") || errorStr.includes("undefined") || errorStr.includes("not been defined")) {
        setProjectSweep(mockResponse(sweepDataMock as SweepData));
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
      const result = await invoke<CliJsonResponse<ReportDetailData>>("show_report", { reportId });
      setReportDetail(result);
    } catch (e) {
      const errorStr = String(e);
      if (errorStr.includes("invoke") || errorStr.includes("undefined") || errorStr.includes("not been defined")) {
        setReportDetail(mockResponse(reportDetailMock as ReportDetailData));
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
      const result = await invoke<CliJsonResponse<AuditEventDetailData>>("show_audit_event", { eventId });
      setAuditEventDetail(result);
    } catch (e) {
      const errorStr = String(e);
      if (errorStr.includes("invoke") || errorStr.includes("undefined") || errorStr.includes("not been defined")) {
        setAuditEventDetail(mockResponse(auditEventDetailMock as AuditEventDetailData));
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
      const result = await invoke<CliJsonResponse<SandboxResultDetailData>>("show_sandbox_result", { reportId });
      setSandboxResultDetail(result);
    } catch (e) {
      const errorStr = String(e);
      if (errorStr.includes("invoke") || errorStr.includes("undefined") || errorStr.includes("not been defined")) {
        setSandboxResultDetail(mockResponse(sandboxResultDetailMock as SandboxResultDetailData));
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

  async function runPolicyValidate() {
    setPolicyValidateLoading(true);
    try {
      const result = await invoke<CliJsonResponse<PolicyValidateData>>("run_policy_validate");
      setPolicyValidate(result);
    } catch (e) {
      const errorStr = String(e);
      if (errorStr.includes("invoke") || errorStr.includes("undefined") || errorStr.includes("not been defined")) {
        setPolicyValidate(mockResponse(policyValidateMock as PolicyValidateData));
      } else {
        setError(errorStr);
      }
    } finally {
      setPolicyValidateLoading(false);
    }
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
              offset={reportsOffset}
              totalCount={reportsList?.data?.total_count}
              onPagePrev={reportsOffset > 0 ? handleReportPagePrev : undefined}
              onPageNext={(reportsOffset + reportLimit) < (reportsList?.data?.total_count ?? 0) ? handleReportPageNext : undefined}
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
            <PolicyOverviewCard policyOverview={policyOverview} />
            <PolicyValidateCard
              policyValidate={policyValidate}
              loading={policyValidateLoading}
              onRunValidate={runPolicyValidate}
            />
          </>
        )}
      </div>
    </main>
  );
}

export default App;
