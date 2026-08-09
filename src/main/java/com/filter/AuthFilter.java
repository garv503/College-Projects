package com.filter;

import java.io.IOException;
import java.util.Arrays;
import java.util.HashSet;
import java.util.Set;
import javax.servlet.Filter;
import javax.servlet.FilterChain;
import javax.servlet.FilterConfig;
import javax.servlet.ServletException;
import javax.servlet.ServletRequest;
import javax.servlet.ServletResponse;
import javax.servlet.annotation.WebFilter;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;
import javax.servlet.http.HttpSession;

import com.util.Json;

/**
 * Requires a signed-in session for the API, except the public auth endpoints.
 *
 * <p>Only {@code /api/*} is guarded. Everything else is the React bundle - HTML,
 * JS and CSS containing no user data - which is served to anyone; the app calls
 * {@code /api/auth/session} on load and renders a signed-out view if there is no
 * session. Because unauthenticated API calls are answered with 401 JSON rather
 * than a redirect to a login page, the client can tell "not signed in" apart
 * from "here is a page".
 */
@WebFilter("/api/*")
public class AuthFilter implements Filter {

    /** Endpoints that must work before there is a session. */
    private static final Set<String> PUBLIC_API_PATHS = new HashSet<>(Arrays.asList(
            "/api/auth/session",
            "/api/auth/login",
            "/api/auth/register",
            "/api/auth/logout"));

    @Override
    public void init(FilterConfig filterConfig) {
    }

    @Override
    public void doFilter(ServletRequest servletRequest, ServletResponse servletResponse, FilterChain chain)
            throws IOException, ServletException {

        HttpServletRequest request = (HttpServletRequest) servletRequest;
        HttpServletResponse response = (HttpServletResponse) servletResponse;

        String path = request.getRequestURI().substring(request.getContextPath().length());

        if (PUBLIC_API_PATHS.contains(path) || isSignedIn(request)) {
            chain.doFilter(request, response);
            return;
        }

        Json.error(response, HttpServletResponse.SC_UNAUTHORIZED, "Please sign in to continue.");
    }

    @Override
    public void destroy() {
    }

    private boolean isSignedIn(HttpServletRequest request) {
        HttpSession session = request.getSession(false);
        return session != null && session.getAttribute("userD") != null;
    }
}
