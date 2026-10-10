import type { Metadata } from "next";
import { ModelPerformance } from "@/components/model/ModelPerformance";

export const metadata: Metadata = { title: "Model performance" };

export default function ModelPage() {
  return <ModelPerformance />;
}
