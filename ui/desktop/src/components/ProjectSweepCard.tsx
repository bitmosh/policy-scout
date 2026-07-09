// SPDX-License-Identifier: Apache-2.0
import { CliJsonResponse, SweepData } from "../types";
import { SweepResultPreview } from "./SweepResultPreview";

interface ProjectSweepCardProps {
  projectSweep: CliJsonResponse<SweepData> | null;
  loading: boolean;
  onRunSweep: () => void;
}

export function ProjectSweepCard({ projectSweep, loading, onRunSweep }: ProjectSweepCardProps) {
  const data = projectSweep?.data as SweepData | undefined;

  return (
    <div className="card project-sweep-card">
      <h2>Project Sweep</h2>
      <p className="card-subtitle">Comprehensive project scan (all files, dependencies, configurations)</p>

      {!projectSweep && !loading && (
        <button className="sweep-button" onClick={onRunSweep}>
          Run Project Sweep
        </button>
      )}

      {loading && !projectSweep && (
        <p className="status-message">Running project sweep...</p>
      )}

      {projectSweep && (
        <>
          <SweepResultPreview data={data} maxFindings={10} maxCouldNotVerify={5} showProjectRoot={true} />

          <button className="sweep-button" onClick={onRunSweep}>
            Run Project Sweep Again
          </button>
        </>
      )}
    </div>
  );
}
