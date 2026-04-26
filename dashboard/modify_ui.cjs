const fs = require('fs');
const FILE = 'c:\\cruxy_seromod\\Cruxy---ModVerse\\dashboard\\src\\App.jsx';
let content = fs.readFileSync(FILE, 'utf8');

// 1. Accordion
content = content.replace(
  'className="border border-white/10 rounded-xl overflow-hidden mb-4 transition-all duration-300"',
  'className="rounded-xl overflow-hidden mb-4 transition-all duration-300"'
).replace(
  'hover:bg-white/5 transition-colors',
  'transition-colors bg-transparent'
);

// 2. Features container
content = content.replace(
  /className="p-6 rounded-2xl border border-white\/10 hover:border-white\/20 transition-all duration-300 text-left transform hover:-translate-y-2"/g,
  'className="p-6 rounded-2xl transition-all duration-300 text-left transform hover:-translate-y-2 bg-transparent"'
);

// 3. GuildSelector container
content = content.replace(
  /className="p-6 rounded-2xl border border-white\/10 hover:border-white\/25 transition-all duration-300 transform hover:-translate-y-2 focus:outline-none focus:ring-2 focus:ring-\[#5865F2\]"/g,
  'className="p-6 rounded-2xl transition-all duration-300 transform hover:-translate-y-2 focus:outline-none bg-transparent"'
);

// 4. OverviewView container
content = content.replace(
  /className="p-6 rounded-2xl border border-white\/10"/g,
  'className="p-6 rounded-2xl bg-transparent"'
);

// 5. AIManagerView input and dialog
content = content.replace(
  '<div className="p-8 rounded-2xl border border-white/10">',
  '<div className="p-8 rounded-2xl bg-transparent">'
);
content = content.replace(
  'className="w-full h-32 p-3 bg-white/5 rounded-lg text-gray-200 border border-white/10 focus:ring-2 focus:ring-[#5865F2] focus:border-transparent transition mb-4 resize-none placeholder-gray-500"',
  'className="w-full h-32 p-3 bg-transparent rounded-lg text-gray-200 focus:outline-none transition mb-4 resize-none placeholder-gray-500 border-none"'
);
content = content.replace(
  '<div className="p-6 rounded-2xl border border-yellow-500/30 animate-fade-in">',
  '<div className="p-6 rounded-2xl animate-fade-in bg-transparent">'
);
content = content.replace(
  '<h4 className="text-lg font-bold text-white mb-2">Do you want to reset the server?</h4>\n                    <p className="text-gray-300 mb-4 text-sm">It will delete the existing structure, proceed with caution.</p>',
  '<h4 className="text-lg font-bold text-white mb-4">Do you want to reset the server? (It will delete the existing structure, proceed with caution)</h4>'
);

// 6. AIManager preview panels
content = content.replace(
  '<div className="rounded-2xl border border-white/10 p-6 space-y-6 animate-fade-in">',
  '<div className="rounded-2xl p-6 space-y-6 animate-fade-in bg-transparent">'
);
content = content.replace(
  '<div className="rounded-xl border border-white/10 p-5">',
  '<div className="rounded-xl p-5 bg-transparent">'
);
content = content.replace(
  '<div className="rounded-xl border border-white/10 p-5">',
  '<div className="rounded-xl p-5 bg-transparent">'
);
content = content.replace(
  /className="rounded-xl border border-white\/10 p-4"/g,
  'className="rounded-xl p-4 bg-transparent"'
);
content = content.replace(
  /className="rounded-lg border border-white\/5 p-3"/g,
  'className="rounded-lg p-3 bg-transparent"'
);

