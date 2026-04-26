import React, { useCallback, useEffect, useMemo, useState } from 'react';
import RainingLetters from '@/components/ui/modern-animated-hero-section';
import FeaturesSection from '@/components/ui/bento-features';
import { ScrollReveal } from '@/components/ui/scroll-reveal';
import {
    AlertTriangle,
    BookOpen,
    Bot,
    CheckCircle,
    ChevronDown,
    ChevronUp,
    HelpCircle,
    Info,
    LayoutDashboard,
    Loader2,
    LogOut,
    Mail,
    PanelLeftClose,
    PanelLeftOpen,
    RefreshCw,
    RotateCcw,
    ShieldCheck,
    X,
} from 'lucide-react';
import { ShinyButton } from '@/components/ui/shiny-button';
import { Navbar } from '@/components/ui/mini-navbar';
import { VercelV0Chat } from '@/components/ui/v0-ai-chat';
import Plan from '@/components/ui/agent-plan';

const API_URL = import.meta.env.VITE_API_URL || '';
const API_KEY = import.meta.env.VITE_API_SECRET_KEY || '';
const AUTH_LOGIN_URL = API_URL ? `${API_URL}/auth/login` : '/auth/login';
const DISCORD_INVITE_URL =
    'https://discord.com/oauth2/authorize?client_id=1361039241760604261&permissions=268527702&scope=bot%20applications.commands';

async function apiFetch(path, options = {}) {
    const url = API_URL ? `${API_URL}${path}` : path;
    const headers = {
        'Content-Type': 'application/json',
        ...(options.headers || {}),
    };
    const hasSessionCookie =
        typeof document !== 'undefined' && document.cookie.includes('session=');
    if (API_KEY && !hasSessionCookie) {
        headers['X-API-Key'] = API_KEY;
    }
    return fetch(url, {
        credentials: 'include',
        ...options,
        headers,
    });
}

function getInitialPage() {
    if (typeof window === 'undefined') return 'home';
    const path = window.location.pathname.toLowerCase();
    if (path.startsWith('/dashboard')) return 'dashboard';
    if (path.startsWith('/guide')) return 'guide';
    return 'home';
}

