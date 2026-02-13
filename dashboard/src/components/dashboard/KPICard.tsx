import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { cn, formatNumber, formatCurrency, formatLatency, formatPercentage } from '@/lib/utils';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';

interface KPICardProps {
    title: string;
    value: string | number;
    trend?: {
        value: number;
        direction: 'up' | 'down' | 'neutral';
    };
    formatter?: 'number' | 'currency' | 'latency' | 'percentage' | 'none';
    grade?: 'A' | 'B' | 'C' | 'D' | 'F';
    className?: string;
}

export function KPICard({ title, value, trend, formatter = 'none', grade, className }: KPICardProps) {
    const formattedValue = (() => {
        if (typeof value === 'string') return value;
        switch (formatter) {
            case 'number':
                return formatNumber(value);
            case 'currency':
                return formatCurrency(value);
            case 'latency':
                return formatLatency(value);
            case 'percentage':
                return formatPercentage(value);
            default:
                return value.toString();
        }
    })();

    const TrendIcon = trend?.direction === 'up' ? TrendingUp : trend?.direction === 'down' ? TrendingDown : Minus;
    const trendColor = trend?.direction === 'up' ? 'text-secondary' : trend?.direction === 'down' ? 'text-destructive' : 'text-muted-foreground';

    return (
        <Card className={cn('', className)}>
            <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                    {title}
                </CardTitle>
            </CardHeader>
            <CardContent>
                <div className="flex items-baseline justify-between">
                    <div className="flex items-baseline gap-2">
                        <div className="text-3xl font-bold">{formattedValue}</div>
                        {grade && (
                            <span className="text-sm font-medium text-muted-foreground/70">
                                ({grade})
                            </span>
                        )}
                    </div>
                    {trend && (
                        <div className={cn('flex items-center text-xs font-medium', trendColor)}>
                            <TrendIcon className="mr-1 h-3 w-3" />
                            {formatPercentage(Math.abs(trend.value))}
                        </div>
                    )}
                </div>
            </CardContent>
        </Card>
    );
}
