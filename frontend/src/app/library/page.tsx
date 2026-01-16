'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { getVideos, searchVideos, SearchResult } from '@/services/api';

interface VideoItem {
    video_id: string;
    title: string;
    category?: string;
    viral_score?: number;
    key_message?: string;
    target_audience?: string;
    status?: string;
    analyzed_at?: string;
    created_at?: string;
}

export default function LibraryPage() {
    const router = useRouter();

    const [videos, setVideos] = useState<VideoItem[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [total, setTotal] = useState(0);

    // Search state
    const [searchQuery, setSearchQuery] = useState('');
    const [categoryFilter, setCategoryFilter] = useState('');
    const [minScore, setMinScore] = useState<number | null>(null);
    const [isSearching, setIsSearching] = useState(false);

    // Fetch videos
    const fetchVideos = useCallback(async () => {
        setLoading(true);
        setError(null);

        try {
            if (searchQuery.trim() || categoryFilter || minScore) {
                // Use search API
                setIsSearching(true);
                const response = await searchVideos(searchQuery || '*', {
                    category: categoryFilter || undefined,
                    minViralScore: minScore || undefined,
                    limit: 50
                });

                if (response.success) {
                    setVideos(response.results);
                    setTotal(response.total);
                }
            } else {
                // Use list API
                setIsSearching(false);
                const response = await getVideos(0, 50);

                if (response.success) {
                    // Transform list response to match search format
                    const items: VideoItem[] = response.videos.map((v: { video_id: string; title: string; status: string; created_at: string }) => ({
                        video_id: v.video_id,
                        title: v.title,
                        status: v.status,
                        created_at: v.created_at
                    }));
                    setVideos(items);
                    setTotal(response.total);
                }
            }
        } catch (err) {
            console.error('Error fetching videos:', err);
            setError('Không thể tải danh sách video');
        } finally {
            setLoading(false);
        }
    }, [searchQuery, categoryFilter, minScore]);

    // Initial fetch
    useEffect(() => {
        fetchVideos();
    }, [fetchVideos]);

    // Handle search
    const handleSearch = (e: React.FormEvent) => {
        e.preventDefault();
        fetchVideos();
    };

    // Clear filters
    const clearFilters = () => {
        setSearchQuery('');
        setCategoryFilter('');
        setMinScore(null);
    };

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
                        <span className="text-white font-medium">📚 Library</span>
                    </nav>
                </div>
            </header>

            <main className="max-w-7xl mx-auto px-6 py-8">
                {/* Page Title */}
                <div className="mb-8">
                    <h1 className="text-3xl font-bold mb-2">📚 Video Library</h1>
                    <p className="text-gray-400">Tất cả video đã phân tích</p>
                </div>

                {/* Search & Filters */}
                <form onSubmit={handleSearch} className="bg-gray-800/50 rounded-xl p-4 border border-gray-700 mb-8">
                    <div className="flex flex-wrap gap-4">
                        {/* Search Input */}
                        <div className="flex-1 min-w-[200px]">
                            <input
                                type="text"
                                placeholder="Tìm kiếm theo title, category, key message..."
                                className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg focus:outline-none focus:border-blue-500"
                                value={searchQuery}
                                onChange={(e) => setSearchQuery(e.target.value)}
                            />
                        </div>

                        {/* Category Filter */}
                        <select
                            className="px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg focus:outline-none focus:border-blue-500"
                            value={categoryFilter}
                            onChange={(e) => setCategoryFilter(e.target.value)}
                        >
                            <option value="">Tất cả Category</option>
                            <option value="Tutorial">Tutorial</option>
                            <option value="Vlog">Vlog</option>
                            <option value="Review">Review</option>
                            <option value="Entertainment">Entertainment</option>
                            <option value="Education">Education</option>
                            <option value="Comedy">Comedy</option>
                            <option value="Ads">Ads</option>
                        </select>

                        {/* Viral Score Filter */}
                        <select
                            className="px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg focus:outline-none focus:border-blue-500"
                            value={minScore || ''}
                            onChange={(e) => setMinScore(e.target.value ? parseInt(e.target.value) : null)}
                        >
                            <option value="">Viral Score</option>
                            <option value="8">8+ (Cao)</option>
                            <option value="6">6+ (Trung bình)</option>
                            <option value="4">4+ (Thấp)</option>
                        </select>

                        {/* Search Button */}
                        <button
                            type="submit"
                            className="px-6 py-2 bg-blue-600 rounded-lg font-medium hover:bg-blue-700 transition"
                        >
                            🔍 Tìm kiếm
                        </button>

                        {/* Clear Filters */}
                        {(searchQuery || categoryFilter || minScore) && (
                            <button
                                type="button"
                                onClick={clearFilters}
                                className="px-4 py-2 text-gray-400 hover:text-white transition"
                            >
                                ✕ Xóa filter
                            </button>
                        )}
                    </div>
                </form>

                {/* Results Count */}
                <div className="flex items-center justify-between mb-4">
                    <span className="text-gray-400">
                        {isSearching ? `Tìm thấy ${total} kết quả` : `Tổng ${total} video`}
                    </span>
                    <a
                        href="/upload"
                        className="text-blue-400 hover:underline"
                    >
                        + Upload video mới
                    </a>
                </div>

                {/* Loading State */}
                {loading && (
                    <div className="text-center py-12">
                        <div className="animate-spin text-4xl mb-4">⏳</div>
                        <p className="text-gray-400">Đang tải...</p>
                    </div>
                )}

                {/* Error State */}
                {error && (
                    <div className="text-center py-12">
                        <div className="text-4xl mb-4">❌</div>
                        <p className="text-red-400">{error}</p>
                        <button
                            onClick={fetchVideos}
                            className="mt-4 text-blue-400 hover:underline"
                        >
                            Thử lại
                        </button>
                    </div>
                )}

                {/* Empty State */}
                {!loading && !error && videos.length === 0 && (
                    <div className="text-center py-12 bg-gray-800/30 rounded-xl">
                        <div className="text-5xl mb-4">📭</div>
                        <h3 className="text-xl font-semibold mb-2">Chưa có video nào</h3>
                        <p className="text-gray-400 mb-4">
                            {isSearching
                                ? 'Không tìm thấy video phù hợp với bộ lọc'
                                : 'Bắt đầu upload video để phân tích'
                            }
                        </p>
                        <a
                            href="/upload"
                            className="inline-block px-6 py-2 bg-blue-600 rounded-lg font-medium hover:bg-blue-700 transition"
                        >
                            📤 Upload video đầu tiên
                        </a>
                    </div>
                )}

                {/* Video Grid */}
                {!loading && !error && videos.length > 0 && (
                    <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
                        {videos.map((video) => (
                            <VideoCard
                                key={video.video_id}
                                video={video}
                                onClick={() => router.push(`/videos/${video.video_id}`)}
                            />
                        ))}
                    </div>
                )}
            </main>
        </div>
    );
}

