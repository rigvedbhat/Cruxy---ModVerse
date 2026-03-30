import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { ShieldCheck, Bot, Swords, Users, Settings, HelpCircle, Send, MessageSquare, BookOpen, ChevronDown, ChevronUp, Loader2, Home, LayoutDashboard, Menu, X, CheckCircle, AlertTriangle, Info, LogOut, RefreshCw } from 'lucide-react';

const API_URL = import.meta.env.VITE_API_URL || '';
const API_KEY = import.meta.env.VITE_API_SECRET_KEY || '';
const DISCORD_INVITE_URL =
    'https://discord.com/oauth2/authorize?client_id=1361039241760604261&permissions=268527702&scope=bot%20applications.commands';

async function apiFetch(path, options = {}) {
    const url = API_URL ? `${API_URL}${path}` : path;
    const headers = {
        'Content-Type': 'application/json',
        'X-API-Key': API_KEY,
        ...(options.headers || {}),
    };
    return fetch(url, { ...options, headers });
}

function formatPermissionLabel(permissions) {
    if (!permissions || permissions === 'public') return 'Public';
    if (permissions === 'read-only') return 'Read-only';
    if (typeof permissions === 'object' && permissions.type === 'restricted') {
        const allowedRoles = Array.isArray(permissions.allow) ? permissions.allow : [];
        return allowedRoles.length > 0 ? `Restricted: ${allowedRoles.join(', ')}` : 'Restricted';
    }
    return 'Custom';
}

// --- Helper Components ---

const ToastNotification = ({ notification, onClose }) => {
    if (!notification) return null;
    const { message, type } = notification;
    const toastStyles = {
        success: { bg: 'bg-green-600/90', border: 'border-green-500', icon: <CheckCircle className="w-6 h-6 text-white" /> },
        error: { bg: 'bg-red-600/90', border: 'border-red-500', icon: <AlertTriangle className="w-6 h-6 text-white" /> },
        info: { bg: 'bg-blue-600/90', border: 'border-blue-500', icon: <Info className="w-6 h-6 text-white" /> }
    };
    const currentStyle = toastStyles[type] || toastStyles.info;

    useEffect(() => {
        const timer = setTimeout(() => onClose(), 4000);
        return () => clearTimeout(timer);
    }, [onClose]);

    return (
        <div className={`fixed top-5 right-5 z-50 p-4 rounded-xl shadow-2xl flex items-center gap-3 text-white border ${currentStyle.bg} ${currentStyle.border} animate-fade-in-down`}>
            {currentStyle.icon}
            <p className="font-semibold">{message}</p>
            <button onClick={onClose} className="ml-4 p-1 rounded-full hover:bg-white/20 transition-colors"><X className="w-4 h-4" /></button>
        </div>
    );
};

const AccordionItem = ({ title, content, isOpen, onClick }) => (
    <div className="border border-cyan-400/20 bg-gray-900/50 rounded-xl overflow-hidden mb-4 transition-all duration-300">
        <button onClick={onClick} className="w-full flex justify-between items-center p-5 text-left font-semibold text-white hover:bg-cyan-400/10 transition-colors">
            <span>{title}</span>
            {isOpen ? <ChevronUp className="w-5 h-5 text-cyan-400" /> : <ChevronDown className="w-5 h-5 text-cyan-400" />}
        </button>
        <div className={`transition-all duration-500 ease-in-out overflow-hidden ${isOpen ? 'max-h-96' : 'max-h-0'}`}>
            <div className="p-5 pt-0 text-gray-300">{content}</div>
        </div>
    </div>
);

// --- Page Components ---

