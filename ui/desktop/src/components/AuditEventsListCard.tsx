import { CliJsonResponse } from "../types";

interface AuditEventsListCardProps {
  auditEventsList: CliJsonResponse | null;
  onEventClick?: (eventId: string) => void;
}

export function AuditEventsListCard({ auditEventsList, onEventClick }: AuditEventsListCardProps) {
  return (
    <div className="audit-events-card">
      <div className="card-header">
        <h2>Audit Events List</h2>
      </div>

      {auditEventsList && auditEventsList.ok && auditEventsList.data && (
        <div className="audit-events-data">
          {Array.isArray(auditEventsList.data) && auditEventsList.data.length > 0 ? (
            <div className="audit-events-list">
              {auditEventsList.data.map((event: any) => (
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
            <p className="empty-message">No audit events found</p>
          )}
        </div>
      )}
    </div>
  );
}
