import { format, formatDistanceToNow } from 'date-fns';

/**
 * Standard formats for the application UI
 */
export const DATE_FORMATS = {
    DEFAULT: 'MMM d, yyyy',           // e.g. Feb 10, 2026
    WITH_TIME: 'MMM d, yyyy HH:mm',   // e.g. Feb 10, 2026 21:30
    RELATIVE: 'relative',             // special case for distance to now
};

/**
 * Formats a date string or object consistently across the UI
 */
export function formatDate(date: string | Date | null | undefined, formatStr: string = DATE_FORMATS.DEFAULT): string {
    if (!date) return 'N/A';

    const dateObj = typeof date === 'string' ? new Date(date) : date;

    // Check if valid date
    if (isNaN(dateObj.getTime())) return 'Invalid Date';

    if (formatStr === DATE_FORMATS.RELATIVE) {
        return formatDistanceToNow(dateObj, { addSuffix: true });
    }

    return format(dateObj, formatStr);
}
