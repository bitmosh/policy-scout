import { CliJsonResponse } from "../types";

interface ReportsListCardProps {
  reportsList: CliJsonResponse | null;
}

export function ReportsListCard({ reportsList }: ReportsListCardProps) {
  return (
    <div className="reports-card">
      <div className="card-header">
        <h2>Reports List</h2>
      </div>

      {reportsList && reportsList.ok && reportsList.data && (
        <div className="reports-data">
          {Array.isArray(reportsList.data) && reportsList.data.length > 0 ? (
            <div className="reports-list">
              {reportsList.data.map((report: any) => (
                <div key={report.report_id} className="report-item">
                  <div className="report-info">
                    <span className="report-id">{report.report_id}</span>
                    <span className="report-type">{report.report_type}</span>
                  </div>
                  <div className="report-title">{report.title}</div>
                  {report.created_at && (
                    <div className="report-created">{report.created_at}</div>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <p className="empty-message">No reports found</p>
          )}
        </div>
      )}
    </div>
  );
}
