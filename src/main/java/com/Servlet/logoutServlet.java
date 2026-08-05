package com.Servlet;

import java.io.IOException;
import javax.servlet.ServletException;
import javax.servlet.annotation.WebServlet;
import javax.servlet.http.HttpServlet;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;
import javax.servlet.http.HttpSession;

import com.util.WebUtils;

/**
 * Ends the session.
 *
 * <p>POST rather than GET: as a link, any third-party page could sign the user
 * out by pointing an image or iframe at it.
 */
@WebServlet("/logoutServlet")
public class logoutServlet extends HttpServlet {

    private static final long serialVersionUID = 1L;

    @Override
    protected void doPost(HttpServletRequest request, HttpServletResponse response)
            throws ServletException, IOException {

        HttpSession session = request.getSession(false);
        if (session != null) {
            // Drop the whole session rather than just the user attribute, so no
            // per-user state survives the sign-out.
            session.invalidate();
        }

        WebUtils.success(request, "You have been signed out.");
        response.sendRedirect("login.jsp");
    }
}
