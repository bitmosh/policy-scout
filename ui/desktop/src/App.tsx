import { useState, useEffect } from "react";
import { invoke } from "@tauri-apps/api/core";
import "./App.css";
import {
  CliJsonResponse, ReportTypeFilter, AuditEventTypeFilter, CleanupTarget,
  DoctorStatusData, DataStatusData, AuditStatsData, CleanupDryRunData, CleanupApplyData,
  EvalRunData, SweepData, ReportListData, ReportDetailData,
  AuditEventListData, AuditEventDetailData, SandboxResultDetailData, SandboxLaunchResultData, SandboxMigrationData,
  PolicyOverviewData, PolicyValidateData,
  ApprovalListData, ApprovalActionData,
  LockdownStatusData, WatchStatusData,
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
import sandboxLaunchResultMock from "./mocks/sandbox_launch_result.json";
import sandboxMigrationDryRunMock from "./mocks/sandbox_migration_dry_run.json";
import approvalsListMock from "./mocks/approvals_list.json";
import lockdownStatusMock from "./mocks/lockdown_status.json";
import watchStatusMock from "./mocks/watch_status.json";
import policyOverviewMock from "./mocks/policy_overview.json";
import policyValidateMock from "./mocks/policy_validate.json";

import { applyTheme, readStoredTheme, readStoredTexture, type ThemeId } from "./themes";
import { Sidebar, TopBar, NAV, type ViewId } from "./components/Shell";
import { Toast, type ToastData } from "./components/Toast";
import { OverviewView, Placeholder, deriveReviewRows } from "./components/OverviewView";

import { ReportsListCard } from "./components/ReportsListCard";
import { ReportDetailCard } from "./components/ReportDetailCard";
import { AuditEventsListCard } from "./components/AuditEventsListCard";
import { AuditEventDetailCard } from "./components/AuditEventDetailCard";
import { QuickSweepCard } from "./components/QuickSweepCard";
import { ProjectSweepCard } from "./components/ProjectSweepCard";
import { SandboxResultsListCard } from "./components/SandboxResultsListCard";
import { SandboxResultDetailCard } from "./components/SandboxResultDetailCard";
import { DecisionCheckCard } from "./components/DecisionCheckCard";
import { DoctorStatusCard } from "./components/DoctorStatusCard";
import { DataStatusCard } from "./components/DataStatusCard";
import { EvalResultsCard } from "./components/EvalResultsCard";
import { CleanupDryRunCard } from "./components/CleanupDryRunCard";
import { PolicyOverviewCard } from "./components/PolicyOverviewCard";
import { PolicyValidateCard } from "./components/PolicyValidateCard";
import { PolicySimulateCard } from "./components/PolicySimulateCard";
import { HelpDrawer } from "./components/HelpDrawer";
import { ApprovalsView } from "./components/ApprovalsView";
import { SandboxLaunchCard } from "./components/SandboxLaunchCard";
import { LiveStatusCard } from "./components/LiveStatusCard";
import { ScanView } from "./components/ScanView";
import { AuditVerifyChainCard } from "./components/AuditVerifyChainCard";

function mockResponse<T>(data: T): CliJsonResponse<T> {
  return { ok: true, exit_code: 0, data, error: null, stderr_summary: null };
}

function isMockError(e: unknown): boolean {
  const s = String(e);
  return s.includes("invoke") || s.includes("undefined") || s.includes("not been defined");
}

function deriveLastSweep(auditEventsList?: CliJsonResponse<AuditEventListData> | null): string {
  const events = auditEventsList?.data?.events;
  if (!events) return "—";
  const sweep = events.find(e => e.event_type === "SweepCompleted");
  if (!sweep?.timestamp) return "—";
  const diff = (Date.now() - new Date(sweep.timestamp).getTime()) / 1000;
  if (diff < 60) return "just now";
  if (diff < 3600) return `${Math.floor(diff / 60)} min ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)} hr ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

function App() {
  // ── shell state ──────────────────────────────────────────────
  const [activeView, setActiveView] = useState<ViewId>("overview");
  const [themeId, setThemeId] = useState<ThemeId>(readStoredTheme);
  const [texture, setTexture] = useState<boolean>(readStoredTexture);
  const [toast, setToast] = useState<ToastData | null>(null);
  const [lastSweepOverride, setLastSweepOverride] = useState<string | null>(null);
  const [helpOpen, setHelpOpen] = useState(false);

  useEffect(() => { applyTheme(themeId, texture); }, [themeId, texture]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setActiveView("check");
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  useEffect(() => {
    if (!toast) return;
    const t = setTimeout(() => setToast(null), 4400);
    return () => clearTimeout(t);
  }, [toast]);

  // ── data state ───────────────────────────────────────────────
  const [doctorStatus, setDoctorStatus] = useState<CliJsonResponse<DoctorStatusData> | null>(null);
  const [dataStatus, setDataStatus] = useState<CliJsonResponse<DataStatusData> | null>(null);
  const [reportsList, setReportsList] = useState<CliJsonResponse<ReportListData> | null>(null);
  const [reportsOffset, setReportsOffset] = useState<number>(0);
  const [auditStats, setAuditStats] = useState<CliJsonResponse<AuditStatsData> | null>(null);
  const [auditEventsList, setAuditEventsList] = useState<CliJsonResponse<AuditEventListData> | null>(null);
  const [cleanupResult, setCleanupResult] = useState<CliJsonResponse<CleanupDryRunData> | null>(null);
  const [cleanupTarget, setCleanupTarget] = useState<CleanupTarget>("demo");
  const [cleanupLoading, setCleanupLoading] = useState(false);
  const [cleanupApplyResult, setCleanupApplyResult] = useState<CliJsonResponse<CleanupApplyData> | null>(null);
  const [cleanupApplyLoading, setCleanupApplyLoading] = useState(false);
  const [evalResults, setEvalResults] = useState<CliJsonResponse<EvalRunData> | null>(null);
  const [sandboxResultsList, setSandboxResultsList] = useState<CliJsonResponse<ReportListData> | null>(null);
  const [sandboxLimit, setSandboxLimit] = useState<number>(5);
  const [sandboxOffset, setSandboxOffset] = useState<number>(0);
  const [sandboxLoading, setSandboxLoading] = useState(false);
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
  const [auditEventsOffset, setAuditEventsOffset] = useState<number>(0);
  const [auditEventsLimit, setAuditEventsLimit] = useState<number>(25);
  const [auditEventsLoading, setAuditEventsLoading] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [approvalsList, setApprovalsList] = useState<CliJsonResponse<ApprovalListData> | null>(null);
  const [approvalsLoading, setApprovalsLoading] = useState(false);
  const [approvalActionLoading, setApprovalActionLoading] = useState<Record<string, boolean>>({});
  const [approvalActionResults, setApprovalActionResults] = useState<Record<string, CliJsonResponse<ApprovalActionData>>>({});
  const [sandboxLaunchResult, setSandboxLaunchResult] = useState<CliJsonResponse<SandboxLaunchResultData> | null>(null);
  const [sandboxLaunchLoading, setSandboxLaunchLoading] = useState(false);
  const [migrationPreview, setMigrationPreview] = useState<CliJsonResponse<SandboxMigrationData> | null>(null);
  const [migrationPreviewLoading, setMigrationPreviewLoading] = useState(false);
  const [migrationResult, setMigrationResult] = useState<CliJsonResponse<SandboxMigrationData> | null>(null);
  const [migrationLoading, setMigrationLoading] = useState(false);
  const [lockdownStatus, setLockdownStatus] = useState<CliJsonResponse<LockdownStatusData> | null>(null);
  const [watchStatus, setWatchStatus] = useState<CliJsonResponse<WatchStatusData> | null>(null);
  const [liveStatusLoading, setLiveStatusLoading] = useState(false);
  const [checkTab, setCheckTab] = useState<"check" | "simulate">("check");

  useEffect(() => {
    fetchAuditEvents(auditEventType);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [auditEventType]);

  // Initial data load on mount
  useEffect(() => {
    fetchAllStatus();
    fetchApprovals();
    fetchLiveStatus();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

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
        invoke<CliJsonResponse<ReportListData>>("list_sandbox_results", { limit: sandboxLimit, offset: 0 }),
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
    } catch (e) {
      if (isMockError(e)) {
        setDoctorStatus(mockResponse(doctorStatusMock as DoctorStatusData));
        setDataStatus(mockResponse(dataStatusMock as DataStatusData));
        setReportsList(mockResponse(reportListMockRaw as ReportListData));
        setAuditStats(mockResponse(auditStatsMock as AuditStatsData));
        setCleanupResult(mockResponse(cleanupDryRunMock as CleanupDryRunData));
        setEvalResults(mockResponse(evalResultsMock as EvalRunData));
        setSandboxResultsList(mockResponse(sandboxResultListMock as ReportListData));
        setPolicyOverview(mockResponse(policyOverviewMock as PolicyOverviewData));
        setPolicyValidate(mockResponse(policyValidateMock as PolicyValidateData));
      } else {
        setError(String(e));
      }
    } finally {
      setLoading(false);
    }
    // Always refresh audit events alongside main status so review rows stay in sync
    fetchAuditEvents(auditEventType);
  }

  async function fetchReports(limit: number, type: ReportTypeFilter, offset: number = 0) {
    setReportsLoading(true);
    setReportsOffset(offset);
    try {
      const result = await invoke<CliJsonResponse<ReportListData>>("list_reports_filtered", { limit, reportType: type || null, offset });
      setReportsList(result);
    } catch (e) {
      if (isMockError(e)) setReportsList(mockResponse(reportListMockRaw as ReportListData));
      else setError(String(e));
    } finally {
      setReportsLoading(false);
    }
  }

  function handleReportPagePrev() { fetchReports(reportLimit, reportType, Math.max(0, reportsOffset - reportLimit)); }
  function handleReportPageNext() {
    const newOffset = reportsOffset + reportLimit;
    if (newOffset < (reportsList?.data?.total_count ?? 0)) fetchReports(reportLimit, reportType, newOffset);
  }
  function handleReportLimitChange(limit: number) { setReportLimit(limit); fetchReports(limit, reportType); }
  function handleReportTypeChange(type: ReportTypeFilter) {
    setReportType(type);
    if (selectedReportId) { setSelectedReportId(null); setReportDetail(null); }
    fetchReports(reportLimit, type);
  }

  async function fetchCleanupDryRun(target: CleanupTarget) {
    setCleanupLoading(true);
    try {
      const result = await invoke<CliJsonResponse<CleanupDryRunData>>("get_cleanup_dry_run", { target });
      setCleanupResult(result);
    } catch (e) {
      if (isMockError(e)) setCleanupResult(mockResponse(cleanupDryRunMock as CleanupDryRunData));
      else setError(String(e));
    } finally {
      setCleanupLoading(false);
    }
  }

  function handleCleanupTargetChange(target: CleanupTarget) {
    setCleanupTarget(target);
    setCleanupApplyResult(null);
    fetchCleanupDryRun(target);
  }

  async function runCleanupApply() {
    setCleanupApplyLoading(true);
    try {
      const result = await invoke<CliJsonResponse<CleanupApplyData>>("run_cleanup_apply", { target: cleanupTarget });
      setCleanupApplyResult(result);
      fetchCleanupDryRun(cleanupTarget);
    } catch (e) {
      setCleanupApplyResult({ ok: false, exit_code: -1, data: null as unknown as CleanupApplyData, error: String(e), stderr_summary: null });
    } finally {
      setCleanupApplyLoading(false);
    }
  }

  async function fetchSandboxResults(limit: number, offset: number = 0) {
    setSandboxLoading(true);
    setSandboxOffset(offset);
    try {
      const result = await invoke<CliJsonResponse<ReportListData>>("list_sandbox_results", { limit, offset });
      setSandboxResultsList(result);
    } catch (e) {
      if (isMockError(e)) setSandboxResultsList(mockResponse(sandboxResultListMock as ReportListData));
      else setError(String(e));
    } finally {
      setSandboxLoading(false);
    }
  }

  function handleSandboxLimitChange(limit: number) { setSandboxLimit(limit); fetchSandboxResults(limit, 0); }
  function handleSandboxPagePrev() { fetchSandboxResults(sandboxLimit, Math.max(0, sandboxOffset - sandboxLimit)); }
  function handleSandboxPageNext() {
    const newOffset = sandboxOffset + sandboxLimit;
    if (newOffset < (sandboxResultsList?.data?.total_count ?? 0)) fetchSandboxResults(sandboxLimit, newOffset);
  }

  async function fetchAuditEvents(type: AuditEventTypeFilter, limit: number = auditEventsLimit, offset: number = 0) {
    setAuditEventsLoading(true);
    setAuditEventsOffset(offset);
    try {
      const result = await invoke<CliJsonResponse<AuditEventListData>>("list_audit_events_filtered", {
        event_type: type === "all" ? null : type, limit, offset,
      });
      setAuditEventsList(result);
    } catch (e) {
      if (isMockError(e)) setAuditEventsList(mockResponse(auditEventsListMock as AuditEventListData));
      else setError(String(e));
    } finally {
      setAuditEventsLoading(false);
    }
  }

  function handleAuditEventTypeChange(type: AuditEventTypeFilter) {
    setAuditEventType(type);
    setAuditEventsOffset(0);
    setSelectedAuditEventId(null);
    setAuditEventDetail(null);
  }
  function handleAuditLimitChange(limit: number) { setAuditEventsLimit(limit); fetchAuditEvents(auditEventType, limit, 0); }
  function handleAuditPagePrev() { fetchAuditEvents(auditEventType, auditEventsLimit, Math.max(0, auditEventsOffset - auditEventsLimit)); }
  function handleAuditPageNext() {
    const newOffset = auditEventsOffset + auditEventsLimit;
    if (newOffset < (auditEventsList?.data?.total_count ?? 0)) fetchAuditEvents(auditEventType, auditEventsLimit, newOffset);
  }

  async function runQuickSweep() {
    setSweepLoading(true);
    try {
      const result = await invoke<CliJsonResponse<SweepData>>("run_sweep_quick");
      setQuickSweep(result);
      setLastSweepOverride("just now");
      const count = result.data?.findings?.length ?? 0;
      setToast({
        title: "Quick sweep complete",
        sub: `${count} finding${count !== 1 ? "s" : ""}`,
        actionLabel: "View in Sweeps",
        onAction: () => setActiveView("sweeps"),
      });
    } catch (e) {
      if (isMockError(e)) {
        const mock = mockResponse(sweepDataMock as SweepData);
        setQuickSweep(mock);
        setLastSweepOverride("just now");
        const count = mock.data?.findings?.length ?? 0;
        setToast({
          title: "Quick sweep complete",
          sub: `${count} finding${count !== 1 ? "s" : ""}`,
          actionLabel: "View in Sweeps",
          onAction: () => setActiveView("sweeps"),
        });
      } else {
        setError(String(e));
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
      if (isMockError(e)) setProjectSweep(mockResponse(sweepDataMock as SweepData));
      else setError(String(e));
    } finally {
      setProjectSweepLoading(false);
    }
  }

  async function runPolicyValidate() {
    setPolicyValidateLoading(true);
    try {
      const result = await invoke<CliJsonResponse<PolicyValidateData>>("run_policy_validate");
      setPolicyValidate(result);
    } catch (e) {
      if (isMockError(e)) setPolicyValidate(mockResponse(policyValidateMock as PolicyValidateData));
      else setError(String(e));
    } finally {
      setPolicyValidateLoading(false);
    }
  }

  async function fetchLiveStatus() {
    setLiveStatusLoading(true);
    try {
      const [lockdown, watch] = await Promise.all([
        invoke<CliJsonResponse<LockdownStatusData>>("get_lockdown_status"),
        invoke<CliJsonResponse<WatchStatusData>>("get_watch_status"),
      ]);
      setLockdownStatus(lockdown);
      setWatchStatus(watch);
    } catch (e) {
      if (isMockError(e)) {
        setLockdownStatus(mockResponse(lockdownStatusMock as LockdownStatusData));
        setWatchStatus(mockResponse(watchStatusMock as WatchStatusData));
      }
    } finally {
      setLiveStatusLoading(false);
    }
  }

  async function runSandboxMigrateDryRun(sandboxId: string) {
    setMigrationPreviewLoading(true);
    setMigrationPreview(null);
    setMigrationResult(null);
    try {
      const result = await invoke<CliJsonResponse<SandboxMigrationData>>("run_sandbox_migrate_dry_run", { sandboxId });
      setMigrationPreview(result);
    } catch (e) {
      if (isMockError(e)) setMigrationPreview(mockResponse(sandboxMigrationDryRunMock as SandboxMigrationData));
      else setMigrationPreview({ ok: false, exit_code: -1, data: null as unknown as SandboxMigrationData, error: String(e), stderr_summary: null });
    } finally {
      setMigrationPreviewLoading(false);
    }
  }

  async function runSandboxMigrate(sandboxId: string) {
    setMigrationLoading(true);
    try {
      const result = await invoke<CliJsonResponse<SandboxMigrationData>>("run_sandbox_migrate", { sandboxId });
      setMigrationResult(result);
    } catch (e) {
      setMigrationResult({ ok: false, exit_code: -1, data: null as unknown as SandboxMigrationData, error: String(e), stderr_summary: null });
    } finally {
      setMigrationLoading(false);
    }
  }

  async function fetchApprovals() {
    setApprovalsLoading(true);
    try {
      const result = await invoke<CliJsonResponse<ApprovalListData>>("list_approvals");
      setApprovalsList(result);
    } catch (e) {
      if (isMockError(e)) setApprovalsList(mockResponse(approvalsListMock as ApprovalListData));
      else setError(String(e));
    } finally {
      setApprovalsLoading(false);
    }
  }

  async function handleApproveRequest(approvalId: string) {
    setApprovalActionLoading(prev => ({ ...prev, [approvalId]: true }));
    try {
      const result = await invoke<CliJsonResponse<ApprovalActionData>>("approve_request", { approvalId });
      setApprovalActionResults(prev => ({ ...prev, [approvalId]: result }));
      if (result.ok) setApprovalsList(prev => {
        if (!prev?.data) return prev;
        return { ...prev, data: { approvals: prev.data.approvals.filter(a => a.approval_id !== approvalId) } };
      });
    } catch (e) {
      setApprovalActionResults(prev => ({
        ...prev, [approvalId]: { ok: false, exit_code: -1, data: null as unknown as ApprovalActionData, error: String(e), stderr_summary: null },
      }));
    } finally {
      setApprovalActionLoading(prev => ({ ...prev, [approvalId]: false }));
    }
  }

  async function handleDenyRequest(approvalId: string) {
    setApprovalActionLoading(prev => ({ ...prev, [approvalId]: true }));
    try {
      const result = await invoke<CliJsonResponse<ApprovalActionData>>("deny_request", { approvalId });
      setApprovalActionResults(prev => ({ ...prev, [approvalId]: result }));
      if (result.ok) setApprovalsList(prev => {
        if (!prev?.data) return prev;
        return { ...prev, data: { approvals: prev.data.approvals.filter(a => a.approval_id !== approvalId) } };
      });
    } catch (e) {
      setApprovalActionResults(prev => ({
        ...prev, [approvalId]: { ok: false, exit_code: -1, data: null as unknown as ApprovalActionData, error: String(e), stderr_summary: null },
      }));
    } finally {
      setApprovalActionLoading(prev => ({ ...prev, [approvalId]: false }));
    }
  }

  async function runSandboxInstall(commandText: string) {
    setSandboxLaunchLoading(true);
    setSandboxLaunchResult(null);
    try {
      const result = await invoke<CliJsonResponse<SandboxLaunchResultData>>("run_sandbox_install", { commandText });
      setSandboxLaunchResult(result);
    } catch (e) {
      if (isMockError(e)) setSandboxLaunchResult(mockResponse(sandboxLaunchResultMock as SandboxLaunchResultData));
      else setSandboxLaunchResult({ ok: false, exit_code: -1, data: null as unknown as SandboxLaunchResultData, error: String(e), stderr_summary: null });
    } finally {
      setSandboxLaunchLoading(false);
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
      if (isMockError(e)) setReportDetail(mockResponse(reportDetailMock as ReportDetailData));
      else setError(String(e));
    } finally {
      setReportDetailLoading(false);
    }
  }

  function handleCloseReportDetail() { setSelectedReportId(null); setReportDetail(null); }

  async function handleAuditEventClick(eventId: string) {
    setSelectedAuditEventId(eventId);
    setAuditEventDetail(null);
    setAuditEventDetailLoading(true);
    try {
      const result = await invoke<CliJsonResponse<AuditEventDetailData>>("show_audit_event", { eventId });
      setAuditEventDetail(result);
    } catch (e) {
      if (isMockError(e)) setAuditEventDetail(mockResponse(auditEventDetailMock as AuditEventDetailData));
      else setError(String(e));
    } finally {
      setAuditEventDetailLoading(false);
    }
  }

  function handleCloseAuditEventDetail() { setSelectedAuditEventId(null); setAuditEventDetail(null); }

  async function handleSandboxResultClick(reportId: string) {
    setSelectedSandboxResultId(reportId);
    setSandboxResultDetail(null);
    setSandboxResultDetailLoading(true);
    setMigrationPreview(null);
    setMigrationResult(null);
    try {
      const result = await invoke<CliJsonResponse<SandboxResultDetailData>>("show_sandbox_result", { reportId });
      setSandboxResultDetail(result);
    } catch (e) {
      if (isMockError(e)) setSandboxResultDetail(mockResponse(sandboxResultDetailMock as SandboxResultDetailData));
      else setError(String(e));
    } finally {
      setSandboxResultDetailLoading(false);
    }
  }

  function handleCloseSandboxResultDetail() { setSelectedSandboxResultId(null); setSandboxResultDetail(null); }


  // ── derived values ───────────────────────────────────────────
  const checks = doctorStatus?.data?.checks ?? {};
  const isDoctorHealthy = Object.keys(checks).length > 0
    ? Object.values(checks).every(c => c.status === "ok")
    : undefined;
  const cliVersion = checks["policy_scout_version"]?.message?.replace("policy-scout ", "v") || undefined;
  const reviewLoading = auditEventsLoading || !auditEventsList;
  const reviewRows = deriveReviewRows(auditEventsList?.data?.events);
  const lastSweepLabel = sweepLoading
    ? "Scanning…"
    : (lastSweepOverride ?? deriveLastSweep(auditEventsList));
  const currentLabel = NAV.find(n => n.id === activeView)?.label ?? "Overview";
  const auditBadge = reviewRows.length;
  const policyBadge = (policyValidate?.data?.error_count ?? 0) + (policyValidate?.data?.warning_count ?? 0);
  const policyIssueCount = policyBadge;
  const approvalsBadge = (approvalsList?.data?.approvals ?? []).filter(a =>
    a.status === "pending" && (!a.expires_at || new Date(a.expires_at).getTime() > Date.now())
  ).length;

  // ── content area for each view ───────────────────────────────
  const viewPad: React.CSSProperties = { position: "absolute", inset: 0, padding: 24 };

  function renderView() {
    switch (activeView) {
      case "overview":
        return (
          <OverviewView
            doctorStatus={doctorStatus}
            dataStatus={dataStatus}
            auditStats={auditStats}
            auditEventsList={auditEventsList}
            quickSweep={quickSweep}
            sweeping={sweepLoading}
            lastSweepLabel={lastSweepLabel}
            reviewLoading={reviewLoading}
            reviewRows={reviewRows}
            policyIssueCount={policyIssueCount}
            onSweep={runQuickSweep}
            onGoToSweeps={() => setActiveView("sweeps")}
            onGoToAudit={() => setActiveView("audit")}
            onGoToPolicy={() => setActiveView("policy")}
            onGoToSystem={() => setActiveView("system")}
          />
        );

      case "check":
        return (
          <div className="scrollv" style={viewPad}>
            <div style={{ display: "flex", borderBottom: "1px solid var(--color-border-muted)", marginBottom: 20 }}>
              {(["check", "simulate"] as const).map(tab => (
                <button
                  key={tab}
                  onClick={() => setCheckTab(tab)}
                  style={{
                    padding: "7px 18px", fontSize: 12.5, fontWeight: checkTab === tab ? 600 : 400,
                    background: "transparent", border: "none",
                    borderBottom: `2px solid ${checkTab === tab ? "var(--color-info)" : "transparent"}`,
                    color: checkTab === tab ? "var(--color-text-primary)" : "var(--color-text-muted)",
                    cursor: "pointer", marginBottom: -1,
                  }}
                >
                  {tab === "check" ? "Check" : "Simulate"}
                </button>
              ))}
            </div>
            {checkTab === "check"
              ? <DecisionCheckCard onGoTo={(view) => setActiveView(view as ViewId)} />
              : <PolicySimulateCard />
            }
          </div>
        );

      case "reports":
        return (
          <div className="scrollv" style={viewPad}>
            {error && <div style={{ marginBottom: 16, color: "var(--color-danger)", fontSize: 13 }}>Error: {error}</div>}
            {selectedReportId ? (
              <ReportDetailCard
                reportDetail={reportDetail}
                loading={reportDetailLoading}
                selectedId={selectedReportId}
                onClose={handleCloseReportDetail}
              />
            ) : (
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
            )}
          </div>
        );

      case "audit":
        return (
          <div className="scrollv" style={viewPad}>
            {selectedAuditEventId ? (
              <AuditEventDetailCard
                auditEventDetail={auditEventDetail}
                loading={auditEventDetailLoading}
                selectedId={selectedAuditEventId}
                onClose={handleCloseAuditEventDetail}
              />
            ) : (
              <>
                <AuditEventsListCard
                  auditEventsList={auditEventsList}
                  onEventClick={handleAuditEventClick}
                  auditEventType={auditEventType}
                  onTypeChange={handleAuditEventTypeChange}
                  loading={auditEventsLoading}
                  limit={auditEventsLimit}
                  onLimitChange={handleAuditLimitChange}
                  offset={auditEventsOffset}
                  totalCount={auditEventsList?.data?.total_count}
                  onPagePrev={auditEventsOffset > 0 ? handleAuditPagePrev : undefined}
                  onPageNext={(auditEventsOffset + auditEventsLimit) < (auditEventsList?.data?.total_count ?? 0) ? handleAuditPageNext : undefined}
                />
                <div style={{ marginTop: 20 }}>
                  <AuditVerifyChainCard />
                </div>
              </>
            )}
          </div>
        );

      case "approvals":
        return (
          <ApprovalsView
            approvalsList={approvalsList}
            loading={approvalsLoading}
            actionResults={approvalActionResults}
            actionLoading={approvalActionLoading}
            onApprove={handleApproveRequest}
            onDeny={handleDenyRequest}
            onRefresh={fetchApprovals}
          />
        );

      case "scan":
        return (
          <div className="scrollv" style={viewPad}>
            <ScanView />
          </div>
        );

      case "sweeps":
        return (
          <div className="scrollv" style={viewPad}>
            <QuickSweepCard quickSweep={quickSweep} loading={sweepLoading} onRunSweep={runQuickSweep} />
            <div style={{ marginTop: 20 }}>
              <ProjectSweepCard projectSweep={projectSweep} loading={projectSweepLoading} onRunSweep={runProjectSweep} />
            </div>
          </div>
        );

      case "sandbox":
        return (
          <div className="scrollv" style={viewPad}>
            {selectedSandboxResultId ? (
              <SandboxResultDetailCard
                sandboxResultDetail={sandboxResultDetail}
                loading={sandboxResultDetailLoading}
                selectedId={selectedSandboxResultId}
                onClose={handleCloseSandboxResultDetail}
                migrationPreview={migrationPreview}
                migrationPreviewLoading={migrationPreviewLoading}
                migrationResult={migrationResult}
                migrationLoading={migrationLoading}
                onMigrateDryRun={runSandboxMigrateDryRun}
                onMigrate={runSandboxMigrate}
              />
            ) : (
              <>
                <SandboxLaunchCard
                  launchResult={sandboxLaunchResult}
                  launchLoading={sandboxLaunchLoading}
                  onLaunch={runSandboxInstall}
                />
                <SandboxResultsListCard
                  sandboxResults={sandboxResultsList}
                  onResultClick={handleSandboxResultClick}
                  loading={sandboxLoading}
                  limit={sandboxLimit}
                  onLimitChange={handleSandboxLimitChange}
                  offset={sandboxOffset}
                  totalCount={sandboxResultsList?.data?.total_count}
                  onPagePrev={sandboxOffset > 0 ? handleSandboxPagePrev : undefined}
                  onPageNext={(sandboxOffset + sandboxLimit) < (sandboxResultsList?.data?.total_count ?? 0) ? handleSandboxPageNext : undefined}
                />
              </>
            )}
          </div>
        );

      case "system":
        return (
          <div className="scrollv" style={viewPad}>
            {loading && <div style={{ marginBottom: 16, fontSize: 13, color: "var(--color-text-muted)" }}>Loading…</div>}
            {error && <div style={{ marginBottom: 16, color: "var(--color-danger)", fontSize: 13 }}>Error: {error}</div>}
            <LiveStatusCard
              lockdownStatus={lockdownStatus}
              watchStatus={watchStatus}
              loading={liveStatusLoading}
              onRefresh={fetchLiveStatus}
            />
            <div style={{ marginTop: 20 }}>
              <DoctorStatusCard doctorStatus={doctorStatus} loading={loading} onRefresh={fetchAllStatus} />
            </div>
            <div style={{ marginTop: 20 }}>
              <DataStatusCard dataStatus={dataStatus} />
            </div>
            <div style={{ marginTop: 20 }}>
              <EvalResultsCard evalResults={evalResults} />
            </div>
            <div style={{ marginTop: 20 }}>
              <CleanupDryRunCard
                cleanupResult={cleanupResult}
                cleanupTarget={cleanupTarget}
                onTargetChange={handleCleanupTargetChange}
                loading={cleanupLoading}
                onApply={runCleanupApply}
                applyResult={cleanupApplyResult}
                applyLoading={cleanupApplyLoading}
              />
            </div>
          </div>
        );

      case "policy":
        return (
          <div className="scrollv" style={viewPad}>
            <PolicyOverviewCard policyOverview={policyOverview} loading={loading} />
            <div style={{ marginTop: 20 }}>
              <PolicyValidateCard
                policyValidate={policyValidate}
                loading={policyValidateLoading}
                onRunValidate={runPolicyValidate}
              />
            </div>
            <div style={{ marginTop: 20 }}>
              <PolicySimulateCard />
            </div>
          </div>
        );

      default:
        return <Placeholder label={currentLabel} />;
    }
  }

  return (
    <div style={{ width: "100%", height: "100%", display: "grid", gridTemplateColumns: "240px minmax(0, 1fr)", overflow: "hidden" }}>
      <Sidebar
        active={activeView} onSelect={setActiveView} cliVersion={cliVersion} healthy={isDoctorHealthy}
        badges={{ audit: auditBadge, policy: policyBadge, approvals: approvalsBadge }}
      />
      <div style={{ position: "relative", display: "flex", flexDirection: "column", minWidth: 0, height: "100%" }}>
        <TopBar
          label={currentLabel}
          onCheck={() => setActiveView("check")}
          onRefresh={fetchAllStatus}
          onHelp={() => setHelpOpen(true)}
          lockdownActive={lockdownStatus?.data?.active ?? false}
          theme={themeId}
          texture={texture}
          setTheme={setThemeId}
          setTexture={setTexture}
        />
        <main style={{ flex: 1, minHeight: 0, backgroundColor: "var(--color-background)", position: "relative", overflow: "hidden" }}>
          {renderView()}
        </main>
        {toast && <Toast title={toast.title} sub={toast.sub} onClose={() => setToast(null)} />}
      </div>
      <HelpDrawer open={helpOpen} onClose={() => setHelpOpen(false)} />
    </div>
  );
}

export default App;
