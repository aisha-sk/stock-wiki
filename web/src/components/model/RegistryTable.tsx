import { formatAlgorithm, formatDate, formatRate, formatThreshold, formatVersion } from "@/lib/format";
import type { Gate, ModelVersion, VersionStatus } from "@/lib/types";

const STATUS_NAME: Record<VersionStatus, string> = {
  production: "Production",
  archived: "Archived",
  rejected: "Rejected, below gate",
};

export function RegistryTable({ versions, gate }: { versions: ModelVersion[]; gate: Gate }) {
  const rejected = versions.filter((v) => v.status === "rejected").length;
  return (
    <section className="flex min-w-0 flex-[1_1_420px] flex-col gap-3 rounded-xl border border-line bg-card p-6">
      <h2 className="text-[17px] font-semibold">Model registry (MLflow)</h2>
      {versions.length === 0 ? (
        <p className="text-[15px] text-muted">No versions have been trained yet.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[340px] border-collapse text-sm">
            <thead>
              <tr className="text-left text-muted">
                <th className="py-2 pr-2 font-medium">Version</th>
                <th className="p-2 font-medium">Trained</th>
                <th className="p-2 font-medium">Algorithm</th>
                <th className="p-2 font-medium">Task</th>
                <th className="p-2 text-right font-medium">Accuracy</th>
                <th className="py-2 pl-2 font-medium">Status</th>
              </tr>
            </thead>
            <tbody>
              {versions.map((version) => (
                <tr key={version.version} className="border-t border-line">
                  <td className="py-3 pr-2 font-mono">{formatVersion(version.version)}</td>
                  <td className="px-2 py-3">{formatDate(version.trained_at.slice(0, 10))}</td>
                  <td className="px-2 py-3">{formatAlgorithm(version.algorithm)}</td>
                  <td className="px-2 py-3">{version.task === "move" ? "Large vs quiet" : "Direction"}</td>
                  <td className="px-2 py-3 text-right font-mono">{formatRate(version.directional_accuracy)}</td>
                  <td className="py-3 pl-2 font-medium">{STATUS_NAME[version.status]}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <p className="text-[13px] text-muted">
        Accuracy is the share of correct calls for each version&apos;s task. A version only serves forecasts if
        that accuracy reaches the {formatThreshold(gate.threshold)} gate and beats always guessing quiet.{" "}
        {rejected > 0 && `${rejected} of ${versions.length} versions were rejected and never served.`}
      </p>
    </section>
  );
}
