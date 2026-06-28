// Sidebar Component
interface SidebarProps {
    jobs?: any[];
    onNewJob?: () => void;
}

const Sidebar: React.FC<SidebarProps> = ({ jobs = [], onNewJob }) => {
    const { Button } = window.Components;

    return (
        <aside className="w-64 h-screen bg-dark-900 border-r border-dark-700 p-6 flex flex-col flex-shrink-0">
            {/* Logo */}
            <div className="mb-10">
                <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2">
                    <div className="w-6 h-6 bg-primary rounded flex items-center justify-center">
                        <span className="text-white text-xs font-black">S</span>
                    </div>
                    SubStudy
                </h1>
            </div>

            {/* New Job CTA */}
            <Button variant="primary" fullWidth className="mb-10" onClick={onNewJob}>
                <span className="mr-2 text-lg leading-none">+</span> New Job
            </Button>

            {/* Recent Jobs */}
            <div className="flex-1 overflow-y-auto">
                <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-4">
                    Recent
                </h3>

                {/* الشرط الديناميكي */}
                {jobs.length === 0 ? (
                    <div className="flex flex-col items-center justify-center py-8 opacity-60">
                        <svg className="w-8 h-8 text-gray-600 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                        </svg>
                        <p className="text-sm text-gray-500 font-medium">No jobs yet</p>
                    </div>
                ) : (
                    <div className="space-y-3">
                        {jobs.map((job, index) => (
                            <div key={index} className="p-3 bg-dark-800 rounded-lg border border-dark-700 hover:border-primary/50 transition-colors cursor-pointer text-sm">
                                <div className="text-gray-200 font-medium truncate mb-1">
                                    Job: {job.job_id ? job.job_id.substring(0, 8) : "Unknown"}...
                                </div>
                                <div className="flex justify-between items-center">
                                    <span className="text-xs text-gray-500">
                                        {job.source_lang || "Auto"} &rarr; {job.target_lang || "En"}
                                    </span>
                                    <span className={`text-xs font-semibold ${
                                        job.status === 'completed' ? 'text-green-400' : 
                                        job.status === 'failed' ? 'text-red-400' : 
                                        'text-primary animate-pulse'
                                    }`}>
                                        {job.status || "Processing"}
                                    </span>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </aside>
    );
};

window.Components.Sidebar = Sidebar;