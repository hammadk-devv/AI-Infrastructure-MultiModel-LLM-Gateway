import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Users, Key, Shield, FileText, Plus, Search } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { formatDistanceToNow } from 'date-fns';

import { useKeys } from '@/lib/hooks/useMetrics';

export function AdminPage() {
    const { data: realKeys } = useKeys();

    // Mock data for users (placeholder for now)
    const users = [
        { id: '1', name: 'John Doe', email: 'john@example.com', org: 'Engineering', role: 'admin', lastActive: new Date(Date.now() - 1000 * 60 * 15) },
    ];

    const handleAction = (action: string, target: string) => {
        alert(`${action} triggered for ${target}`);
    };

    const apiKeys = realKeys || [];

    // Mock data for audit logs
    const auditLogs = [
        { id: '1', action: 'API Key Created', user: 'john@example.com', target: 'lkg_prod_***', timestamp: new Date(Date.now() - 1000 * 60 * 30), severity: 'info' },
        { id: '2', action: 'Model Configuration Updated', user: 'jane@example.com', target: 'gpt-4o', timestamp: new Date(Date.now() - 1000 * 60 * 60), severity: 'info' },
        { id: '3', action: 'Failed Authentication', user: 'unknown', target: 'lkg_invalid_***', timestamp: new Date(Date.now() - 1000 * 60 * 60 * 2), severity: 'warning' },
        { id: '4', action: 'User Role Changed', user: 'john@example.com', target: 'bob@example.com', timestamp: new Date(Date.now() - 1000 * 60 * 60 * 24), severity: 'critical' },
    ];

    const getSeverityColor = (severity: string) => {
        switch (severity) {
            case 'critical':
                return 'bg-destructive';
            case 'warning':
                return 'bg-warning';
            default:
                return 'bg-primary';
        }
    };

    const getRoleColor = (role: string) => {
        return role === 'admin' ? 'bg-purple-500/10 text-purple-700 dark:text-purple-400' : 'bg-blue-500/10 text-blue-700 dark:text-blue-400';
    };

    return (
        <div className="space-y-6">
            {/* Header */}
            <div>
                <div className="flex items-center justify-between">
                    <div>
                        <h1 className="text-3xl font-bold">Administration</h1>
                        <p className="text-muted-foreground">Manage users, API keys, and audit logs</p>
                    </div>
                    <div className="flex items-center gap-4">
                        <Button variant="ghost" className="text-muted-foreground hover:text-primary">
                            Export Audit Logs
                        </Button>
                        <select className="bg-background border rounded-md px-3 py-2 text-sm font-medium focus:outline-none focus:ring-2 focus:ring-ring">
                            <option>Across 12 organizations</option>
                            <option>Acme Corp (Current)</option>
                            <option>Stark Industries</option>
                            <option>Wayne Enterprises</option>
                        </select>
                    </div>
                </div>
            </div>

            {/* Summary Cards */}
            <div className="grid gap-4 md:grid-cols-4">
                <Card>
                    <CardHeader className="flex flex-row items-center justify-between pb-2">
                        <CardTitle className="text-sm font-medium">Total Users</CardTitle>
                        <Users className="h-4 w-4 text-muted-foreground" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">{users.length}</div>
                        <p className="text-xs text-muted-foreground">Across {new Set(users.map(u => u.org)).size} organizations</p>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader className="flex flex-row items-center justify-between pb-2">
                        <CardTitle className="text-sm font-medium">Active API Keys</CardTitle>
                        <Key className="h-4 w-4 text-muted-foreground" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">{apiKeys.filter(k => k.status === 'active').length}</div>
                        <p className="text-xs text-muted-foreground">{apiKeys.length} total keys</p>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader className="flex flex-row items-center justify-between pb-2">
                        <CardTitle className="text-sm font-medium">Security Events</CardTitle>
                        <Shield className="h-4 w-4 text-muted-foreground" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">{auditLogs.filter(l => l.severity === 'warning' || l.severity === 'critical').length}</div>
                        <p className="text-xs text-muted-foreground">Last 24 hours</p>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader className="flex flex-row items-center justify-between pb-2">
                        <CardTitle className="text-sm font-medium">Audit Logs</CardTitle>
                        <FileText className="h-4 w-4 text-muted-foreground" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">{auditLogs.length}</div>
                        <p className="text-xs text-muted-foreground">Recent activities</p>
                    </CardContent>
                </Card>
            </div>

            {/* Users Section */}
            <Card>
                <CardHeader>
                    <div className="flex items-center justify-between">
                        <div>
                            <CardTitle>Users</CardTitle>
                            <CardDescription>Manage user accounts and permissions</CardDescription>
                        </div>
                        <Button size="sm" onClick={() => handleAction('Add User', 'New User')}>
                            <Plus className="mr-2 h-4 w-4" />
                            Add User
                        </Button>
                    </div>
                </CardHeader>
                <CardContent>
                    <div className="space-y-4">
                        <div className="relative">
                            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                            <Input placeholder="Search users..." className="pl-9" />
                        </div>

                        <div className="space-y-3">
                            {users.map((user) => (
                                <div
                                    key={user.id}
                                    className="flex items-center justify-between rounded-lg border p-4 hover:bg-accent transition-colors"
                                >
                                    <div className="space-y-1">
                                        <div className="flex items-center gap-2">
                                            <p className="font-medium">{user.name}</p>
                                            <Badge variant="outline" className={getRoleColor(user.role)}>
                                                {user.role}
                                            </Badge>
                                        </div>
                                        <p className="text-sm text-muted-foreground">{user.email} • {user.org}</p>
                                        <p className="text-xs text-muted-foreground">
                                            Last active {formatDistanceToNow(user.lastActive, { addSuffix: true })}
                                        </p>
                                    </div>
                                    <Button variant="outline" size="sm" onClick={() => handleAction('Manage User', user.name)}>
                                        Manage
                                    </Button>
                                </div>
                            ))}
                        </div>
                    </div>
                </CardContent>
            </Card>

            {/* Active Sessions Section */}
            <Card>
                <CardHeader>
                    <CardTitle>Active Sessions</CardTitle>
                    <CardDescription>Currently logged in users and devices</CardDescription>
                </CardHeader>
                <CardContent>
                    <div className="space-y-4">
                        {[
                            { id: '1', user: 'John Doe', device: 'Chrome on Mac', ip: '198.51.100.78', time: new Date() },
                            { id: '2', user: 'Jane Smith', device: 'Safari on iPhone', ip: '203.0.113.45', time: new Date(Date.now() - 1000 * 60 * 10) },
                        ].map((session) => (
                            <div key={session.id} className="flex items-center justify-between rounded-lg border p-4 group hover:bg-muted/50 transition-colors">
                                <div className="space-y-0.5">
                                    <p className="font-medium text-sm">{session.user}</p>
                                    <p className="text-xs text-muted-foreground">
                                        {session.device} • {formatDistanceToNow(session.time, { addSuffix: true })} • IP: {session.ip}
                                    </p>
                                </div>
                                <Button variant="ghost" size="sm" className="opacity-0 group-hover:opacity-100 text-destructive hover:text-destructive hover:bg-destructive/10">
                                    Revoke
                                </Button>
                            </div>
                        ))}
                    </div>
                </CardContent>
            </Card>

            {/* API Keys Section */}
            <Card>
                <CardHeader>
                    <div className="flex items-center justify-between">
                        <div>
                            <CardTitle>API Keys</CardTitle>
                            <CardDescription>Manage authentication keys</CardDescription>
                        </div>
                        <Button size="sm" onClick={() => handleAction('Generate Key', 'Organization')}>
                            <Plus className="mr-2 h-4 w-4" />
                            Generate Key
                        </Button>
                    </div>
                </CardHeader>
                <CardContent>
                    <div className="space-y-3">
                        {apiKeys.map((key) => (
                            <div
                                key={key.id}
                                className="flex items-center justify-between rounded-lg border p-4 hover:bg-accent transition-colors"
                            >
                                <div className="space-y-1">
                                    <div className="flex items-center gap-2">
                                        <p className="font-medium">{key.name}</p>
                                        <Badge className={key.status === 'active' ? 'bg-secondary' : 'bg-muted'}>
                                            {key.status}
                                        </Badge>
                                    </div>
                                    <p className="text-sm text-muted-foreground font-mono">{key.preview}</p>
                                    <p className="text-xs text-muted-foreground mt-1">
                                        Read-only • Models: gpt-4 only • Monthly limit: $100
                                    </p>
                                    <p className="text-xs text-muted-foreground">
                                        {key.last_used_at ? `Last used ${formatDistanceToNow(new Date(key.last_used_at), { addSuffix: true })}` : 'Never used'}
                                    </p>
                                </div>
                                <div className="flex gap-2">
                                    <Button variant="outline" size="sm" onClick={() => handleAction('Rotate Key', key.name)}>
                                        Rotate
                                    </Button>
                                    <Button variant="destructive" size="sm" onClick={() => handleAction('Revoke Key', key.name)}>
                                        Revoke
                                    </Button>
                                </div>
                            </div>
                        ))}
                    </div>
                </CardContent>
            </Card>

            {/* Audit Logs Section */}
            <Card>
                <CardHeader>
                    <CardTitle>Audit Logs</CardTitle>
                    <CardDescription>Security and compliance activity trail</CardDescription>
                </CardHeader>
                <CardContent>
                    <div className="space-y-3">
                        {auditLogs.map((log) => (
                            <div
                                key={log.id}
                                className="flex items-start gap-3 rounded-lg border p-4 hover:bg-accent transition-colors"
                            >
                                <div className={`mt-0.5 h-2 w-2 rounded-full ${getSeverityColor(log.severity)}`} />
                                <div className="flex-1 space-y-1">
                                    <div className="flex items-center justify-between">
                                        <p className="font-medium">{log.action}</p>
                                        <p className="text-xs text-muted-foreground">
                                            {formatDistanceToNow(log.timestamp, { addSuffix: true })}
                                        </p>
                                    </div>
                                    <p className="text-sm text-muted-foreground">
                                        {log.user} → {log.target} <span className="ml-2 text-xs opacity-70">• IP: 203.0.113.45 (Singapore)</span>
                                    </p>
                                </div>
                            </div>
                        ))}
                    </div>
                </CardContent>
            </Card>
        </div>
    );
}
