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
}

export function AuditEventsListCard({ auditEventsList, onEventClick, auditEventType, onTypeChange, loading }: AuditEventsListCardProps) {
  const events: AuditEventListItem[] = auditEventsList?.data?.events ?? [];

  return (
    <div className="audit-events-card">
      <div className="card-header">
        <h2>Audit Events List</h2>
        <div className="list-controls">
          <div className="list-control-group">
            <label className="list-control-label">Type:</label>
            <select
              className="list-control-select"
              value={auditEventType}
              onChange={(e) => onTypeChange(e.target.value as AuditEventTypeFilter)}
              disabled={loading}
            >
              {AUDIT_EVENT_TYPE_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {auditEventsList && auditEventsList.ok && auditEventsList.data && (
        <div className="audit-events-data">
          {events.length > 0 ? (
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
          ) : (
            <p className="empty-message">No audit events found. Run a check, sweep, or report command to generate audit entries.</p>
          )}
        </div>
      )}
    </div>
  );
}
