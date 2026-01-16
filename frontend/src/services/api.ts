/**
 * API Service - Centralized API configuration
 */
import axios from 'axios';

// Get API URL from environment or use default
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Create axios instance with default config
export const api = axios.create({
    baseURL: API_BASE_URL,
    timeout: 300000, // 5 minutes for video uploads
    headers: {
        'Content-Type': 'application/json',
    },
});

// Request interceptor for logging
api.interceptors.request.use(
    (config) => {
        console.log(`[API] ${config.method?.toUpperCase()} ${config.url}`);
        return config;
    },
    (error) => {
        console.error('[API] Request error:', error);
        return Promise.reject(error);
    }
);

// Response interceptor for error handling
api.interceptors.response.use(
    (response) => response,
    (error) => {
        console.error('[API] Response error:', error.response?.data || error.message);
        return Promise.reject(error);
    }
);

// ============================================================
// HEALTH & DB FUNCTIONS
// ============================================================

export const healthCheck = async () => {
    const response = await api.get('/health');
    return response.data;
};

export const dbTest = async () => {
    const response = await api.get('/db/test');
    return response.data;
};

export const dbStats = async () => {
    const response = await api.get('/db/stats');
    return response.data;
};

// ============================================================
// VIDEO UPLOAD FUNCTIONS
// ============================================================

export const uploadVideo = async (
    file: File,
    onProgress?: (progress: number) => void
) => {
    const formData = new FormData();
    formData.append('file', file);

    const response = await api.post('/videos/upload', formData, {
        headers: {
            'Content-Type': 'multipart/form-data',
        },
        onUploadProgress: (progressEvent) => {
            if (progressEvent.total && onProgress) {
                const progress = Math.round((progressEvent.loaded / progressEvent.total) * 100);
                onProgress(progress);
            }
        },
    });
    return response.data;
};

export const downloadFromUrl = async (url: string) => {
    const response = await api.post('/videos/url', { url });
    return response.data;
};

export const getUploadInfo = async () => {
    const response = await api.get('/videos/config/upload-info');
    return response.data;
};

// ============================================================
// VIDEO LIST & DETAILS
// ============================================================

export const getVideos = async (skip: number = 0, limit: number = 20) => {
    const response = await api.get('/videos/', { params: { skip, limit } });
    return response.data;
};

export const getVideo = async (videoId: string) => {
    const response = await api.get(`/videos/${videoId}`);
    return response.data;
};

// ============================================================
// VIDEO ANALYSIS FUNCTIONS
// ============================================================

export const analyzeVideo = async (videoId: string) => {
    const response = await api.post(`/videos/${videoId}/analyze`);
    return response.data;
};

export const getVideoAnalysis = async (videoId: string) => {
    const response = await api.get(`/videos/${videoId}/analysis`);
    return response.data;
};

export const searchVideos = async (
    query: string,
    options?: {
        category?: string;
        minViralScore?: number;
        skip?: number;
        limit?: number;
    }
) => {
    const response = await api.get('/videos/search/query', {
        params: {
            q: query,
            category: options?.category,
            min_viral_score: options?.minViralScore,
            skip: options?.skip || 0,
            limit: options?.limit || 20,
        },
    });
    return response.data;
};

// ============================================================
// TYPES
// ============================================================

export interface VideoUploadResponse {
    success: boolean;
    message: string;
    video_id?: string;
    path?: string;
    filename?: string;
    size_mb?: number;
    source?: string;
    platform?: string;
}

export interface VideoAnalysis {
    general_info: {
        title: string;
        category: string;
        overall_sentiment: string;
        target_audience: string;
    };
    content_analysis: {
        main_objective: string;
        key_message: string;
        hook_strategy: string;
    };
    script_breakdown: Array<{
        segment_id: number;
        time_range: string;
        start_seconds?: number;
        end_seconds?: number;
        visual_description: string;
        camera_angle: string;
        audio_transcript: string;
        on_screen_text: string;
        pacing: string;
    }>;
    technical_audit: {
        editing_style: string;
        sound_design: string;
        cta_analysis: string;
        video_quality?: string;
        transitions?: string;
    };
    virality_factors: {
        score: number;
        reasons: string;
        improvement_suggestions: string;
        strengths?: string[];
        weaknesses?: string[];
    };
}

export interface VideoAnalysisResponse {
    success: boolean;
    video_id: string;
    status: string;
    has_analysis: boolean;
    analysis?: VideoAnalysis;
    analyzed_at?: string;
    processing_time_ms?: number;
    error?: string;
}

export interface SearchResult {
    video_id: string;
    title: string;
    category: string;
    viral_score: number;
    key_message: string;
    target_audience: string;
    analyzed_at: string;
}

export interface SearchResponse {
    success: boolean;
    query: string;
    total: number;
    skip: number;
    limit: number;
    results: SearchResult[];
}

export default api;

