package com.util;

import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpSession;

import com.User.UserDetails;

/** Small helpers shared by the servlets: the signed-in user, flash messages, and input cleaning. */
public final class WebUtils {

    public static final String FLASH_SUCCESS = "flashSuccess";
    public static final String FLASH_ERROR = "flashError";

    private WebUtils() {
    }

    /**
     * Returns the signed-in user, or {@code null}.
     *
     * <p>Servlets take the acting user id from here rather than from a request
     * parameter. The add-note form used to post the author id in a hidden field,
     * which any user could edit to file a note under someone else's account.
     */
    public static UserDetails currentUser(HttpServletRequest request) {
        HttpSession session = request.getSession(false);
        return session == null ? null : (UserDetails) session.getAttribute("userD");
    }

    /** Stores a one-shot success message for the next page render. */
    public static void success(HttpServletRequest request, String message) {
        request.getSession().setAttribute(FLASH_SUCCESS, message);
    }

    /** Stores a one-shot error message for the next page render. */
    public static void error(HttpServletRequest request, String message) {
        request.getSession().setAttribute(FLASH_ERROR, message);
    }

    /** Trims a parameter and converts blank/absent values to {@code null}. */
    public static String trimmed(HttpServletRequest request, String name) {
        String value = request.getParameter(name);
        if (value == null) {
            return null;
        }
        value = value.trim();
        return value.isEmpty() ? null : value;
    }

    /** Parses an int parameter, returning {@code fallback} when absent or malformed. */
    public static int intParam(HttpServletRequest request, String name, int fallback) {
        String raw = request.getParameter(name);
        if (raw == null || raw.trim().isEmpty()) {
            return fallback;
        }
        try {
            return Integer.parseInt(raw.trim());
        } catch (NumberFormatException e) {
            return fallback;
        }
    }

    /** Basic shape check for an email address. */
    public static boolean looksLikeEmail(String value) {
        if (value == null) {
            return false;
        }
        int at = value.indexOf('@');
        int dot = value.lastIndexOf('.');
        return at > 0 && dot > at + 1 && dot < value.length() - 1 && !value.contains(" ");
    }
}
