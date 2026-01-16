'use client';

import { useState, useEffect, useRef } from 'react';
import { useParams } from 'next/navigation';
import { getVideoAnalysis, VideoAnalysis, VideoAnalysisResponse } from '@/services/api';

export default function VideoAnalysisPage() {
    const params = useParams();
    const videoId = params.id as string;
    const videoRef = useRef<HTMLVideoElement>(null);

    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [status, setStatus] = useState<string>('pending');
    const [analysis, setAnalysis] = useState<VideoAnalysis | null>(null);
    const [selectedSegment, setSelectedSegment] = useState<number | null>(null);

    // Polling for analysis status
    useEffect(() => {
        let pollInterval: NodeJS.Timeout;

        const fetchAnalysis = async () => {
            try {
                const response: VideoAnalysisResponse = await getVideoAnalysis(videoId);
                setStatus(response.status);

                if (response.has_analysis && response.analysis) {
                    setAnalysis(response.analysis);
                    setLoading(false);
                    // Stop polling when analysis is complete
                    if (pollInterval) clearInterval(pollInterval);
                } else if (response.status === 'failed') {
                    setError(response.error || 'Phân tích thất bại');
                    setLoading(false);
                    if (pollInterval) clearInterval(pollInterval);
                } else if (response.status === 'processing') {
                    // Continue polling
                    setLoading(true);
                }
            } catch (err) {
                console.error('Error fetching analysis:', err);
                setError('Không thể tải dữ liệu phân tích');
                setLoading(false);
                if (pollInterval) clearInterval(pollInterval);
            }
        };

        // Initial fetch
        fetchAnalysis();

        // Poll every 3 seconds if still processing
        pollInterval = setInterval(fetchAnalysis, 3000);

        return () => {
            if (pollInterval) clearInterval(pollInterval);
        };
    }, [videoId]);

    // Seek video to segment time
    const handleSegmentClick = (segment: VideoAnalysis['script_breakdown'][0]) => {
        setSelectedSegment(segment.segment_id);

        if (videoRef.current && segment.start_seconds !== undefined) {
            videoRef.current.currentTime = segment.start_seconds;
            videoRef.current.play();
        }
    };

    if (loading) {
        return (
            <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 text-white flex items-center justify-center">
                <div className="text-center">
                    <div className="animate-spin text-5xl mb-4">⏳</div>
                    <h2 className="text-xl font-semibold mb-2">
                        {status === 'processing' ? 'Đang phân tích video...' : 'Đang tải...'}
                    </h2>
                    <p className="text-gray-400">
                        {status === 'processing'
                            ? 'AI đang phân tích nội dung video của bạn. Quá trình này có thể mất 1-2 phút.'
                            : 'Vui lòng đợi trong giây lát.'
                        }
                    </p>
                    <div className="mt-6 w-64 h-2 bg-gray-700 rounded-full overflow-hidden mx-auto">
                        <div className="h-full bg-blue-500 animate-pulse" style={{ width: '60%' }} />
                    </div>
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 text-white flex items-center justify-center">
                <div className="text-center">
                    <div className="text-5xl mb-4">❌</div>
                    <h2 className="text-xl font-semibold mb-2 text-red-400">Có lỗi xảy ra</h2>
                    <p className="text-gray-400 mb-4">{error}</p>
                    <a
                        href="/upload"
                        className="px-6 py-2 bg-blue-600 rounded-lg hover:bg-blue-700 transition"
                    >
                        Upload video khác
                    </a>
                </div>
            </div>
        );
    }

    if (!analysis) {
        return (
            <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 text-white flex items-center justify-center">
                <div className="text-center">
                    <div className="text-5xl mb-4">📭</div>
                    <h2 className="text-xl font-semibold mb-2">Chưa có dữ liệu phân tích</h2>
                    <a href="/upload" className="text-blue-400 hover:underline">
                        Upload và phân tích video mới
                    </a>
                </div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 text-white">
            {/* Header */}
            <header className="border-b border-gray-700 bg-gray-900/50 backdrop-blur-sm">
                <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
                    <a href="/" className="text-2xl font-bold bg-gradient-to-r from-blue-400 to-purple-500 bg-clip-text text-transparent">
                        🎬 Video Analysis AI
                    </a>
                    <nav className="flex gap-4">
                        <a href="/upload" className="text-gray-400 hover:text-white transition">📤 Upload</a>
                        <a href="/library" className="text-gray-400 hover:text-white transition">📚 Library</a>
                    </nav>
                </div>
            </header>

            <main className="max-w-7xl mx-auto px-6 py-8">
                {/* Top Section: Video + General Info */}
                <div className="grid lg:grid-cols-2 gap-8 mb-8">
                    {/* Video Player Placeholder */}
                    <div className="bg-gray-800 rounded-xl overflow-hidden aspect-video flex items-center justify-center">
                        <div className="text-center">
                            <div className="text-6xl mb-4">🎬</div>
                            <p className="text-gray-400">Video Player</p>
                            <p className="text-sm text-gray-500">Video ID: {videoId}</p>
                        </div>
                    </div>

                    {/* General Info Card */}
                    <div className="bg-gray-800/50 rounded-xl p-6 border border-gray-700">
                        <h2 className="text-2xl font-bold mb-4">{analysis.general_info.title}</h2>

                        <div className="grid grid-cols-2 gap-4 mb-6">
                            <InfoItem label="Category" value={analysis.general_info.category} />
                            <InfoItem label="Sentiment" value={analysis.general_info.overall_sentiment} />
                        </div>

                        <div className="mb-6">
                            <label className="text-sm text-gray-400">Target Audience</label>
                            <p className="mt-1">{analysis.general_info.target_audience}</p>
                        </div>

                        {/* Viral Score Gauge */}
                        <div className="bg-gray-700/50 rounded-lg p-4">
                            <div className="flex items-center justify-between mb-2">
                                <span className="font-semibold">🔥 Viral Score</span>
                                <span className="text-2xl font-bold text-yellow-400">
                                    {analysis.virality_factors.score}/10
                                </span>
                            </div>
                            <div className="h-3 bg-gray-600 rounded-full overflow-hidden">
                                <div
                                    className="h-full bg-gradient-to-r from-red-500 via-yellow-500 to-green-500 transition-all"
                                    style={{ width: `${analysis.virality_factors.score * 10}%` }}
                                />
                            </div>
                            <p className="text-sm text-gray-400 mt-2">
                                {analysis.virality_factors.reasons}
                            </p>
                        </div>
                    </div>
                </div>

                {/* Content Analysis */}
                <div className="grid md:grid-cols-3 gap-6 mb-8">
                    <AnalysisCard
                        icon="🎯"
                        title="Mục tiêu chính"
                        content={analysis.content_analysis.main_objective}
                    />
                    <AnalysisCard
                        icon="💬"
                        title="Thông điệp cốt lõi"
                        content={analysis.content_analysis.key_message}
                    />
                    <AnalysisCard
                        icon="🪝"
                        title="Hook Strategy"
                        content={analysis.content_analysis.hook_strategy}
                    />
                </div>

                {/* Script Breakdown */}
                <div className="bg-gray-800/50 rounded-xl border border-gray-700 mb-8">
                    <div className="p-4 border-b border-gray-700 flex items-center justify-between">
                        <h3 className="text-xl font-semibold">📝 Script Breakdown</h3>
                        <span className="text-sm text-gray-400">
                            {analysis.script_breakdown.length} segments
                        </span>
                    </div>

                    <div className="overflow-x-auto">
                        <table className="w-full">
                            <thead className="bg-gray-900/50">
                                <tr>
                                    <th className="px-4 py-3 text-left text-sm font-medium text-gray-400">Time</th>
                                    <th className="px-4 py-3 text-left text-sm font-medium text-gray-400">Visual</th>
                                    <th className="px-4 py-3 text-left text-sm font-medium text-gray-400">Camera</th>
                                    <th className="px-4 py-3 text-left text-sm font-medium text-gray-400">Audio</th>
                                    <th className="px-4 py-3 text-left text-sm font-medium text-gray-400">Text</th>
                                    <th className="px-4 py-3 text-left text-sm font-medium text-gray-400">Pacing</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-gray-700">
                                {analysis.script_breakdown.map((segment) => (
                                    <tr
                                        key={segment.segment_id}
                                        className={`hover:bg-gray-700/50 cursor-pointer transition ${selectedSegment === segment.segment_id ? 'bg-blue-900/30' : ''
                                            }`}
                                        onClick={() => handleSegmentClick(segment)}
                                    >
                                        <td className="px-4 py-3 text-sm whitespace-nowrap text-blue-400 font-mono">
                                            {segment.time_range}
                                        </td>
                                        <td className="px-4 py-3 text-sm max-w-xs truncate">
                                            {segment.visual_description}
                                        </td>
                                        <td className="px-4 py-3 text-sm whitespace-nowrap">
                                            <span className="px-2 py-1 bg-gray-700 rounded text-xs">
                                                {segment.camera_angle}
                                            </span>
                                        </td>
                                        <td className="px-4 py-3 text-sm max-w-xs truncate text-gray-400">
                                            {segment.audio_transcript || '-'}
                                        </td>
                                        <td className="px-4 py-3 text-sm max-w-xs truncate text-yellow-400">
                                            {segment.on_screen_text || '-'}
                                        </td>
                                        <td className="px-4 py-3 text-sm whitespace-nowrap">
                                            <PacingBadge pacing={segment.pacing} />
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>

                    <div className="p-3 bg-gray-900/30 text-center text-sm text-gray-500">
                        💡 Click vào dòng để xem chi tiết segment
                    </div>
                </div>

                {/* Technical Audit */}
                <div className="grid md:grid-cols-2 gap-6 mb-8">
                    <div className="bg-gray-800/50 rounded-xl p-6 border border-gray-700">
                        <h3 className="text-lg font-semibold mb-4">🎬 Technical Audit</h3>
                        <div className="space-y-3">
                            <TechItem label="Editing Style" value={analysis.technical_audit.editing_style} />
                            <TechItem label="Sound Design" value={analysis.technical_audit.sound_design} />
                            <TechItem label="CTA Analysis" value={analysis.technical_audit.cta_analysis} />
                            {analysis.technical_audit.video_quality && (
                                <TechItem label="Video Quality" value={analysis.technical_audit.video_quality} />
                            )}
                            {analysis.technical_audit.transitions && (
                                <TechItem label="Transitions" value={analysis.technical_audit.transitions} />
                            )}
                        </div>
                    </div>

                    <div className="bg-gray-800/50 rounded-xl p-6 border border-gray-700">
                        <h3 className="text-lg font-semibold mb-4">💡 Improvement Suggestions</h3>
                        <p className="text-gray-300 mb-4">
                            {analysis.virality_factors.improvement_suggestions}
                        </p>

                        {analysis.virality_factors.strengths && analysis.virality_factors.strengths.length > 0 && (
                            <div className="mb-3">
                                <span className="text-sm text-green-400 font-medium">✅ Điểm mạnh:</span>
                                <ul className="mt-1 space-y-1">
                                    {analysis.virality_factors.strengths.map((s, i) => (
                                        <li key={i} className="text-sm text-gray-400">• {s}</li>
                                    ))}
                                </ul>
                            </div>
                        )}

                        {analysis.virality_factors.weaknesses && analysis.virality_factors.weaknesses.length > 0 && (
                            <div>
                                <span className="text-sm text-red-400 font-medium">⚠️ Cần cải thiện:</span>
                                <ul className="mt-1 space-y-1">
                                    {analysis.virality_factors.weaknesses.map((w, i) => (
                                        <li key={i} className="text-sm text-gray-400">• {w}</li>
                                    ))}
                                </ul>
                            </div>
                        )}
                    </div>
                </div>

                {/* Actions */}
                <div className="flex justify-center gap-4">
                    <a
                        href="/upload"
                        className="px-6 py-3 bg-blue-600 rounded-lg font-medium hover:bg-blue-700 transition"
                    >
                        📤 Phân tích video khác
                    </a>
                    <a
                        href="/library"
                        className="px-6 py-3 bg-gray-700 rounded-lg font-medium hover:bg-gray-600 transition"
                    >
                        📚 Xem thư viện
                    </a>
                </div>
            </main>
        </div>
    );
}

// Helper Components
function InfoItem({ label, value }: { label: string; value: string }) {
    return (
        <div>
            <label className="text-sm text-gray-400">{label}</label>
            <p className="font-medium">{value}</p>
        </div>
    );
}

function AnalysisCard({ icon, title, content }: { icon: string; title: string; content: string }) {
    return (
        <div className="bg-gray-800/50 rounded-xl p-5 border border-gray-700">
            <div className="text-2xl mb-2">{icon}</div>
            <h4 className="font-semibold mb-2">{title}</h4>
            <p className="text-sm text-gray-400">{content}</p>
        </div>
    );
}

function TechItem({ label, value }: { label: string; value: string }) {
    return (
        <div className="flex justify-between">
            <span className="text-gray-400">{label}</span>
            <span className="text-right ml-4">{value}</span>
        </div>
    );
}

function PacingBadge({ pacing }: { pacing: string }) {
    const colors: Record<string, string> = {
        'Nhanh': 'bg-red-500/20 text-red-400',
        'Chậm': 'bg-blue-500/20 text-blue-400',
        'Dồn dập': 'bg-orange-500/20 text-orange-400',
        'Vừa phải': 'bg-green-500/20 text-green-400',
        'Tĩnh lặng': 'bg-gray-500/20 text-gray-400',
    };

    const colorClass = colors[pacing] || 'bg-gray-500/20 text-gray-400';

    return (
        <span className={`px-2 py-1 rounded text-xs ${colorClass}`}>
            {pacing}
        </span>
    );
}
