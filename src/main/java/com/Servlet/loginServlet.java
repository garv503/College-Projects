package com.Servlet;

import java.io.IOException;
import javax.servlet.ServletException;
import javax.servlet.annotation.WebServlet;
import javax.servlet.http.HttpServlet;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;
import javax.servlet.http.HttpSession;

import com.DAO.UserDAO;
import com.User.UserDetails;
import com.util.WebUtils;

/** Handles sign-in. */
@WebServlet("/loginServlet")
public class loginServlet extends HttpServlet {

    private static final long serialVersionUID = 1L;

    @Override
    protected void doPost(HttpServletRequest request, HttpServletResponse response)
            throws ServletException, IOException {

        String email = WebUtils.trimmed(request, "uemail");
        String password = request.getParameter("upassword");

        if (email == null || password == null || password.isEmpty()) {
            WebUtils.error(request, "Please enter both your email and password.");
            response.sendRedirect("login.jsp");
            return;
        }

        UserDetails credentials = new UserDetails();
        credentials.setEmail(email.toLowerCase());
        credentials.setPassword(password);

        UserDetails user = new UserDAO().loginUser(credentials);

        if (user == null) {
            // One message for both "no such email" and "wrong password", so the
            // response cannot be used to discover which emails are registered.
            WebUtils.error(request, "Invalid email or password.");
            response.sendRedirect("login.jsp");
            return;
        }

        // Issue a new session id on sign-in, so a session id planted before
        // login cannot be reused afterwards (session fixation).
        HttpSession oldSession = request.getSession(false);
        if (oldSession != null) {
            oldSession.invalidate();
        }

        HttpSession session = request.getSession(true);
        session.setAttribute("userD", user);
        session.setMaxInactiveInterval(60 * 60);

        WebUtils.success(request, "Welcome back, " + user.getName() + ".");
        response.sendRedirect("home.jsp");
    }
}
