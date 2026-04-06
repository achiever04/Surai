import React, { useState, useEffect } from 'react';
import { settingsAPI } from '../services/api';
import {
  Brain,
  Bell,
  Cpu,
  Camera,
  Save,
  Trash2,
  Plus,
  ChevronDown,
  Info,
  CheckCircle,
  X,
  HardDrive,
  SlidersHorizontal,
} from 'lucide-react';

/* ─────────────────────────────────────────────
   Backend ↔ Frontend key mapping helpers
───────────────────────────────────────────── */

/**
 * Convert the backend snake_case payload → frontend camelCase state.
 * Called on page load to populate controls from the API.
 */
function backendToFrontend(data) {
  // frame_skip → frame_skip value maps to the dropdown option value
  const frameSkipMap = { 0: 'every', 1: 'skip1', 3: 'skip3' };
  return {
    confidenceThreshold: Math.round((data.confidence_threshold ?? 0.60) * 100),
    iouThreshold:        Math.round((data.iou_threshold        ?? 0.45) * 100),
    activeYoloModel:     data.active_yolo_model  ?? 'nano',
    dedupCooldown:       String(data.db_dedup_seconds ?? 60) + 's',
    frameProcessingRate: frameSkipMap[data.frame_skip ?? 0] ?? 'every',
    lowMemoryMode:       data.low_memory_mode ?? false,
    dataRetentionDays:   data.data_retention_days ?? 7,
  };
}

/**
 * Convert the frontend camelCase state → backend snake_case payload.
 * Called on Save to build the POST body.
 */
function frontendToBackend(settings) {
  const frameSkipMap = { every: 0, skip1: 1, skip3: 3 };
  // Strip trailing 's' from dedupCooldown (e.g. "3600s" → 3600).
  // parseInt handles both "3600s" and plain numbers safely.
  const dedupSecs = parseInt(String(settings.dedupCooldown), 10);
  return {
    confidence_threshold: settings.confidenceThreshold / 100,
    iou_threshold:        settings.iouThreshold / 100,
    db_dedup_seconds:     isNaN(dedupSecs) ? 60 : dedupSecs,
    frame_skip:           frameSkipMap[settings.frameProcessingRate] ?? 0,
    low_memory_mode:      settings.lowMemoryMode,
    // active_yolo_model and data_retention_days are included for completeness;
    // the backend silently ignores fields it doesn’t recognise.
    active_yolo_model:    settings.activeYoloModel,
    data_retention_days:  settings.dataRetentionDays,
  };
}

/* ─────────────────────────────────────────────
   Reusable sub-components
───────────────────────────────────────────── */

/** Section card wrapper */
function SettingsCard({ icon: Icon, title, accent, children }) {
  const accentMap = {
    blue:   { ring: 'ring-blue-500/20',   icon: 'bg-blue-500/10 text-blue-500',   bar: 'bg-blue-500' },
    amber:  { ring: 'ring-amber-500/20',  icon: 'bg-amber-500/10 text-amber-500', bar: 'bg-amber-500' },
    violet: { ring: 'ring-violet-500/20', icon: 'bg-violet-500/10 text-violet-500',bar: 'bg-violet-500' },
    teal:   { ring: 'ring-teal-500/20',   icon: 'bg-teal-500/10 text-teal-500',   bar: 'bg-teal-500' },
  };
  const c = accentMap[accent] || accentMap.blue;

  return (
    <div
      className={`bg-white dark:bg-gray-800 rounded-2xl shadow-sm ring-1 ${c.ring}
                  border border-gray-100 dark:border-gray-700 overflow-hidden`}
    >
      {/* Coloured top bar */}
      <div className={`h-1 w-full ${c.bar}`} />

      {/* Card header */}
      <div className="flex items-center gap-3 px-6 pt-5 pb-4 border-b border-gray-100 dark:border-gray-700">
        <div className={`p-2.5 rounded-xl ${c.icon}`}>
          <Icon className="h-5 w-5" />
        </div>
        <h2 className="text-base font-semibold text-gray-800 dark:text-gray-100 tracking-tight">
          {title}
        </h2>
      </div>

      <div className="px-6 py-5 space-y-6">{children}</div>
    </div>
  );
}

