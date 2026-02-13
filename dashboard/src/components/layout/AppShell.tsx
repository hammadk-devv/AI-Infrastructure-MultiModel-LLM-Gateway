import { Link, useLocation } from 'react-router-dom';
import { cn } from '@/lib/utils';
import { UserNav } from './UserNav';
import {
    LayoutDashboard,
    BarChart3,
    Layers,
    MessageSquare,
    Settings,
    Menu,
    X,
} from 'lucide-react';
import { useState } from 'react';
import { Button } from '@/components/ui/button';

const navigation = [
    { name: 'Overview', href: '/', icon: LayoutDashboard },
    { name: 'Analytics', href: '/analytics', icon: BarChart3 },
    { name: 'Models', href: '/models', icon: Layers },
    { name: 'Conversations', href: '/conversations', icon: MessageSquare },
    { name: 'Admin', href: '/admin', icon: Settings },
];

export function AppShell({ children }: { children: React.ReactNode }) {
    const location = useLocation();
    const [sidebarOpen, setSidebarOpen] = useState(true);

    return (
        <div className="flex h-screen bg-background">
            {/* Sidebar */}
            <aside
                className={cn(
                    'flex flex-col border-r bg-card transition-all duration-300',
                    sidebarOpen ? 'w-64' : 'w-16'
                )}
            >
                {/* Logo & Toggle */}
                <div className="flex h-16 items-center justify-between border-b px-4">
                    {sidebarOpen && (
                        <h1 className="text-xl font-bold">LLM Gateway</h1>
                    )}
                    <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => setSidebarOpen(!sidebarOpen)}
                    >
                        {sidebarOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
                    </Button>
                </div>

                {/* Navigation */}
                <nav className="flex-1 space-y-1 p-2">
                    {navigation.map((item) => {
                        const isActive = location.pathname === item.href;
                        return (
                            <Link
                                key={item.name}
                                to={item.href}
                                className={cn(
                                    'flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors',
                                    isActive
                                        ? 'bg-primary text-primary-foreground'
                                        : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
                                )}
                            >
                                <item.icon className="h-5 w-5 flex-shrink-0" />
                                {sidebarOpen && <span>{item.name}</span>}
                            </Link>
                        );
                    })}
                </nav>
            </aside>

            {/* Main Content */}
            <div className="flex flex-1 flex-col overflow-hidden">
                {/* Header */}
                <header className="flex h-16 items-center justify-between border-b bg-card px-6">
                    <h2 className="text-2xl font-semibold">
                        {navigation.find((item) => item.href === location.pathname)?.name || 'Dashboard'}
                    </h2>
                    <UserNav />
                </header>

                {/* Content */}
                <main className="flex-1 overflow-auto">
                    <div className="container mx-auto p-6">
                        {children}
                    </div>
                </main>
            </div>
        </div>
    );
}
