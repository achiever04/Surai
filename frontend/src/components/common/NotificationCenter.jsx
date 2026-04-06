import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  Bell, X, AlertTriangle, Shield, Crosshair, UserCheck,
  Frown, User, Swords, Camera, Clock, ChevronRight,
  Volume2, VolumeX, Trash2, Eye
} from 'lucide-react';
import { useWebSocket } from '../../hooks/useWebSocket';

// ── Severity config ──────────────────────────────────────────────────
const SEVERITY = {
  critical: {
    bg: 'bg-gradient-to-r from-red-500/10 to-red-600/5',
    border: 'border-l-red-500',
    badge: 'bg-red-500',
    text: 'text-red-600 dark:text-red-400',
    ring: 'ring-red-500/20',
    label: 'CRITICAL',
  },
  high: {
    bg: 'bg-gradient-to-r from-orange-500/10 to-orange-600/5',
    border: 'border-l-orange-500',
    badge: 'bg-orange-500',
    text: 'text-orange-600 dark:text-orange-400',
    ring: 'ring-orange-500/20',
    label: 'HIGH',
  },
  medium: {
    bg: 'bg-gradient-to-r from-yellow-500/10 to-yellow-600/5',
    border: 'border-l-yellow-500',
    badge: 'bg-yellow-500',
    text: 'text-yellow-600 dark:text-yellow-400',
    ring: 'ring-yellow-500/20',
    label: 'MEDIUM',
  },
  low: {
    bg: 'bg-gradient-to-r from-blue-500/10 to-blue-600/5',
    border: 'border-l-blue-500',
    badge: 'bg-blue-500',
    text: 'text-blue-600 dark:text-blue-400',
    ring: 'ring-blue-500/20',
    label: 'LOW',
  },
};

// ── Detection type config ────────────────────────────────────────────
const TYPE_CONFIG = {
  weapon_detected:   { icon: Crosshair, label: 'Weapon Detected' },
  watchlist_match:   { icon: UserCheck, label: 'Watchlist Match' },
  spoof_attempt:     { icon: Shield,    label: 'Spoof Attempt' },
  aggressive_pose:   { icon: Swords,    label: 'Aggressive Pose' },
  emotion_alert:     { icon: Frown,     label: 'Emotion Alert' },
  face_detection:    { icon: User,      label: 'Face Detected' },
  suspicious_object: { icon: AlertTriangle, label: 'Suspicious Object' },
};

const getTypeInfo = (type) =>
  TYPE_CONFIG[type] || { icon: AlertTriangle, label: type?.replace(/_/g, ' ') || 'Detection' };

const getSeverity = (sev) => SEVERITY[sev] || SEVERITY.low;