function getInitialIntroPhase() {
    if (typeof window === 'undefined') return 'intro';
    return window.sessionStorage.getItem('intro_shown') ? 'done' : 'intro';
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

function isBuildPrompt(prompt) {
    const buildKeywords = /\b(build|create|make|set\s*up|setup|new server|generate server|start fresh|from scratch|design a server)\b/i;
    return buildKeywords.test(prompt);
}

const ToastNotification = ({ notification, onClose }) => {
    if (!notification) return null;
    const { message, type } = notification;
    const toastStyles = {
        success: {
            bg: 'bg-green-600/90',
            border: 'border-green-500',
            icon: <CheckCircle className="w-6 h-6 text-white" />,
        },
        error: {
            bg: 'bg-red-600/90',
            border: 'border-red-500',
            icon: <AlertTriangle className="w-6 h-6 text-white" />,
        },
        info: {
            bg: 'bg-gray-700/90',
            border: 'border-gray-500',
            icon: <Info className="w-6 h-6 text-white" />,
        },
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
            <button onClick={onClose} className="ml-4 p-1 rounded-full hover:bg-white/20 transition-colors">
                <X className="w-4 h-4" />
            </button>
        </div>
    );
};

const AccordionItem = ({ title, content, isOpen, onClick }) => (
    <div className="rounded-xl overflow-hidden mb-4 transition-all duration-300">
        <button onClick={onClick} className="w-full flex justify-between items-center p-5 text-left font-semibold text-white bg-transparent">
            <span>{title}</span>
            {isOpen ? <ChevronUp className="w-5 h-5 text-gray-400" /> : <ChevronDown className="w-5 h-5 text-gray-400" />}
        </button>
        <div className={`transition-all duration-500 ease-in-out overflow-hidden ${isOpen ? 'max-h-96' : 'max-h-0'}`}>
            <div className="p-5 pt-0 text-gray-300">{content}</div>
        </div>
    </div>
);

const HomePage = () => (
    <div className="animate-fade-in text-center px-4 md:px-8">
        <ScrollReveal>
            <div className="max-w-4xl mx-auto mt-16 mb-24 p-8 md:p-12 rounded-2xl">
                <h1 className="text-4xl md:text-6xl font-extrabold mb-6">
                    <span className="bg-clip-text text-transparent bg-gradient-to-r from-white to-gray-400">Sero</span>
                    <span style={{ color: '#5865F2' }}>mod</span>
                    <span className="bg-clip-text text-transparent bg-gradient-to-r from-white to-gray-400">: The AI-Powered Discord Bot</span>
                </h1>
                <p className="text-lg text-gray-300 max-w-2xl mx-auto mb-8">
                    Enhance your Discord server with Seromod, an AI-driven assistant designed to elevate moderation, setup, and community interaction.
                </p>
                <a href={DISCORD_INVITE_URL} target="_blank" rel="noopener noreferrer">
                    <ShinyButton>Add to Discord</ShinyButton>
                </a>
            </div>
        </ScrollReveal>
        <FeaturesSection />
    </div>
);

const GuidePage = () => {
    const [openAccordion, setOpenAccordion] = useState(0);
    const faqs = [
        { q: 'How do I add Seromod to my server?', a: "Click the 'Add to Discord' button and complete the Discord authorization flow." },
        { q: 'What commands does Seromod have?', a: 'Seromod includes AI-powered server building with /buildserver, natural-language server edits with /serveredit, moderation tools, and more.' },
        { q: 'How do I set up moderation features?', a: 'You can configure all moderation settings from the AutoMod section in your dashboard.' },
        { q: "Can I customize Seromod's AI responses?", a: 'You can guide its actions through detailed prompts in commands like /buildserver and /serveredit.' },
    ];

    return (
        <ScrollReveal className="max-w-4xl mx-auto p-4 md:p-8">
            <h1 className="text-4xl font-extrabold text-white text-center mb-12">Guide & Help</h1>
            <div className="text-center mb-16">
                <a
                    href="https://github.com/rigvedbhat/Seromod/wiki"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-2 bg-[#5865F2] text-white font-bold py-3 px-8 rounded-xl hover:bg-[#4752C4] transition-all duration-300 shadow-lg hover:shadow-[#5865F2]/40 transform hover:scale-105"
                >
                    <BookOpen />
                    Official Wiki
                </a>
            </div>
            <h2 className="text-3xl font-bold text-white text-center mb-8">Frequently Asked Questions</h2>
            <div>
                {faqs.map((faq, index) => (
                    <AccordionItem
                        key={faq.q}
                        title={faq.q}
                        content={faq.a}
                        isOpen={openAccordion === index}
                        onClick={() => setOpenAccordion(openAccordion === index ? null : index)}
                    />
                ))}
            </div>
        </ScrollReveal>
    );
};

const GuildSelector = ({ guilds, onSelectGuild, isLoading }) => (
    <ScrollReveal className="max-w-5xl mx-auto text-center">
        <h1 className="text-4xl font-bold text-white mb-4">Select a Server</h1>
        <p className="text-gray-400 mb-12">Choose a server to manage its settings.</p>
        {isLoading ? (
            <div className="flex justify-center items-center h-64">
                <Loader2 className="w-16 h-16 animate-spin text-white" />
            </div>
        ) : guilds.length === 0 ? (
            <div className="border border-yellow-600/30 p-6 rounded-xl text-yellow-200">
                <h3 className="font-bold text-lg">No Servers Found</h3>
                <p>Seromod does not seem to be in any servers, or your account does not manage a server where the bot is present yet.</p>
            </div>
        ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
                {guilds.map((guild) => (
                    <button
                        key={guild.id}
                        onClick={() => onSelectGuild(guild)}
                        className="p-6 rounded-2xl transition-all duration-300 transform hover:-translate-y-2 focus:outline-none bg-transparent"
                    >
                        <img
                            src={guild.icon || `https://placehold.co/128x128/1a1a2e/FFFFFF?text=${guild.name.charAt(0)}`}
                            alt={`${guild.name} icon`}
                            className="w-32 h-32 rounded-full mx-auto mb-4 object-cover"
                        />
                        <span className="font-semibold text-lg">{guild.name}</span>
                    </button>
                ))}
            </div>
        )}
    </ScrollReveal>
);

const DashboardLoginView = ({ isCheckingAuth }) => (
    <ScrollReveal className="max-w-3xl mx-auto text-center">
        <div className="rounded-3xl border border-white/10 bg-black/30 backdrop-blur-md p-8 md:p-12">
            {isCheckingAuth ? (
                <div className="flex flex-col items-center gap-4">
                    <Loader2 className="w-12 h-12 animate-spin text-white" />
                    <p className="text-gray-300">Checking your Discord session...</p>
                </div>
            ) : (
                <>
                    <p className="text-sm uppercase tracking-[0.3em] text-gray-400 mb-3">Secure Dashboard Access</p>
                    <h1 className="text-4xl font-bold text-white mb-4">Login with Discord</h1>
                    <p className="text-gray-300 max-w-xl mx-auto mb-8">
                        Seromod now protects guild controls behind your Discord session, so only server admins can manage their communities from the dashboard.
                    </p>
                    <a
                        href={AUTH_LOGIN_URL}
                        className="inline-flex items-center gap-3 bg-[#5865F2] px-6 py-3 rounded-2xl font-bold text-white hover:bg-[#4752C4] transition-all shadow-lg hover:shadow-[#5865F2]/30"
                    >
                        <ShieldCheck className="w-5 h-5" />
                        Login with Discord
                    </a>
                </>
            )}
        </div>
    </ScrollReveal>
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
        const interval = setInterval(fetchStats, 60000);
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
                <button onClick={fetchStats} disabled={isLoading} className="flex items-center gap-2 bg-white/10 text-gray-300 font-semibold py-2 px-4 rounded-lg hover:bg-white/15 transition-colors disabled:opacity-50 disabled:cursor-wait">
                    <RefreshCw className={`w-5 h-5 ${isLoading ? 'animate-spin' : ''}`} />
                    Sync
                </button>
            </div>
            {isLoading && !stats.member_count ? (
                <div className="flex justify-center items-center h-24">
                    <Loader2 className="w-8 h-8 animate-spin text-white" />
                </div>
            ) : (
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 mb-12">
                    {statCards.map((stat) => (
                        <div key={stat.title} className="p-6 rounded-2xl bg-transparent">
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
    const [prompt, setPrompt] = useState('');
    const [resetServer, setResetServer] = useState(false);
    const [showResetConfirm, setShowResetConfirm] = useState(false);
    const [buildPreview, setBuildPreview] = useState(null);
    const [isProcessing, setIsProcessing] = useState(false);
    const [isApprovingBuild, setIsApprovingBuild] = useState(false);
    const [activeJob, setActiveJob] = useState(null);

    const previewRoles = useMemo(() => buildPreview?.preview?.roles || [], [buildPreview]);
    const previewCategories = useMemo(() => buildPreview?.preview?.categories || [], [buildPreview]);
    const buildJobInProgress = activeJob && !['completed', 'failed'].includes(activeJob.status);

    useEffect(() => {
        setBuildPreview(null);
        setShowResetConfirm(false);
        setActiveJob(null);
    }, [selectedGuild?.id]);

    useEffect(() => {
        if (!activeJob?.id) {
            return undefined;
        }

        let cancelled = false;
        let timeoutId;

        const pollBuildStatus = async () => {
            try {
                const response = await apiFetch(`/api/buildserver/status/${activeJob.id}`);
                const data = await response.json();
                if (!response.ok) throw new Error(data.error || 'Failed to fetch build status.');
                if (cancelled) return;

                setActiveJob((current) => (
                    current && current.id === activeJob.id
                        ? { ...current, status: data.status, message: data.message || current.message }
                        : current
                ));

                if (data.status === 'completed') {
                    showToast(data.message || 'Build completed!', 'success');
                    setBuildPreview(null);
                    setPrompt('');
                    return;
                }

                if (data.status === 'failed') {
                    showToast(data.message || 'Build failed.', 'error');
                    return;
                }
            } catch (_error) {
                if (cancelled) return;
            }

            timeoutId = window.setTimeout(pollBuildStatus, 3000);
        };

        pollBuildStatus();

        return () => {
            cancelled = true;
            if (timeoutId) {
                window.clearTimeout(timeoutId);
            }
        };
    }, [activeJob?.id, showToast]);

    const handleSubmit = () => {
        if (buildJobInProgress) {
            showToast('A server build is already running for this guild.', 'info');
            return;
        }
        if (!prompt.trim() || !selectedGuild) {
            showToast('Please enter a prompt.', 'error');
            return;
        }
        if (isBuildPrompt(prompt)) {
            setShowResetConfirm(true);
            return;
        }
        void handleEditServer();
    };

    const handleConfirmBuild = (shouldReset) => {
        setResetServer(shouldReset);
        setShowResetConfirm(false);
        void handlePreviewBuild(false, shouldReset);
    };

    const handlePreviewBuild = async (regenerate = false, resetOverride = resetServer) => {
        if (buildJobInProgress) {
            showToast('Wait for the current build to finish before starting another.', 'info');
            return;
        }

        setIsProcessing(true);
        try {
            const response = await apiFetch('/api/buildserver/preview', {
                method: 'POST',
                body: JSON.stringify({
                    guildId: selectedGuild.id,
                    prompt,
                    resetServer: resetOverride,
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
            setIsProcessing(false);
        }
    };

    const handleApproveBuild = async () => {
        if (!selectedGuild || !buildPreview?.planToken) {
            showToast('Generate a preview before approving the build.', 'error');
            return;
        }

        setIsApprovingBuild(true);
        try {
            const response = await apiFetch('/api/buildserver/execute', {
                method: 'POST',
                body: JSON.stringify({
                    guildId: selectedGuild.id,
                    planToken: buildPreview.planToken,
                }),
            });
            const data = await response.json();
            if (!response.ok) throw new Error(data.error || 'Failed to approve the build.');
            setActiveJob({
                id: data.jobId,
                status: 'pending',
                message: data.message || 'Build started.',
            });
            showToast(data.message || 'Build started.', 'success');
        } catch (error) {
            showToast(error.message, 'error');
        } finally {
            setIsApprovingBuild(false);
        }
    };

    const handleEditServer = async () => {
        setIsProcessing(true);
        try {
            const response = await apiFetch('/api/serveredit', {
                method: 'POST',
                body: JSON.stringify({ guildId: selectedGuild.id, prompt }),
            });
            const data = await response.json();
            if (!response.ok) throw new Error(data.error || 'Failed to execute command.');
            showToast(data.message || 'Edit command sent successfully!', 'success');
            setPrompt('');
        } catch (error) {
            showToast(error.message, 'error');
        } finally {
            setIsProcessing(false);
        }
    };

    return (
        <div className="animate-fade-in space-y-8">
            <h2 className="text-3xl font-bold text-white">AI Manager</h2>

            <VercelV0Chat
                prompt={prompt}
                setPrompt={(value) => {
                    setPrompt(value);
                    setBuildPreview(null);
                    setShowResetConfirm(false);
                }}
                onSubmit={handleSubmit}
                isProcessing={isProcessing}
            />

            {activeJob && (
                <div className="rounded-2xl border border-white/10 bg-black/30 backdrop-blur-md p-5 animate-fade-in">
                    <p className="text-xs uppercase tracking-[0.3em] text-gray-400 mb-2">Build Status</p>
                    <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
                        <div>
                            <h4 className="text-xl font-bold text-white capitalize">{activeJob.status}</h4>
                            <p className="text-sm text-gray-300">{activeJob.message || 'Waiting for an update from the bot...'}</p>
                        </div>
                        <span className={`inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold ${
                            activeJob.status === 'completed'
                                ? 'bg-emerald-500/20 text-emerald-200'
                                : activeJob.status === 'failed'
                                    ? 'bg-red-500/20 text-red-200'
                                    : 'bg-amber-500/20 text-amber-200'
                        }`}>
                            Job ID: {activeJob.id}
                        </span>
                    </div>
                </div>
            )}

            {showResetConfirm && (
                <div className="p-6 rounded-2xl animate-fade-in bg-transparent">
                    <h4 className="text-lg font-bold text-white mb-4">Do you want to reset the server? (It will delete the existing structure, proceed with caution)</h4>
                    <div className="flex gap-3">
                        <button onClick={() => handleConfirmBuild(true)} className="flex items-center bg-red-500/80 text-white font-bold py-2 px-5 rounded-xl hover:bg-red-500 transition-all">
                            Yes, Reset & Build
                        </button>
                        <button onClick={() => handleConfirmBuild(false)} className="flex items-center bg-white/10 text-white font-bold py-2 px-5 rounded-xl hover:bg-white/15 transition-all">
                            No, Keep Existing
                        </button>
                    </div>
                </div>
            )}

            {buildPreview && (
                <div className="rounded-2xl space-y-4 animate-fade-in">
                    <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                        <div>
                            <p className="text-sm uppercase tracking-[0.2em] text-gray-400 mb-1">Server Preview</p>
                            <h4 className="text-2xl font-bold text-white mb-1">Review before building</h4>
                            <p className="text-gray-300 max-w-2xl text-sm">Prompt: {buildPreview.prompt || prompt}</p>
                            <p className={`mt-1 text-sm font-semibold ${resetServer ? 'text-red-300' : 'text-emerald-300'}`}>
                                {resetServer ? 'Reset mode is enabled for this build.' : 'Reset mode is disabled for this build.'}
                            </p>
                        </div>
                        <div className="flex flex-wrap gap-3 flex-shrink-0">
                            <button
                                onClick={() => void handlePreviewBuild(true)}
                                disabled={isProcessing || isApprovingBuild || buildJobInProgress}
                                className="flex items-center justify-center bg-white/10 text-white font-bold py-3 px-5 rounded-xl hover:bg-white/15 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                                {isProcessing ? <Loader2 className="animate-spin mr-2" /> : <RefreshCw className="mr-2 w-5 h-5" />}
                                Redo
                            </button>
                            <button
                                onClick={() => void handleApproveBuild()}
                                disabled={isApprovingBuild || isProcessing || buildJobInProgress}
                                className="flex items-center justify-center bg-emerald-500/80 text-white font-bold py-3 px-5 rounded-xl hover:bg-emerald-500 transition-all shadow-lg hover:shadow-emerald-500/30 disabled:bg-gray-600 disabled:cursor-not-allowed"
                            >
                                {isApprovingBuild ? <Loader2 className="animate-spin mr-2" /> : <CheckCircle className="mr-2 w-5 h-5" />}
                                {isApprovingBuild ? 'Approving...' : 'Approve & Build'}
                            </button>
                        </div>
                    </div>
                    <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
                        <Plan />
                        <div className="bg-black/40 backdrop-blur-md border border-white/20 rounded-lg p-4 text-white overflow-auto max-h-80">
                            <p className="text-xs uppercase tracking-widest text-white/40 mb-3">Structure Preview</p>
                            {previewRoles.length > 0 && (
                                <div className="mb-3">
                                    <p className="text-xs font-semibold text-white/60 mb-1.5">Roles</p>
                                    <div className="flex flex-wrap gap-1.5">
                                        {previewRoles.map((role) => (
                                            <span key={role} className="rounded-full border border-white/15 px-2 py-0.5 text-xs text-gray-300">{role}</span>
                                        ))}
                                    </div>
                                </div>
                            )}
                            <div className="space-y-2">
                                {previewCategories.map((category) => (
                                    <details key={category.name} className="group">
                                        <summary className="flex items-center justify-between cursor-pointer py-1 px-2 rounded hover:bg-white/5 transition-colors list-none">
                                            <span className="text-xs font-semibold text-white/80">{category.name}</span>
                                            <span className="text-[10px] text-white/30">{category.channels.length} ch</span>
                                        </summary>
                                        <div className="mt-1 ml-2 space-y-0.5">
                                            {category.channels.map((channel) => (
                                                <div key={`${category.name}-${channel.name}`} className="flex items-center justify-between px-2 py-0.5 rounded text-xs text-white/60 hover:bg-white/5">
                                                    <span className="flex items-center gap-1">
                                                        <span className="text-white/30">{channel.type === 'voice' ? '🔊' : '#'}</span>
                                                        {channel.name}
                                                    </span>
                                                    <span className="text-[10px] text-white/30">{formatPermissionLabel(channel.permissions)}</span>
                                                </div>
                                            ))}
                                        </div>
                                    </details>
                                ))}
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

const AutoModView = ({ showToast, selectedGuild }) => {
    const [settings, setSettings] = useState({ profanityFilter: false, warningLimit: 3, limitAction: 'Kick' });
    const [isLoading, setIsLoading] = useState(true);
    const [isSaving, setIsSaving] = useState(false);
    const [members, setMembers] = useState([]);
    const [selectedMember, setSelectedMember] = useState('');
    const [isResetting, setIsResetting] = useState(false);
    const [isLoadingMembers, setIsLoadingMembers] = useState(false);

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

    const fetchMembers = useCallback(async () => {
        setIsLoadingMembers(true);
        try {
            const response = await apiFetch(`/api/guilds/${selectedGuild.id}/members`);
            const data = await response.json();
            if (!response.ok) throw new Error(data.error || 'Failed to fetch members.');
            const resolvedMembers = Array.isArray(data) ? data : Array.isArray(data.members) ? data.members : [];
            setMembers(resolvedMembers);
        } catch (_error) {
            setMembers([]);
        } finally {
            setIsLoadingMembers(false);
        }
    }, [selectedGuild.id]);

    useEffect(() => {
        fetchSettings();
        fetchMembers();
    }, [fetchMembers, fetchSettings]);

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

    const handleResetWarnings = async () => {
        if (!selectedMember) {
            showToast('Please select a member first.', 'error');
            return;
        }
        setIsResetting(true);
        try {
            const response = await apiFetch(`/api/guilds/${selectedGuild.id}/warnings/reset`, {
                method: 'POST',
                body: JSON.stringify({ userId: selectedMember }),
            });
            const data = await response.json();
            if (!response.ok) throw new Error(data.error || 'Failed to reset warnings.');
            showToast(data.message || 'Warnings reset successfully!', 'success');
            setSelectedMember('');
        } catch (error) {
            showToast(error.message, 'error');
        } finally {
            setIsResetting(false);
        }
    };

    if (isLoading) {
        return (
            <div className="flex justify-center items-center h-64">
                <Loader2 className="w-12 h-12 animate-spin text-white" />
            </div>
        );
    }

    const sliderPercent = ((settings.warningLimit - 1) / 19) * 100;

    return (
        <div className="animate-fade-in">
            <h2 className="text-3xl font-bold text-white mb-8">AutoMod Settings</h2>
            <div className="space-y-10">
                <div>
                    <h3 className="text-xl font-bold text-white">Profanity Filter</h3>
                    <p className="text-gray-400 mb-4">Automatically issue warnings for profanity.</p>
                    <button
                        onClick={() => setSettings((previous) => ({ ...previous, profanityFilter: !previous.profanityFilter }))}
                        className={`px-4 py-2 rounded-lg font-semibold transition-colors text-white ${settings.profanityFilter ? 'bg-green-500 hover:bg-green-600' : 'bg-red-500 hover:bg-red-600'}`}
                    >
                        {settings.profanityFilter ? 'Enabled' : 'Disabled'}
                    </button>
                </div>

                <div>
                    <h3 className="text-xl font-bold text-white">Warning System</h3>
                    <p className="text-gray-400 mb-4">Configure actions after a user reaches the warning limit.</p>
                    <div className="space-y-6">
                        <div>
                            <label className="block text-gray-300 mb-3">Warning Limit: <span className="text-white font-bold text-lg">{settings.warningLimit}</span></label>
                            <input
                                type="range"
                                min="1"
                                max="20"
                                value={settings.warningLimit}
                                onChange={(event) => setSettings((previous) => ({ ...previous, warningLimit: parseInt(event.target.value, 10) }))}
                                className="w-full max-w-md h-2 rounded-lg appearance-none cursor-pointer"
                                style={{
                                    background: `linear-gradient(to right, #5865F2 0%, #5865F2 ${sliderPercent}%, rgba(255,255,255,0.15) ${sliderPercent}%, rgba(255,255,255,0.15) 100%)`,
                                    accentColor: '#5865F2',
                                }}
                            />
                            <div className="flex justify-between max-w-md text-xs text-gray-500 mt-1">
                                <span>1</span><span>5</span><span>10</span><span>15</span><span>20</span>
                            </div>
                        </div>
                        <div>
                            <label className="block text-gray-300 mb-2">Action on Limit</label>
                            <select
                                value={settings.limitAction}
                                onChange={(event) => setSettings((previous) => ({ ...previous, limitAction: event.target.value }))}
                                className="bg-transparent border-none rounded-lg p-2 text-white focus:outline-none focus:ring-0 transition"
                            >
                                <option value="Ban" className="bg-[#0a0a0a]">Ban</option>
                                <option value="Kick" className="bg-[#0a0a0a]">Kick</option>
                            </select>
                        </div>
                    </div>
                </div>

                <div>
                    <h3 className="text-xl font-bold text-white">Reset User Warnings</h3>
                    <p className="text-gray-400 mb-4">Select a member to reset their warning count to zero.</p>
                    <div className="flex flex-col sm:flex-row gap-3 items-start sm:items-end">
                        <div className="flex-grow w-full sm:w-auto">
                            <label className="block text-gray-300 mb-2">Select Member</label>
                            <select
                                value={selectedMember}
                                onChange={(event) => setSelectedMember(event.target.value)}
                                className="w-full bg-transparent border-none rounded-lg p-2 text-white focus:outline-none focus:ring-0 transition"
                                disabled={isLoadingMembers}
                            >
                                <option value="" className="bg-[#0a0a0a]">-- Select a member --</option>
                                {members.map((member) => (
                                    <option key={member.id} value={member.id} className="bg-[#0a0a0a]">
                                        {member.name || member.username || member.id}
                                    </option>
                                ))}
                            </select>
                        </div>
                        <button
                            onClick={() => void handleResetWarnings()}
                            disabled={isResetting || !selectedMember}
                            className="flex items-center gap-2 bg-red-500/80 text-white font-semibold py-2 px-5 rounded-xl hover:bg-red-500 transition-all disabled:bg-gray-600 disabled:cursor-not-allowed"
                        >
                            {isResetting ? <Loader2 className="animate-spin w-4 h-4" /> : <RotateCcw className="w-4 h-4" />}
                            Reset Warnings
                        </button>
                    </div>
                </div>
            </div>
            <div className="mt-12">
                <button onClick={() => void handleSaveSettings()} disabled={isSaving} className="w-48 flex items-center justify-center bg-[#5865F2] text-white font-bold py-3 px-6 rounded-xl hover:bg-[#4752C4] transition-all shadow-lg hover:shadow-[#5865F2]/30 disabled:bg-gray-600 disabled:cursor-not-allowed">
                    {isSaving ? <Loader2 className="animate-spin mr-2" /> : null}
                    {isSaving ? 'Saving...' : 'Save Changes'}
                </button>
            </div>
        </div>
    );
};

const FeedbackHelpView = ({ showToast }) => {
    const [feedback, setFeedback] = useState('');
    const [isSubmitting, setIsSubmitting] = useState(false);

    const handleSubmitFeedback = async () => {
        if (!feedback.trim()) {
            showToast('Please enter a message.', 'error');
            return;
        }
        setIsSubmitting(true);
        try {
            const response = await apiFetch('/api/feedback', {
                method: 'POST',
                body: JSON.stringify({ message: feedback }),
            });
            const data = await response.json();
            if (!response.ok) throw new Error(data.error || 'Failed to submit.');
            showToast('Feedback submitted!', 'success');
            setFeedback('');
        } catch (error) {
            showToast(error.message, 'error');
        } finally {
            setIsSubmitting(false);
        }
    };

    return (
        <div className="animate-fade-in">
            <h2 className="text-3xl font-bold text-white mb-2">Submit Feedback</h2>
            <p className="text-gray-400 mb-8">Your feedback helps us improve Seromod.</p>
            <textarea
                value={feedback}
                onChange={(event) => setFeedback(event.target.value)}
                className="w-full h-40 p-3 bg-transparent rounded-lg text-gray-200 border-none focus:outline-none transition mb-4 resize-none placeholder-gray-500"
                placeholder="Your Message..."
            />
            <button onClick={() => void handleSubmitFeedback()} disabled={isSubmitting} className="w-48 flex items-center justify-center bg-[#5865F2] text-white font-bold py-3 px-6 rounded-xl hover:bg-[#4752C4] transition-all shadow-lg hover:shadow-[#5865F2]/30 disabled:bg-gray-600 disabled:cursor-not-allowed">
                {isSubmitting ? <Loader2 className="animate-spin mr-2" /> : null}
                {isSubmitting ? 'Submitting...' : 'Submit'}
            </button>

            <div className="mt-16">
                <h2 className="text-3xl font-bold text-white mb-2">Contact Us</h2>
                <p className="text-gray-400 mb-6">Have questions or need support? Reach out to us directly.</p>
                <a
                    href="mailto:seromod.info@gmail.com"
                    className="inline-flex items-center gap-2 bg-[#5865F2] text-white font-bold py-3 px-6 rounded-xl hover:bg-[#4752C4] transition-all shadow-lg hover:shadow-[#5865F2]/30"
                >
                    <Mail className="w-5 h-5" />
                    seromod.info@gmail.com
                </a>
            </div>
        </div>
    );
};

const DashboardPage = ({ showToast, selectedGuild, onDeselectGuild }) => {
    const [activeView, setActiveView] = useState('AI Manager');
    const [isSidebarOpen, setIsSidebarOpen] = useState(false);
    const [showDisclaimer, setShowDisclaimer] = useState(false);
    const sidebarItems = [
        { name: 'Overview', icon: <LayoutDashboard /> },
        { name: 'AI Manager', icon: <Bot /> },
        { name: 'AutoMod', icon: <ShieldCheck /> },
        { name: 'Feedback/Help', icon: <HelpCircle /> },
    ];

    return (
        <div className="relative min-h-[calc(100vh-120px)]">
            <header className="p-4 mb-6 rounded-xl flex justify-between items-center animate-fade-in-down">
                <div className="flex items-center gap-4">
                    <button
                        onClick={() => setIsSidebarOpen((previous) => !previous)}
                        className="p-2 rounded-lg hover:bg-white/10 transition-colors text-gray-400 hover:text-white"
                        title={isSidebarOpen ? 'Hide sidebar' : 'Show sidebar'}
                    >
                        {isSidebarOpen ? <PanelLeftClose className="w-5 h-5" /> : <PanelLeftOpen className="w-5 h-5" />}
                    </button>
                    <img
                        src={selectedGuild.icon || `https://placehold.co/64x64/1a1a2e/FFFFFF?text=${selectedGuild.name.charAt(0)}`}
                        alt="Server Icon"
                        className="w-12 h-12 rounded-full object-cover"
                    />
                    <h1 className="text-2xl font-bold text-white">{selectedGuild.name}</h1>
                </div>
                <button onClick={onDeselectGuild} className="flex items-center gap-2 bg-white/10 text-gray-300 font-semibold py-2 px-4 rounded-lg hover:bg-white/15 transition-colors">
                    <LogOut className="w-5 h-5" />
                    Change Server
                </button>
            </header>
            <div className="flex flex-col md:flex-row animate-fade-in">
                {isSidebarOpen && (
                    <aside className="w-full md:w-64 p-6 shrink-0 transition-all duration-300">
                        <h2 className="text-xl font-bold text-white mb-8 hidden md:block">Settings</h2>
                        <nav>
                            <ul className="space-y-2">
                                {sidebarItems.map((item) => (
                                    <li key={item.name}>
                                        <button
                                            onClick={() => setActiveView(item.name)}
                                            className={`w-full flex items-center gap-3 p-3 rounded-lg text-left transition-colors ${activeView === item.name ? 'text-[#5865F2]' : 'text-gray-400 hover:text-white'}`}
                                        >
                                            {item.icon}
                                            <span className="font-semibold">{item.name}</span>
                                        </button>
                                    </li>
                                ))}
                            </ul>
                        </nav>
                    </aside>
                )}
                <main className="flex-grow p-6 md:p-10">
                    {activeView === 'Overview' && <OverviewView selectedGuild={selectedGuild} showToast={showToast} />}
                    {activeView === 'AI Manager' && <AIManagerView selectedGuild={selectedGuild} showToast={showToast} />}
                    {activeView === 'AutoMod' && <AutoModView selectedGuild={selectedGuild} showToast={showToast} />}
                    {activeView === 'Feedback/Help' && <FeedbackHelpView showToast={showToast} />}
                </main>
            </div>

            <div className="fixed bottom-4 right-4 z-10">
                <button onClick={() => setShowDisclaimer((previous) => !previous)} className="text-gray-500 hover:text-white text-xs transition-colors underline underline-offset-2">
                    {showDisclaimer ? 'Hide warning' : 'Show warning'}
                </button>
            </div>
            {showDisclaimer && (
                <div className="fixed bottom-0 left-0 w-full z-10 animate-fade-in">
                    <p className="text-white bg-transparent font-bold text-sm text-center py-2">
                        "Seromod" can make mistakes, review before taking the action.
                    </p>
                </div>
            )}
        </div>
    );
};

export default function App() {
    const [introPhase, setIntroPhase] = useState(getInitialIntroPhase);
    const [page, setPage] = useState(getInitialPage);
    const [notification, setNotification] = useState(null);
    const [guilds, setGuilds] = useState([]);
    const [selectedGuild, setSelectedGuild] = useState(null);
    const [isLoadingGuilds, setIsLoadingGuilds] = useState(true);
    const [authState, setAuthState] = useState({
        checked: false,
        authenticated: false,
        username: '',
    });

    const hasDashboardAccess = authState.authenticated || Boolean(API_KEY);

    const showToast = useCallback((message, type = 'info') => {
        setNotification({ message, type, id: Date.now() });
    }, []);

    const handleIntroComplete = useCallback(() => {
        if (introPhase !== 'intro') {
            return;
        }
        window.sessionStorage.setItem('intro_shown', '1');
        setTimeout(() => {
            setIntroPhase('fading');
            setTimeout(() => setIntroPhase('done'), 1000);
        }, 2000);
    }, [introPhase]);

    useEffect(() => {
        let cancelled = false;

        const checkAuth = async () => {
            try {
                const response = await apiFetch('/auth/me');
                const data = await response.json();
                if (cancelled) return;
                setAuthState({
                    checked: true,
                    authenticated: Boolean(data.authenticated),
                    username: data.username || '',
                });
            } catch (error) {
                if (cancelled) return;
                console.error('Failed to verify auth session:', error);
                if (!API_KEY) {
                    showToast('Could not verify your Discord session.', 'error');
                }
                setAuthState({
                    checked: true,
                    authenticated: false,
                    username: '',
                });
            }
        };

        checkAuth();
        return () => {
            cancelled = true;
        };
    }, [showToast]);

    useEffect(() => {
        if (!authState.checked) {
            return;
        }

        if (!hasDashboardAccess) {
            setGuilds([]);
            setSelectedGuild(null);
            setIsLoadingGuilds(false);
            sessionStorage.removeItem('selectedGuildId');
            return;
        }

        let cancelled = false;

        const fetchGuilds = async () => {
            setIsLoadingGuilds(true);
            try {
                const response = await apiFetch('/api/guilds');
                const data = await response.json();
                if (!response.ok) throw new Error(data.error || 'Could not load guilds.');
                if (cancelled) return;
                setGuilds(Array.isArray(data) ? data : []);
            } catch (error) {
                if (cancelled) return;
                console.error('Failed to fetch guilds:', error);
                showToast(error.message || 'Could not connect to the backend server.', 'error');
                setGuilds([]);
            } finally {
                if (!cancelled) {
                    setIsLoadingGuilds(false);
                }
            }
        };

        fetchGuilds();
        return () => {
            cancelled = true;
        };
    }, [authState.checked, hasDashboardAccess, showToast]);

    useEffect(() => {
        const savedGuildId = sessionStorage.getItem('selectedGuildId');
        if (!savedGuildId || guilds.length === 0) {
            return;
        }
        const savedGuild = guilds.find((guild) => guild.id === savedGuildId);
        if (savedGuild) {
            setSelectedGuild(savedGuild);
        }
    }, [guilds]);

    useEffect(() => {
        if (selectedGuild && !guilds.some((guild) => guild.id === selectedGuild.id)) {
            setSelectedGuild(null);
            sessionStorage.removeItem('selectedGuildId');
        }
    }, [guilds, selectedGuild]);

    const handleNavigate = (newPage) => {
        setPage(newPage);
        const targetPath = newPage === 'home' ? '/' : `/${newPage}`;
        window.history.replaceState({}, '', targetPath);
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

    const renderPage = () => {
        if (page === 'dashboard') {
            if (!authState.checked && !API_KEY) {
                return <DashboardLoginView isCheckingAuth={true} />;
            }
            if (!hasDashboardAccess) {
                return <DashboardLoginView isCheckingAuth={false} />;
            }
            return selectedGuild
                ? <DashboardPage showToast={showToast} selectedGuild={selectedGuild} onDeselectGuild={handleDeselectGuild} />
                : <GuildSelector guilds={guilds} onSelectGuild={handleSelectGuild} isLoading={isLoadingGuilds} />;
        }
        if (page === 'guide') {
            return <GuidePage />;
        }
        return <HomePage />;
    };

    return (
        <>
            <div
                style={{
                    position: 'fixed',
                    inset: 0,
                    zIndex: 0,
                    opacity: 1,
                    transition: 'opacity 1s ease-in-out',
                    pointerEvents: 'none',
                }}
            >
                <RainingLetters onComplete={handleIntroComplete} showTitle={introPhase === 'intro'} />
            </div>

            <div
                className="relative min-h-screen text-white font-sans z-10"
                style={{
                    opacity: introPhase === 'intro' ? 0 : 1,
                    visibility: introPhase === 'intro' ? 'hidden' : 'visible',
                    transition: 'opacity 1s ease-in-out',
                }}
            >
                <ToastNotification notification={notification} onClose={() => setNotification(null)} />
                <Navbar
                    onNavigate={handleNavigate}
                    onDashboardClick={() => handleNavigate('dashboard')}
                    onGetStartedClick={() => window.open(DISCORD_INVITE_URL, '_blank')}
                />
                <main className="container mx-auto px-2 pt-28 pb-8 md:pt-32 md:pb-12">{renderPage()}</main>
                <footer className="border-t border-white/5 mt-16">
                    <div className="container mx-auto px-6 py-6 text-center text-gray-500">
                        <p>&copy; 2025 Seromod. All Rights Reserved.</p>
                    </div>
                </footer>
            </div>
        </>
    );
}
