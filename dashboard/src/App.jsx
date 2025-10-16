import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { ShieldCheck, Bot, Swords, Users, Settings, HelpCircle, Send, MessageSquare, BookOpen, ChevronDown, ChevronUp, Loader2, Home, LayoutDashboard, Menu, X, CheckCircle, AlertTriangle, Info, LogOut } from 'lucide-react';

const API_URL = 'http://127.0.0.1:5000';

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
    const INVITE_LINK = "#"; // Placeholder
    const features = [
        { icon: <Bot size={32} />, title: "AI-Powered Server Building", description: "Experience dynamic building experience through cruxy's AI server building. /buildserver the way you want it." },
        { icon: <Users size={32} />, title: "Community Engagement", description: "Boost user participation and create a thriving community with Cruxy's AI chat feature. Just @Cruxy and start chatting!" },
        { icon: <ShieldCheck size={32} />, title: "Intelligent Moderation", description: "Maintain a safe and positive environment with cruxy's smart moderation tools, ensuring a respectful atmosphere." },
        { icon: <Swords size={32} />, title: "Fun Commands", description: "Keep your server members entertained with a variety of fun and interactive commands.", status: "Under development" },
    ];

    return (
        <div className="animate-fade-in text-center px-4 md:px-8">
            <div className="max-w-4xl mx-auto mt-16 mb-24 bg-gray-900/50 border border-cyan-400/30 p-8 md:p-12 rounded-2xl shadow-2xl shadow-cyan-500/10 backdrop-blur-sm">
                <h1 className="text-4xl md:text-6xl font-extrabold bg-clip-text text-transparent bg-gradient-to-r from-cyan-300 to-blue-400 mb-6">Crux AI: The AI-Powered Discord Bot</h1>
                <p className="text-lg text-gray-300 max-w-2xl mx-auto mb-8">Enhance your Discord server with Crux AI, an AI-driven bot designed to elevate user engagement and community interaction.</p>
                <a href={INVITE_LINK} className="inline-block bg-cyan-400 text-gray-900 font-bold py-3 px-8 rounded-xl hover:bg-cyan-300 transition-all duration-300 shadow-lg hover:shadow-cyan-400/40 transform hover:scale-105">Add to Discord</a>
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
    const WIKI_URL = "https://github.com/rigvedbhat/Cruxy---ModVerse";
    const faqs = [
        { q: "How do I add Cruxy to my server?", a: "To add Cruxy to your server, simply click the 'Add to Server' button on the Cruxy website and follow the authorization prompts." },
        { q: "What commands does Cruxy have?", a: "Cruxy features a variety of commands, including AI-powered server building (/buildserver), moderation tools, and leveling systems." },
        { q: "How do I set up moderation features?", a: "You can configure all moderation settings from the AutoMod section in your dashboard." },
        { q: "Can I customize Cruxy's AI responses?", a: "You can guide its actions through detailed prompts in commands like /buildserver and /serveredit." },
    ];

    return (
        <div className="max-w-4xl mx-auto p-4 md:p-8 animate-fade-in">
            <h1 className="text-4xl font-extrabold text-white text-center mb-12">Guide & Help</h1>
            <div className="text-center mb-16">
                <a href={WIKI_URL} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-2 bg-cyan-400 text-gray-900 font-bold py-3 px-8 rounded-xl hover:bg-cyan-300 transition-all duration-300 shadow-lg hover:shadow-cyan-400/40 transform hover:scale-105">
                    <BookOpen />Read the Full Documentation (Wiki)
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
                <p>Crux AI doesn't seem to be in any servers, or the backend is not connected. Invite the bot to a server to get started.</p>
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

const OverviewView = () => (
    <div className="animate-fade-in">
        <h2 className="text-3xl font-bold text-white mb-8">Overview</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 mb-12">
            {[{ title: 'Total Members', value: '1,234' }, { title: 'Members Online', value: '456' }, { title: 'Mod Actions (24h)', value: '78' }, { title: 'Levels Awarded (24h)', value: '90' }]
                .map(stat => (
                    <div key={stat.title} className="bg-gray-800/60 p-6 rounded-2xl border border-cyan-400/20">
                        <p className="text-gray-400 text-sm mb-2">{stat.title}</p>
                        <p className="text-3xl font-bold text-white">{stat.value}</p>
                    </div>
                ))}
        </div>
        <h3 className="text-2xl font-bold text-white mb-4">Live Activity Feed (Placeholder)</h3>
        <div className="bg-gray-800/60 p-6 rounded-2xl border border-cyan-400/20">
            <ul className="space-y-3 text-gray-300">
                <li className="flex items-center gap-3"><span className="text-cyan-400/70 text-sm">12:38 PM</span> - User @Casey joined the server</li>
                <li className="flex items-center gap-3"><span className="text-cyan-400/70 text-sm">12:37 PM</span> - User @Morgan muted for 1 hour</li>
                <li className="flex items-center gap-3"><span className="text-cyan-400/70 text-sm">12:36 PM</span> - User @Taylor leveled up to level 5</li>
            </ul>
        </div>
    </div>
);

const AIManagerView = ({ showToast, selectedGuild }) => {
    const [buildServerPrompt, setBuildServerPrompt] = useState('');
    const [editServerPrompt, setEditServerPrompt] = useState('');
    const [resetServer, setResetServer] = useState(false);
    const [isBuilding, setIsBuilding] = useState(false);
    const [isEditing, setIsEditing] = useState(false);

    const handleBuildServer = async () => {
        if (!buildServerPrompt || !selectedGuild) {
            showToast('Please enter a prompt.', 'error');
            return;
        }
        setIsBuilding(true);
        try {
            const response = await fetch(`${API_URL}/api/buildserver`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    guildId: selectedGuild.id,
                    prompt: buildServerPrompt,
                    resetServer: resetServer,
                }),
            });
            const data = await response.json();
            if (!response.ok) throw new Error(data.error || 'Failed to execute command.');
            showToast(data.message || 'Build command sent successfully!', 'success');
            setBuildServerPrompt('');
        } catch (error) {
            showToast(error.message, 'error');
        } finally {
            setIsBuilding(false);
        }
    };

    const handleEditServer = async () => {
        if (!editServerPrompt || !selectedGuild) {
            showToast('Please enter a prompt.', 'error');
            return;
        }
        setIsEditing(true);
        try {
            const response = await fetch(`${API_URL}/api/serveredit`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
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
                <p className="text-gray-400 mb-6">Describe the server you want to create. The AI will generate channels, roles, and permissions.</p>
                <textarea value={buildServerPrompt} onChange={(e) => setBuildServerPrompt(e.target.value)} className="w-full h-32 p-3 bg-gray-900 rounded-lg text-gray-200 border border-gray-700 focus:ring-2 focus:ring-cyan-400 transition mb-4 resize-none" placeholder="e.g., 'Create a server for a Valorant community...'" />
                <div className="flex items-center justify-between mt-4">
                    <label className="flex items-center gap-2 cursor-pointer text-yellow-300">
                        <input type="checkbox" checked={resetServer} onChange={(e) => setResetServer(e.target.checked)} className="form-checkbox h-5 w-5 rounded bg-gray-700 border-gray-600 text-yellow-500 focus:ring-yellow-500" />
                        <span className="font-semibold">Reset Server (Deletes all channels/roles)</span>
                    </label>
                    <button onClick={handleBuildServer} disabled={isBuilding} className="flex items-center justify-center bg-cyan-400 text-gray-900 font-bold py-3 px-6 rounded-xl hover:bg-cyan-300 transition-all shadow-lg hover:shadow-cyan-400/40 disabled:bg-gray-500 disabled:cursor-not-allowed">
                        {isBuilding ? <Loader2 className="animate-spin mr-2" /> : <Bot className="mr-2" />}
                        {isBuilding ? 'Executing...' : 'Execute /buildserver'}
                    </button>
                </div>
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
        </div>
    );
};

const AutoModView = ({ showToast, selectedGuild }) => {
    const [settings, setSettings] = useState({ profanityFilter: false, warningLimit: 3, limitAction: 'Kick', muteDuration: 10 });
    const [isLoading, setIsLoading] = useState(true);
    const [isSaving, setIsSaving] = useState(false);

    const fetchSettings = useCallback(async () => {
        setIsLoading(true);
        try {
            const response = await fetch(`${API_URL}/api/automod_settings/${selectedGuild.id}`);
            const data = await response.json();
            if (!response.ok) throw new Error(data.error || 'Failed to fetch settings.');
            setSettings({
                profanityFilter: data.profanity_filter_enabled || false,
                warningLimit: data.warning_limit || 3,
                limitAction: data.punishment_type || 'Kick',
                muteDuration: data.mute_duration_minutes || 10,
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
            const response = await fetch(`${API_URL}/api/automod_settings/${selectedGuild.id}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
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
                                <option value="Mute">Mute</option>
                            </select>
                        </div>
                        {settings.limitAction === 'Mute' && (
                             <div>
                                <label className="block text-gray-300 mb-2">Mute Duration (minutes)</label>
                                <input type="number" min="1" value={settings.muteDuration} onChange={(e) => handleSettingChange('muteDuration', parseInt(e.target.value))} className="bg-gray-900 border border-gray-700 rounded-lg p-2 text-white w-24" />
                            </div>
                        )}
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
        <div className="animate-fade-in"><h2 className="text-3xl font-bold text-white mb-2">Submit Feedback</h2><p className="text-gray-400 mb-8">Your feedback helps us improve Cruxy.</p><textarea value={feedback} onChange={(e) => setFeedback(e.target.value)} className="w-full h-40 p-3 bg-gray-900 rounded-lg text-gray-200 border border-gray-700 focus:ring-2 focus:ring-cyan-400 transition mb-4 resize-none" placeholder="Your Message..." /><button onClick={handleSubmitFeedback} disabled={isSubmitting} className="w-48 flex items-center justify-center bg-cyan-400 text-gray-900 font-bold py-3 px-6 rounded-xl hover:bg-cyan-300 transition-all shadow-lg hover:shadow-cyan-400/40 disabled:bg-gray-500 disabled:cursor-not-allowed">{isSubmitting ? <Loader2 className="animate-spin mr-2" /> : null}{isSubmitting ? 'Submitting...' : 'Submit'}</button></div>
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
                    {activeView === 'Overview' && <OverviewView />}
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
                const response = await fetch(`${API_URL}/api/guilds`);
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
        const savedGuildId = localStorage.getItem('selectedGuildId');
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
        localStorage.setItem('selectedGuildId', guild.id);
    };

    const handleDeselectGuild = () => {
        setSelectedGuild(null);
        localStorage.removeItem('selectedGuildId');
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
                    <div className="flex items-center gap-2 cursor-pointer" onClick={() => handleNavigate('home')}><Bot className="text-cyan-400" size={28}/><span className="text-2xl font-bold">Crux AI</span></div>
                    <nav className="hidden md:flex items-center gap-8"><NavLink pageName="Home">Home</NavLink><NavLink pageName="Dashboard">Dashboard</NavLink><NavLink pageName="Guide">Guide</NavLink></nav>
                    <div className="hidden md:block"><a href="#" className="bg-cyan-500/20 border border-cyan-400 text-cyan-300 font-bold py-2 px-5 rounded-xl hover:bg-cyan-400 hover:text-gray-900 transition-all duration-300">Add to Discord</a></div>
                    <div className="md:hidden"><button onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}>{isMobileMenuOpen ? <X size={28} /> : <Menu size={28} />}</button></div>
                </div>
                {isMobileMenuOpen && (
                    <div className="md:hidden bg-gray-900/90 backdrop-blur-lg pb-4 animate-fade-in-down">
                        <nav className="flex flex-col items-center gap-6 pt-4"><NavLink pageName="Home">Home</NavLink><NavLink pageName="Dashboard">Dashboard</NavLink><NavLink pageName="Guide">Guide</NavLink><a href="#" className="bg-cyan-400 text-gray-900 font-bold py-2 px-5 rounded-xl hover:bg-cyan-300 transition-all">Add to Discord</a></nav>
                    </div>
                )}
            </header>
            <main className="container mx-auto px-2 py-8 md:py-12">{renderPage()}</main>
            <footer className="bg-gray-900/50 border-t border-cyan-400/10 mt-16"><div className="container mx-auto px-6 py-6 text-center text-gray-400"><p>&copy; 2025 Crux AI by ModVerse. All Rights Reserved.</p></div></footer>
        </div>
    );
}