// Video Card Component
function VideoCard({ video, onClick }: { video: VideoItem; onClick: () => void }) {
    const statusColors: Record<string, string> = {
        'analyzed': 'bg-green-500/20 text-green-400',
        'processing': 'bg-yellow-500/20 text-yellow-400',
        'uploaded': 'bg-blue-500/20 text-blue-400',
        'pending': 'bg-gray-500/20 text-gray-400',
        'failed': 'bg-red-500/20 text-red-400',
    };

    const statusLabels: Record<string, string> = {
        'analyzed': '✅ Đã phân tích',
        'processing': '⏳ Đang xử lý',
        'uploaded': '📤 Đã upload',
        'pending': '⏳ Đang chờ',
        'failed': '❌ Thất bại',
    };

    return (
        <div
            className="bg-gray-800/50 rounded-xl border border-gray-700 overflow-hidden hover:border-gray-500 transition cursor-pointer group"
            onClick={onClick}
        >
            {/* Thumbnail Placeholder */}
            <div className="aspect-video bg-gray-700 flex items-center justify-center group-hover:bg-gray-600 transition">
                <span className="text-4xl">🎬</span>
            </div>

            {/* Content */}
            <div className="p-4">
                <h3 className="font-semibold mb-2 line-clamp-2 group-hover:text-blue-400 transition">
                    {video.title || `Video ${video.video_id}`}
                </h3>

                <div className="flex items-center gap-2 text-sm mb-3">
                    {video.category && (
                        <span className="px-2 py-0.5 bg-gray-700 rounded">
                            {video.category}
                        </span>
                    )}
                    {video.viral_score !== undefined && video.viral_score > 0 && (
                        <span className="px-2 py-0.5 bg-yellow-500/20 text-yellow-400 rounded">
                            🔥 {video.viral_score}/10
                        </span>
                    )}
                </div>

                {video.key_message && (
                    <p className="text-sm text-gray-400 line-clamp-2 mb-3">
                        {video.key_message}
                    </p>
                )}

                <div className="flex items-center justify-between text-xs">
                    <span className={`px-2 py-0.5 rounded ${statusColors[video.status || 'pending']}`}>
                        {statusLabels[video.status || 'pending']}
                    </span>
                    {video.analyzed_at && (
                        <span className="text-gray-500">
                            {new Date(video.analyzed_at).toLocaleDateString('vi-VN')}
                        </span>
                    )}
                </div>
            </div>
        </div>
    );
}
