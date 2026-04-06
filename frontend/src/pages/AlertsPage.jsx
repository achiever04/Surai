import React, { useState, useEffect, useCallback } from 'react';
import { alertsAPI, detectionAPI } from '../services/api';
import {
    AlertTriangle, Shield, Crosshair, UserCheck, Eye, Frown, User,
    Clock, Camera, Filter, X, ChevronDown, Activity, Swords, Search
} from 'lucide-react';
import LoadingSpinner from '../components/common/LoadingSpinner';
import { useWebSocket } from '../hooks/useWebSocket';
import { formatTimestamp } from '../utils/formatTime';

// ── Constants ────────────────────────────────────────────────────────
const SEVERITY_CONFIG = {
    critical: {
        label: 'Critical',
        color: 'bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-300 border-red-200 dark:border-red-800',
        dot: 'bg-red-500',
        cardBg: 'bg-gradient-to-br from-red-500 to-red-600',
        ring: 'ring-red-400/30',
    },
    high: {
        label: 'High',
        color: 'bg-orange-100 dark:bg-orange-900/30 text-orange-800 dark:text-orange-300 border-orange-200 dark:border-orange-800',
        dot: 'bg-orange-500',
        cardBg: 'bg-gradient-to-br from-orange-500 to-orange-600',
        ring: 'ring-orange-400/30',
    },
    medium: {
        label: 'Medium',
        color: 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-800 dark:text-yellow-300 border-yellow-200 dark:border-yellow-800',
        dot: 'bg-yellow-500',
        cardBg: 'bg-gradient-to-br from-yellow-500 to-amber-600',
        ring: 'ring-yellow-400/30',
    },
    low: {
        label: 'Low',
        color: 'bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-300 border-green-200 dark:border-green-800',
        dot: 'bg-green-500',
        cardBg: 'bg-gradient-to-br from-emerald-500 to-green-600',
        ring: 'ring-green-400/30',
    },
};

const TYPE_CONFIG = {
    weapon_detected: { label: 'Weapon Detected', icon: Crosshair, accent: 'text-red-600' },
    watchlist_match: { label: 'Watchlist Match', icon: UserCheck, accent: 'text-red-600' },
    suspicious_object: { label: 'Suspicious Object', icon: Search, accent: 'text-orange-600' },
    spoof_attempt: { label: 'Spoof Attempt', icon: Shield, accent: 'text-orange-600' },
    aggressive_pose: { label: 'Aggressive Pose', icon: Swords, accent: 'text-orange-600' },
    emotion_alert: { label: 'Emotion Alert', icon: Frown, accent: 'text-yellow-600' },
    face_detection: { label: 'Face Detected', icon: User, accent: 'text-blue-600' },
};