/** Labelled field row */
function FieldRow({ label, hint, children }) {
  return (
    <div className="flex flex-col sm:flex-row sm:items-start gap-2 sm:gap-6">
      <div className="sm:w-52 flex-shrink-0 pt-0.5">
        <p className="text-sm font-medium text-gray-700 dark:text-gray-200">{label}</p>
        {hint && <p className="text-xs text-gray-400 dark:text-gray-500 mt-0.5 leading-snug">{hint}</p>}
      </div>
      <div className="flex-1">{children}</div>
    </div>
  );
}

/** Styled range slider with live value badge */
function SliderField({ id, value, onChange, min = 0, max = 100, accentColor = 'blue' }) {
  const pct = ((value - min) / (max - min)) * 100;

  const trackColors = {
    blue:   '#3b82f6',
    amber:  '#f59e0b',
    violet: '#8b5cf6',
    teal:   '#14b8a6',
  };
  const color = trackColors[accentColor] || trackColors.blue;

  return (
    <div className="flex items-center gap-4">
      <div className="relative flex-1 h-2 rounded-full bg-gray-200 dark:bg-gray-600">
        {/* Filled track */}
        <div
          className="absolute left-0 top-0 h-2 rounded-full transition-all"
          style={{ width: `${pct}%`, backgroundColor: color }}
        />
        <input
          id={id}
          type="range"
          min={min}
          max={max}
          value={value}
          onChange={(e) => onChange(Number(e.target.value))}
          className="absolute inset-0 w-full opacity-0 cursor-pointer h-2"
        />
        {/* Thumb */}
        <div
          className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2 h-4 w-4 rounded-full border-2 border-white shadow-md transition-all pointer-events-none"
          style={{ left: `${pct}%`, backgroundColor: color }}
        />
      </div>
      <span
        className="min-w-[3.25rem] text-center text-sm font-semibold px-2.5 py-1 rounded-lg text-white"
        style={{ backgroundColor: color }}
      >
        {value}%
      </span>
    </div>
  );
}

/** Styled select dropdown */
function SelectField({ id, value, onChange, options }) {
  return (
    <div className="relative">
      <select
        id={id}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full appearance-none rounded-xl border border-gray-200 dark:border-gray-600
                   bg-gray-50 dark:bg-gray-700 text-gray-800 dark:text-gray-100
                   px-4 py-2.5 pr-10 text-sm font-medium
                   focus:outline-none focus:ring-2 focus:ring-blue-500/40
                   transition-colors cursor-pointer"
      >
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
      <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400 pointer-events-none" />
    </div>
  );
}

/** iOS-style toggle switch */
function ToggleSwitch({ id, checked, onChange, label, description }) {
  return (
    <div className="flex items-start justify-between gap-4">
      <div className="flex-1">
        <p className="text-sm font-medium text-gray-700 dark:text-gray-200">{label}</p>
        {description && (
          <p className="text-xs text-gray-400 dark:text-gray-500 mt-0.5 leading-snug">{description}</p>
        )}
      </div>
      <button
        id={id}
        role="switch"
        aria-checked={checked}
        onClick={() => onChange(!checked)}
        className={`relative flex-shrink-0 w-12 h-6 rounded-full transition-colors duration-300 focus:outline-none focus:ring-2 focus:ring-blue-500/40 ${
          checked ? 'bg-blue-500' : 'bg-gray-300 dark:bg-gray-600'
        }`}
      >
        <span
          className={`absolute top-0.5 left-0.5 h-5 w-5 rounded-full bg-white shadow-md
                      transform transition-transform duration-300 ${checked ? 'translate-x-6' : 'translate-x-0'}`}
        />
      </button>
    </div>
  );
}

