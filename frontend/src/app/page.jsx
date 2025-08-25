"use client";
import React, { useState, useEffect, useRef } from 'react';
import { Search, Shield, AlertTriangle, Globe, Calendar, TrendingUp, Loader, CheckCircle, XCircle, AlertCircle} from 'lucide-react';

const CyberSecurityApp = () => {
  // Get API URL from environment variable or use localhost for development
  const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
  const WS_BASE_URL = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000';
  
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
  const [validationErrors, setValidationErrors] = useState([]);
  const [showValidationErrors, setShowValidationErrors] = useState(false);
  const [currentStatus, setCurrentStatus] = useState('');
  const [progress, setProgress] = useState(0);
  
  const wsRef = useRef(null);

  // WebSocket connection for real-time progress updates
  useEffect(() => {
    const connectWebSocket = () => {
      const ws = new WebSocket(`${WS_BASE_URL}/ws`);
      
      ws.onopen = () => {
        console.log('WebSocket connected');
      };
      
      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'progress') {
            setCurrentStatus(data.status);
            setProgress(data.progress);
          } else if (data.type === 'error') {
            setError(data.status);
            setLoading(false);
          }
        } catch (e) {
          console.log('WebSocket message:', event.data);
        }
      };
      
      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
      };
      
      ws.onclose = () => {
        console.log('WebSocket disconnected');
        // Reconnect after 5 seconds
        setTimeout(connectWebSocket, 5000);
      };
      
      wsRef.current = ws;
    };
    
    connectWebSocket();
    
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [WS_BASE_URL]);

  const validateForm = () => {
    const errors = [];
    
    if (searchParams.severity.length === 0) {
      errors.push("Please select at least one severity level");
    }
    
    if (searchParams.max_results > 30) {
      errors.push("Maximum results cannot exceed 30");
    }
    
    if (searchParams.max_results < 1) {
      errors.push("Maximum results must be at least 1");
    }
    
    if (searchParams.days_back < 1) {
      errors.push("Days back must be at least 1");
    }
    
    setValidationErrors(errors);
    return errors.length === 0;
  };

  useEffect(() => {
    if (showValidationErrors) {
      const isValid = validateForm();
      if (isValid) {
        setShowValidationErrors(false);
      }
    }
  }, [searchParams.severity, searchParams.max_results, searchParams.days_back, showValidationErrors]);

  const handleSearch = async () => {
    const isValid = validateForm();

    if (!isValid) {
      setShowValidationErrors(true);
      return;
    }
    
    setLoading(true);
    setError(null);
    setResults(null);
    setShowValidationErrors(false);
    setProgress(0);
    setCurrentStatus('Starting intelligence gathering...');
    
    try {
      const response = await fetch(`${API_BASE_URL}/search`, {
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
      setCurrentStatus('Complete!');
      setProgress(100);
    } catch (err) {
      setError(err.message);
      setCurrentStatus('');
      setProgress(0);
    } finally {
      setLoading(false);
      setTimeout(() => {
        setCurrentStatus('');
        setProgress(0);
      }, 3000);
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

  const formatTimeAgo = (isoString) => {
    if (!isoString) return 'Unknown';
    const date = new Date(isoString);
    const now = new Date();
    const diffMs = now - date;
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    const diffDays = Math.floor(diffHours / 24);
    
    if (diffDays > 0) {
      return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`;
    } else if (diffHours > 0) {
      return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
    } else {
      return 'Less than an hour ago';
    }
  };

  const getFreshnessColor = (isoString) => {
    if (!isoString) return 'text-slate-400';
    const date = new Date(isoString);
    const now = new Date();
    const diffHours = (now - date) / (1000 * 60 * 60);
    
    if (diffHours < 1) return 'text-green-400';
    if (diffHours < 24) return 'text-yellow-400';
    return 'text-red-400';
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      {/* Header */}
      <div className="bg-slate-800/80 backdrop-blur-sm border-b border-slate-700">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex items-center space-x-3">
            <Shield className="h-8 w-8 text-cyan-400" />
            <h1 className="text-3xl font-bold text-white">Sentinel</h1>
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
          {/* Validation Errors */}
          {showValidationErrors && validationErrors.length > 0 && (
            <div className="mb-6 bg-red-900/30 border border-red-700 rounded-lg p-4">
              <div className="flex items-center mb-2">
                <AlertCircle className="h-5 w-5 text-red-400 mr-2" />
                <span className="text-red-300 font-medium">Please fix the following issues:</span>
              </div>
              <ul className="list-disc list-inside space-y-1">
                {validationErrors.map((error, index) => (
                  <li key={index} className="text-red-300 text-sm">{error}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Current Status with Progress Bar */}
          {loading && currentStatus && (
            <div className="mb-6 bg-blue-900/30 border border-blue-700 rounded-lg p-4">
              <div className="flex items-center mb-3">
                <Loader className="animate-spin h-5 w-5 text-blue-400 mr-2" />
                <span className="text-blue-300 font-medium">{currentStatus}</span>
              </div>
              <div className="w-full bg-slate-700 rounded-full h-2">
                <div 
                  className="bg-gradient-to-r from-cyan-400 to-blue-500 h-2 rounded-full transition-all duration-500 ease-out"
                  style={{ width: `${progress}%` }}
                ></div>
              </div>
              <div className="flex justify-between text-xs text-slate-400 mt-1">
                <span>Progress</span>
                <span>{progress}%</span>
              </div>
            </div>
          )}
          
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
              <label className="block text-sm font-medium text-slate-300 mb-2">
                Max Results 
                <span className="text-xs text-slate-400 ml-1">(1-30)</span>
              </label>
              <input
                type="number"
                value={searchParams.max_results}
                onChange={(e) => setSearchParams({...searchParams, max_results: parseInt(e.target.value) || 1})}
                className="w-full px-4 py-3 bg-slate-700 border border-slate-600 rounded-lg text-white focus:ring-2 focus:ring-cyan-500 focus:border-transparent"
                min="1"
                max="30"
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
            <label className="block text-sm font-medium text-slate-300 mb-3">
              Severity Filter 
              <span className="text-red-400 ml-1">*</span>
              <span className="text-xs text-slate-400 ml-1">(select at least one)</span>
            </label>
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
            {searchParams.severity.length === 0 && showValidationErrors && (
              <p className="text-red-400 text-sm mt-2">Please select at least one severity level</p>
            )}
          </div>

         {/* Search Button */}
         <div className="mt-8">
            <button
              onClick={handleSearch}
              disabled={loading}
              className={`w-full md:w-auto px-8 py-4 font-semibold rounded-lg transition-all flex items-center justify-center ${
                loading
                  ? 'bg-gray-600 text-gray-300 cursor-not-allowed'
                  : 'bg-gradient-to-r from-cyan-500 to-blue-600 text-white hover:from-cyan-600 hover:to-blue-700'
              }`}
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

            {/* Freshness Indicator */}
            {results.freshness && (
              <div className="bg-slate-800/30 backdrop-blur-sm rounded-lg border border-slate-600 p-4 mb-6">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-4">
                    <div className="flex items-center text-slate-300">
                      <Calendar className="h-5 w-5 mr-2 text-cyan-400" />
                      <span className="text-sm">
                        Last updated: 
                        <span className={`ml-1 font-medium ${getFreshnessColor(results.freshness.last_update)}`}>
                          {formatTimeAgo(results.freshness.last_update)}
                        </span>
                      </span>
                    </div>
                    {results.freshness.total_articles > 0 && (
                      <div className="text-slate-400 text-sm">
                        {results.freshness.total_articles} total articles in database
                      </div>
                    )}
                  </div>
                  <div className="text-slate-400 text-xs">
                    Results may be the same because we show the highest-priority vulnerabilities
                  </div>
                </div>
              </div>
            )}

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
                            <span>•</span>
                            <span className={`${getFreshnessColor(cve.published_date)}`}>
                              {formatTimeAgo(cve.published_date)}
                            </span>
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
                        <div className="flex items-center space-x-2">
                          <span className="text-cyan-400 text-sm font-medium">
                            Intrigue: {news.intrigue}/10
                          </span>
                          <span className={`text-sm ${getFreshnessColor(news.published_date)}`}>
                            {formatTimeAgo(news.published_date)}
                          </span>
                        </div>
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