// ── Component ────────────────────────────────────────────────────────
const AlertsPage = () => {
    const [alerts, setAlerts] = useState([]);
    const [summary, setSummary] = useState(null);
    const [isLoading, setIsLoading] = useState(true);
    const [selectedAlert, setSelectedAlert] = useState(null);
    const [severityFilter, setSeverityFilter] = useState('all');
    const [typeFilter, setTypeFilter] = useState('all');
    const [hoursFilter, setHoursFilter] = useState(24);

    // ── Data loading ──
    const loadAlerts = useCallback(async () => {
        try {
            const params = { hours: hoursFilter, limit: 300 };
            if (severityFilter !== 'all') params.severity = severityFilter;
            if (typeFilter !== 'all') params.detection_type = typeFilter;

            const [alertsRes, summaryRes] = await Promise.all([
                alertsAPI.getAll(params),
                alertsAPI.getSummary({ hours: hoursFilter }),
            ]);

            setAlerts(alertsRes.data || []);
            setSummary(summaryRes.data || null);
        } catch (err) {
            console.error('Failed to load alerts:', err);
        } finally {
            setIsLoading(false);
        }
    }, [hoursFilter, severityFilter, typeFilter]);

    useEffect(() => { loadAlerts(); }, [loadAlerts]);

    // Real-time updates
    useWebSocket('new_detection', () => { loadAlerts(); });
    useWebSocket('detection_deleted', () => { loadAlerts(); });

    // ── Alert detail ──
    const handleViewAlert = async (alert) => {
        try {
            const res = await detectionAPI.getById(alert.id);
            setSelectedAlert({ ...alert, ...res.data });
        } catch {
            setSelectedAlert(alert);
        }
    };

    // ── Helpers ──
    const getTypeInfo = (type) => TYPE_CONFIG[type] || { label: type?.replace(/_/g, ' ') || 'Unknown', icon: AlertTriangle, accent: 'text-gray-600' };
    const getSeverityInfo = (sev) => SEVERITY_CONFIG[sev] || SEVERITY_CONFIG.low;
    const uniqueTypes = [...new Set(alerts.map(a => a.detection_type))];

    // ── Loading ──
    if (isLoading) return <LoadingSpinner />;

    return (
        <div className="space-y-6">
            {/* ── Page Title ── */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-2xl font-bold text-gray-800 flex items-center gap-2">
                        <AlertTriangle className="w-7 h-7 text-red-500" />
                        Alerts Center
                    </h1>
                    <p className="text-sm text-gray-500 mt-1">
                        Real-time security alerts sorted by priority
                    </p>
                </div>
                <div className="flex items-center gap-2 text-sm text-gray-500">
                    <Activity className="w-4 h-4 text-green-500 animate-pulse" />
                    Live — last {hoursFilter}h
                </div>
            </div>

            {/* ── Summary Cards ── */}
            {summary && (
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    {['critical', 'high', 'medium', 'low'].map((sev) => {
                        const cfg = SEVERITY_CONFIG[sev];
                        const count = summary.by_severity?.[sev] || 0;
                        return (
                            <button
                                key={sev}
                                onClick={() => setSeverityFilter(severityFilter === sev ? 'all' : sev)}
                                className={`relative overflow-hidden rounded-xl p-5 text-white shadow-lg transition-all duration-200 ${cfg.cardBg} ${severityFilter === sev ? `ring-4 ${cfg.ring} scale-[1.03]` : 'hover:scale-[1.02]'
                                    }`}
                            >
                                <div className="relative z-10">
                                    <p className="text-sm font-medium opacity-90 uppercase tracking-wide">{cfg.label}</p>
                                    <p className="text-3xl font-extrabold mt-1">{count}</p>
                                </div>
                                {/* background decoration */}
                                <div className="absolute -top-4 -right-4 w-20 h-20 rounded-full bg-white/10" />
                            </button>
                        );
                    })}
                </div>
            )}

            {/* ── Filters ── */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 flex flex-wrap items-center gap-4">
                <div className="flex items-center gap-2 text-sm font-medium text-gray-700">
                    <Filter className="w-4 h-4" />
                    Filters
                </div>

                {/* Severity */}
                <div className="relative">
                    <select
                        value={severityFilter}
                        onChange={(e) => setSeverityFilter(e.target.value)}
                        className="appearance-none bg-gray-50 border border-gray-200 rounded-lg px-3 py-2 pr-8 text-sm focus:ring-2 focus:ring-blue-500 outline-none"
                    >
                        <option value="all">All Severities</option>
                        <option value="critical">🔴 Critical</option>
                        <option value="high">🟠 High</option>
                        <option value="medium">🟡 Medium</option>
                        <option value="low">🟢 Low</option>
                    </select>
                    <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none" />
                </div>

                {/* Type */}
                <div className="relative">
                    <select
                        value={typeFilter}
                        onChange={(e) => setTypeFilter(e.target.value)}
                        className="appearance-none bg-gray-50 border border-gray-200 rounded-lg px-3 py-2 pr-8 text-sm focus:ring-2 focus:ring-blue-500 outline-none"
                    >
                        <option value="all">All Types</option>
                        {Object.entries(TYPE_CONFIG).map(([key, cfg]) => (
                            <option key={key} value={key}>{cfg.label}</option>
                        ))}
                    </select>
                    <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none" />
                </div>

                {/* Time window */}
                <div className="relative">
                    <select
                        value={hoursFilter}
                        onChange={(e) => { setHoursFilter(Number(e.target.value)); setIsLoading(true); }}
                        className="appearance-none bg-gray-50 border border-gray-200 rounded-lg px-3 py-2 pr-8 text-sm focus:ring-2 focus:ring-blue-500 outline-none"
                    >
                        <option value={1}>Last 1 hour</option>
                        <option value={6}>Last 6 hours</option>
                        <option value={24}>Last 24 hours</option>
                        <option value={72}>Last 3 days</option>
                        <option value={168}>Last 7 days</option>
                    </select>
                    <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none" />
                </div>

                {(severityFilter !== 'all' || typeFilter !== 'all') && (
                    <button
                        onClick={() => { setSeverityFilter('all'); setTypeFilter('all'); }}
                        className="text-xs text-blue-600 hover:text-blue-800 flex items-center gap-1"
                    >
                        <X className="w-3 h-3" /> Clear filters
                    </button>
                )}
            </div>

            {/* ── Alert List ── */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
                <div className="px-5 py-3 border-b border-gray-100 bg-gray-50 flex items-center justify-between">
                    <h2 className="text-sm font-semibold text-gray-700">
                        {alerts.length} Alert{alerts.length !== 1 ? 's' : ''}
                    </h2>
                </div>

                <div className="divide-y divide-gray-100 max-h-[600px] overflow-y-auto">
                    {alerts.length > 0 ? (
                        alerts.map((alert) => {
                            const typeInfo = getTypeInfo(alert.detection_type);
                            const sevInfo = getSeverityInfo(alert.severity);
                            const TypeIcon = typeInfo.icon;

                            return (
                                <div
                                    key={alert.id}
                                    onClick={() => handleViewAlert(alert)}
                                    className="flex items-center gap-4 px-5 py-4 hover:bg-gray-50 dark:hover:bg-gray-700 cursor-pointer transition-colors group"
                                >
                                    {/* Severity dot */}
                                    <div className="flex-shrink-0">
                                        <div className={`w-3 h-3 rounded-full ${sevInfo.dot} ring-4 ring-opacity-20 ${sevInfo.dot.replace('bg-', 'ring-')}`} />
                                    </div>

                                    {/* Icon */}
                                    <div className={`flex-shrink-0 p-2.5 rounded-xl ${sevInfo.color} border`}>
                                        <TypeIcon className="w-5 h-5" />
                                    </div>

                                    {/* Content */}
                                    <div className="flex-1 min-w-0">
                                        <div className="flex items-center gap-2">
                                            <span className="text-sm font-semibold text-gray-900">{typeInfo.label}</span>
                                            <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider ${sevInfo.color} border`}>
                                                {sevInfo.label}
                                            </span>
                                            {alert.is_verified && (
                                                <span className="inline-flex items-center px-1.5 py-0.5 rounded-full text-[10px] font-semibold bg-green-100 text-green-700 border border-green-200">
                                                    Verified
                                                </span>
                                            )}
                                        </div>
                                        <div className="flex items-center gap-4 mt-1 text-xs text-gray-500">
                                            <span className="flex items-center gap-1">
                                                <Camera className="w-3 h-3" />
                                                Camera {alert.camera_id}
                                            </span>
                                            <span className="flex items-center gap-1">
                                                <Clock className="w-3 h-3" />
                                                {formatTimestamp(alert.timestamp)}
                                            </span>
                                            <span>
                                                Confidence: <strong className="text-gray-700">{(alert.confidence * 100).toFixed(1)}%</strong>
                                            </span>
                                            {alert.matched_person_id && (
                                                <span className="flex items-center gap-1 text-red-600 font-medium">
                                                    <UserCheck className="w-3 h-3" />
                                                    Person #{alert.matched_person_id}
                                                </span>
                                            )}
                                            {alert.emotion && alert.detection_type === 'emotion_alert' && (
                                                <span className="capitalize text-purple-600 font-medium">{alert.emotion}</span>
                                            )}
                                        </div>
                                    </div>

                                    {/* Arrow */}
                                    <Eye className="w-4 h-4 text-gray-300 group-hover:text-blue-500 transition-colors flex-shrink-0" />
                                </div>
                            );
                        })
                    ) : (
                        <div className="py-16 text-center">
                            <Shield className="w-12 h-12 mx-auto text-gray-300 mb-3" />
                            <p className="text-gray-500 font-medium">No alerts found</p>
                            <p className="text-xs text-gray-400 mt-1">Adjust filters or time window to see more alerts</p>
                        </div>
                    )}
                </div>
            </div>

            {/* ── Detail Modal ── */}
            {selectedAlert && (
                <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4" onClick={() => setSelectedAlert(null)}>
                    <div
                        className="bg-white dark:bg-gray-800 rounded-2xl shadow-2xl w-full max-w-lg max-h-[85vh] overflow-y-auto"
                        onClick={(e) => e.stopPropagation()}
                    >
                        {/* Modal Header */}
                        <div className={`px-6 py-4 rounded-t-2xl text-white ${getSeverityInfo(selectedAlert.severity).cardBg}`}>
                            <div className="flex items-center justify-between">
                                <div className="flex items-center gap-3">
                                    {React.createElement(getTypeInfo(selectedAlert.detection_type).icon, { className: 'w-6 h-6' })}
                                    <div>
                                        <h3 className="text-lg font-bold">{getTypeInfo(selectedAlert.detection_type).label}</h3>
                                        <p className="text-sm opacity-80">{selectedAlert.event_id}</p>
                                    </div>
                                </div>
                                <button onClick={() => setSelectedAlert(null)} className="p-1 hover:bg-white/20 rounded-lg transition-colors">
                                    <X className="w-5 h-5" />
                                </button>
                            </div>
                        </div>

                        {/* Modal Body */}
                        <div className="p-6 space-y-5">
                            {/* Key Info Grid */}
                            <div className="grid grid-cols-2 gap-3">
                                <InfoCard label="Severity" value={getSeverityInfo(selectedAlert.severity).label} badgeClass={getSeverityInfo(selectedAlert.severity).color} />
                                <InfoCard label="Confidence" value={`${(selectedAlert.confidence * 100).toFixed(1)}%`} />
                                <InfoCard label="Camera" value={`Camera ${selectedAlert.camera_id}`} />
                                <InfoCard label="Timestamp" value={formatTimestamp(selectedAlert.timestamp)} />
                                <InfoCard label="Status" value={selectedAlert.is_verified ? '✅ Verified' : '⏳ Unverified'} />
                                {selectedAlert.emotion && (
                                    <InfoCard label="Emotion" value={selectedAlert.emotion} />
                                )}
                            </div>

                            {/* Weapon details */}
                            {selectedAlert.has_weapon && selectedAlert.weapons_detected?.length > 0 && (
                                <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl p-4">
                                    <h4 className="text-sm font-semibold text-red-800 flex items-center gap-2 mb-2">
                                        <Crosshair className="w-4 h-4" /> Weapons Detected
                                    </h4>
                                    <div className="flex flex-wrap gap-2">
                                        {selectedAlert.weapons_detected.map((w, i) => (
                                            <span key={i} className="px-2 py-1 bg-red-100 text-red-800 text-xs font-medium rounded-lg border border-red-200">
                                                {typeof w === 'string' ? w : (w.label || w.class || 'Weapon')} — {typeof w === 'object' && w.confidence ? `${(w.confidence * 100).toFixed(0)}%` : ''}
                                            </span>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {/* Spoof info */}
                            {selectedAlert.detection_type === 'spoof_attempt' && (
                                <div className="bg-orange-50 dark:bg-orange-900/20 border border-orange-200 dark:border-orange-800 rounded-xl p-4">
                                    <h4 className="text-sm font-semibold text-orange-800 flex items-center gap-2">
                                        <Shield className="w-4 h-4" /> Anti-Spoofing Alert
                                    </h4>
                                    <p className="text-xs text-orange-700 mt-1">A non-genuine face was detected. This may indicate a presentation attack (photo, video, or mask).</p>
                                </div>
                            )}

                            {/* Matched person */}
                            {selectedAlert.matched_person_name && (
                                <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-xl p-4">
                                    <h4 className="text-sm font-semibold text-blue-800 flex items-center gap-2 mb-2">
                                        <UserCheck className="w-4 h-4" /> Matched Person
                                    </h4>
                                    <p className="text-sm font-medium text-blue-900">{selectedAlert.matched_person_name}</p>
                                    {selectedAlert.matched_person_category && (
                                        <p className="text-xs text-blue-700 capitalize mt-0.5">{selectedAlert.matched_person_category.replace('_', ' ')}</p>
                                    )}
                                    {selectedAlert.matched_person_photos?.length > 0 && (
                                        <div className="grid grid-cols-3 gap-2 mt-3">
                                            {selectedAlert.matched_person_photos.map((photo, i) => (
                                                <img key={i} src={photo} alt={`Enrolled ${i + 1}`} className="rounded-lg border border-blue-200 w-full h-20 object-cover" />
                                            ))}
                                        </div>
                                    )}
                                </div>
                            )}

                            {/* Age Progression */}
                            {selectedAlert.detection_metadata && (
                                <div className="grid grid-cols-2 gap-3">
                                    {selectedAlert.detection_metadata.detected_age && (
                                        <div className="bg-purple-50 dark:bg-purple-900/20 border border-purple-200 dark:border-purple-800 rounded-xl p-3">
                                            <p className="text-[10px] text-purple-600 uppercase font-semibold">Detected Age</p>
                                            <p className="text-lg font-bold text-purple-800 mt-0.5">{Math.round(selectedAlert.detection_metadata.detected_age)} yrs</p>
                                        </div>
                                    )}
                                    {selectedAlert.detection_metadata.registered_age != null && (
                                        <div className="bg-indigo-50 dark:bg-indigo-900/20 border border-indigo-200 dark:border-indigo-800 rounded-xl p-3">
                                            <p className="text-[10px] text-indigo-600 uppercase font-semibold">Registered Age</p>
                                            <p className="text-lg font-bold text-indigo-800 mt-0.5">{selectedAlert.detection_metadata.registered_age} yrs</p>
                                        </div>
                                    )}
                                    {selectedAlert.detection_metadata.age_gap != null && (
                                        <div className={`col-span-2 rounded-xl p-3 border ${
                                            selectedAlert.detection_metadata.age_gap === 0
                                                ? 'bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800'
                                                : 'bg-amber-50 dark:bg-amber-900/20 border-amber-200 dark:border-amber-800'
                                        }`}>
                                            <p className={`text-[10px] uppercase font-semibold ${
                                                selectedAlert.detection_metadata.age_gap === 0 ? 'text-green-600' : 'text-amber-700'
                                            }`}>Age Progression</p>
                                            {selectedAlert.detection_metadata.age_gap === 0 ? (
                                                <p className="text-sm font-bold text-green-800 mt-0.5">No Age Gap — ages match</p>
                                            ) : (
                                                <>
                                                    <p className="text-lg font-bold text-amber-800 mt-0.5">{selectedAlert.detection_metadata.age_gap} years gap</p>
                                                    <p className="text-xs text-amber-600 mt-0.5">{selectedAlert.detection_metadata.age_gap_label}</p>
                                                </>
                                            )}
                                        </div>
                                    )}
                                </div>
                            )}

                            {/* Thumbnail */}
                            {selectedAlert.thumbnail_path && (
                                <div>
                                    <h4 className="text-xs text-gray-500 uppercase font-semibold mb-2">Detection Snapshot</h4>
                                    <img
                                        src={`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/${selectedAlert.thumbnail_path}`}
                                        alt="Detection snapshot"
                                        className="rounded-xl border border-gray-200 w-full max-h-48 object-contain bg-gray-50"
                                        onError={(e) => { e.target.style.display = 'none'; }}
                                    />
                                </div>
                            )}

                            {/* Blockchain */}
                            {selectedAlert.blockchain_tx_id && (
                                <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-xl p-3 flex items-center gap-2">
                                    <Shield className="w-4 h-4 text-green-600" />
                                    <div>
                                        <p className="text-xs font-semibold text-green-800">Blockchain Anchored</p>
                                        <p className="text-[10px] font-mono text-green-700 truncate">{selectedAlert.blockchain_tx_id}</p>
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

// ── Sub-component ─────────────────────────────────────────────────
const InfoCard = ({ label, value, badgeClass }) => (
    <div className="bg-gray-50 rounded-lg p-3">
        <p className="text-[10px] text-gray-500 uppercase font-semibold tracking-wider">{label}</p>
        {badgeClass ? (
            <span className={`inline-flex items-center px-2 py-0.5 mt-1 rounded-full text-xs font-bold border ${badgeClass}`}>{value}</span>
        ) : (
            <p className="text-sm font-medium text-gray-900 mt-0.5">{value}</p>
        )}
    </div>
);

export default AlertsPage;
