package com.filter;

import java.io.IOException;
import javax.servlet.Filter;
import javax.servlet.FilterChain;
import javax.servlet.FilterConfig;
import javax.servlet.RequestDispatcher;
import javax.servlet.ServletContext;
import javax.servlet.ServletException;
import javax.servlet.ServletRequest;
import javax.servlet.ServletResponse;
import javax.servlet.annotation.WebFilter;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;

/**
 * Serves the React shell for client-side routes.
 *
 * <p>Routing happens in the browser, so a path like {@code /notes} has no file
 * behind it. Opening or refreshing that URL directly would otherwise 404 -
 * Tomcat looks for a resource that was never on disk. This forwards such
 * requests to {@code index.html} and lets the router decide what to render.
 *
 * <p>Requests for the API and for real files (anything with an extension, such
 * as the hashed JS and CSS bundles) are left alone.
 */
@WebFilter("/*")
public class SpaFilter implements Filter {

    private ServletContext context;

    @Override
    public void init(FilterConfig filterConfig) {
        this.context = filterConfig.getServletContext();
    }

    @Override
    public void doFilter(ServletRequest servletRequest, ServletResponse servletResponse, FilterChain chain)
            throws IOException, ServletException {

        HttpServletRequest request = (HttpServletRequest) servletRequest;
        HttpServletResponse response = (HttpServletResponse) servletResponse;

        String path = request.getRequestURI().substring(request.getContextPath().length());

        if (shouldForward(request, path)) {
            RequestDispatcher dispatcher = request.getRequestDispatcher("/index.html");
            dispatcher.forward(request, response);
            return;
        }

        chain.doFilter(request, response);
    }

    @Override
    public void destroy() {
    }

    private boolean shouldForward(HttpServletRequest request, String path) {
        // Only navigations: never rewrite an API call or a form/fetch write.
        if (!"GET".equalsIgnoreCase(request.getMethod()) || path.startsWith("/api/")) {
            return false;
        }

        // "/" is served by the welcome file, and anything with a file extension
        // is a real asset - forwarding either would break normal serving.
        if (path.isEmpty() || "/".equals(path) || hasExtension(path)) {
            return false;
        }

        // Guard against forwarding a path that does exist on disk.
        try {
            return context.getResource(path) == null;
        } catch (java.net.MalformedURLException e) {
            return false;
        }
    }

    private boolean hasExtension(String path) {
        int lastSlash = path.lastIndexOf('/');
        int lastDot = path.lastIndexOf('.');
        return lastDot > lastSlash;
    }
}