// 7. AutoMod Select inputs "Ensure the user has Admin permissions in the said server"
content = content.replace(
  'Select a member to reset their warning count to zero. Requires Admin permissions.',
  'Select a member to reset their warning count to zero. <span className="text-white font-bold">Ensure the user has Admin permissions in the said server.</span>'
);
content = content.replace(
  'className="w-full bg-gray-800 border border-white/10 rounded-lg p-2 text-white focus:ring-2 focus:ring-[#5865F2] transition"',
  'className="w-full bg-transparent border-none rounded-lg p-2 text-white focus:outline-none focus:ring-0 transition"'
);
content = content.replace(
  'className="bg-gray-800 border border-white/10 rounded-lg p-2 text-white focus:ring-2 focus:ring-[#5865F2] transition"',
  'className="bg-transparent border-none rounded-lg p-2 text-white focus:outline-none focus:ring-0 transition"'
);

// Fix options to be visible
content = content.replace(
  '<option value="Ban">Ban</option>\n                                <option value="Kick">Kick</option>',
  '<option value="Ban" className="bg-[#0a0a0a]">Ban</option>\n                                <option value="Kick" className="bg-[#0a0a0a]">Kick</option>'
);
content = content.replace(
  '<option value="">-- Select a member --</option>',
  '<option value="" className="bg-[#0a0a0a]">-- Select a member --</option>'
);
content = content.replace(
  /<option key=\{member\.id\} value=\{member\.id\}>/g,
  '<option key={member.id} value={member.id} className="bg-[#0a0a0a]">'
);

// 8. feedback
content = content.replace(
  'className="w-full h-40 p-3 bg-white/5 rounded-lg text-gray-200 border border-white/10 focus:ring-2 focus:ring-[#5865F2] transition mb-4 resize-none placeholder-gray-500"',
  'className="w-full h-40 p-3 bg-transparent rounded-lg text-gray-200 border-none focus:outline-none transition mb-4 resize-none placeholder-gray-500"'
);

// 9. Nav link floating
content = content.replace(
  'className={`font-semibold transition-colors pb-1 border-b-2 ${page === pageName.toLowerCase() ? \'text-white border-[#5865F2]\' : \'text-gray-400 border-transparent hover:text-white\'}`}',
  'className={`font-semibold  transition-colors ${page === pageName.toLowerCase() ? \'text-[#5865F2]\' : \'text-gray-400 hover:text-white\'}`}'
);

// 10. Disclaimer warning
content = content.replace(
  '<div className="fixed bottom-4 right-4 z-10">\n                <button\n                    onClick={() => setShowDisclaimer(!showDisclaimer)}\n                    className="text-gray-500 hover:text-gray-300 text-xs transition-colors underline underline-offset-2"\n                >\n                    {showDisclaimer ? \'Hide disclaimer\' : \'Disclaimer\'}\n                </button>\n            </div>\n            {showDisclaimer && (\n                <div className="fixed bottom-10 left-1/2 transform -translate-x-1/2 z-10 animate-fade-in">\n                    <p className="text-white/60 text-sm text-center whitespace-nowrap">\n                        "Seromod" can make mistakes, review before taking the action.\n                    </p>\n                </div>\n            )}',
  `<div className="fixed bottom-4 right-4 z-10">
                <button
                    onClick={() => setShowDisclaimer(!showDisclaimer)}
                    className="text-gray-500 hover:text-white text-xs transition-colors underline underline-offset-2"
                >
                    {showDisclaimer ? 'Hide warning' : 'Show warning'}
                </button>
            </div>
            {showDisclaimer && (
                <div className="fixed bottom-0 left-0 w-full z-10 animate-fade-in">
                    <p className="text-white bg-transparent font-bold text-sm text-center py-2">
                        "Seromod" can make mistakes, review before taking the action.
                    </p>
                </div>
            )}`
);

// 11. Optional active states for sidebar to clear out backgrounds
content = content.replace(
  "className={`w-full flex items-center gap-3 p-3 rounded-lg text-left transition-colors ${activeView === item.name ? 'bg-white/10 text-white' : 'text-gray-400 hover:bg-white/5 hover:text-white'}`}",
  "className={`w-full flex items-center gap-3 p-3 rounded-lg text-left transition-colors ${activeView === item.name ? 'text-[#5865F2]' : 'text-gray-400 hover:text-white'}`}"
);

fs.writeFileSync(FILE, content);
console.log('Replacements complete.');