// ── Format relative time ─────────────────────────────────────────────
const timeAgo = (ts) => {
  const diff = (Date.now() - new Date(ts).getTime()) / 1000;
  if (diff < 5) return 'Just now';
  if (diff < 60) return `${Math.floor(diff)}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
};

// Max notifications kept in history
const MAX_HISTORY = 50;

// ── Audio alert (web audio API — no file needed) ─────────────────────
const playAlertSound = (severity) => {
  try {
    const ctx = new (window.AudioContext || window.webkitAudioContext)();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.connect(gain);
    gain.connect(ctx.destination);

    if (severity === 'critical') {
      // Urgent double-beep
      osc.frequency.value = 880;
      gain.gain.setValueAtTime(0.3, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.15);
      gain.gain.setValueAtTime(0.3, ctx.currentTime + 0.2);
      gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.35);
      osc.start(ctx.currentTime);
      osc.stop(ctx.currentTime + 0.4);
    } else if (severity === 'high') {
      // Single alert tone
      osc.frequency.value = 660;
      gain.gain.setValueAtTime(0.2, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.25);
      osc.start(ctx.currentTime);
      osc.stop(ctx.currentTime + 0.3);
    } else {
      // Subtle chime
      osc.frequency.value = 520;
      osc.type = 'sine';
      gain.gain.setValueAtTime(0.1, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.2);
      osc.start(ctx.currentTime);
      osc.stop(ctx.currentTime + 0.25);
    }
  } catch {
    // Audio not supported or blocked
  }
};


// ═══════════════════════════════════════════════════════════════════════
// ── Individual Popup Toast ───────────────────────────────────────────
// ═══════════════════════════════════════════════════════════════════════
const NotificationPopup = ({ notification, onDismiss, onView }) => {
  const sev = getSeverity(notification.severity);
  const typeInfo = getTypeInfo(notification.detection_type);
  const Icon = typeInfo.icon;

  useEffect(() => {
    const timer = setTimeout(onDismiss, notification.severity === 'critical' ? 12000 : 8000);
    return () => clearTimeout(timer);
  }, [onDismiss, notification.severity]);

  return (
    <div
      className={`
        notification-popup-enter
        relative w-[380px] rounded-xl border-l-4 ${sev.border}
        bg-white dark:bg-gray-800 shadow-2xl shadow-black/15
        overflow-hidden cursor-pointer group
        hover:shadow-2xl hover:scale-[1.01] transition-all duration-200
      `}
      onClick={onView}
    >
      {/* Severity accent strip */}
      <div className={`absolute top-0 left-0 right-0 h-[2px] ${sev.badge}`} />

      <div className="p-4">
        {/* Header row */}
        <div className="flex items-start gap-3">
          {/* Icon badge */}
          <div className={`
            flex-shrink-0 w-10 h-10 rounded-lg flex items-center justify-center
            ${sev.bg} ${sev.text} ring-1 ${sev.ring}
          `}>
            <Icon className="w-5 h-5" />
          </div>

          {/* Content */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-0.5">
              <span className={`text-[10px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded ${sev.badge} text-white`}>
                {sev.label}
              </span>
              <span className="text-xs text-gray-400 dark:text-gray-500">
                {timeAgo(notification.timestamp)}
              </span>
            </div>

            <h4 className="text-sm font-semibold text-gray-900 dark:text-gray-100 truncate">
              {typeInfo.label}
            </h4>

            <div className="flex items-center gap-3 mt-1.5 text-xs text-gray-500 dark:text-gray-400">
              <span className="flex items-center gap-1">
                <Camera className="w-3 h-3" />
                Camera {notification.camera_id}
              </span>
              <span>
                Confidence: <strong className="text-gray-700 dark:text-gray-300">
                  {(notification.confidence * 100).toFixed(0)}%
                </strong>
              </span>
            </div>

            {/* Extra detail for critical alerts */}
            {notification.has_weapon && notification.weapons_detected?.length > 0 && (
              <div className="mt-2 flex flex-wrap gap-1">
                {notification.weapons_detected.map((w, i) => (
                  <span key={i} className="px-1.5 py-0.5 bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300 text-[10px] font-medium rounded">
                    {typeof w === 'string' ? w : (w.class || w.label || 'Weapon')}
                  </span>
                ))}
              </div>
            )}

            {notification.matched_person_name && (
              <p className="mt-1.5 text-xs text-red-600 dark:text-red-400 font-medium flex items-center gap-1">
                <UserCheck className="w-3 h-3" />
                Matched: {notification.matched_person_name}
              </p>
            )}
          </div>

          {/* Close button */}
          <button
            onClick={(e) => { e.stopPropagation(); onDismiss(); }}
            className="flex-shrink-0 p-1 rounded-lg text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors opacity-0 group-hover:opacity-100"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Progress bar — auto-dismiss indicator */}
      <div className="h-[3px] bg-gray-100 dark:bg-gray-700">
        <div
          className={`h-full ${sev.badge} notification-progress`}
          style={{
            animationDuration: notification.severity === 'critical' ? '12s' : '8s',
          }}
        />
      </div>
    </div>
  );
};


// ═══════════════════════════════════════════════════════════════════════
// ── Notification Panel Item ──────────────────────────────────────────
// ═══════════════════════════════════════════════════════════════════════
const PanelItem = ({ notification, onClick }) => {
  const sev = getSeverity(notification.severity);
  const typeInfo = getTypeInfo(notification.detection_type);
  const Icon = typeInfo.icon;

  return (
    <div
      className={`
        flex items-start gap-3 px-4 py-3 cursor-pointer transition-colors
        ${notification.read
          ? 'bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-750'
          : `${sev.bg} hover:brightness-95`
        }
        border-b border-gray-100 dark:border-gray-700/50 last:border-b-0
      `}
      onClick={onClick}
    >
      <div className={`
        flex-shrink-0 w-8 h-8 rounded-lg flex items-center justify-center
        ${notification.read ? 'bg-gray-100 dark:bg-gray-700 text-gray-400' : `${sev.bg} ${sev.text}`}
      `}>
        <Icon className="w-4 h-4" />
      </div>

      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold text-gray-900 dark:text-gray-100 truncate">
            {typeInfo.label}
          </span>
          {!notification.read && (
            <span className={`w-2 h-2 rounded-full ${sev.badge} flex-shrink-0`} />
          )}
        </div>
        <p className="text-[11px] text-gray-500 dark:text-gray-400 mt-0.5 flex items-center gap-2">
          <span className="flex items-center gap-0.5">
            <Camera className="w-3 h-3" /> Camera {notification.camera_id}
          </span>
          <span>•</span>
          <span>{(notification.confidence * 100).toFixed(0)}%</span>
        </p>
      </div>

      <span className="text-[10px] text-gray-400 dark:text-gray-500 flex-shrink-0 whitespace-nowrap">
        {timeAgo(notification.timestamp)}
      </span>
    </div>
  );
};


// ═══════════════════════════════════════════════════════════════════════
// ── Main NotificationCenter Component ────────────────────────────────
// ═══════════════════════════════════════════════════════════════════════
const NotificationCenter = () => {
  const [notifications, setNotifications] = useState([]);
  const [popups, setPopups] = useState([]);
  const [panelOpen, setPanelOpen] = useState(false);
  const [soundEnabled, setSoundEnabled] = useState(true);
  const panelRef = useRef(null);

  const unreadCount = notifications.filter(n => !n.read).length;

  // Close panel when clicking outside
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (panelRef.current && !panelRef.current.contains(e.target)) {
        setPanelOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // ── Handle incoming detection ──────────────────────────────────────
  const handleDetection = useCallback((data) => {
    // Determine effective severity
    const severity = data.severity || data.data?.severity || 'low';

    // Only show popup for medium+ severity, or any critical detection type
    const isAlert = severity === 'critical' || severity === 'high' || severity === 'medium'
      || data.detection_type === 'weapon_detected'
      || data.detection_type === 'watchlist_match'
      || data.detection_type === 'aggressive_pose'
      || data.detection_type === 'spoof_attempt';

    const notification = {
      id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
      ...(data.data || data),  // Handle both {type, data:{...}} and flat formats
      severity,
      timestamp: data.timestamp || data.data?.timestamp || new Date().toISOString(),
      read: false,
    };

    // Add to notification history
    setNotifications(prev => [notification, ...prev].slice(0, MAX_HISTORY));

    if (isAlert) {
      // Show toast popup
      setPopups(prev => [...prev, notification]);

      // Play sound
      if (soundEnabled) {
        playAlertSound(severity);
      }
    }
  }, [soundEnabled]);

  // ── Handle watchlist match ─────────────────────────────────────────
  const handleWatchlistMatch = useCallback((data) => {
    const notification = {
      id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
      detection_type: 'watchlist_match',
      severity: data.severity || 'high',
      camera_id: data.location?.replace('Camera ', '') || '?',
      confidence: data.confidence || 0,
      matched_person_name: data.person_name,
      timestamp: data.timestamp || new Date().toISOString(),
      read: false,
    };

    setNotifications(prev => [notification, ...prev].slice(0, MAX_HISTORY));
    setPopups(prev => [...prev, notification]);

    if (soundEnabled) {
      playAlertSound('high');
    }
  }, [soundEnabled]);

  // ── Listen to WebSocket events ─────────────────────────────────────
  useWebSocket('new_detection', handleDetection);
  useWebSocket('watchlist_match', handleWatchlistMatch);
  useWebSocket('detection_alert', handleDetection);

  // ── Actions ────────────────────────────────────────────────────────
  const dismissPopup = useCallback((id) => {
    setPopups(prev => prev.filter(p => p.id !== id));
  }, []);

  const markAllRead = useCallback(() => {
    setNotifications(prev => prev.map(n => ({ ...n, read: true })));
  }, []);

  const clearAll = useCallback(() => {
    setNotifications([]);
  }, []);

  const handleNotificationClick = useCallback((notification) => {
    // Mark as read
    setNotifications(prev =>
      prev.map(n => n.id === notification.id ? { ...n, read: true } : n)
    );
    // Navigate to alerts page
    window.location.href = '/alerts';
    setPanelOpen(false);
  }, []);

  return (
    <>
      {/* ── Bell Button (rendered into Header via portal or direct) ─── */}
      <div className="relative" ref={panelRef}>
        <button
          onClick={() => setPanelOpen(!panelOpen)}
          className={`
            relative p-2 rounded-xl transition-all duration-200
            ${panelOpen
              ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-600'
              : 'text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 hover:text-gray-700 dark:hover:text-gray-200'
            }
          `}
          id="notification-bell"
          title="Notifications"
        >
          <Bell className={`w-5 h-5 ${unreadCount > 0 ? 'notification-bell-ring' : ''}`} />

          {/* Unread badge */}
          {unreadCount > 0 && (
            <span className="absolute -top-0.5 -right-0.5 flex items-center justify-center min-w-[18px] h-[18px] px-1 rounded-full bg-red-500 text-white text-[10px] font-bold shadow-md notification-badge-pulse">
              {unreadCount > 99 ? '99+' : unreadCount}
            </span>
          )}
        </button>

        {/* ── Notification Panel ─────────────────────────────────────── */}
        {panelOpen && (
          <div className="
            absolute right-0 top-12 w-[400px] max-h-[520px]
            bg-white dark:bg-gray-800 rounded-2xl shadow-2xl shadow-black/15
            border border-gray-200 dark:border-gray-700
            overflow-hidden z-[9998]
            notification-panel-enter
          ">
            {/* Panel header */}
            <div className="px-4 py-3 border-b border-gray-100 dark:border-gray-700 bg-gray-50/80 dark:bg-gray-800/80 backdrop-blur-sm">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100">
                    Notifications
                  </h3>
                  {unreadCount > 0 && (
                    <span className="px-2 py-0.5 rounded-full bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400 text-[10px] font-bold">
                      {unreadCount} new
                    </span>
                  )}
                </div>

                <div className="flex items-center gap-1">
                  <button
                    onClick={() => setSoundEnabled(!soundEnabled)}
                    className="p-1.5 rounded-lg text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                    title={soundEnabled ? 'Mute sounds' : 'Enable sounds'}
                  >
                    {soundEnabled ? <Volume2 className="w-4 h-4" /> : <VolumeX className="w-4 h-4" />}
                  </button>
                  {unreadCount > 0 && (
                    <button
                      onClick={markAllRead}
                      className="p-1.5 rounded-lg text-gray-400 hover:text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/20 transition-colors"
                      title="Mark all read"
                    >
                      <Eye className="w-4 h-4" />
                    </button>
                  )}
                  {notifications.length > 0 && (
                    <button
                      onClick={clearAll}
                      className="p-1.5 rounded-lg text-gray-400 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors"
                      title="Clear all"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  )}
                </div>
              </div>
            </div>

            {/* Panel body — scrollable list */}
            <div className="max-h-[420px] overflow-y-auto overscroll-contain">
              {notifications.length > 0 ? (
                notifications.map(n => (
                  <PanelItem
                    key={n.id}
                    notification={n}
                    onClick={() => handleNotificationClick(n)}
                  />
                ))
              ) : (
                <div className="py-12 text-center">
                  <Bell className="w-10 h-10 mx-auto text-gray-300 dark:text-gray-600 mb-3" />
                  <p className="text-sm text-gray-500 dark:text-gray-400 font-medium">No notifications yet</p>
                  <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">
                    Alerts will appear here in real-time
                  </p>
                </div>
              )}
            </div>

            {/* Panel footer */}
            {notifications.length > 0 && (
              <div className="px-4 py-2.5 border-t border-gray-100 dark:border-gray-700 bg-gray-50/80 dark:bg-gray-800/80">
                <a
                  href="/alerts"
                  className="flex items-center justify-center gap-1 text-xs font-medium text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 transition-colors"
                >
                  View All Alerts <ChevronRight className="w-3 h-3" />
                </a>
              </div>
            )}
          </div>
        )}
      </div>

      {/* ── Popup Toast Stack (fixed position, top-right) ───────────── */}
      <div className="fixed top-4 right-4 z-[9999] flex flex-col gap-3 pointer-events-auto">
        {popups.map(popup => (
          <NotificationPopup
            key={popup.id}
            notification={popup}
            onDismiss={() => dismissPopup(popup.id)}
            onView={() => {
              dismissPopup(popup.id);
              handleNotificationClick(popup);
            }}
          />
        ))}
      </div>
    </>
  );
};

export default NotificationCenter;