/** Number input */
function NumberField({ id, value, onChange, min = 1, max = 3650, suffix }) {
  return (
    <div className="flex items-center gap-2">
      <input
        id={id}
        type="number"
        min={min}
        max={max}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-24 rounded-xl border border-gray-200 dark:border-gray-600
                   bg-gray-50 dark:bg-gray-700 text-gray-800 dark:text-gray-100
                   px-3 py-2.5 text-sm font-medium text-center
                   focus:outline-none focus:ring-2 focus:ring-blue-500/40 transition-colors"
      />
      {suffix && <span className="text-sm text-gray-500 dark:text-gray-400">{suffix}</span>}
    </div>
  );
}

/* ─────────────────────────────────────────────
   Toast notification (local)
───────────────────────────────────────────── */
function SaveToast({ visible, onClose, isError = false }) {
  useEffect(() => {
    if (visible) {
      const t = setTimeout(onClose, 3500);
      return () => clearTimeout(t);
    }
  }, [visible, onClose]);

  return (
    <div
      className={`fixed bottom-6 right-6 z-50 flex items-center gap-3 px-5 py-3.5 rounded-2xl shadow-xl
                  text-white text-sm font-medium
                  transition-all duration-300 ${
                    visible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4 pointer-events-none'
                  } ${
                    isError ? 'bg-red-600 dark:bg-red-700' : 'bg-gray-900 dark:bg-gray-700'
                  }`}
    >
      {isError
        ? <AlertTriangleIcon className="h-5 w-5 text-red-200 flex-shrink-0" />
        : <CheckCircle className="h-5 w-5 text-green-400 flex-shrink-0" />}
      <span>{isError ? 'Save failed — check the console for details' : 'Configuration saved successfully'}</span>
      <button onClick={onClose} className="ml-2 text-white/60 hover:text-white transition-colors">
        <X className="h-4 w-4" />
      </button>
    </div>
  );
}

// Local alias so we don't need another icon import
const AlertTriangleIcon = ({ className }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v4m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
  </svg>
);

/* ─────────────────────────────────────────────
   Add Camera Modal (placeholder)
───────────────────────────────────────────── */
function AddCameraModal({ onClose }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
      <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-2xl w-full max-w-md ring-1 ring-gray-100 dark:ring-gray-700 overflow-hidden animate-slide-in">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100 dark:border-gray-700">
          <h3 className="text-base font-semibold text-gray-800 dark:text-gray-100">Add New Camera</h3>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>
        <div className="px-6 py-8 flex flex-col items-center text-center gap-3">
          <div className="p-4 bg-blue-50 dark:bg-blue-900/20 rounded-2xl">
            <Camera className="h-8 w-8 text-blue-500" />
          </div>
          <p className="text-sm font-medium text-gray-700 dark:text-gray-200">Camera Configuration</p>
          <p className="text-xs text-gray-400 dark:text-gray-500 max-w-xs">
            This modal will be wired to the backend camera API. Camera RTSP URL, name, and stream settings will be configured here.
          </p>
          <div className="mt-2 px-4 py-2 bg-amber-50 dark:bg-amber-900/20 rounded-xl border border-amber-200 dark:border-amber-800 flex items-start gap-2 text-left">
            <Info className="h-4 w-4 text-amber-500 flex-shrink-0 mt-0.5" />
            <p className="text-xs text-amber-700 dark:text-amber-400">Backend integration pending — placeholder UI only.</p>
          </div>
        </div>
        <div className="px-6 pb-5 flex justify-end gap-2">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium rounded-xl border border-gray-200 dark:border-gray-600 text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium rounded-xl bg-blue-600 hover:bg-blue-700 text-white transition-colors shadow-sm"
          >
            Add Camera
          </button>
        </div>
      </div>
    </div>
  );
}

