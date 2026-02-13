import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { useModelPerformance } from '@/lib/hooks/useMetrics';
import { Badge } from '@/components/ui/badge';
import { Activity, TrendingUp, DollarSign, Zap, CheckCircle } from 'lucide-react';
import { formatNumber, formatCurrency, formatLatency, formatPercentage } from '@/lib/utils';

export function ModelsPage() {
    const { data: models, isLoading } = useModelPerformance(24);

    const handleAction = (action: string, target: string) => {
        alert(`${action} triggered for ${target}`);
    };

    if (isLoading) {
        return <div className="flex items-center justify-center h-96">Loading models...</div>;
    }

    const modelData = models || [];

    const getStatusColor = (status: string) => {
        return status === 'active' ? 'bg-secondary' : 'bg-muted';
    };

    const getProviderColor = (provider: string) => {
        switch (provider) {
            case 'OpenAI':
                return 'bg-blue-500/10 text-blue-700 dark:text-blue-400';
            case 'Anthropic':
                return 'bg-purple-500/10 text-purple-700 dark:text-purple-400';
            case 'Google':
                return 'bg-orange-500/10 text-orange-700 dark:text-orange-400';
            default:
                return 'bg-muted';
        }
    };

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold">Model Registry</h1>
                    <p className="text-muted-foreground">Manage and monitor LLM models across providers</p>
                </div>
                <Button onClick={() => handleAction('Add Model', 'Registry')}>
                    <Activity className="mr-2 h-4 w-4" />
                    Add Model
                </Button>
            </div>

            {/* Summary Stats */}
            <div className="grid gap-4 md:grid-cols-4">
                <Card>
                    <CardHeader className="pb-2">
                        <CardTitle className="text-sm font-medium text-muted-foreground">Active Models</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">{modelData.length}</div>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader className="pb-2">
                        <CardTitle className="text-sm font-medium text-muted-foreground">Total Requests</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">
                            {formatNumber(modelData.reduce((sum, m) => sum + m.requests, 0))}
                        </div>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader className="pb-2">
                        <CardTitle className="text-sm font-medium text-muted-foreground">Avg Success Rate</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">
                            {formatPercentage(modelData.length > 0 ? modelData.reduce((sum, m) => sum + m.success_rate, 0) / modelData.length : 0)}
                        </div>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader className="pb-2">
                        <CardTitle className="text-sm font-medium text-muted-foreground">Total Cost (24h)</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="flex items-baseline justify-between">
                            <div className="text-2xl font-bold">
                                {formatCurrency(modelData.reduce((sum, m) => sum + m.total_cost, 0))}
                            </div>
                            <span className="text-xs font-medium text-destructive flex items-center">
                                <TrendingUp className="mr-1 h-3 w-3" />
                                8% vs yesterday
                            </span>
                        </div>
                    </CardContent>
                </Card>
            </div>

            {/* Model Cards */}
            <div className="grid gap-4">
                <div className="flex items-center gap-2 mb-2">
                    <input type="checkbox" className="h-4 w-4 rounded border-gray-300 text-primary focus:ring-primary" />
                    <span className="text-sm text-muted-foreground">Select All</span>
                </div>
                {modelData.map((model) => (
                    <Card key={model.model_id} className="hover:shadow-md transition-shadow">
                        <CardHeader>
                            <div className="flex items-start justify-between">
                                <div className="space-y-1">
                                    <div className="flex items-center gap-2">
                                        <CardTitle className="flex items-baseline gap-2">
                                            {model.model_name}
                                            <span className="text-xs font-normal text-muted-foreground">v2024-02</span>
                                        </CardTitle>
                                        <Badge variant="outline" className={getProviderColor(model.provider)}>
                                            {model.provider}
                                        </Badge>
                                        <Badge className={getStatusColor('active')}>
                                            <CheckCircle className="mr-1 h-3 w-3" />
                                            Active
                                        </Badge>
                                        <span className="text-xs text-muted-foreground flex items-center ml-2">
                                            → {model.provider === 'OpenAI' ? 'claude-3-haiku' : 'gpt-3.5-turbo'}
                                        </span>
                                    </div>
                                    <CardDescription>
                                        {['chat', 'streaming'].map((cap) => (
                                            <span key={cap} className="mr-2 text-xs">
                                                • {cap}
                                            </span>
                                        ))}
                                    </CardDescription>
                                </div>
                                <Button variant="outline" size="sm" onClick={() => handleAction('Configure Model', model.model_name)}>
                                    Configure
                                </Button>
                            </div>
                        </CardHeader>
                        <CardContent>
                            <div className="grid gap-4 md:grid-cols-6">
                                <div className="space-y-1">
                                    <div className="flex items-center text-xs text-muted-foreground">
                                        <Zap className="mr-1 h-3 w-3" />
                                        Requests
                                    </div>
                                    <div className="text-lg font-semibold">{formatNumber(model.requests)}</div>
                                </div>

                                <div className="space-y-1">
                                    <div className="flex items-center text-xs text-muted-foreground">
                                        <CheckCircle className="mr-1 h-3 w-3" />
                                        Success Rate
                                    </div>
                                    <div className="text-lg font-semibold text-secondary">
                                        {formatPercentage(model.success_rate)}
                                    </div>
                                </div>

                                <div className="space-y-1">
                                    <div className="flex items-center text-xs text-muted-foreground">
                                        <Activity className="mr-1 h-3 w-3" />
                                        Avg Latency
                                    </div>
                                    <div className="text-lg font-semibold">{formatLatency(model.avg_latency)}</div>
                                </div>

                                <div className="space-y-1">
                                    <div className="flex items-center text-xs text-muted-foreground">
                                        <TrendingUp className="mr-1 h-3 w-3" />
                                        P95 Latency
                                    </div>
                                    <div className="text-lg font-semibold">{formatLatency(model.p95_latency)}</div>
                                </div>

                                <div className="space-y-1">
                                    <div className="flex items-center text-xs text-muted-foreground">
                                        <Activity className="mr-1 h-3 w-3" />
                                        Tokens
                                    </div>
                                    <div className="text-lg font-semibold">{formatNumber(model.total_tokens)}</div>
                                </div>

                                <div className="space-y-1">
                                    <div className="flex items-center text-xs text-muted-foreground">
                                        <DollarSign className="mr-1 h-3 w-3" />
                                        Cost (24h)
                                    </div>
                                    <div className="text-lg font-semibold">{formatCurrency(model.total_cost)}</div>
                                </div>
                            </div>
                        </CardContent>
                    </Card>
                ))}
            </div>
        </div>
    );
}
