// UploadDropzone Component

interface UploadDropzoneProps {
    onFileSelect: (file: File) => void;
    selectedFile: File | null;
}

const UploadDropzone: React.FC<UploadDropzoneProps> = ({ onFileSelect, selectedFile }) => {
    const [isDragOver, setIsDragOver] = React.useState(false);
    const fileInputRef = React.useRef<HTMLInputElement>(null);

    const handleDragOver = (e: React.DragEvent) => {
        e.preventDefault();
        setIsDragOver(true);
    };

    const handleDragLeave = (e: React.DragEvent) => {
        e.preventDefault();
        setIsDragOver(false);
    };

    const handleDrop = (e: React.DragEvent) => {
        e.preventDefault();
        setIsDragOver(false);
        if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
            onFileSelect(e.dataTransfer.files[0]);
        }
    };

    const handleClick = () => {
        fileInputRef.current?.click();
    };

    const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files.length > 0) {
            onFileSelect(e.target.files[0]);
        }
    };

    return (
        <div 
            onClick={handleClick}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            className={`
                w-full h-64 border-2 border-dashed rounded-2xl flex flex-col items-center justify-center p-6 cursor-pointer transition-colors duration-200
                ${isDragOver ? 'border-primary bg-primary/5' : 'border-dark-700 hover:border-gray-500 bg-dark-900'}
            `}
        >
            <input 
                type="file" 
                ref={fileInputRef} 
                onChange={handleChange} 
                accept=".mp4,.mkv,.mov,.avi,.webm" 
                className="hidden" 
            />
            
            <div className="w-16 h-16 rounded-full bg-dark-800 flex items-center justify-center mb-4 text-primary">
                <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                </svg>
            </div>
            
            {selectedFile ? (
                <div className="text-center">
                    <p className="text-gray-200 font-medium text-lg mb-1">{selectedFile.name}</p>
                    <p className="text-gray-500 text-sm">{(selectedFile.size / (1024 * 1024)).toFixed(2)} MB</p>
                </div>
            ) : (
                <p className="text-gray-400 font-medium text-lg text-center">
                    Drop a video here or <span className="text-primary hover:underline">click to browse</span>
                </p>
            )}
        </div>
    );
};

window.Components.UploadDropzone = UploadDropzone;
