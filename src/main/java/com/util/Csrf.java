package com.util;

import java.security.SecureRandom;
import java.util.Base64;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpSession;

/**
 * Per-session CSRF tokens.
 *
 * <p>Without these, another site can make a visitor's browser submit a request
 * to E-Notes using their live session cookie. Every state-changing form carries
 * the session's token in a hidden field, and {@code CsrfFilter} rejects any
 * write that does not present it - an attacker's page cannot read the token, so
 * it cannot forge the request.
 */
public final class Csrf {

    public static final String SESSION_ATTRIBUTE = "csrfToken";
    public static final String PARAMETER_NAME = "csrfToken";

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
        String supplied = request.getParameter(PARAMETER_NAME);

        return expected != null && PasswordHasher.constantTimeEquals(expected, supplied);
    }
}
