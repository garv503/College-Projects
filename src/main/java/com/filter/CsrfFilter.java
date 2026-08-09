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

import com.util.Csrf;
import com.util.Json;

/**
 * Rejects state-changing API calls that do not carry the session's CSRF token.
 *
 * <p>Guards every method that is not read-only, not just POST, because the API
 * also updates with PUT and removes with DELETE.
 *
 * <p>Sign-in and registration are exempt: they are the requests that establish a
 * session, so there is no meaningful token to present yet, and there is nothing
 * to forge - an attacker gains nothing by causing a victim's browser to log in
 * as the attacker's own account would require the attacker's credentials.
 */
@WebFilter("/api/*")
public class CsrfFilter implements Filter {

    private static final Set<String> SAFE_METHODS = new HashSet<>(Arrays.asList(
            "GET", "HEAD", "OPTIONS"));

    private static final Set<String> EXEMPT_PATHS = new HashSet<>(Arrays.asList(
            "/api/auth/login",
            "/api/auth/register"));

    @Override
    public void init(FilterConfig filterConfig) {
    }

    @Override
    public void doFilter(ServletRequest servletRequest, ServletResponse servletResponse, FilterChain chain)
            throws IOException, ServletException {

        HttpServletRequest request = (HttpServletRequest) servletRequest;
        HttpServletResponse response = (HttpServletResponse) servletResponse;

        String path = request.getRequestURI().substring(request.getContextPath().length());
        boolean needsToken = !SAFE_METHODS.contains(request.getMethod().toUpperCase())
                && !EXEMPT_PATHS.contains(path);

        if (needsToken && !Csrf.isValid(request)) {
            Json.error(response, HttpServletResponse.SC_FORBIDDEN,
                    "Invalid or missing security token. Please reload the page and try again.");
            return;
        }

        chain.doFilter(request, response);
    }

    @Override
    public void destroy() {
    }
}
