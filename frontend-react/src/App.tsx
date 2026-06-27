const { React } = window;
const { useState } = React;

const App: React.FC = () => {
    const { Sidebar, UploadDropzone, Select, Button, Card } = window.Components;
    const [selectedFile, setSelectedFile] = useState<File | null>(null);
    const [sourceLang, setSourceLang] = useState('auto');
    const [targetLang, setTargetLang] = useState('english');

    const handleProcess = () => {
        if (!selectedFile) return;
        console.log("Processing...", { selectedFile, sourceLang, targetLang });
        // The actual API logic goes here. For this UI task, we just log it.
    };

    return (
        <div className="flex h-screen bg-[#0B0B0D] overflow-hidden text-gray-100 font-sans">
            <Sidebar />
            
            <main className="flex-1 overflow-y-auto relative">
                {/* Subtle background glow effect */}
                <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[400px] bg-primary/10 blur-[120px] rounded-full pointer-events-none"></div>

                <div className="max-w-4xl mx-auto px-12 py-20 relative z-10">
                    
                    {/* Hero Section */}
                    <div className="mb-16">
                        <div className="inline-block px-3 py-1 rounded-full border border-dark-700 bg-dark-800 text-gray-400 text-xs font-semibold tracking-widest uppercase mb-6">
                            V1 • Local Pipeline
                        </div>
                        <h2 className="text-5xl md:text-6xl font-bold tracking-tight text-white leading-tight mb-6">
                            Turn any video into <br/>
                            <span className="text-transparent bg-clip-text bg-gradient-to-r from-primary to-[#a890ff]">
                                transcripts, subtitles, <br/> and summaries.
                            </span>
                        </h2>
                        <p className="text-lg text-gray-400 max-w-2xl leading-relaxed">
                            Process your media entirely on your local machine. No cloud uploads, 
                            complete privacy, and state-of-the-art ML models running securely.
                        </p>
                    </div>

                    {/* Upload Workflow */}
                    <Card className="p-8 backdrop-blur-sm bg-dark-800/80">
                        <div className="mb-6">
                            <h3 className="text-2xl font-semibold text-white mb-2">Upload a video</h3>
                            <p className="text-gray-400 text-sm">Supports MP4, MKV, MOV, AVI and WebM. Maximum 500 MB.</p>
                        </div>
                        
                        <div className="mb-8">
                            <UploadDropzone 
                                selectedFile={selectedFile} 
                                onFileSelect={setSelectedFile} 
                            />
                        </div>

                        <div className="flex flex-col sm:flex-row gap-6 items-end">
                            <div className="flex-1 grid grid-cols-2 gap-6">
                                <Select 
                                    id="sourceLang"
                                    label="Source Language"
                                    value={sourceLang}
                                    onChange={(e) => setSourceLang(e.target.value)}
                                    options={[
                                        { value: 'auto', label: 'Auto Detect' },
                                        { value: 'english', label: 'English' },
                                        { value: 'arabic', label: 'Arabic' }
                                    ]}
                                />
                                <Select 
                                    id="targetLang"
                                    label="Target Language"
                                    value={targetLang}
                                    onChange={(e) => setTargetLang(e.target.value)}
                                    options={[
                                        { value: 'english', label: 'English' },
                                        { value: 'arabic', label: 'Arabic' }
                                    ]}
                                />
                            </div>
                            
                            <div className="w-full sm:w-auto">
                                <Button 
                                    onClick={handleProcess}
                                    disabled={!selectedFile}
                                    fullWidth
                                >
                                    Start Processing
                                </Button>
                            </div>
                        </div>
                    </Card>
                    
                </div>
            </main>
        </div>
    );
};

window.Components.App = App;
