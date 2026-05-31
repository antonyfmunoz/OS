import { Layout } from "@/components/layout";
import { PerformanceAnalytics } from "@/components/performance-analytics";

export default function AnalyticsPage() {
  return (
    <Layout title="Analytics Dashboard">
      <div className="space-y-8">
        <h1 className="text-2xl font-bold">Agent Performance & Task Analytics</h1>
        <p className="text-muted-foreground">
          Track agent efficiency, task completion rates, and collaboration metrics.
        </p>
        
        <PerformanceAnalytics />
      </div>
    </Layout>
  );
}