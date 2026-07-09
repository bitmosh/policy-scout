// SPDX-License-Identifier: Apache-2.0
import { CliJsonResponse, AuditEventListData, AuditEventListItem, AuditEventTypeFilter } from "../types";

const AUDIT_EVENT_TYPE_OPTIONS: { value: AuditEventTypeFilter; label: string }[] = [
  { value: "all", label: "All recent events" },
  { value: "SweepCompleted", label: "Sweep Completed" },
  { value: "SweepError", label: "Sweep Error" },
  { value: "SandboxInstallCompleted", label: "Sandbox Install Completed" },
  { value: "SandboxInstallStarted", label: "Sandbox Install Started" },
  { value: "SandboxResultWritten", label: "Sandbox Result Written" },
  { value: "ScoutReportGenerated", label: "Scout Report Generated" },
  { value: "CommandExecutionCompleted", label: "Command Execution Completed" },
  { value: "CommandExecutionBlocked", label: "Command Execution Blocked" },
  { value: "ApprovalRequested", label: "Approval Requested" },
  { value: "ApprovalApprovedOnce", label: "Approval Approved Once" },
  { value: "ApprovalDeniedOnce", label: "Approval Denied Once" },
  { value: "DecisionIssued", label: "Decision Issued" },
];

interface AuditEventsListCardProps {
  auditEventsList: CliJsonResponse<AuditEventListData> | null;
  onEventClick?: (eventId: string) => void;
  auditEventType: AuditEventTypeFilter;
  onTypeChange: (type: AuditEventTypeFilter) => void;
  loading?: boolean;
  limit: number;
  onLimitChange: (limit: number) => void;
  offset?: number;
  totalCount?: number;
  onPagePrev?: () => void;
  onPageNext?: () => void;
}

export function AuditEventsListCard({
  auditEventsList,
  onEventClick,
  auditEventType,
  onTypeChange,
  loading = false,
  limit,
  onLimitChange,
  offset = 0,
  totalCount,
  onPagePrev,
  onPageNext,
}: AuditEventsListCardProps) {
  const events: AuditEventListItem[] = auditEventsList?.data?.events ?? [];
  const showing = events.length;
  const from = offset + 1;
  const to = offset + showing;

  return (
    <div className="audit-events-card">
      <div className="card-header">
        <h2>Audit Events List</h2>
        <div className="list-controls">
          <div className="list-control-group">
            <label className="list-control-label">Limit</label>
            <select
              className="list-control-select"
              value={limit}
              onChange={(e) => onLimitChange(Number(e.target.value))}
              disabled={loading}
            >
              <option value={5}>5</option>
              <option value={10}>10</option>
              <option value={25}>25</option>
              <option value={50}>50</option>
            </select>
          </div>
          <div className="list-control-group">
            <label className="list-control-label">Type:</label>
            <select
              className="list-control-select"
              value={auditEventType}
              onChange={(e) => onTypeChange(e.target.value as AuditEventTypeFilter)}
            >
              {AUDIT_EVENT_TYPE_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {loading && <p className="status-message">Loading audit events...</p>}

      {!loading && auditEventsList?.ok && (
        <div className="audit-events-data">
          {events.length > 0 ? (
            <>
              <div className="audit-events-list">
                {events.map((event) => (
                  <div
                    key={event.event_id}
                    className="audit-event-item"
                    onClick={() => onEventClick?.(event.event_id)}
                  >
                    <div className="event-info">
                      <span className="event-id">{event.event_id}</span>
                      <span className="event-type">{event.event_type}</span>
                    </div>
                    <div className="event-summary">{event.summary}</div>
                    <div className="event-meta">
                      {event.timestamp && (
                        <span className="event-timestamp">{event.timestamp}</span>
                      )}
                      {event.request_id && (
                        <span className="event-request-id">{event.request_id}</span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
              {(onPagePrev || onPageNext) && (
                <div className="pagination-controls">
                  {totalCount !== undefined && (
                    <span className="pagination-label">
                      {from}–{to} of {totalCount}
                    </span>
                  )}
                  <button
                    className="pagination-btn"
                    onClick={onPagePrev}
                    disabled={!onPagePrev || offset === 0}
                  >
                    ← Prev
                  </button>
                  <button
                    className="pagination-btn"
                    onClick={onPageNext}
                    disabled={!onPageNext || (totalCount !== undefined && to >= totalCount)}
                  >
                    Next →
                  </button>
                </div>
              )}
            </>
          ) : (
            <p className="empty-message">No audit events found. Run a check, sweep, or report command to generate audit entries.</p>
          )}
        </div>
      )}
    </div>
  );
}
