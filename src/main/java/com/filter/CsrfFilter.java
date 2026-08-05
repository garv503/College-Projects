package com.filter;

import java.io.IOException;
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

/**
 * Rejects state-changing requests that do not carry the session's CSRF token.
 *
 * <p>Applies to POST only. Every write in the app is now a POST for exactly this
 * reason: deleting a note used to be a plain GET link, so any page that could
 * make a signed-in user's browser issue a request - even an {@code <img>} tag -
 * could delete their notes.
 */
@WebFilter("/*")
public class CsrfFilter implements Filter {

    @Override
    public void init(FilterConfig filterConfig) {
    }

    @Override
    public void doFilter(ServletRequest servletRequest, ServletResponse servletResponse, FilterChain chain)
            throws IOException, ServletException {

        HttpServletRequest request = (HttpServletRequest) servletRequest;
        HttpServletResponse response = (HttpServletResponse) servletResponse;

        boolean isWrite = "POST".equalsIgnoreCase(request.getMethod());

        if (isWrite && !Csrf.isValid(request)) {
            response.sendError(HttpServletResponse.SC_FORBIDDEN,
                    "Invalid or missing security token. Please reload the page and try again.");
            return;
        }

        chain.doFilter(request, response);
    }

    @Override
    public void destroy() {
    }
}
