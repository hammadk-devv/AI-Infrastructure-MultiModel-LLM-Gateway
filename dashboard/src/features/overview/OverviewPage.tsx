import { KPICard } from '@/components/dashboard/KPICard';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { useMetricsSummary, useActiveAlerts } from '@/lib/hooks/useMetrics';
import { AlertCircle, AlertTriangle, Info } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';

export function OverviewPage() {
    const { data: metrics, isLoading } = useMetricsSummary(24);
    const { data: alerts } = useActiveAlerts();

    if (isLoading) {
        return <div className="flex items-center justify-center h-96">Loading...</div>;
    }

    if (!metrics) {
        return <div className="flex items-center justify-center h-96">No data available</div>;
    }

    const successRate = (metrics.requests.success / metrics.requests.total) * 100;
    const cacheGrade = metrics.cache.ratio >= 0.9 ? 'A' : metrics.cache.ratio >= 0.8 ? 'B' : metrics.cache.ratio >= 0.7 ? 'C' : metrics.cache.ratio >= 0.5 ? 'D' : 'F';

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold">Overview</h1>
                    <p className="text-muted-foreground">Last 24 hours</p>
                </div>
            </div>

            {/* KPI Cards */}
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                <KPICard
                    title="Total Tokens"
                    value={metrics.tokens.total}
                    formatter="number"
                    trend={{ value: 12, direction: 'up' }}
                />
                <KPICard
                    title="Total Cost"
                    value={metrics.cost.total}
                    formatter="currency"
                    trend={{ value: 8, direction: 'up' }}
                />
                <KPICard
                    title="P95 Latency"
                    value={metrics.latency.p95}
                    formatter="latency"
                    trend={{ value: 5, direction: 'down' }}
                />
                <KPICard
                    title="Success Rate"
                    value={successRate}
                    formatter="percentage"
                    trend={{ value: 0.2, direction: 'up' }}
                />
            </div>

            {/* Charts Row */}
            <div className="grid gap-4 md:grid-cols-2">
                {/* Provider Distribution */}
                <Card>
                    <CardHeader>
                        <CardTitle>Requests by Provider</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="space-y-3">
                            {Object.entries(metrics.cost)
                                .filter(([key]) => key !== 'total')
                                .map(([provider, cost]) => {
                                    const percentage = ((cost / metrics.cost.total) * 100).toFixed(1);
                                    return (
                                        <div key={provider} className="space-y-1">
                                            <div className="flex items-center justify-between text-sm">
                                                <span className="capitalize">{provider}</span>
                                                <span className="font-medium">{percentage}%</span>
                                            </div>
                                            <div className="h-2 w-full overflow-hidden rounded-full bg-muted">
                                                <div
                                                    className="h-full bg-primary transition-all"
                                                    style={{ width: `${percentage}%` }}
                                                />
                                            </div>
                                        </div>
                                    );
                                })}
                        </div>
                        <div className="mt-4 pt-4 border-t text-xs text-muted-foreground flex items-center gap-2">
                            <div className="h-2 w-2 rounded-full bg-emerald-500" />
                            All providers operational
                        </div>
                    </CardContent>
                </Card>

                {/* Cache Performance */}
                <Card>
                    <CardHeader>
                        <CardTitle>Cache Performance</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="space-y-4">
                            <div className="flex items-center justify-between">
                                <span className="text-sm text-muted-foreground">Hit Rate</span>
                                <span className="text-2xl font-bold">
                                    {(metrics.cache.ratio * 100).toFixed(1)}%
                                    <span className="ml-2 text-sm font-medium text-muted-foreground">({cacheGrade})</span>
                                </span>
                            </div>
                            <div className="space-y-2">
                                <div className="flex justify-between text-sm">
                                    <span>Hits</span>
                                    <span className="font-medium">{metrics.cache.hits.toLocaleString()}</span>
                                </div>
                                <div className="flex justify-between text-sm">
                                    <span>Misses</span>
                                    <span className="font-medium">{metrics.cache.misses.toLocaleString()}</span>
                                </div>
                            </div>
                        </div>
                    </CardContent>
                </Card>
            </div>

            {/* Recent Alerts */}
            <Card>
                <CardHeader>
                    <div className="flex items-center justify-between">
                        <CardTitle>Recent Alerts</CardTitle>
                        <a href="/alerts" className="text-sm text-primary hover:underline">
                            View All →
                        </a>
                    </div>
                </CardHeader>
                <CardContent>
                    <div className="space-y-3">
                        {alerts?.slice(0, 3).map((alertEntry) => {
                            const Icon =
                                alertEntry.severity === 'critical'
                                    ? AlertCircle
                                    : alertEntry.severity === 'high'
                                        ? AlertTriangle
                                        : Info;
                            const colorClass =
                                alertEntry.severity === 'critical'
                                    ? 'text-destructive'
                                    : alertEntry.severity === 'high'
                                        ? 'text-warning'
                                        : 'text-muted-foreground';

                            return (
                                <div
                                    key={alertEntry.id}
                                    className="flex items-start gap-3 rounded-lg border p-3"
                                >
                                    <Icon className={`mt-0.5 h-4 w-4 flex-shrink-0 ${colorClass}`} />
                                    <div className="flex-1 space-y-1">
                                        <p className="text-sm font-medium">{alertEntry.title}</p>
                                        <p className="text-xs text-muted-foreground flex items-center justify-between">
                                            <span>
                                                {alertEntry.severity === 'critical' ? 'p1' : alertEntry.severity === 'high' ? 'p2' : 'p3'} • {formatDistanceToNow(new Date(alertEntry.timestamp), { addSuffix: true })}
                                            </span>
                                            <a href="#" className="hover:underline text-primary" onClick={(e) => { e.preventDefault(); alert('Opening runbook for ' + alertEntry.title); }}>
                                                View Runbook →
                                            </a>
                                        </p>
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                </CardContent>
            </Card>
        </div>
    );
}
