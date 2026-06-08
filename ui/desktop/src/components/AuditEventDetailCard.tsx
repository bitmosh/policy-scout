import { CliJsonResponse } from "../types";

interface AuditEventDetailCardProps {
  auditEventDetail: CliJsonResponse | null;
  loading: boolean;
  onClose: () => void;
}

export function AuditEventDetailCard({ auditEventDetail, loading, onClose }: AuditEventDetailCardProps) {
  if (loading) {
    return (
      <div className="audit-event-detail-card">
        <div className="card-header">
          <h2>Audit Event Detail</h2>
          <button onClick={onClose} className="close-button">Close</button>
        </div>
        <p className="status-message">Loading event detail...</p>
      </div>
    );
  }

  if (!auditEventDetail || !auditEventDetail.ok || !auditEventDetail.data) {
    return (
      <div className="audit-event-detail-card">
        <div className="card-header">
          <h2>Audit Event Detail</h2>
          <button onClick={onClose} className="close-button">Close</button>
        </div>
        <p className="error-message">
          {auditEventDetail?.error || "Failed to load event detail"}
        </p>
      </div>
    );
  }

  const event = auditEventDetail.data;

  return (
    <div className="audit-event-detail-card">
      <div className="card-header">
        <h2>Audit Event Detail</h2>
        <button onClick={onClose} className="close-button">Close</button>
      </div>

      <div className="event-detail-content">
        <div className="event-detail-section">
          <h3>Event ID</h3>
          <p className="event-detail-value">{event.event_id || "N/A"}</p>
        </div>

        <div className="event-detail-section">
          <h3>Event Type</h3>
          <p className="event-detail-value">{event.event_type || "N/A"}</p>
        </div>

        <div className="event-detail-section">
          <h3>Timestamp</h3>
          <p className="event-detail-value">{event.timestamp || "N/A"}</p>
        </div>

        {event.request_id && (
          <div className="event-detail-section">
            <h3>Request ID</h3>
            <p className="event-detail-value">{event.request_id}</p>
          </div>
        )}

        {(event.actor_type || event.actor_name) && (
          <div className="event-detail-section">
            <h3>Actor</h3>
            <p className="event-detail-value">
              {event.actor_type && <span>Type: {event.actor_type}</span>}
              {event.actor_name && <span>Name: {event.actor_name}</span>}
              {!event.actor_type && !event.actor_name && <span>N/A</span>}
            </p>
          </div>
        )}

        {event.summary && (
          <div className="event-detail-section">
            <h3>Summary</h3>
            <p className="event-detail-value">{event.summary}</p>
          </div>
        )}

        {event.data_json && (
          <div className="event-detail-section">
            <h3>Data</h3>
            <pre className="event-detail-json">
              <code>{JSON.stringify(JSON.parse(event.data_json), null, 2)}</code>
            </pre>
          </div>
        )}

        <div className="event-detail-section">
          <h3>Additional Fields</h3>
          <div className="event-detail-fields">
            {event.decision_id && <p>Decision ID: {event.decision_id}</p>}
            {event.approval_id && <p>Approval ID: {event.approval_id}</p>}
            {event.sandbox_id && <p>Sandbox ID: {event.sandbox_id}</p>}
            {event.sweep_id && <p>Sweep ID: {event.sweep_id}</p>}
            {event.report_id && <p>Report ID: {event.report_id}</p>}
            {event.execution_id && <p>Execution ID: {event.execution_id}</p>}
            {event.schema_version && <p>Schema Version: {event.schema_version}</p>}
            {event.created_at && <p>Created At: {event.created_at}</p>}
            {!event.decision_id && !event.approval_id && !event.sandbox_id && !event.sweep_id && !event.report_id && !event.execution_id && !event.schema_version && !event.created_at && <p>N/A</p>}
          </div>
        </div>
      </div>
    </div>
  );
}
