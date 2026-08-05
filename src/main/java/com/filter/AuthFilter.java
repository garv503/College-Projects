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

/**
 * Requires a signed-in session for everything except the public pages.
 *
 * <p>Access used to be checked by a scriptlet at the top of each JSP, and three
 * of those called {@code sendRedirect} without {@code return}, so the page body
 * kept executing and rendering after the "redirect". Enforcing it in one filter
 * means protection cannot be forgotten on a new page, and a rejected request is
 * stopped before any handler runs.
 */
@WebFilter("/*")
public class AuthFilter implements Filter {

    /** Pages and endpoints reachable without signing in. */
    private static final Set<String> PUBLIC_PATHS = new HashSet<>(Arrays.asList(
            "/",
            "/index.jsp",
            "/login.jsp",
            "/register.jsp",
            "/loginServlet",
            "/UserServlet"));

    /** Static assets are served to anyone; they contain no user data. */
    private static final Set<String> PUBLIC_PREFIXES = new HashSet<>(Arrays.asList(
            "/css/",
            "/js/",
            "/img/"));

    @Override
    public void init(FilterConfig filterConfig) {
    }

    @Override
    public void doFilter(ServletRequest servletRequest, ServletResponse servletResponse, FilterChain chain)
            throws IOException, ServletException {

        HttpServletRequest request = (HttpServletRequest) servletRequest;
        HttpServletResponse response = (HttpServletResponse) servletResponse;

        String path = request.getRequestURI().substring(request.getContextPath().length());

        if (isPublic(path) || isSignedIn(request)) {
            chain.doFilter(request, response);
            return;
        }

        HttpSession session = request.getSession();
        session.setAttribute("flashError", "Please sign in to continue.");
        response.sendRedirect(request.getContextPath() + "/login.jsp");
    }

    @Override
    public void destroy() {
    }

    private boolean isPublic(String path) {
        if (PUBLIC_PATHS.contains(path)) {
            return true;
        }
        for (String prefix : PUBLIC_PREFIXES) {
            if (path.startsWith(prefix)) {
                return true;
            }
        }
        return false;
    }

    private boolean isSignedIn(HttpServletRequest request) {
        HttpSession session = request.getSession(false);
        return session != null && session.getAttribute("userD") != null;
    }
}
