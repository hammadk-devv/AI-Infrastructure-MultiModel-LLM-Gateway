import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Search, MessageSquare, User, Clock, Download, ChevronRight, Terminal } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import { useState } from 'react';
import { SidePanel } from '@/components/ui/side-panel';
import { Button } from '@/components/ui/button';
import { useConversations } from '@/lib/hooks/useMetrics';

export function ConversationsPage() {
    const { data: realConversations, isLoading } = useConversations();
    const [selectedConversationId, setSelectedConversationId] = useState<string | null>(null);
    const [searchTerm, setSearchTerm] = useState('');



    if (isLoading) {
        return <div className="flex items-center justify-center h-96">Loading conversations...</div>;
    }

    const conversations = realConversations || [];
    const selectedConversation = conversations.find((c: any) => c.id === selectedConversationId);

    const getStatusColor = (status: string) => {
        return status === 'active' ? 'bg-secondary' : 'bg-muted';
    };

    const getModelColor = (model: string) => {
        if (model.includes('GPT')) return 'bg-blue-500/10 text-blue-700 dark:text-blue-400';
        if (model.includes('Claude')) return 'bg-purple-500/10 text-purple-700 dark:text-purple-400';
        if (model.includes('Gemini')) return 'bg-orange-500/10 text-orange-700 dark:text-orange-400';
        return 'bg-muted';
    };

    const recentSearches = ['rate limiting', 'gpt-4', 'high latency', 'error 500'];

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold">Conversations</h1>
                    <p className="text-muted-foreground">Monitor and analyze chat interactions</p>
                </div>
                <Button variant="ghost" className="text-muted-foreground hover:text-primary" onClick={() => alert('Exporting to CSV...')}>
                    <Download className="mr-2 h-4 w-4" />
                    Export CSV
                </Button>
            </div>

            {/* Summary Cards */}
            <div className="grid gap-4 md:grid-cols-4">
                <Card>
                    <CardHeader className="pb-2">
                        <CardTitle className="text-sm font-medium text-muted-foreground">Total Conversations</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">{conversations.length}</div>
                        <p className="text-xs text-muted-foreground">
                            {conversations.filter((c: any) => c.status === 'active').length} active
                        </p>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader className="pb-2">
                        <CardTitle className="text-sm font-medium text-muted-foreground">Total Messages</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">
                            {conversations.reduce((sum: number, c: any) => sum + c.messages, 0)}
                        </div>
                        <p className="text-xs text-muted-foreground">Across all conversations</p>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader className="pb-2">
                        <CardTitle className="text-sm font-medium text-muted-foreground">Total Tokens</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">
                            {(conversations.reduce((sum: number, c: any) => sum + c.tokens, 0) / 1000).toFixed(1)}K
                        </div>
                        <p className="text-xs text-muted-foreground">Processed tokens</p>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader className="pb-2">
                        <CardTitle className="text-sm font-medium text-muted-foreground">Total Cost</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">
                            ${conversations.reduce((sum: number, c: any) => sum + c.cost, 0).toFixed(2)}
                        </div>
                        <p className="text-xs text-muted-foreground">Conversation costs</p>
                    </CardContent>
                </Card>
            </div>

            {/* Search */}
            <Card>
                <CardContent className="pt-6 space-y-4">
                    <div className="relative">
                        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                        <Input
                            placeholder="Search conversations by user, model, or content..."
                            className="pl-9"
                            value={searchTerm}
                            onChange={(e) => setSearchTerm(e.target.value)}
                        />
                    </div>
                    <div className="flex items-center gap-2">
                        <span className="text-xs text-muted-foreground font-medium">Recent:</span>
                        {recentSearches.map((term) => (
                            <div
                                key={term}
                                className="px-2 py-1 rounded-full bg-muted/50 hover:bg-muted text-xs text-muted-foreground cursor-pointer transition-colors"
                                onClick={() => setSearchTerm(term)}
                            >
                                {term}
                            </div>
                        ))}
                    </div>
                </CardContent>
            </Card>

            {/* Conversations List */}
            <div className="space-y-4">
                {conversations.map((conversation: any) => (
                    <Card
                        key={conversation.id}
                        className="hover:shadow-md transition-all cursor-pointer group"
                        onClick={() => setSelectedConversationId(conversation.id)}
                    >
                        <CardHeader className="group-hover:bg-muted/5 transition-colors">
                            <div className="flex items-start justify-between">
                                <div className="space-y-1">
                                    <div className="flex items-center gap-2">
                                        <MessageSquare className="h-4 w-4 text-muted-foreground" />
                                        <CardTitle className="text-base group-hover:text-primary transition-colors">
                                            Conversation {conversation.id.substring(0, 8)}...
                                        </CardTitle>
                                        <Badge className={getStatusColor(conversation.status)}>
                                            {conversation.status}
                                        </Badge>
                                        <span className="text-xs text-muted-foreground italic hidden group-hover:inline ml-2">
                                            Click to view details
                                        </span>
                                    </div>
                                    <CardDescription className="flex items-center gap-4">
                                        <span className="flex items-center gap-1">
                                            <User className="h-3 w-3" />
                                            {conversation.user}
                                        </span>
                                        <span className="flex items-center gap-1">
                                            <Clock className="h-3 w-3" />
                                            {formatDistanceToNow(new Date(conversation.started_at), { addSuffix: true })}
                                        </span>
                                    </CardDescription>
                                </div>
                                <div className="flex items-center gap-4">
                                    <Badge variant="outline" className={getModelColor(conversation.model)}>
                                        {conversation.model}
                                    </Badge>
                                    <ChevronRight className="h-4 w-4 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
                                </div>
                            </div>
                        </CardHeader>
                        <CardContent>
                            <div className="grid gap-4 md:grid-cols-4">
                                <div className="space-y-1">
                                    <p className="text-xs text-muted-foreground">Messages</p>
                                    <p className="text-lg font-semibold">{conversation.messages}</p>
                                </div>
                                <div className="space-y-1">
                                    <p className="text-xs text-muted-foreground">Tokens</p>
                                    <p className="text-lg font-semibold">{(conversation.tokens / 1000).toFixed(1)}K</p>
                                </div>
                                <div className="space-y-1">
                                    <p className="text-xs text-muted-foreground">Cost</p>
                                    <p className="text-lg font-semibold">${conversation.cost.toFixed(2)}</p>
                                </div>
                                <div className="space-y-1">
                                    <p className="text-xs text-muted-foreground">Avg Cost/Message</p>
                                    <p className="text-lg font-semibold">
                                        ${(conversation.cost / conversation.messages).toFixed(3)}
                                    </p>
                                </div>
                            </div>
                        </CardContent>
                    </Card>
                ))}
            </div>

            {/* Side Panel */}
            <SidePanel
                isOpen={!!selectedConversation}
                onClose={() => setSelectedConversationId(null)}
                title={selectedConversation ? `Conversation ${selectedConversation.id}` : ''}
            >
                {selectedConversation && (
                    <div className="space-y-8">
                        {/* Meta Grid */}
                        <div className="grid grid-cols-2 gap-4 pb-6 border-b">
                            <div>
                                <label className="text-xs text-muted-foreground font-medium">Provider</label>
                                <div className="font-medium">{selectedConversation.model}</div>
                            </div>
                            <div>
                                <label className="text-xs text-muted-foreground font-medium">Started</label>
                                <div className="font-medium">{new Date(selectedConversation.started_at).toLocaleString()}</div>
                            </div>
                            <div>
                                <label className="text-xs text-muted-foreground font-medium">Total Cost</label>
                                <div className="font-medium">${selectedConversation.cost.toFixed(4)}</div>
                            </div>
                            <div>
                                <label className="text-xs text-muted-foreground font-medium">Est. Latency</label>
                                <div className="font-medium">234ms</div>
                            </div>
                        </div>

                        {/* Message History (Mock) */}
                        <div className="space-y-4">
                            <h3 className="font-semibold text-sm">Message History</h3>
                            <div className="space-y-4">
                                <div className="bg-muted/30 p-4 rounded-lg space-y-2">
                                    <div className="flex justify-between items-center text-xs text-muted-foreground">
                                        <span className="font-bold text-primary">USER</span>
                                        <span>12s ago • 45 tokens</span>
                                    </div>
                                    <p className="text-sm">Hello, can you help me optimize my database schema for high throughput?</p>
                                </div>

                                <div className="bg-primary/5 p-4 rounded-lg space-y-2 border border-primary/10">
                                    <div className="flex justify-between items-center text-xs text-muted-foreground">
                                        <span className="font-bold text-primary">ASSISTANT</span>
                                        <span>8s ago • 256 tokens</span>
                                    </div>
                                    <p className="text-sm">Certainly! For high throughput, consider partitioned tables, read replicas, and caching strategies...</p>
                                </div>
                            </div>
                        </div>

                        {/* Raw JSON */}
                        <div className="pt-4 border-t">
                            <div className="flex items-center gap-2 mb-2 text-sm font-medium">
                                <Terminal className="h-4 w-4" />
                                Raw Debug Data
                            </div>
                            <pre className="bg-slate-950 text-slate-50 p-4 rounded-lg text-xs overflow-auto font-mono">
                                {JSON.stringify(selectedConversation, null, 2)}
                            </pre>
                        </div>
                    </div>
                )}
            </SidePanel>
        </div>
    );
}
