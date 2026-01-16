'use client';

import { useState, useEffect } from 'react';
import { healthCheck, dbStats } from '@/services/api';

interface HealthStatus {
  status: string;
  timestamp: string;
  version: string;
}

interface DbStatsData {
  status: string;
  collection: string;
  counts: {
    total: number;
    pending: number;
    completed: number;
    failed: number;
  };
  indexes: string[];
}

export default function Home() {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [dbStatsData, setDbStatsData] = useState<DbStatsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);

        // Call health check
        const healthData = await healthCheck();
        setHealth(healthData);

        // Call db stats
        const statsData = await dbStats();
        setDbStatsData(statsData);

        setError(null);
      } catch (err) {
        console.error('API Error:', err);
        setError('Failed to connect to backend. Make sure the server is running.');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 text-white">
      {/* Header */}
      <header className="border-b border-gray-700 bg-gray-900/50 backdrop-blur-sm">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          <h1 className="text-2xl font-bold bg-gradient-to-r from-blue-400 to-purple-500 bg-clip-text text-transparent">
            🎬 Video Analysis AI
          </h1>
          <span className="text-sm text-gray-400">
            Powered by Gemini API
          </span>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-6xl mx-auto px-6 py-12">
        {/* Hero Section */}
        <div className="text-center mb-12">
          <h2 className="text-4xl font-bold mb-4">
            AI-Powered Video Content Analysis
          </h2>
          <p className="text-xl text-gray-400 max-w-2xl mx-auto">
            Upload TikTok videos and get detailed AI analysis including script breakdown,
            camera angles, audio transcripts, and viral potential scoring.
          </p>
        </div>

        {/* Status Cards */}
        <div className="grid md:grid-cols-2 gap-6 mb-12">
          {/* API Status Card */}
          <div className="bg-gray-800/50 rounded-xl p-6 border border-gray-700">
            <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <span className="text-2xl">🔌</span> Backend Status
            </h3>

            {loading ? (
              <div className="animate-pulse space-y-3">
                <div className="h-4 bg-gray-700 rounded w-3/4"></div>
                <div className="h-4 bg-gray-700 rounded w-1/2"></div>
              </div>
            ) : error ? (
              <div className="text-red-400 flex items-center gap-2">
                <span className="text-xl">❌</span>
                <span>{error}</span>
              </div>
            ) : health ? (
              <div className="space-y-3">
                <div className="flex items-center gap-2">
                  <span className="w-3 h-3 bg-green-500 rounded-full animate-pulse"></span>
                  <span className="text-green-400 font-medium">Connected</span>
                </div>
                <div className="text-sm text-gray-400 space-y-1">
                  <p>Status: <span className="text-white">{health.status}</span></p>
                  <p>Version: <span className="text-white">{health.version}</span></p>
                  <p>Timestamp: <span className="text-white">{health.timestamp}</span></p>
                </div>
              </div>
            ) : null}
          </div>

          {/* Database Status Card */}
          <div className="bg-gray-800/50 rounded-xl p-6 border border-gray-700">
            <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <span className="text-2xl">🗄️</span> Database Status
            </h3>

            {loading ? (
              <div className="animate-pulse space-y-3">
                <div className="h-4 bg-gray-700 rounded w-3/4"></div>
                <div className="h-4 bg-gray-700 rounded w-1/2"></div>
              </div>
            ) : error ? (
              <div className="text-gray-500">-</div>
            ) : dbStatsData ? (
              <div className="space-y-3">
                <div className="flex items-center gap-2">
                  <span className="w-3 h-3 bg-green-500 rounded-full"></span>
                  <span className="text-green-400 font-medium">MongoDB Connected</span>
                </div>
                <div className="text-sm text-gray-400 space-y-1">
                  <p>Collection: <span className="text-white">{dbStatsData.collection}</span></p>
                  <p>Total Videos: <span className="text-white">{dbStatsData.counts?.total || 0}</span></p>
                  <p>Indexes: <span className="text-white">{dbStatsData.indexes?.length || 0}</span></p>
                </div>
              </div>
            ) : null}
          </div>
        </div>

        {/* Coming Soon Features */}
        <div className="bg-gray-800/30 rounded-xl p-8 border border-gray-700">
          <h3 className="text-xl font-semibold mb-6 text-center">🚀 Coming Soon</h3>
          <div className="grid md:grid-cols-3 gap-6">
            <FeatureCard
              icon="📤"
              title="Upload Video"
              description="Upload MP4 files or paste TikTok links"
            />
            <FeatureCard
              icon="🤖"
              title="AI Analysis"
              description="Gemini-powered script and visual analysis"
            />
            <FeatureCard
              icon="📊"
              title="Viral Score"
              description="Predict viral potential (1-10)"
            />
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-gray-800 mt-12">
        <div className="max-w-6xl mx-auto px-6 py-6 text-center text-gray-500 text-sm">
          Video Analysis AI • Built with Next.js + FastAPI + Gemini
        </div>
      </footer>
    </div>
  );
}

function FeatureCard({ icon, title, description }: { icon: string; title: string; description: string }) {
  return (
    <div className="text-center p-4">
      <div className="text-4xl mb-3">{icon}</div>
      <h4 className="font-semibold mb-2">{title}</h4>
      <p className="text-sm text-gray-400">{description}</p>
    </div>
  );
}
