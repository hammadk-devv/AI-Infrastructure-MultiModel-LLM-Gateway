import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { useMetricsSummary } from '@/lib/hooks/useMetrics';
import { BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import { DollarSign, TrendingUp, Clock, Zap } from 'lucide-react';
import { formatCurrency, formatNumber } from '@/lib/utils';

export function AnalyticsPage() {
    const { data: metrics, isLoading } = useMetricsSummary(168); // 7 days

    const handleAction = (action: string, target: string) => {
        alert(`${action} triggered for ${target}`);
    };

    if (isLoading) {
        return <div className="flex items-center justify-center h-96">Loading analytics...</div>;
    }

    const data = metrics || {
        tokens: { total: 0 },
        cost: { total: 0 },
        requests: { total: 0 },
        latency: { p50: 0 }
    };

    // Mock data for cost breakdown by provider
    const costByProvider = [
        { name: 'OpenAI', cost: 275.30, percentage: 65 },
        { name: 'Anthropic', cost: 105.20, percentage: 25 },
        { name: 'Gemini', cost: 43.00, percentage: 10 },
    ];

    // Mock data for cost over time (7 days)
    const costOverTime = [
        { date: 'Feb 5', openai: 35, anthropic: 12, gemini: 5 },
        { date: 'Feb 6', openai: 38, anthropic: 15, gemini: 6 },
        { date: 'Feb 7', openai: 42, anthropic: 14, gemini: 7 },
        { date: 'Feb 8', openai: 40, anthropic: 16, gemini: 6 },
        { date: 'Feb 9', openai: 45, anthropic: 18, gemini: 8 },
        { date: 'Feb 10', openai: 38, anthropic: 15, gemini: 5 },
        { date: 'Feb 11', openai: 37, anthropic: 15, gemini: 6 },
    ];

    // Mock data for latency by model
    const latencyByModel = [
        { model: 'GPT-4o', p50: 187, p95: 542, p99: 1205 },
        { model: 'Claude 3.5', p50: 210, p95: 680, p99: 1450 },
        { model: 'Gemini 1.5', p50: 165, p95: 490, p99: 980 },
    ];

    // Mock data for request volume
    const requestVolume = [
        { hour: '00:00', requests: 120 },
        { hour: '04:00', requests: 80 },
        { hour: '08:00', requests: 350 },
        { hour: '12:00', requests: 520 },
        { hour: '16:00', requests: 480 },
        { hour: '20:00', requests: 290 },
    ];

    return (
        <div className="space-y-6">
            {/* Header */}
            <div>
                <div className="flex items-center justify-between">
                    <div>
                        <h1 className="text-3xl font-bold">Analytics</h1>
                        <p className="text-muted-foreground">Deep-dive into costs, performance, and usage patterns</p>
                    </div>
                    <div className="flex items-center gap-2">
                        <span className="text-sm text-muted-foreground">Time Range:</span>
                        <select className="text-sm font-medium bg-transparent border-none outline-none cursor-pointer hover:text-primary transition-colors">
                            <option>Last 7 days</option>
                            <option>Last 24 hours</option>
                            <option>Last 30 days</option>
                            <option>Last 90 days</option>
                            <option>Custom range...</option>
                        </select>
                    </div>
                </div>
            </div>

            {/* Summary Cards */}
            <div className="grid gap-4 md:grid-cols-4">
                <Card className="cursor-pointer hover:bg-accent transition-colors" onClick={() => handleAction('View Spend Details', '7d')}>
                    <CardHeader className="flex flex-row items-center justify-between pb-2">
                        <CardTitle className="text-sm font-medium">Total Spend (7d)</CardTitle>
                        <DollarSign className="h-4 w-4 text-muted-foreground" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">{formatCurrency(data.cost.total)}</div>
                        <p className="text-xs text-muted-foreground">
                            Live data from backend
                        </p>
                    </CardContent>
                </Card>

                <Card className="cursor-pointer hover:bg-accent transition-colors" onClick={() => handleAction('View Efficiency', 'requests')}>
                    <CardHeader className="flex flex-row items-center justify-between pb-2">
                        <CardTitle className="text-sm font-medium">Avg Cost/Request</CardTitle>
                        <TrendingUp className="h-4 w-4 text-muted-foreground" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">{formatCurrency(data.requests.total > 0 ? data.cost.total / data.requests.total : 0)}</div>
                        <p className="text-xs text-muted-foreground">
                            Calculated per request
                        </p>
                    </CardContent>
                </Card>

                <Card className="cursor-pointer hover:bg-accent transition-colors" onClick={() => handleAction('View Latency Trends', 'ms')}>
                    <CardHeader className="flex flex-row items-center justify-between pb-2">
                        <div className="space-y-0.5">
                            <CardTitle className="text-sm font-medium">Avg Latency</CardTitle>
                            <p className="text-xs text-muted-foreground">SLO: 95% &lt;500ms • <span className="text-emerald-500 font-medium">98.7%</span></p>
                        </div>
                        <Clock className="h-4 w-4 text-muted-foreground" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">{data.latency.p50}ms</div>
                        <p className="text-xs text-muted-foreground">
                            Median response time
                        </p>
                    </CardContent>
                </Card>

                <Card className="cursor-pointer hover:bg-accent transition-colors" onClick={() => handleAction('View Request Volume', 'all')}>
                    <CardHeader className="flex flex-row items-center justify-between pb-2">
                        <CardTitle className="text-sm font-medium">Total Requests</CardTitle>
                        <Zap className="h-4 w-4 text-muted-foreground" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">{formatNumber(data.requests.total)}</div>
                        <p className="text-xs text-muted-foreground">
                            Successful interactions
                        </p>
                    </CardContent>
                </Card>
            </div>

            {/* Cost Analysis */}
            <div className="grid gap-4 md:grid-cols-2">
                <Card>
                    <CardHeader>
                        <CardTitle>Cost by Provider</CardTitle>
                        <CardDescription>7-day breakdown by LLM provider</CardDescription>
                    </CardHeader>
                    <CardContent>
                        <ResponsiveContainer width="100%" height={300}>
                            <BarChart data={costByProvider}>
                                <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                                <XAxis dataKey="name" className="text-xs" />
                                <YAxis className="text-xs" />
                                <Tooltip
                                    contentStyle={{ backgroundColor: 'hsl(var(--card))', border: '1px solid hsl(var(--border))' }}
                                    formatter={(value) => formatCurrency(Number(value))}
                                />
                                <Bar dataKey="cost" fill="hsl(var(--primary))" radius={[4, 4, 0, 0]} />
                            </BarChart>
                        </ResponsiveContainer>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader>
                        <div className="flex items-center justify-between">
                            <div>
                                <CardTitle>Cost Trend</CardTitle>
                                <CardDescription>Daily spend by provider (7 days)</CardDescription>
                            </div>
                            <div className="text-right">
                                <p className="text-sm font-medium text-muted-foreground">Projected month-end</p>
                                <p className="text-lg font-bold">
                                    {formatCurrency(data.cost.total * 4.2)} {/* logical projection logic simulation */}
                                    <span className="ml-1 text-xs font-normal text-muted-foreground">(↑12%)</span>
                                </p>
                            </div>
                        </div>
                    </CardHeader>
                    <CardContent>
                        <ResponsiveContainer width="100%" height={300}>
                            <LineChart data={costOverTime}>
                                <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                                <XAxis dataKey="date" className="text-xs" />
                                <YAxis className="text-xs" />
                                <Tooltip
                                    contentStyle={{ backgroundColor: 'hsl(var(--card))', border: '1px solid hsl(var(--border))' }}
                                    formatter={(value) => `$${value}`}
                                />
                                <Legend />
                                <Line type="monotone" dataKey="openai" stroke="hsl(221 83% 53%)" strokeWidth={2} name="OpenAI" />
                                <Line type="monotone" dataKey="anthropic" stroke="hsl(142 71% 45%)" strokeWidth={2} name="Anthropic" />
                                <Line type="monotone" dataKey="gemini" stroke="hsl(38 92% 50%)" strokeWidth={2} name="Gemini" />
                            </LineChart>
                        </ResponsiveContainer>
                    </CardContent>
                </Card>
            </div>

            {/* Performance Analysis */}
            <div className="grid gap-4 md:grid-cols-2">
                <Card>
                    <CardHeader>
                        <CardTitle>Latency by Model</CardTitle>
                        <CardDescription>P50, P95, and P99 latency (ms)</CardDescription>
                    </CardHeader>
                    <CardContent>
                        <ResponsiveContainer width="100%" height={300}>
                            <BarChart data={latencyByModel}>
                                <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                                <XAxis dataKey="model" className="text-xs" />
                                <YAxis className="text-xs" />
                                <Tooltip
                                    contentStyle={{ backgroundColor: 'hsl(var(--card))', border: '1px solid hsl(var(--border))' }}
                                    formatter={(value) => `${value}ms`}
                                />
                                <Legend />
                                <Bar dataKey="p50" fill="hsl(142 71% 45%)" radius={[4, 4, 0, 0]} name="P50" />
                                <Bar dataKey="p95" fill="hsl(38 92% 50%)" radius={[4, 4, 0, 0]} name="P95" />
                                <Bar dataKey="p99" fill="hsl(0 84% 60%)" radius={[4, 4, 0, 0]} name="P99" />
                            </BarChart>
                        </ResponsiveContainer>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader>
                        <CardTitle>Request Volume</CardTitle>
                        <CardDescription>Requests per hour (last 24h)</CardDescription>
                    </CardHeader>
                    <CardContent>
                        <ResponsiveContainer width="100%" height={300}>
                            <LineChart data={requestVolume}>
                                <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                                <XAxis dataKey="hour" className="text-xs" />
                                <YAxis className="text-xs" />
                                <Tooltip
                                    contentStyle={{ backgroundColor: 'hsl(var(--card))', border: '1px solid hsl(var(--border))' }}
                                />
                                <Line
                                    type="monotone"
                                    dataKey="requests"
                                    stroke="hsl(var(--primary))"
                                    strokeWidth={2}
                                    fill="hsl(var(--primary))"
                                    fillOpacity={0.1}
                                />
                            </LineChart>
                        </ResponsiveContainer>
                    </CardContent>
                </Card>
            </div>
        </div>
    );
}
