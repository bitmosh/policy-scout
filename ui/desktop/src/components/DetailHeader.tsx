interface DetailHeaderProps {
  detailType: "Scout Report" | "Audit Event";
  selectedId: string;
  onClose: () => void;
}

export function DetailHeader({ detailType, selectedId, onClose }: DetailHeaderProps) {
  return (
    <div className="detail-header">
      <div className="detail-breadcrumb">
        <span className="breadcrumb-text">Dashboard</span>
        <span className="breadcrumb-separator">›</span>
        <span className="breadcrumb-text">{detailType}</span>
      </div>
      <div className="detail-title-row">
        <div className="detail-title-group">
          <h2>{detailType} Detail</h2>
          <span className="detail-id">{selectedId}</span>
          <span className="read-only-badge">Read-only</span>
        </div>
        <button onClick={onClose} className="close-button">Close</button>
      </div>
      <p className="detail-subtitle">Selected from loaded list</p>
    </div>
  );
}