const HomePage = () => {
    const features = [
        { icon: <Bot size={32} />, title: "AI-Powered Server Building", description: "Generate full server structures with Seromod's AI planning and build workflows." },
        { icon: <Users size={32} />, title: "Community Engagement", description: "Keep your community active with conversational AI support and smart server automation." },
        { icon: <ShieldCheck size={32} />, title: "Intelligent Moderation", description: "Maintain a safe and positive environment with Seromod's moderation and AutoMod tools." },
        { icon: <Swords size={32} />, title: "Fun Commands", description: "Keep your server members entertained with a variety of fun and interactive commands.", status: "Under development" },
    ];

    return (
        <div className="animate-fade-in text-center px-4 md:px-8">
            <div className="max-w-4xl mx-auto mt-16 mb-24 bg-gray-900/50 border border-cyan-400/30 p-8 md:p-12 rounded-2xl shadow-2xl shadow-cyan-500/10 backdrop-blur-sm">
                <h1 className="text-4xl md:text-6xl font-extrabold bg-clip-text text-transparent bg-gradient-to-r from-cyan-300 to-blue-400 mb-6">Seromod: The AI-Powered Discord Bot</h1>
                <p className="text-lg text-gray-300 max-w-2xl mx-auto mb-8">Enhance your Discord server with Seromod, an AI-driven assistant designed to elevate moderation, setup, and community interaction.</p>
                <a href={DISCORD_INVITE_URL} target="_blank" rel="noopener noreferrer" className="inline-block bg-cyan-400 text-gray-900 font-bold py-3 px-8 rounded-xl hover:bg-cyan-300 transition-all duration-300 shadow-lg hover:shadow-cyan-400/40 transform hover:scale-105">Add to Discord</a>
            </div>
            <div className="max-w-6xl mx-auto">
                <h2 className="text-3xl font-bold text-white mb-10">Key Features</h2>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-8">
                    {features.map((feature, index) => (
                        <div key={index} className="bg-gray-800/60 p-6 rounded-2xl border border-cyan-400/20 shadow-lg hover:border-cyan-400/50 hover:shadow-cyan-500/20 transition-all duration-300 text-left transform hover:-translate-y-2">
                            <div className="text-cyan-400 mb-4">{feature.icon}</div>
                            <h3 className="text-xl font-bold text-white mb-2">{feature.title}</h3>
                            <p className="text-gray-400">{feature.description}</p>
                            {feature.status && <p className="text-sm text-yellow-400 mt-4 font-semibold">{feature.status}</p>}
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
};

const GuidePage = () => {
    const [openAccordion, setOpenAccordion] = useState(0);
    const WIKI_URL = 'https://github.com/rigvedbhat';
    const faqs = [
        { q: "How do I add Seromod to my server?", a: "To add Seromod to your server, click the 'Add to Discord' button and complete the Discord authorization flow." },
        { q: "What commands does Seromod have?", a: "Seromod includes AI-powered server building with /buildserver, natural-language server edits with /serveredit, moderation tools, and more." },
        { q: "How do I set up moderation features?", a: "You can configure all moderation settings from the AutoMod section in your dashboard." },
        { q: "Can I customize Seromod's AI responses?", a: "You can guide its actions through detailed prompts in commands like /buildserver and /serveredit." },
    ];

    return (
        <div className="max-w-4xl mx-auto p-4 md:p-8 animate-fade-in">
            <h1 className="text-4xl font-extrabold text-white text-center mb-12">Guide & Help</h1>
            <div className="text-center mb-16">
                <a href={WIKI_URL} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-2 bg-cyan-400 text-gray-900 font-bold py-3 px-8 rounded-xl hover:bg-cyan-300 transition-all duration-300 shadow-lg hover:shadow-cyan-400/40 transform hover:scale-105">
                    <BookOpen />View Project Resources
                </a>
            </div>
            <h2 className="text-3xl font-bold text-white text-center mb-8">Frequently Asked Questions</h2>
            <div>
                {faqs.map((faq, index) => (
                    <AccordionItem key={index} title={faq.q} content={faq.a} isOpen={openAccordion === index} onClick={() => setOpenAccordion(openAccordion === index ? null : index)} />
                ))}
            </div>
        </div>
    );
};

// --- Dashboard Components ---

const GuildSelector = ({ guilds, onSelectGuild, isLoading }) => (
    <div className="max-w-5xl mx-auto text-center animate-fade-in-down">
        <h1 className="text-4xl font-bold text-white mb-4">Select a Server</h1>
        <p className="text-gray-400 mb-12">Choose a server to manage its settings.</p>
        {isLoading ? (
            <div className="flex justify-center items-center h-64"><Loader2 className="w-16 h-16 animate-spin text-cyan-400" /></div>
        ) : guilds.length === 0 ? (
            <div className="bg-yellow-900/50 border border-yellow-600 p-6 rounded-xl text-yellow-200">
                <h3 className="font-bold text-lg">No Servers Found</h3>
                <p>Seromod does not seem to be in any servers, or the backend is not connected. Invite the bot to a server to get started.</p>
            </div>
        ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
                {guilds.map((guild) => (
                    <button key={guild.id} onClick={() => onSelectGuild(guild)} className="bg-gray-800/60 p-6 rounded-2xl border border-cyan-400/20 shadow-lg hover:border-cyan-400/50 hover:shadow-cyan-500/20 transition-all duration-300 transform hover:-translate-y-2 focus:outline-none focus:ring-2 focus:ring-cyan-400">
                        <img src={guild.icon || `https://placehold.co/128x128/1F2937/7DD3FC?text=${guild.name.charAt(0)}`} alt={`${guild.name} icon`} className="w-32 h-32 rounded-full mx-auto mb-4 object-cover" />
                        <span className="font-semibold text-lg">{guild.name}</span>
                    </button>
                ))}
            </div>
        )}
    </div>
);

const OverviewView = ({ selectedGuild, showToast }) => {
    const [stats, setStats] = useState({
        member_count: 0,
        premium_tier: 0,
        premium_subscription_count: 0,
        channels: 0,
        roles: 0,
    });
    const [isLoading, setIsLoading] = useState(true);

    const fetchStats = useCallback(async () => {
        setIsLoading(true);
        try {
            const response = await apiFetch(`/api/guilds/${selectedGuild.id}/info`);
            const data = await response.json();
            if (!response.ok) throw new Error(data.error || 'Failed to fetch server info.');
            setStats(data);
        } catch (error) {
            showToast(error.message, 'error');
        } finally {
            setIsLoading(false);
        }
    }, [selectedGuild, showToast]);

    useEffect(() => {
        fetchStats();
        const interval = setInterval(fetchStats, 60000); // Auto-refresh every 60 seconds
        return () => clearInterval(interval);
    }, [fetchStats]);

    const statCards = [
        { title: 'Total Members', value: stats.member_count },
        { title: 'Boost Level', value: `${stats.premium_tier} (${stats.premium_subscription_count} boosts)` },
        { title: 'Channels', value: stats.channels },
        { title: 'Roles', value: stats.roles },
    ];

    return (
        <div className="animate-fade-in">
            <div className="flex justify-between items-center mb-8">
                <h2 className="text-3xl font-bold text-white">Overview</h2>
                <button onClick={fetchStats} disabled={isLoading} className="flex items-center gap-2 bg-gray-700/80 text-gray-300 font-semibold py-2 px-4 rounded-lg hover:bg-gray-600 transition-colors disabled:opacity-50 disabled:cursor-wait">
                    <RefreshCw className={`w-5 h-5 ${isLoading ? 'animate-spin' : ''}`} /> Sync
                </button>
            </div>
            {isLoading && !stats.member_count ? (
                <div className="flex justify-center items-center h-24"><Loader2 className="w-8 h-8 animate-spin text-cyan-400" /></div>
            ) : (
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 mb-12">
                    {statCards.map(stat => (
                        <div key={stat.title} className="bg-gray-800/60 p-6 rounded-2xl border border-cyan-400/20">
                            <p className="text-gray-400 text-sm mb-2">{stat.title}</p>
                            <p className="text-3xl font-bold text-white">{stat.value}</p>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
};


const AIManagerView = ({ showToast, selectedGuild }) => {
    const [buildServerPrompt, setBuildServerPrompt] = useState('');
    const [editServerPrompt, setEditServerPrompt] = useState('');
    const [resetServer, setResetServer] = useState(false);
    const [buildPreview, setBuildPreview] = useState(null);
    const [isGeneratingPreview, setIsGeneratingPreview] = useState(false);
    const [isApprovingBuild, setIsApprovingBuild] = useState(false);
    const [isEditing, setIsEditing] = useState(false);

    const previewRoles = useMemo(() => buildPreview?.preview?.roles || [], [buildPreview]);
    const previewCategories = useMemo(() => buildPreview?.preview?.categories || [], [buildPreview]);

    const resetPreviewState = () => setBuildPreview(null);

    useEffect(() => {
        setBuildPreview(null);
    }, [selectedGuild?.id]);

    const handlePreviewBuild = async (regenerate = false) => {
        if (!buildServerPrompt || !selectedGuild) {
            showToast('Please enter a prompt.', 'error');
            return;
        }

        setIsGeneratingPreview(true);
        try {
            const response = await apiFetch('/api/buildserver/preview', {
                method: 'POST',
                body: JSON.stringify({
                    guildId: selectedGuild.id,
                    prompt: buildServerPrompt,
                    resetServer,
                    variationHint: regenerate ? `${Date.now()}` : '',
                }),
            });
            const data = await response.json();
            if (!response.ok) throw new Error(data.error || 'Failed to generate preview.');
            setBuildPreview(data);
            showToast(
                regenerate ? 'Generated a fresh server draft.' : 'Preview generated. Review it before approving.',
                'success'
            );
        } catch (error) {
            showToast(error.message, 'error');
        } finally {
            setIsGeneratingPreview(false);
        }
    };

    const handleApproveBuild = async () => {
        if (!selectedGuild || !buildPreview?.setupPlan) {
            showToast('Generate a preview before approving the build.', 'error');
            return;
        }

        setIsApprovingBuild(true);
        try {
            const response = await apiFetch('/api/buildserver/execute', {
                method: 'POST',
                body: JSON.stringify({
                    guildId: selectedGuild.id,
                    prompt: buildServerPrompt,
                    resetServer,
                    setupPlan: buildPreview.setupPlan,
                }),
            });
            const data = await response.json();
            if (!response.ok) throw new Error(data.error || 'Failed to approve the build.');
            showToast(data.message || 'Approved build sent successfully!', 'success');
            setBuildServerPrompt('');
            setResetServer(false);
            setBuildPreview(null);
        } catch (error) {
            showToast(error.message, 'error');
        } finally {
            setIsApprovingBuild(false);
        }
    };

    const handleEditServer = async () => {
        if (!editServerPrompt || !selectedGuild) {
            showToast('Please enter a prompt.', 'error');
            return;
        }
        setIsEditing(true);
        try {
            const response = await apiFetch('/api/serveredit', {
                method: 'POST',
                body: JSON.stringify({ guildId: selectedGuild.id, prompt: editServerPrompt }),
            });
            const data = await response.json();
            if (!response.ok) throw new Error(data.error || 'Failed to execute command.');
            showToast(data.message || 'Edit command sent successfully!', 'success');
            setEditServerPrompt('');
        } catch (error) {
            showToast(error.message, 'error');
        } finally {
            setIsEditing(false);
        }
    };

    return (
        <div className="animate-fade-in space-y-12">
            <h2 className="text-3xl font-bold text-white">AI Manager</h2>
            <div className="bg-gray-800/60 p-8 rounded-2xl border border-cyan-400/20">
                <h3 className="text-2xl font-bold text-white mb-2">Server Build (/buildserver)</h3>
                <p className="text-gray-400 mb-6">Describe the server you want to create. Seromod will draft the roles, categories, and channels first so you can review them before anything is created.</p>
                <textarea
                    value={buildServerPrompt}
                    onChange={(e) => {
                        setBuildServerPrompt(e.target.value);
                        resetPreviewState();
                    }}
                    className="w-full h-32 p-3 bg-gray-900 rounded-lg text-gray-200 border border-gray-700 focus:ring-2 focus:ring-cyan-400 transition mb-4 resize-none"
                    placeholder="e.g., 'Create a server for a Valorant community...'"
                />
                <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between mt-4">
                    <div className="flex items-center gap-4">
                        <div>
                            <p className="font-semibold text-red-300">Reset the server</p>
                            <p className="text-sm text-gray-400">Deletes all current channels and roles before building.</p>
                        </div>
                        <button
                            type="button"
                            aria-pressed={resetServer}
                            onClick={() => {
                                setResetServer((current) => !current);
                                resetPreviewState();
                            }}
                            className={`relative inline-flex h-8 w-16 items-center rounded-full border transition-colors ${
                                resetServer
                                    ? 'bg-red-500 border-red-400'
                                    : 'bg-gray-700 border-gray-600'
                            }`}
                        >
                            <span
                                className={`inline-block h-6 w-6 transform rounded-full bg-white shadow transition-transform ${
                                    resetServer ? 'translate-x-9' : 'translate-x-1'
                                }`}
                            />
                        </button>
                    </div>
                    <button
                        onClick={() => handlePreviewBuild(false)}
                        disabled={isGeneratingPreview}
                        className="flex items-center justify-center bg-cyan-400 text-gray-900 font-bold py-3 px-6 rounded-xl hover:bg-cyan-300 transition-all shadow-lg hover:shadow-cyan-400/40 disabled:bg-gray-500 disabled:cursor-not-allowed"
                    >
                        {isGeneratingPreview ? <Loader2 className="animate-spin mr-2" /> : <Bot className="mr-2" />}
                        {isGeneratingPreview ? 'Generating Preview...' : 'Generate Preview'}
                    </button>
                </div>
                {buildPreview && (
                    <div className="mt-8 rounded-2xl border border-cyan-400/25 bg-gray-900/70 p-6 space-y-6">
                        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                            <div>
                                <p className="text-sm uppercase tracking-[0.2em] text-cyan-300 mb-2">Server Preview</p>
                                <h4 className="text-2xl font-bold text-white mb-2">Review before building</h4>
                                <p className="text-gray-300 max-w-2xl">Prompt: {buildPreview.prompt || buildServerPrompt}</p>
                                <p className={`mt-2 text-sm font-semibold ${resetServer ? 'text-red-300' : 'text-emerald-300'}`}>
                                    {resetServer ? 'Reset mode is enabled for this build.' : 'Reset mode is disabled for this build.'}
                                </p>
                            </div>
                            <div className="flex flex-wrap gap-3">
                                <button
                                    onClick={() => handlePreviewBuild(true)}
                                    disabled={isGeneratingPreview || isApprovingBuild}
                                    className="flex items-center justify-center bg-gray-700 text-white font-bold py-3 px-5 rounded-xl hover:bg-gray-600 transition-all disabled:bg-gray-600 disabled:cursor-not-allowed"
                                >
                                    {isGeneratingPreview ? <Loader2 className="animate-spin mr-2" /> : <RefreshCw className="mr-2 w-5 h-5" />}
                                    Redo
                                </button>
                                <button
                                    onClick={handleApproveBuild}
                                    disabled={isApprovingBuild || isGeneratingPreview}
                                    className="flex items-center justify-center bg-emerald-400 text-gray-900 font-bold py-3 px-5 rounded-xl hover:bg-emerald-300 transition-all shadow-lg hover:shadow-emerald-400/30 disabled:bg-gray-500 disabled:cursor-not-allowed"
                                >
                                    {isApprovingBuild ? <Loader2 className="animate-spin mr-2" /> : <CheckCircle className="mr-2 w-5 h-5" />}
                                    {isApprovingBuild ? 'Approving...' : 'Approve & Build'}
                                </button>
                            </div>
                        </div>
                        <div className="grid gap-6 xl:grid-cols-[280px_1fr]">
                            <div className="rounded-xl border border-cyan-400/15 bg-gray-800/70 p-5">
                                <h5 className="text-lg font-bold text-white mb-4">Roles</h5>
                                {previewRoles.length > 0 ? (
                                    <div className="flex flex-wrap gap-2">
                                        {previewRoles.map((role) => (
                                            <span key={role} className="rounded-full border border-cyan-400/20 bg-cyan-400/10 px-3 py-1 text-sm text-cyan-200">
                                                {role}
                                            </span>
                                        ))}
                                    </div>
                                ) : (
                                    <p className="text-sm text-gray-400">No new roles are planned for this draft.</p>
                                )}
                            </div>
                            <div className="rounded-xl border border-cyan-400/15 bg-gray-800/70 p-5">
                                <h5 className="text-lg font-bold text-white mb-4">Server Structure</h5>
                                {previewCategories.length > 0 ? (
                                    <div className="space-y-4">
                                        {previewCategories.map((category) => (
                                            <div key={category.name} className="rounded-xl border border-gray-700/80 bg-gray-900/70 p-4">
                                                <div className="flex flex-col gap-1 md:flex-row md:items-center md:justify-between">
                                                    <p className="font-semibold text-cyan-200">{category.name}</p>
                                                    <p className="text-xs uppercase tracking-[0.18em] text-gray-500">{category.channels.length} channels</p>
                                                </div>
                                                {category.channels.length > 0 ? (
                                                    <div className="mt-4 space-y-3">
                                                        {category.channels.map((channel) => (
                                                            <div key={`${category.name}-${channel.name}`} className="rounded-lg border border-gray-800 bg-gray-950/70 p-3">
                                                                <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
                                                                    <p className="font-semibold text-white">
                                                                        {channel.type === 'voice' ? 'Voice' : 'Text'}: {channel.name}
                                                                    </p>
                                                                    <span className="text-xs text-gray-400">{formatPermissionLabel(channel.permissions)}</span>
                                                                </div>
                                                                {channel.topic && <p className="mt-2 text-sm text-gray-400">Topic: {channel.topic}</p>}
                                                                {channel.message && <p className="mt-2 text-sm text-gray-500">Starter message: {channel.message}</p>}
                                                            </div>
                                                        ))}
                                                    </div>
                                                ) : (
                                                    <p className="mt-3 text-sm text-gray-500">No channels planned for this category.</p>
                                                )}
                                            </div>
                                        ))}
                                    </div>
                                ) : (
                                    <p className="text-sm text-gray-400">No server structure was returned for this preview.</p>
                                )}
                            </div>
                        </div>
                    </div>
                )}
            </div>
            <div className="bg-gray-800/60 p-8 rounded-2xl border border-cyan-400/20">
                <h3 className="text-2xl font-bold text-white mb-2">Server Edit (/serveredit)</h3>
                <p className="text-gray-400 mb-6">Describe changes to make to the current server configuration.</p>
                <textarea value={editServerPrompt} onChange={(e) => setEditServerPrompt(e.target.value)} className="w-full h-32 p-3 bg-gray-900 rounded-lg text-gray-200 border border-gray-700 focus:ring-2 focus:ring-cyan-400 transition mb-4 resize-none" placeholder="e.g., 'Add a new text channel called #announcements...'" />
                <button onClick={handleEditServer} disabled={isEditing} className="w-full flex items-center justify-center bg-cyan-400 text-gray-900 font-bold py-3 px-6 rounded-xl hover:bg-cyan-300 transition-all shadow-lg hover:shadow-cyan-400/40 disabled:bg-gray-500 disabled:cursor-not-allowed">
                    {isEditing ? <Loader2 className="animate-spin mr-2" /> : <Bot className="mr-2" />}
                    {isEditing ? 'Executing...' : 'Execute /serveredit'}
                </button>
            </div>
            <div className="sticky bottom-4 z-10">
                <div className="rounded-full border border-yellow-400/30 bg-gray-950/90 px-5 py-3 text-center text-sm text-yellow-200 shadow-lg backdrop-blur">
                    "Seromod" can make mistakes, review before taking the action.
                </div>
            </div>
        </div>
    );
};

const AutoModView = ({ showToast, selectedGuild }) => {
    const [settings, setSettings] = useState({ profanityFilter: false, warningLimit: 3, limitAction: 'Kick' });
    const [isLoading, setIsLoading] = useState(true);
    const [isSaving, setIsSaving] = useState(false);

    const fetchSettings = useCallback(async () => {
        setIsLoading(true);
        try {
            const response = await apiFetch(`/api/automod_settings/${selectedGuild.id}`);
            const data = await response.json();
            if (!response.ok) throw new Error(data.error || 'Failed to fetch settings.');
            setSettings({
                profanityFilter: data.profanityFilter || false,
                warningLimit: data.warningLimit || 3,
                limitAction: data.limitAction || 'Kick',
            });
        } catch (error) {
            showToast(error.message, 'error');
        } finally {
            setIsLoading(false);
        }
    }, [selectedGuild, showToast]);

    useEffect(() => {
        fetchSettings();
    }, [fetchSettings]);

    const handleSaveSettings = async () => {
        setIsSaving(true);
        try {
            const response = await apiFetch(`/api/automod_settings/${selectedGuild.id}`, {
                method: 'POST',
                body: JSON.stringify(settings),
            });
            const data = await response.json();
            if (!response.ok) throw new Error(data.error || 'Failed to save settings.');
            showToast('AutoMod settings saved successfully!', 'success');
        } catch (error) {
            showToast(error.message, 'error');
        } finally {
            setIsSaving(false);
        }
    };

    const handleSettingChange = (key, value) => {
        setSettings(prev => ({ ...prev, [key]: value }));
    };

    if (isLoading) {
        return <div className="flex justify-center items-center h-64"><Loader2 className="w-12 h-12 animate-spin text-cyan-400" /></div>;
    }

    return (
        <div className="animate-fade-in">
            <h2 className="text-3xl font-bold text-white mb-8">AutoMod Settings</h2>
            <div className="space-y-10">
                <div>
                    <h3 className="text-xl font-bold text-white">Profanity Filter</h3>
                    <p className="text-gray-400 mb-4">Automatically issue warnings for profanity.</p>
                    <button onClick={() => handleSettingChange('profanityFilter', !settings.profanityFilter)} className={`px-4 py-2 rounded-lg font-semibold transition-colors text-white ${settings.profanityFilter ? 'bg-green-500 hover:bg-green-600' : 'bg-red-500 hover:bg-red-600'}`}>{settings.profanityFilter ? 'Enabled' : 'Disabled'}</button>
                </div>
                <div>
                    <h3 className="text-xl font-bold text-white">Warning System</h3>
                    <p className="text-gray-400 mb-4">Configure actions after a user reaches the warning limit.</p>
                    <div className="space-y-4">
                        <div>
                            <label className="block text-gray-300 mb-2">Warning Limit</label>
                            <input type="number" min="1" max="20" value={settings.warningLimit} onChange={(e) => handleSettingChange('warningLimit', parseInt(e.target.value))} className="bg-gray-900 border border-gray-700 rounded-lg p-2 text-white w-24" />
                        </div>
                        <div>
                            <label className="block text-gray-300 mb-2">Action on Limit</label>
                            <select value={settings.limitAction} onChange={(e) => handleSettingChange('limitAction', e.target.value)} className="bg-gray-900 border border-gray-700 rounded-lg p-2 text-white focus:ring-2 focus:ring-cyan-400 transition">
                                <option value="Ban">Ban</option>
                                <option value="Kick">Kick</option>
                            </select>
                        </div>
                    </div>
                </div>
            </div>
            <div className="mt-12">
                <button onClick={handleSaveSettings} disabled={isSaving} className="w-48 flex items-center justify-center bg-cyan-400 text-gray-900 font-bold py-3 px-6 rounded-xl hover:bg-cyan-300 transition-all shadow-lg hover:shadow-cyan-400/40 disabled:bg-gray-500 disabled:cursor-not-allowed">
                    {isSaving ? <Loader2 className="animate-spin mr-2" /> : null}
                    {isSaving ? 'Saving...' : 'Save Changes'}
                </button>
            </div>
        </div>
    );
};

const FeedbackHelpView = ({ showToast }) => {
    // This component remains simple and can keep its state internal
    const [feedback, setFeedback] = useState('');
    const [isSubmitting, setIsSubmitting] = useState(false);
    const handleSubmitFeedback = async () => { setIsSubmitting(true); console.log("Submitting feedback:", feedback); await new Promise(r => setTimeout(r, 1000)); showToast('Feedback submitted!', 'success'); setFeedback(''); setIsSubmitting(false); };
    return (
        <div className="animate-fade-in"><h2 className="text-3xl font-bold text-white mb-2">Submit Feedback</h2><p className="text-gray-400 mb-8">Your feedback helps us improve Seromod.</p><textarea value={feedback} onChange={(e) => setFeedback(e.target.value)} className="w-full h-40 p-3 bg-gray-900 rounded-lg text-gray-200 border border-gray-700 focus:ring-2 focus:ring-cyan-400 transition mb-4 resize-none" placeholder="Your Message..." /><button onClick={handleSubmitFeedback} disabled={isSubmitting} className="w-48 flex items-center justify-center bg-cyan-400 text-gray-900 font-bold py-3 px-6 rounded-xl hover:bg-cyan-300 transition-all shadow-lg hover:shadow-cyan-400/40 disabled:bg-gray-500 disabled:cursor-not-allowed">{isSubmitting ? <Loader2 className="animate-spin mr-2" /> : null}{isSubmitting ? 'Submitting...' : 'Submit'}</button></div>
    );
};

const DashboardPage = ({ showToast, selectedGuild, onDeselectGuild }) => {
    const [activeView, setActiveView] = useState('Overview');
    const sidebarItems = [ { name: 'Overview', icon: <LayoutDashboard /> }, { name: 'AI Manager', icon: <Bot /> }, { name: 'AutoMod', icon: <ShieldCheck /> }, { name: 'Feedback/Help', icon: <HelpCircle /> }];

    return (
        <>
            <header className="bg-gray-900/50 p-4 border-b border-cyan-400/20 mb-6 rounded-xl flex justify-between items-center animate-fade-in-down">
                <div className="flex items-center gap-4">
                    <img src={selectedGuild.icon || `https://placehold.co/64x64/1F2937/7DD3FC?text=${selectedGuild.name.charAt(0)}`} alt="Server Icon" className="w-12 h-12 rounded-full object-cover"/>
                    <h1 className="text-2xl font-bold text-white">{selectedGuild.name}</h1>
                </div>
                <button onClick={onDeselectGuild} className="flex items-center gap-2 bg-gray-700/50 text-gray-300 font-semibold py-2 px-4 rounded-lg hover:bg-gray-600 transition-colors">
                    <LogOut className="w-5 h-5" /> Change Server
                </button>
            </header>
            <div className="flex flex-col md:flex-row min-h-[calc(100vh-80px)] animate-fade-in">
                <aside className="w-full md:w-64 bg-gray-900/50 p-6 border-r border-cyan-400/10 shrink-0 rounded-l-xl">
                    <h2 className="text-xl font-bold text-white mb-8 hidden md:block">Settings</h2>
                    <nav><ul className="space-y-2">{sidebarItems.map(item => (<li key={item.name}><button onClick={() => setActiveView(item.name)} className={`w-full flex items-center gap-3 p-3 rounded-lg text-left transition-colors ${activeView === item.name ? 'bg-cyan-400/10 text-cyan-300' : 'text-gray-400 hover:bg-gray-700/50 hover:text-white'}`}>{item.icon}<span className="font-semibold">{item.name}</span></button></li>))}</ul></nav>
                </aside>
                <main className="flex-grow p-6 md:p-10 bg-gray-900/20 rounded-r-xl">
                    {activeView === 'Overview' && <OverviewView selectedGuild={selectedGuild} showToast={showToast} />}
                    {activeView === 'AI Manager' && <AIManagerView showToast={showToast} selectedGuild={selectedGuild} />}
                    {activeView === 'AutoMod' && <AutoModView showToast={showToast} selectedGuild={selectedGuild} />}
                    {activeView === 'Feedback/Help' && <FeedbackHelpView showToast={showToast} />}
                </main>
            </div>
        </>
    );
};

// --- Main App Component ---
export default function App() {
    const [page, setPage] = useState('home');
    const [notification, setNotification] = useState(null);
    const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
    const [guilds, setGuilds] = useState([]);
    const [selectedGuild, setSelectedGuild] = useState(null);
    const [isLoadingGuilds, setIsLoadingGuilds] = useState(true);

    const showToast = useCallback((message, type = 'info') => {
        setNotification({ message, type, id: Date.now() });
    }, []);

    useEffect(() => {
        const fetchGuilds = async () => {
            setIsLoadingGuilds(true);
            try {
                const response = await apiFetch('/api/guilds');
                if (!response.ok) throw new Error('Network response was not ok');
                const data = await response.json();
                setGuilds(Array.isArray(data) ? data : []);
            } catch (error) {
                console.error('Failed to fetch guilds:', error);
                showToast('Could not connect to the backend server.', 'error');
                setGuilds([]); // Ensure guilds is an array on error
            } finally {
                setIsLoadingGuilds(false);
            }
        };
        fetchGuilds();
    }, [showToast]);

    useEffect(() => {
        const savedGuildId = sessionStorage.getItem('selectedGuildId');
        if (savedGuildId && guilds.length > 0) {
            const savedGuild = guilds.find(g => g.id === savedGuildId);
            if (savedGuild) setSelectedGuild(savedGuild);
        }
    }, [guilds]);

    const handleNavigate = (newPage) => {
        setPage(newPage);
        setIsMobileMenuOpen(false);
        window.scrollTo(0, 0);
    };

    const handleSelectGuild = (guild) => {
        setSelectedGuild(guild);
        sessionStorage.setItem('selectedGuildId', guild.id);
    };

    const handleDeselectGuild = () => {
        setSelectedGuild(null);
        sessionStorage.removeItem('selectedGuildId');
    };
    
    const NavLink = ({ pageName, children }) => (
        <button onClick={() => handleNavigate(pageName.toLowerCase())} className={`font-semibold transition-colors pb-1 border-b-2 ${page === pageName.toLowerCase() ? 'text-cyan-300 border-cyan-300' : 'text-gray-300 border-transparent hover:text-white'}`}>{children}</button>
    );

    const renderPage = () => {
        if (page === 'dashboard') {
            return selectedGuild ? <DashboardPage showToast={showToast} selectedGuild={selectedGuild} onDeselectGuild={handleDeselectGuild} /> : <GuildSelector guilds={guilds} onSelectGuild={handleSelectGuild} isLoading={isLoadingGuilds} />;
        }
        if (page === 'guide') return <GuidePage />;
        return <HomePage />;
    };
    
    return (
        <div className="bg-gray-900 min-h-screen text-white font-sans" style={{ backgroundImage: `radial-gradient(circle at top left, rgba(0, 255, 255, 0.05), transparent 30%), radial-gradient(circle at bottom right, rgba(0, 100, 255, 0.05), transparent 30%)` }}>
            <ToastNotification notification={notification} onClose={() => setNotification(null)} />
            <header className="sticky top-0 z-40 bg-gray-900/80 backdrop-blur-lg border-b border-cyan-400/10">
                <div className="container mx-auto px-6 py-4 flex justify-between items-center">
                    <div className="flex items-center gap-2 cursor-pointer" onClick={() => handleNavigate('home')}><Bot className="text-cyan-400" size={28}/><span className="text-2xl font-bold">Seromod</span></div>
                    <nav className="hidden md:flex items-center gap-8"><NavLink pageName="Home">Home</NavLink><NavLink pageName="Dashboard">Dashboard</NavLink><NavLink pageName="Guide">Guide</NavLink></nav>
                    <div className="hidden md:block"><a href={DISCORD_INVITE_URL} target="_blank" rel="noopener noreferrer" className="bg-cyan-500/20 border border-cyan-400 text-cyan-300 font-bold py-2 px-5 rounded-xl hover:bg-cyan-400 hover:text-gray-900 transition-all duration-300">Add to Discord</a></div>
                    <div className="md:hidden"><button onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}>{isMobileMenuOpen ? <X size={28} /> : <Menu size={28} />}</button></div>
                </div>
                {isMobileMenuOpen && (
                    <div className="md:hidden bg-gray-900/90 backdrop-blur-lg pb-4 animate-fade-in-down">
                        <nav className="flex flex-col items-center gap-6 pt-4"><NavLink pageName="Home">Home</NavLink><NavLink pageName="Dashboard">Dashboard</NavLink><NavLink pageName="Guide">Guide</NavLink><a href={DISCORD_INVITE_URL} target="_blank" rel="noopener noreferrer" className="bg-cyan-400 text-gray-900 font-bold py-2 px-5 rounded-xl hover:bg-cyan-300 transition-all">Add to Discord</a></nav>
                    </div>
                )}
            </header>
            <main className="container mx-auto px-2 py-8 md:py-12">{renderPage()}</main>
            <footer className="bg-gray-900/50 border-t border-cyan-400/10 mt-16"><div className="container mx-auto px-6 py-6 text-center text-gray-400"><p>&copy; 2025 Seromod. All Rights Reserved.</p></div></footer>
        </div>
    );
}
