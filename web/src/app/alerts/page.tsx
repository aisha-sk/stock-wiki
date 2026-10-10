import type { Metadata } from "next";
import { Alerts } from "@/components/Alerts";

export const metadata: Metadata = { title: "Alerts" };

export default function AlertsPage() {
  return <Alerts />;
}
