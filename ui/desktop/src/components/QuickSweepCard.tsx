import { CliJsonResponse, SweepData } from "../types";
import { SweepResultPreview } from "./SweepResultPreview";

interface QuickSweepCardProps {
  quickSweep: CliJsonResponse<SweepData> | null;
  loading: boolean;
  onRunSweep: () => void;
}

export function QuickSweepCard({ quickSweep, loading, onRunSweep }: QuickSweepCardProps) {
  const data = quickSweep?.data as SweepData | undefined;

  return (
    <div className="card quick-sweep-card">
      <h2>Quick Sweep</h2>
      <p className="card-subtitle">System signal scan (Linux-first, evidence-gathering)</p>

      {!quickSweep && !loading && (
        <button className="sweep-button" onClick={onRunSweep}>
          Run Quick Sweep
        </button>
      )}

      {loading && !quickSweep && (
        <p className="status-message">Running sweep...</p>
      )}

      {quickSweep && (
        <>
          <SweepResultPreview data={data} maxFindings={10} maxCouldNotVerify={5} showProjectRoot={false} />

          <button className="sweep-button" onClick={onRunSweep}>
            Run Quick Sweep Again
          </button>
        </>
      )}
    </div>
  );
}
