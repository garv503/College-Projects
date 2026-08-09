package com.util;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.SecureRandom;
import java.util.Base64;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpSession;

/**
 * Per-session CSRF tokens.
 *
 * <p>Without these, another site can make a visitor's browser submit a request
 * to E-Notes using their live session cookie. Every state-changing call carries
 * the session's token, and {@code CsrfFilter} rejects any write that does not
 * present it - an attacker's page cannot read the token, so it cannot forge the
 * request.
 *
 * <p>The client fetches its token from {@code /api/auth/session} and returns it
 * in the {@code X-CSRF-Token} header. A header is required rather than a form
 * field because the API sends JSON bodies, which carry no request parameters.
 */
public final class Csrf {

    public static final String SESSION_ATTRIBUTE = "csrfToken";
    public static final String PARAMETER_NAME = "csrfToken";
    public static final String HEADER_NAME = "X-CSRF-Token";

    private static final SecureRandom RANDOM = new SecureRandom();

    private Csrf() {
    }

    /** Returns the session's token, creating one on first use. */
    public static String token(HttpServletRequest request) {
        HttpSession session = request.getSession();
        synchronized (session.getId().intern()) {
            String token = (String) session.getAttribute(SESSION_ATTRIBUTE);
            if (token == null) {
                byte[] bytes = new byte[32];
                RANDOM.nextBytes(bytes);
                token = Base64.getUrlEncoder().withoutPadding().encodeToString(bytes);
                session.setAttribute(SESSION_ATTRIBUTE, token);
            }
            return token;
        }
    }

    /** Checks a submitted token against the one held in the session. */
    public static boolean isValid(HttpServletRequest request) {
        HttpSession session = request.getSession(false);
        if (session == null) {
            return false;
        }

        String expected = (String) session.getAttribute(SESSION_ATTRIBUTE);

        // Header first (how the API client sends it); the parameter is kept as a
        // fallback so a plain form post would still work.
        String supplied = request.getHeader(HEADER_NAME);
        if (supplied == null) {
            supplied = request.getParameter(PARAMETER_NAME);
        }

        return expected != null && constantTimeEquals(expected, supplied);
    }

    /**
     * Compares two tokens without short-circuiting on the first difference, so
     * response timing does not reveal how much of the token was correct.
     */
    private static boolean constantTimeEquals(String a, String b) {
        if (a == null || b == null) {
            return false;
        }
        return MessageDigest.isEqual(
                a.getBytes(StandardCharsets.UTF_8),
                b.getBytes(StandardCharsets.UTF_8));
    }
}
