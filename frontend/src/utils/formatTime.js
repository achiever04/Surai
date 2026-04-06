/**
 * Centralized timestamp formatting utility.
 * Ensures all timestamps across the app are displayed consistently
 * in the user's local timezone.
 */

/**
 * Format an ISO timestamp string to a readable local date+time string.
 * Handles both timezone-aware (with Z or +00:00) and naive ISO strings.
 *
 * @param {string} isoString - ISO 8601 timestamp from the API
 * @returns {string} Formatted local date and time string
 */
export function formatTimestamp(isoString) {
    if (!isoString) return 'N/A';

    // Normalize: if the ISO string has no timezone indicator, treat it as UTC
    let normalized = isoString;
    if (!normalized.endsWith('Z') && !normalized.includes('+') && !normalized.match(/\d{2}:\d{2}$/)) {
        normalized += 'Z';
    }

    const date = new Date(normalized);

    // Guard against invalid dates
    if (isNaN(date.getTime())) return isoString;

    return date.toLocaleString(undefined, {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: true,
    });
}

/**
 * Format an ISO timestamp to a short date-only string.
 *
 * @param {string} isoString - ISO 8601 timestamp from the API
 * @returns {string} Formatted local date string
 */
export function formatDate(isoString) {
    if (!isoString) return 'N/A';

    let normalized = isoString;
    if (!normalized.endsWith('Z') && !normalized.includes('+') && !normalized.match(/\d{2}:\d{2}$/)) {
        normalized += 'Z';
    }

    const date = new Date(normalized);
    if (isNaN(date.getTime())) return isoString;

    return date.toLocaleDateString(undefined, {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
    });
}
