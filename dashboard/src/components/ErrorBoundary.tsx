import { Component, ErrorInfo, ReactNode } from 'react';
import { AlertTriangle } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface Props {
    children: ReactNode;
}

interface State {
    hasError: boolean;
    error: Error | null;
    errorInfo: ErrorInfo | null;
}

export class ErrorBoundary extends Component<Props, State> {
    public state: State = {
        hasError: false,
        error: null,
        errorInfo: null,
    };

    public static getDerivedStateFromError(error: Error): State {
        return { hasError: true, error, errorInfo: null };
    }

    public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
        console.error('Uncaught error:', error, errorInfo);
        this.setState({ errorInfo });
    }

    public render() {
        if (this.state.hasError) {
            return (
                <div className="flex h-screen w-full flex-col items-center justify-center bg-background p-4 text-center">
                    <div className="flex h-20 w-20 items-center justify-center rounded-full bg-destructive/10">
                        <AlertTriangle className="h-10 w-10 text-destructive" />
                    </div>
                    <h1 className="mt-6 text-2xl font-bold tracking-tight">Something went wrong</h1>
                    <p className="mt-2 max-w-md text-muted-foreground">
                        An unexpected error occurred in the application.
                    </p>

                    <div className="mt-6 w-full max-w-lg rounded-lg border bg-card p-4 text-left font-mono text-xs text-card-foreground overflow-auto max-h-64">
                        <p className="font-bold text-destructive">{this.state.error?.toString()}</p>
                        {this.state.errorInfo && (
                            <pre className="mt-2 whitespace-pre-wrap opacity-70">
                                {this.state.errorInfo.componentStack}
                            </pre>
                        )}
                    </div>

                    <div className="mt-6 flex gap-4">
                        <Button onClick={() => window.location.href = '/'} variant="outline">
                            Go to Home
                        </Button>
                        <Button onClick={() => window.location.reload()}>
                            Reload Page
                        </Button>
                    </div>
                </div>
            );
        }

        return this.props.children;
    }
}
