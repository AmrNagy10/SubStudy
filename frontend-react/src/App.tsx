const { React } = window;
const { useState, useEffect } = React;

const App: React.FC = () => {
    const { Sidebar, UploadDropzone, Select, Button, Card } = window.Components;
    const [selectedFile, setSelectedFile] = useState<File | null>(null);
    const [sourceLang, setSourceLang] = useState('Auto');
    const [targetLang, setTargetLang] = useState('English');
    const [jobs, setJobs] = useState<any[]>([]);

    // 1. قراءة البيانات بشكل آمن ومحمي من حظر المتصفح
    useEffect(() => {
        const loadSavedJobs = async () => {
            let savedJobIds: string[] = [];
            try {
                // إذا كان المتصفح حاظراً للـ storage لن ينهار الكود هنا
                savedJobIds = JSON.parse(localStorage.getItem('substudy_jobs') || '[]');
            } catch (e) {
                console.warn("Storage is blocked by browser tracking prevention. Falling back to memory.");
            }

            if (savedJobIds.length === 0) return;

            const fetchedJobs = [];
            for (const jobId of savedJobIds) {
                try {
                    const response = await fetch(`http://127.0.0.1:8000/api/v1/status/${jobId}`, {
                        headers: {
                            // ⚠️ تأكد من وضع الـ Header والـ Key الصحيح المعتمد في ملف dependencies.py عندك
                            'X-API-Key': 'change_me_in_production'
                        }
                    });
                    if (response.ok) {
                        const data = await response.json();
                        fetchedJobs.push(data);
                    }
                } catch (error) {
                    console.error(`Error fetching job ${jobId}:`, error);
                }
            }
            setJobs(fetchedJobs.reverse());
        };

        loadSavedJobs();
    }, []);

    const handleProcess = async () => {
        if (!selectedFile) return;

        const formData = new FormData();
        formData.append('file', selectedFile);
        formData.append('source_lang', sourceLang);
        formData.append('target_lang', targetLang);

        // إنشاء كائن مؤقت وعرضه فوراً في الـ Sidebar لتتأكد أن الفرونت إند شغال تمام
        // حتى قبل أن ننتظر رد السيرفر أو الـ Storage
        const temporaryJob = {
            job_id: "Sending...",
            status: 'Processing',
            source_lang: sourceLang,
            target_lang: targetLang
        };
        setJobs(prev => [temporaryJob, ...prev]);

        try {
            const response = await fetch('http://127.0.0.1:8000/api/v1/process', {
                method: 'POST',
                headers: {
                    // ⚠️ يجب تغيير هذا للـ Key الصحيح لتفادي الـ 401
                    'X-API-Key': 'change_me_in_production'
                },
                body: formData
            });

            if (response.ok) {
                const data = await response.json();

                // تحديث المهمة المؤقتة بالبيانات الحقيقية القادمة من السيرفر
                setJobs(prev => prev.map(j => j.job_id === "Sending..." ? { ...data, source_lang: sourceLang, target_lang: targetLang } : j));

                // حفظ في الـ Storage بشكل آمن
                try {
                    const savedJobIds = JSON.parse(localStorage.getItem('substudy_jobs') || '[]');
                    localStorage.setItem('substudy_jobs', JSON.stringify([...savedJobIds, data.job_id]));
                } catch (e) {
                    console.error("Could not save to localStorage due to browser restrictions.");
                }

                setSelectedFile(null);
            } else {
                // إذا أرجع السيرفر 401 أو أي خطأ، نغير حالة المهمة في الـ Sidebar لتشاهدها
                setJobs(prev => prev.map(j => j.job_id === "Sending..." ? { ...j, status: `Failed (${response.status})` } : j));
            }
        } catch (error) {
            console.error("Network error:", error);
            setJobs(prev => prev.map(j => j.job_id === "Sending..." ? { ...j, status: 'Network Error' } : j));
        }
    };
    // دالة لتنظيف الصفحة عند الضغط على New Job بدون عمل Refresh
    const handleNewJob = () => {
        setSelectedFile(null);
    };

    return (
        <div className="flex h-screen bg-[#0B0B0D] overflow-hidden text-gray-100 font-sans">
            {/* 4. تمرير الـ jobs ودالة التنظيف للشريط الجانبي */}
            <Sidebar jobs={jobs} onNewJob={handleNewJob} />

            <main className="flex-1 overflow-y-auto relative">
                <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[400px] bg-primary/10 blur-[120px] rounded-full pointer-events-none"></div>

                <div className="max-w-4xl mx-auto px-12 py-20 relative z-10">

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
                                        { value: 'Auto', label: 'Auto Detect' },
                                        { value: 'English', label: 'English' },
                                        { value: 'Arabic', label: 'Arabic' }
                                    ]}
                                />
                                <Select
                                    id="targetLang"
                                    label="Target Language"
                                    value={targetLang}
                                    onChange={(e) => setTargetLang(e.target.value)}
                                    options={[
                                        { value: 'English', label: 'English' },
                                        { value: 'Arabic', label: 'Arabic' }
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