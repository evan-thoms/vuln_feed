"use client";
import React, { useState, useEffect } from 'react';
import { Search, Shield, AlertTriangle, Globe, Calendar, TrendingUp, Loader, CheckCircle, XCircle } from 'lucide-react';

const CyberSecurityApp = () => {
  const [searchParams, setSearchParams] = useState({
    content_type: 'both',
    severity: [],
    max_results: 10,
    days_back: 7,
    output_format: 'json',
    email_address: ''
  });
  
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [searchStatus, setSearchStatus] = useState(null);

  const handleSearch = async () => {
    setLoading(true);
    setError(null);
    setResults(null);
    
    try {
      const response = await fetch('http://localhost:8000/search', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(searchParams)
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      setResults(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleSeverityChange = (severity) => {
    setSearchParams(prev => ({
      ...prev,
      severity: prev.severity.includes(severity)
        ? prev.severity.filter(s => s !== severity)
        : [...prev.severity, severity]
    }));
  };

  const getSeverityColor = (severity) => {
    const colors = {
      'LOW': 'bg-green-100 text-green-800 border-green-200',
      'MEDIUM': 'bg-yellow-100 text-yellow-800 border-yellow-200',
      'HIGH': 'bg-orange-100 text-orange-800 border-orange-200',
      'CRITICAL': 'bg-red-100 text-red-800 border-red-200'
    };
    return colors[severity?.toUpperCase()] || 'bg-gray-100 text-gray-800 border-gray-200';
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      {/* Header */}
      <div className="bg-slate-800/80 backdrop-blur-sm border-b border-slate-700">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex items-center space-x-3">
            <Shield className="h-8 w-8 text-cyan-400" />
            <h1 className="text-3xl font-bold text-white">CyberIntel</h1>
            <span className="text-slate-400 text-sm">Threat Intelligence Platform</span>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Search Form */}
        <div className="bg-slate-800/50 backdrop-blur-sm rounded-2xl border border-slate-700 p-8 mb-8">
          <h2 className="text-2xl font-semibold text-white mb-6 flex items-center">
            <Search className="h-6 w-6 mr-2 text-cyan-400" />
            Intelligence Query
          </h2>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {/* Content Type */}
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">Content Type</label>
              <select
                value={searchParams.content_type}
                onChange={(e) => setSearchParams({...searchParams, content_type: e.target.value})}
                className="w-full px-4 py-3 bg-slate-700 border border-slate-600 rounded-lg text-white focus:ring-2 focus:ring-cyan-500 focus:border-transparent"
              >
                <option value="both">Both CVEs & News</option>
                <option value="cve">CVEs Only</option>
                <option value="news">News Only</option>
              </select>
            </div>

            {/* Max Results */}
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">Max Results</label>
              <input
                type="number"
                value={searchParams.max_results}
                onChange={(e) => setSearchParams({...searchParams, max_results: parseInt(e.target.value)})}
                className="w-full px-4 py-3 bg-slate-700 border border-slate-600 rounded-lg text-white focus:ring-2 focus:ring-cyan-500 focus:border-transparent"
                min="1"
                max="50"
              />
            </div>

            {/* Days Back */}
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">Days Back</label>
              <input
                type="number"
                value={searchParams.days_back}
                onChange={(e) => setSearchParams({...searchParams, days_back: parseInt(e.target.value)})}
                className="w-full px-4 py-3 bg-slate-700 border border-slate-600 rounded-lg text-white focus:ring-2 focus:ring-cyan-500 focus:border-transparent"
                min="1"
                max="30"
              />
            </div>
          </div>

          {/* Severity Filter */}
          <div className="mt-6">
            <label className="block text-sm font-medium text-slate-300 mb-3">Severity Filter</label>
            <div className="flex flex-wrap gap-2">
              {['low', 'medium', 'high', 'critical'].map(severity => (
                <button
                  key={severity}
                  onClick={() => handleSeverityChange(severity)}
                  className={`px-4 py-2 rounded-lg border transition-all ${
                    searchParams.severity.includes(severity)
                      ? 'bg-cyan-500 text-white border-cyan-500'
                      : 'bg-slate-700 text-slate-300 border-slate-600 hover:bg-slate-600'
                  }`}
                >
                  {severity.charAt(0).toUpperCase() + severity.slice(1)}
                </button>
              ))}
            </div>
          </div>

          {/* Search Button */}
          <div className="mt-8">
            <button
              onClick={handleSearch}
              disabled={loading}
              className="w-full md:w-auto px-8 py-4 bg-gradient-to-r from-cyan-500 to-blue-600 text-white font-semibold rounded-lg hover:from-cyan-600 hover:to-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all flex items-center justify-center"
            >
              {loading ? (
                <>
                  <Loader className="animate-spin h-5 w-5 mr-2" />
                  Processing Intelligence...
                </>
              ) : (
                <>
                  <Search className="h-5 w-5 mr-2" />
                  Search Intelligence
                </>
              )}
            </button>
          </div>
        </div>

        {/* Error Display */}
        {error && (
          <div className="bg-red-900/50 border border-red-700 rounded-lg p-4 mb-6">
            <div className="flex items-center">
              <XCircle className="h-5 w-5 text-red-400 mr-2" />
              <span className="text-red-300">Error: {error}</span>
            </div>
          </div>
        )}

        {/* Results */}
        {results && (
          <div className="space-y-6">
            {/* Stats */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="bg-slate-800/50 rounded-lg border border-slate-700 p-6">
                <div className="flex items-center">
                  <AlertTriangle className="h-8 w-8 text-red-400 mr-3" />
                  <div>
                    <p className="text-2xl font-bold text-white">{results.cves?.length || 0}</p>
                    <p className="text-slate-400">Vulnerabilities</p>
                  </div>
                </div>
              </div>
              
              <div className="bg-slate-800/50 rounded-lg border border-slate-700 p-6">
                <div className="flex items-center">
                  <Globe className="h-8 w-8 text-blue-400 mr-3" />
                  <div>
                    <p className="text-2xl font-bold text-white">{results.news?.length || 0}</p>
                    <p className="text-slate-400">News Items</p>
                  </div>
                </div>
              </div>
              
              <div className="bg-slate-800/50 rounded-lg border border-slate-700 p-6">
                <div className="flex items-center">
                  <TrendingUp className="h-8 w-8 text-green-400 mr-3" />
                  <div>
                    <p className="text-2xl font-bold text-white">{results.processing_time?.toFixed(1)}s</p>
                    <p className="text-slate-400">Processing Time</p>
                  </div>
                </div>
              </div>
            </div>

            {/* CVEs */}
            {results.cves && results.cves.length > 0 && (
              <div className="bg-slate-800/50 rounded-2xl border border-slate-700 p-6">
                <h3 className="text-xl font-semibold text-white mb-4 flex items-center">
                  <AlertTriangle className="h-6 w-6 text-red-400 mr-2" />
                  Vulnerabilities ({results.cves.length})
                </h3>
                
                <div className="space-y-4">
                  {results.cves.map((cve, index) => (
                    <div key={index} className="bg-slate-700/50 rounded-lg border border-slate-600 p-6">
                      <div className="flex items-start justify-between mb-3">
                        <div className="flex-1">
                          <h4 className="text-lg font-medium text-white mb-2">{cve.title_translated}</h4>
                          <div className="flex items-center space-x-3 text-sm text-slate-400 mb-2">
                            <span className="font-mono">{cve.cve_id}</span>
                            <span>•</span>
                            <span>CVSS: {cve.cvss_score}</span>
                            <span>•</span>
                            <span>Intrigue: {cve.intrigue}/10</span>
                          </div>
                        </div>
                        <span className={`px-3 py-1 rounded-full text-xs font-medium border ${getSeverityColor(cve.severity)}`}>
                          {cve.severity}
                        </span>
                      </div>
                      
                      <p className="text-slate-300 mb-4">{cve.summary}</p>
                      
                      <div className="flex items-center justify-between text-sm">
                        <div className="flex items-center text-slate-400">
                          <Calendar className="h-4 w-4 mr-1" />
                          {formatDate(cve.published_date)}
                          <span className="mx-2">•</span>
                          <Globe className="h-4 w-4 mr-1" />
                          {cve.source} ({cve.original_language})
                        </div>
                        <a 
                          href={cve.url} 
                          target="_blank" 
                          rel="noopener noreferrer"
                          className="text-cyan-400 hover:text-cyan-300 transition-colors"
                        >
                          View Source →
                        </a>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* News */}
            {results.news && results.news.length > 0 && (
              <div className="bg-slate-800/50 rounded-2xl border border-slate-700 p-6">
                <h3 className="text-xl font-semibold text-white mb-4 flex items-center">
                  <Globe className="h-6 w-6 text-blue-400 mr-2" />
                  News ({results.news.length})
                </h3>
                
                <div className="space-y-4">
                  {results.news.map((news, index) => (
                    <div key={index} className="bg-slate-700/50 rounded-lg border border-slate-600 p-6">
                      <div className="flex items-start justify-between mb-3">
                        <h4 className="text-lg font-medium text-white flex-1 mr-4">{news.title_translated}</h4>
                        <span className="text-cyan-400 text-sm font-medium">
                          Intrigue: {news.intrigue}/10
                        </span>
                      </div>
                      
                      <p className="text-slate-300 mb-4">{news.summary}</p>
                      
                      <div className="flex items-center justify-between text-sm">
                        <div className="flex items-center text-slate-400">
                          <Calendar className="h-4 w-4 mr-1" />
                          {formatDate(news.published_date)}
                          <span className="mx-2">•</span>
                          <Globe className="h-4 w-4 mr-1" />
                          {news.source} ({news.original_language})
                        </div>
                        <a 
                          href={news.url} 
                          target="_blank" 
                          rel="noopener noreferrer"
                          className="text-cyan-400 hover:text-cyan-300 transition-colors"
                        >
                          View Source →
                        </a>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default CyberSecurityApp;