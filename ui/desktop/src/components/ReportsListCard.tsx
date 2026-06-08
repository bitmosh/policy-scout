import { CliJsonResponse, ReportTypeFilter } from "../types";

interface ReportsListCardProps {
  reportsList: CliJsonResponse | null;
  onReportClick?: (reportId: string) => void;
  limit: number;
  reportType: ReportTypeFilter;
  onLimitChange: (limit: number) => void;
  onTypeChange: (type: ReportTypeFilter) => void;
  loading?: boolean;
}

export function ReportsListCard({
  reportsList,
  onReportClick,
  limit,
  reportType,
  onLimitChange,
  onTypeChange,
  loading = false,
}: ReportsListCardProps) {
  return (
    <div className="reports-card">
      <div className="card-header">
        <h2>Reports List</h2>
        <div className="list-controls">
          <div className="list-control-group">
            <label className="list-control-label">Limit</label>
            <select
              className="list-control-select"
              value={limit}
              onChange={(e) => onLimitChange(Number(e.target.value))}
            >
              <option value={5}>5</option>
              <option value={10}>10</option>
              <option value={25}>25</option>
              <option value={50}>50</option>
            </select>
          </div>
          <div className="list-control-group">
            <label className="list-control-label">Type</label>
            <select
              className="list-control-select"
              value={reportType}
              onChange={(e) => onTypeChange(e.target.value as ReportTypeFilter)}
            >
              <option value="">All</option>
              <option value="command_decision">Command Decision</option>
              <option value="sandbox_result">Sandbox Result</option>
              <option value="project_sweep">Project Sweep</option>
              <option value="system_quick_sweep">Quick Sweep</option>
            </select>
          </div>
        </div>
      </div>

      {loading && <p className="status-message">Loading reports...</p>}

      {!loading && reportsList && reportsList.ok && reportsList.data && (
        <div className="reports-data">
          {Array.isArray(reportsList.data) && reportsList.data.length > 0 ? (
            <div className="reports-list">
              {reportsList.data.map((report: any) => (
                <div
                  key={report.report_id}
                  className="report-item clickable"
                  onClick={() => onReportClick && onReportClick(report.report_id)}
                >
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
