'use client';

import { useState, useRef, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { uploadVideo, downloadFromUrl, analyzeVideo, VideoUploadResponse } from '@/services/api';

type TabType = 'file' | 'link';
type UploadStatus = 'idle' | 'uploading' | 'processing' | 'analyzing' | 'success' | 'error';

export default function UploadPage() {
    const router = useRouter();
    const fileInputRef = useRef<HTMLInputElement>(null);

    const [activeTab, setActiveTab] = useState<TabType>('file');
    const [status, setStatus] = useState<UploadStatus>('idle');
    const [progress, setProgress] = useState(0);
    const [statusMessage, setStatusMessage] = useState('');
    const [error, setError] = useState<string | null>(null);
    const [uploadResult, setUploadResult] = useState<VideoUploadResponse | null>(null);

    // File upload state
    const [selectedFile, setSelectedFile] = useState<File | null>(null);
    const [isDragging, setIsDragging] = useState(false);

    // Link input state
    const [videoUrl, setVideoUrl] = useState('');

    // Handle file selection
    const handleFileSelect = useCallback((file: File) => {
        // Validate file type
        const allowedTypes = ['video/mp4', 'video/mov', 'video/avi', 'video/mkv', 'video/webm'];
        if (!allowedTypes.includes(file.type) && !file.name.match(/\.(mp4|mov|avi|mkv|webm)$/i)) {
            setError('File không được hỗ trợ. Vui lòng chọn file video (mp4, mov, avi, mkv, webm)');
            return;
        }

        // Validate file size (500MB max)
        if (file.size > 500 * 1024 * 1024) {
            setError('File quá lớn. Tối đa 500MB');
            return;
        }

        setSelectedFile(file);
        setError(null);
    }, []);

    // Drag and drop handlers
    const handleDragOver = useCallback((e: React.DragEvent) => {
        e.preventDefault();
        setIsDragging(true);
    }, []);

    const handleDragLeave = useCallback((e: React.DragEvent) => {
        e.preventDefault();
        setIsDragging(false);
    }, []);

    const handleDrop = useCallback((e: React.DragEvent) => {
        e.preventDefault();
        setIsDragging(false);

        const file = e.dataTransfer.files[0];
        if (file) {
            handleFileSelect(file);
        }
    }, [handleFileSelect]);

    // Upload file
    const handleUploadFile = async () => {
        if (!selectedFile) return;

        setStatus('uploading');
        setProgress(0);
        setError(null);
        setStatusMessage('Đang upload video...');

        try {
            const result = await uploadVideo(selectedFile, (p) => {
                setProgress(p);
                setStatusMessage(`Đang upload... ${p}%`);
            });

            if (result.success && result.video_id) {
                setUploadResult(result);
                setStatus('analyzing');
                setStatusMessage('Upload thành công! Đang phân tích...');
                setProgress(100);

                // Start analysis
                await analyzeVideo(result.video_id);

                setStatus('success');
                setStatusMessage('Phân tích đã bắt đầu!');

                // Redirect to video page after 2 seconds
                setTimeout(() => {
                    router.push(`/videos/${result.video_id}`);
                }, 2000);
            } else {
                throw new Error(result.message || 'Upload failed');
            }
        } catch (err: unknown) {
            setStatus('error');
            const errorMessage = err instanceof Error ? err.message : 'Upload thất bại';
            setError(errorMessage);
            setStatusMessage('');
        }
    };

    // Download from URL
    const handleDownloadUrl = async () => {
        if (!videoUrl.trim()) {
            setError('Vui lòng nhập link video');
            return;
        }

        setStatus('processing');
        setProgress(30);
        setError(null);
        setStatusMessage('Đang tải video từ link...');

        try {
            const result = await downloadFromUrl(videoUrl);

            if (result.success && result.video_id) {
                setUploadResult(result);
                setProgress(70);
                setStatus('analyzing');
                setStatusMessage('Tải thành công! Đang phân tích...');

                // Start analysis
                await analyzeVideo(result.video_id);

                setProgress(100);
                setStatus('success');
                setStatusMessage('Phân tích đã bắt đầu!');

                // Redirect to video page
                setTimeout(() => {
                    router.push(`/videos/${result.video_id}`);
                }, 2000);
            } else {
                throw new Error(result.message || 'Download failed');
            }
        } catch (err: unknown) {
            setStatus('error');
            const errorMessage = err instanceof Error ? err.message : 'Tải video thất bại';
            setError(errorMessage);
            setStatusMessage('');
        }
    };

    // Reset form
    const handleReset = () => {
        setStatus('idle');
        setProgress(0);
        setSelectedFile(null);
        setVideoUrl('');
        setError(null);
        setStatusMessage('');
        setUploadResult(null);
    };

    return (
        <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 text-white">
            {/* Header */}
            <header className="border-b border-gray-700 bg-gray-900/50 backdrop-blur-sm">
                <div className="max-w-4xl mx-auto px-6 py-4 flex items-center justify-between">
                    <a href="/" className="text-2xl font-bold bg-gradient-to-r from-blue-400 to-purple-500 bg-clip-text text-transparent">
                        🎬 Video Analysis AI
                    </a>
                    <nav className="flex gap-4">
                        <a href="/library" className="text-gray-400 hover:text-white transition">
                            📚 Library
                        </a>
                    </nav>
                </div>
            </header>

            {/* Main Content */}
            <main className="max-w-4xl mx-auto px-6 py-12">
                <div className="text-center mb-8">
                    <h1 className="text-3xl font-bold mb-2">📤 Upload Video</h1>
                    <p className="text-gray-400">Upload video hoặc paste link để phân tích với AI</p>
                </div>

                {/* Tab Buttons */}
                <div className="flex justify-center mb-8">
                    <div className="bg-gray-800 rounded-lg p-1 inline-flex">
                        <button
                            className={`px-6 py-2 rounded-md font-medium transition ${activeTab === 'file'
                                    ? 'bg-blue-600 text-white'
                                    : 'text-gray-400 hover:text-white'
                                }`}
                            onClick={() => { setActiveTab('file'); handleReset(); }}
                        >
                            📁 Upload File
                        </button>
                        <button
                            className={`px-6 py-2 rounded-md font-medium transition ${activeTab === 'link'
                                    ? 'bg-blue-600 text-white'
                                    : 'text-gray-400 hover:text-white'
                                }`}
                            onClick={() => { setActiveTab('link'); handleReset(); }}
                        >
                            🔗 Paste Link
                        </button>
                    </div>
                </div>

                {/* Upload Card */}
                <div className="bg-gray-800/50 rounded-xl p-8 border border-gray-700">
                    {/* File Upload Tab */}
                    {activeTab === 'file' && (
                        <div>
                            {/* Drop Zone */}
                            <div
                                className={`border-2 border-dashed rounded-xl p-12 text-center cursor-pointer transition ${isDragging
                                        ? 'border-blue-500 bg-blue-500/10'
                                        : selectedFile
                                            ? 'border-green-500 bg-green-500/10'
                                            : 'border-gray-600 hover:border-gray-500'
                                    }`}
                                onClick={() => fileInputRef.current?.click()}
                                onDragOver={handleDragOver}
                                onDragLeave={handleDragLeave}
                                onDrop={handleDrop}
                            >
                                <input
                                    ref={fileInputRef}
                                    type="file"
                                    accept="video/*"
                                    className="hidden"
                                    onChange={(e) => e.target.files?.[0] && handleFileSelect(e.target.files[0])}
                                />

                                {selectedFile ? (
                                    <div>
                                        <div className="text-5xl mb-4">🎬</div>
                                        <p className="text-xl font-semibold text-green-400">{selectedFile.name}</p>
                                        <p className="text-gray-400 mt-2">
                                            {(selectedFile.size / (1024 * 1024)).toFixed(1)} MB
                                        </p>
                                        <button
                                            className="mt-4 text-sm text-gray-400 hover:text-white underline"
                                            onClick={(e) => { e.stopPropagation(); setSelectedFile(null); }}
                                        >
                                            Chọn file khác
                                        </button>
                                    </div>
                                ) : (
                                    <div>
                                        <div className="text-5xl mb-4">📤</div>
                                        <p className="text-xl font-semibold">Kéo thả video vào đây</p>
                                        <p className="text-gray-400 mt-2">hoặc click để chọn file</p>
                                        <p className="text-sm text-gray-500 mt-4">
                                            Hỗ trợ: MP4, MOV, AVI, MKV, WebM (tối đa 500MB)
                                        </p>
                                    </div>
                                )}
                            </div>

                            {/* Upload Button */}
                            <button
                                className="w-full mt-6 py-4 bg-gradient-to-r from-blue-600 to-purple-600 rounded-lg font-semibold text-lg hover:opacity-90 transition disabled:opacity-50 disabled:cursor-not-allowed"
                                onClick={handleUploadFile}
                                disabled={!selectedFile || status !== 'idle'}
                            >
                                🚀 Upload & Phân tích
                            </button>
                        </div>
                    )}

                    {/* Link Tab */}
                    {activeTab === 'link' && (
                        <div>
                            <div className="mb-6">
                                <label className="block text-sm font-medium text-gray-400 mb-2">
                                    Link Video (TikTok, YouTube)
                                </label>
                                <input
                                    type="url"
                                    className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-lg focus:outline-none focus:border-blue-500 text-white placeholder-gray-400"
                                    placeholder="https://www.tiktok.com/@user/video/..."
                                    value={videoUrl}
                                    onChange={(e) => setVideoUrl(e.target.value)}
                                    disabled={status !== 'idle'}
                                />
                            </div>

                            <button
                                className="w-full py-4 bg-gradient-to-r from-blue-600 to-purple-600 rounded-lg font-semibold text-lg hover:opacity-90 transition disabled:opacity-50 disabled:cursor-not-allowed"
                                onClick={handleDownloadUrl}
                                disabled={!videoUrl.trim() || status !== 'idle'}
                            >
                                🔗 Tải & Phân tích
                            </button>
                        </div>
                    )}

                    {/* Progress Bar */}
                    {status !== 'idle' && status !== 'error' && (
                        <div className="mt-6">
                            <div className="flex justify-between text-sm mb-2">
                                <span className="text-gray-400">{statusMessage}</span>
                                <span className="text-blue-400">{progress}%</span>
                            </div>
                            <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
                                <div
                                    className={`h-full transition-all duration-300 ${status === 'success' ? 'bg-green-500' : 'bg-blue-500'
                                        }`}
                                    style={{ width: `${progress}%` }}
                                />
                            </div>

                            {status === 'success' && (
                                <div className="mt-4 text-center">
                                    <span className="text-green-400">✅ {statusMessage}</span>
                                    <p className="text-gray-400 text-sm mt-1">Đang chuyển hướng...</p>
                                </div>
                            )}
                        </div>
                    )}

                    {/* Error Message */}
                    {error && (
                        <div className="mt-6 p-4 bg-red-500/20 border border-red-500/50 rounded-lg">
                            <p className="text-red-400">❌ {error}</p>
                            <button
                                className="mt-2 text-sm text-gray-400 hover:text-white underline"
                                onClick={handleReset}
                            >
                                Thử lại
                            </button>
                        </div>
                    )}
                </div>

                {/* Tips */}
                <div className="mt-8 grid md:grid-cols-3 gap-4">
                    <TipCard
                        icon="🎯"
                        title="Chất lượng tốt hơn"
                        description="Video HD với âm thanh rõ ràng sẽ cho kết quả phân tích chính xác hơn"
                    />
                    <TipCard
                        icon="⏱️"
                        title="Thời lượng phù hợp"
                        description="Video từ 15 giây đến 3 phút sẽ được phân tích chi tiết nhất"
                    />
                    <TipCard
                        icon="🔒"
                        title="Bảo mật"
                        description="Video của bạn được xử lý an toàn và không được lưu trữ vĩnh viễn"
                    />
                </div>
            </main>
        </div>
    );
}

function TipCard({ icon, title, description }: { icon: string; title: string; description: string }) {
    return (
        <div className="bg-gray-800/30 rounded-lg p-4 border border-gray-700">
            <div className="text-2xl mb-2">{icon}</div>
            <h3 className="font-semibold mb-1">{title}</h3>
            <p className="text-sm text-gray-400">{description}</p>
        </div>
    );
}
