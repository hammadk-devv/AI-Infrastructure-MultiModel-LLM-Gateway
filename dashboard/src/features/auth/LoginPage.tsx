import { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '@/lib/auth/AuthContext';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Eye, EyeOff, Lock, Sparkles, Shield, Zap } from 'lucide-react';

export function LoginPage() {
    const [apiKey, setApiKey] = useState('');
    const [showKey, setShowKey] = useState(false);
    const [error, setError] = useState('');
    const [isLoading, setIsLoading] = useState(false);

    const { login } = useAuth();
    const navigate = useNavigate();
    const location = useLocation();

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');
        setIsLoading(true);

        try {
            await login(apiKey);

            // Redirect to return URL or home
            const from = (location.state as any)?.from?.pathname || '/';
            navigate(from, { replace: true });
        } catch (err) {
            if (err instanceof Error) {
                const msg = err.message;
                if (msg.includes('AUTH_FAILED')) {
                    setError('Authentication failed. Please check your API key.');
                } else if (msg.includes('NETWORK_ERROR')) {
                    setError('Network error: Could not reach the server. Please check your connection.');
                } else if (msg.includes('SERVER_ERROR')) {
                    setError(`Server error: ${msg.split(': ')[1]}`);
                } else {
                    setError(`Error: ${msg}`);
                }
            } else {
                setError('An unexpected error occurred.');
            }
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="relative flex min-h-screen items-center justify-center overflow-hidden bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50 dark:from-slate-950 dark:via-blue-950 dark:to-indigo-950">
            {/* Animated background elements */}
            <div className="absolute inset-0 overflow-hidden">
                <div className="absolute -top-40 -right-40 h-80 w-80 rounded-full bg-blue-400/20 blur-3xl animate-pulse" />
                <div className="absolute -bottom-40 -left-40 h-80 w-80 rounded-full bg-indigo-400/20 blur-3xl animate-pulse" style={{ animationDelay: '1s' }} />
                <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 h-96 w-96 rounded-full bg-purple-400/10 blur-3xl animate-pulse" style={{ animationDelay: '0.5s' }} />
            </div>

            {/* Main content */}
            <div className="relative z-10 w-full max-w-md px-4">
                <Card className="border-2 shadow-2xl backdrop-blur-sm bg-card/95">
                    <CardHeader className="space-y-4 pb-8">
                        {/* Logo */}
                        <div className="flex items-center justify-center">
                            <div className="relative">
                                <div className="absolute inset-0 rounded-2xl bg-gradient-to-br from-blue-500 to-indigo-600 blur-lg opacity-50" />
                                <div className="relative flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-blue-500 to-indigo-600 shadow-lg">
                                    <Lock className="h-8 w-8 text-white" />
                                </div>
                            </div>
                        </div>

                        {/* Title */}
                        <div className="space-y-2 text-center">
                            <CardTitle className="text-3xl font-bold bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent dark:from-blue-400 dark:to-indigo-400">
                                LLM Gateway
                            </CardTitle>
                            <CardDescription className="text-base">
                                Enterprise AI Infrastructure Platform
                            </CardDescription>
                        </div>

                        {/* Features */}
                        <div className="grid grid-cols-3 gap-4 pt-4">
                            <div className="flex flex-col items-center gap-2 rounded-lg bg-blue-50 dark:bg-blue-950/30 p-3">
                                <Shield className="h-5 w-5 text-blue-600 dark:text-blue-400" />
                                <span className="text-xs font-medium text-muted-foreground">Secure</span>
                            </div>
                            <div className="flex flex-col items-center gap-2 rounded-lg bg-indigo-50 dark:bg-indigo-950/30 p-3">
                                <Zap className="h-5 w-5 text-indigo-600 dark:text-indigo-400" />
                                <span className="text-xs font-medium text-muted-foreground">Fast</span>
                            </div>
                            <div className="flex flex-col items-center gap-2 rounded-lg bg-purple-50 dark:bg-purple-950/30 p-3">
                                <Sparkles className="h-5 w-5 text-purple-600 dark:text-purple-400" />
                                <span className="text-xs font-medium text-muted-foreground">Smart</span>
                            </div>
                        </div>
                    </CardHeader>

                    <CardContent className="space-y-6">
                        <form onSubmit={handleSubmit} className="space-y-4">
                            <div className="space-y-2">
                                <Label htmlFor="apiKey" className="text-sm font-semibold">
                                    API Key
                                </Label>
                                <div className="relative">
                                    <Input
                                        id="apiKey"
                                        type={showKey ? 'text' : 'password'}
                                        placeholder="lkg_..."
                                        value={apiKey}
                                        onChange={(e) => setApiKey(e.target.value)}
                                        className="pr-10 h-11 border-2 focus:border-primary transition-colors"
                                        autoComplete="off"
                                        autoFocus
                                    />
                                    <button
                                        type="button"
                                        onClick={() => setShowKey(!showKey)}
                                        className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
                                        tabIndex={-1}
                                    >
                                        {showKey ? (
                                            <EyeOff className="h-4 w-4" />
                                        ) : (
                                            <Eye className="h-4 w-4" />
                                        )}
                                    </button>
                                </div>
                            </div>

                            {error && (
                                <div className="rounded-lg bg-destructive/10 border border-destructive/20 p-3 text-sm text-destructive">
                                    {error}
                                </div>
                            )}

                            <Button
                                type="submit"
                                className="w-full h-11 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white font-semibold shadow-lg transition-all"
                                disabled={isLoading || !apiKey}
                            >
                                {isLoading ? (
                                    <div className="flex items-center gap-2">
                                        <div className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                                        Authenticating...
                                    </div>
                                ) : (
                                    'Sign in to Dashboard'
                                )}
                            </Button>
                        </form>

                        <div className="space-y-3">
                            <div className="relative">
                                <div className="absolute inset-0 flex items-center">
                                    <div className="w-full border-t" />
                                </div>
                                <div className="relative flex justify-center text-xs uppercase">
                                    <span className="bg-card px-2 text-muted-foreground">Demo Credentials</span>
                                </div>
                            </div>

                            <div className="rounded-lg bg-muted/50 p-4 space-y-2">
                                <p className="text-xs font-semibold text-muted-foreground">Test API Key:</p>
                                <code className="block text-sm font-mono bg-background rounded px-3 py-2 border">
                                    lkg_test_key_12345
                                </code>
                            </div>
                        </div>

                        <p className="text-center text-xs text-muted-foreground">
                            Need an API key?{' '}
                            <span className="font-semibold text-primary cursor-pointer hover:underline">
                                Contact your administrator
                            </span>
                        </p>
                    </CardContent>
                </Card>

                {/* Footer */}
                <p className="mt-8 text-center text-sm text-muted-foreground">
                    Powered by OpenAI, Anthropic, and Google AI
                </p>
            </div>
        </div>
    );
}