/* ─────────────────────────────────────────────
   Main Page
───────────────────────────────────────────── */
const DEFAULT_SETTINGS = {
  // Section 1 — AI & Model Tuning
  confidenceThreshold: 60,
  iouThreshold: 45,
  activeYoloModel: 'nano',

  // Section 2 — Alerts & Deduplication
  dedupCooldown: '60s',

  // Section 3 — Hardware & Performance
  frameProcessingRate: 'every',
  lowMemoryMode: false,

  // Section 4 — Camera & Storage
  cameras: [{ id: 1, name: 'Camera 1 - Main' }],
  dataRetentionDays: 7,
};

const SettingsPage = () => {
  const [settings, setSettings] = useState(DEFAULT_SETTINGS);
  const [showCameraModal, setShowCameraModal] = useState(false);
  const [showToast, setShowToast] = useState(false);
  const [toastError, setToastError] = useState(false);   // true = red error toast
  const [isSaving, setIsSaving] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  /* Load settings from backend on mount */
  useEffect(() => {
    (async () => {
      try {
        const response = await settingsAPI.get();
        const remapped = backendToFrontend(response.data);
        setSettings((prev) => ({ ...prev, ...remapped }));
        console.log('[Settings] Loaded from backend:', response.data);
      } catch (err) {
        console.warn('[Settings] Could not load from backend (using defaults):', err.message);
        // Non-fatal: defaults are already in state
      } finally {
        setIsLoading(false);
      }
    })();
  }, []);

  const update = (key) => (value) =>
    setSettings((prev) => ({ ...prev, [key]: value }));

  const handleSaveConfiguration = async () => {
    setIsSaving(true);
    const payload = frontendToBackend(settings);
    console.log('[Settings] Saving payload:', JSON.stringify(payload, null, 2));
    try {
      const response = await settingsAPI.update(payload);
      console.log('[Settings] Saved successfully:', response.data);
      setToastError(false);
      setShowToast(true);
    } catch (err) {
      console.error('[Settings] Save failed:', err.response?.data || err.message);
      setToastError(true);
      setShowToast(true);
    } finally {
      setIsSaving(false);
    }
  };

  const handleClearCache = () => {
    if (window.confirm('Clear all local cache? This cannot be undone.')) {
      console.log('[Settings] Clear local cache triggered');
      // TODO: wire to backend
    }
  };

  return (
    <div className="space-y-6 pb-10">
      {isLoading && (
        <div className="flex items-center gap-3 px-1 py-2">
          <div className="h-4 w-4 rounded-full border-2 border-blue-500 border-t-transparent animate-spin" />
          <span className="text-sm text-gray-500 dark:text-gray-400">Loading configuration…</span>
        </div>
      )}
      {/* Page header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-gray-800 dark:text-gray-100 tracking-tight flex items-center gap-2">
            <SlidersHorizontal className="h-6 w-6 text-blue-500" />
            Settings &amp; Configuration
          </h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Manage AI parameters, alert rules, hardware limits, and storage preferences.
          </p>
        </div>
        {/* Quick Save shortcut in header */}
        <button
          id="settings-save-header-btn"
          onClick={handleSaveConfiguration}
          disabled={isSaving}
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-700
                     disabled:opacity-60 text-white text-sm font-semibold shadow-sm
                     transition-all duration-200 active:scale-95"
        >
          <Save className="h-4 w-4" />
          {isSaving ? 'Saving…' : 'Save Configuration'}
        </button>
      </div>

      {/* ── Grid of 4 cards ── */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">

        {/* ── Card 1: AI & Model Tuning ── */}
        <SettingsCard icon={Brain} title="AI & Model Tuning" accent="blue">
          <FieldRow
            label="Confidence Threshold"
            hint="Minimum score for a detection to be accepted."
          >
            <SliderField
              id="confidence-threshold"
              value={settings.confidenceThreshold}
              onChange={update('confidenceThreshold')}
              accentColor="blue"
            />
          </FieldRow>

          <div className="border-t border-gray-100 dark:border-gray-700/60" />

          <FieldRow
            label="IoU Threshold"
            hint="Intersection-over-Union for bounding box suppression."
          >
            <SliderField
              id="iou-threshold"
              value={settings.iouThreshold}
              onChange={update('iouThreshold')}
              accentColor="blue"
            />
          </FieldRow>

          <div className="border-t border-gray-100 dark:border-gray-700/60" />

          <FieldRow
            label="Active YOLO Model"
            hint="Larger models are more accurate but slower."
          >
            <SelectField
              id="active-yolo-model"
              value={settings.activeYoloModel}
              onChange={update('activeYoloModel')}
              options={[
                { value: 'nano',   label: 'Nano — Fastest' },
                { value: 'small',  label: 'Small — Balanced' },
                { value: 'medium', label: 'Medium — High Accuracy' },
              ]}
            />
          </FieldRow>
        </SettingsCard>

        {/* ── Card 2: Alerts & Deduplication ── */}
        <SettingsCard icon={Bell} title="Alerts & Deduplication" accent="amber">
          <div className="rounded-xl bg-amber-50 dark:bg-amber-900/15 border border-amber-200 dark:border-amber-800/50 px-4 py-3 flex gap-3">
            <Info className="h-4 w-4 text-amber-500 flex-shrink-0 mt-0.5" />
            <p className="text-xs text-amber-700 dark:text-amber-400 leading-snug">
              Crucial for presentations — prevents duplicate alerts flooding the database during demos.
            </p>
          </div>

          <FieldRow
            label="Database Deduplication Cooldown"
            hint="How long to wait before saving the same alert again."
          >
            <SelectField
              id="dedup-cooldown"
              value={settings.dedupCooldown}
              onChange={update('dedupCooldown')}
              options={[
                { value: '60s',  label: '60 Seconds (Demo / Presentation Mode)' },
                { value: '300s', label: '5 Minutes' },
                { value: '3600s',label: '1 Hour' },
                { value: '43200s',label: '12 Hours (Production Mode)' },
              ]}
            />
          </FieldRow>

          {/* Visual cooldown indicator */}
          <div className="rounded-xl bg-gray-50 dark:bg-gray-700/40 px-4 py-3 flex items-center justify-between">
            <span className="text-xs text-gray-500 dark:text-gray-400">Current mode</span>
            <span className={`text-xs font-semibold px-3 py-1 rounded-full ${
              settings.dedupCooldown === '60s'
                ? 'bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400'
                : settings.dedupCooldown === '43200s'
                ? 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400'
                : 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400'
            }`}>
              {settings.dedupCooldown === '60s' ? '⚡ Demo / Presentation'
                : settings.dedupCooldown === '43200s' ? '🏭 Production'
                : '🔧 Custom'}
            </span>
          </div>
        </SettingsCard>

        {/* ── Card 3: Hardware & Performance ── */}
        <SettingsCard icon={Cpu} title="Hardware & Performance" accent="violet">
          <FieldRow
            label="Frame Processing Rate"
            hint="Skipping frames reduces CPU/GPU load on older hardware."
          >
            <SelectField
              id="frame-processing-rate"
              value={settings.frameProcessingRate}
              onChange={update('frameProcessingRate')}
              options={[
                { value: 'every',  label: 'Process Every Frame' },
                { value: 'skip1',  label: 'Skip 1 Frame' },
                { value: 'skip3',  label: 'Skip 3 Frames' },
              ]}
            />
          </FieldRow>

          <div className="border-t border-gray-100 dark:border-gray-700/60" />

          <ToggleSwitch
            id="low-memory-mode-toggle"
            checked={settings.lowMemoryMode}
            onChange={update('lowMemoryMode')}
            label="Low Memory Mode (< 6 GB RAM)"
            description="Enables memory-saving optimisations. Essential for systems with ~5.8 GB usable RAM to prevent crashes."
          />

          {settings.lowMemoryMode && (
            <div className="rounded-xl bg-violet-50 dark:bg-violet-900/15 border border-violet-200 dark:border-violet-800/50 px-4 py-3 flex gap-3">
              <Info className="h-4 w-4 text-violet-500 flex-shrink-0 mt-0.5" />
              <p className="text-xs text-violet-700 dark:text-violet-400 leading-snug">
                Low Memory Mode is <strong>active</strong>. The system will disable optional in-memory caches and reduce batch sizes automatically.
              </p>
            </div>
          )}
        </SettingsCard>

        {/* ── Card 4: Camera & Storage ── */}
        <SettingsCard icon={HardDrive} title="Camera & Storage" accent="teal">
          {/* Camera list */}
          <FieldRow label="Connected Cameras" hint="Manage cameras used for live surveillance.">
            <div className="space-y-2">
              {settings.cameras.map((cam) => (
                <div
                  key={cam.id}
                  className="flex items-center justify-between px-4 py-3 rounded-xl
                             bg-gray-50 dark:bg-gray-700/50 border border-gray-100 dark:border-gray-700"
                >
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-teal-100 dark:bg-teal-900/30 rounded-lg">
                      <Camera className="h-4 w-4 text-teal-600 dark:text-teal-400" />
                    </div>
                    <span className="text-sm font-medium text-gray-700 dark:text-gray-200">
                      {cam.name}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs px-2.5 py-1 bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400 rounded-full font-medium">
                      Active
                    </span>
                  </div>
                </div>
              ))}

              <button
                id="add-camera-btn"
                onClick={() => setShowCameraModal(true)}
                className="w-full flex items-center justify-center gap-2 px-4 py-3 rounded-xl
                           border-2 border-dashed border-teal-300 dark:border-teal-700
                           text-teal-600 dark:text-teal-400 hover:bg-teal-50 dark:hover:bg-teal-900/20
                           text-sm font-medium transition-colors duration-200"
              >
                <Plus className="h-4 w-4" />
                Add Camera
              </button>
            </div>
          </FieldRow>

          <div className="border-t border-gray-100 dark:border-gray-700/60" />

          <FieldRow
            label="Data Retention"
            hint="Evidence older than this will be auto-deleted."
          >
            <NumberField
              id="data-retention-days"
              value={settings.dataRetentionDays}
              onChange={update('dataRetentionDays')}
              min={1}
              max={3650}
              suffix="days"
            />
          </FieldRow>

          <div className="border-t border-gray-100 dark:border-gray-700/60" />

          {/* Clear Cache */}
          <FieldRow
            label="Clear Local Cache"
            hint="Removes all locally-cached thumbnails, frames, and temp files."
          >
            <button
              id="clear-cache-btn"
              onClick={handleClearCache}
              className="flex items-center gap-2 px-4 py-2.5 rounded-xl
                         bg-red-600 hover:bg-red-700 active:scale-95
                         text-white text-sm font-semibold shadow-sm
                         transition-all duration-200"
            >
              <Trash2 className="h-4 w-4" />
              Clear Local Cache
            </button>
          </FieldRow>
        </SettingsCard>
      </div>

      {/* ── Save footer ── */}
      <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-sm border border-gray-100 dark:border-gray-700 px-6 py-5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div className="flex items-start gap-3">
          <Info className="h-5 w-5 text-blue-500 flex-shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-medium text-gray-700 dark:text-gray-200">
              Ready to apply changes?
            </p>
            <p className="text-xs text-gray-400 dark:text-gray-500 mt-0.5">
              Settings are saved to the backend immediately and persist across server restarts.
            </p>
          </div>
        </div>
        <button
          id="settings-save-footer-btn"
          onClick={handleSaveConfiguration}
          disabled={isSaving}
          className="flex items-center gap-2 px-6 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-700
                     disabled:opacity-60 text-white text-sm font-semibold shadow-md
                     transition-all duration-200 active:scale-95 flex-shrink-0"
        >
          <Save className="h-4 w-4" />
          {isSaving ? 'Saving…' : 'Save Configuration'}
        </button>
      </div>

      {/* Modals & Toasts */}
      {showCameraModal && <AddCameraModal onClose={() => setShowCameraModal(false)} />}
      <SaveToast visible={showToast} onClose={() => setShowToast(false)} isError={toastError} />
    </div>
  );
};

export default SettingsPage;
