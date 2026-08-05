package com.Servlet;

import java.io.IOException;
import javax.servlet.ServletException;
import javax.servlet.annotation.WebServlet;
import javax.servlet.http.HttpServlet;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;

import com.DAO.UserDAO;
import com.User.UserDetails;
import com.util.WebUtils;

/** Handles registration. */
@WebServlet("/UserServlet")
public class UserServlet extends HttpServlet {

    private static final long serialVersionUID = 1L;
    private static final int MIN_PASSWORD_LENGTH = 8;
    private static final int MAX_NAME_LENGTH = 100;
    private static final int MAX_EMAIL_LENGTH = 190;

    @Override
    protected void doPost(HttpServletRequest request, HttpServletResponse response)
            throws ServletException, IOException {

        String name = WebUtils.trimmed(request, "fname");
        String email = WebUtils.trimmed(request, "uemail");
        String password = request.getParameter("upassword");

        String problem = validate(name, email, password);
        if (problem != null) {
            WebUtils.error(request, problem);
            response.sendRedirect("register.jsp");
            return;
        }

        UserDetails user = new UserDetails();
        user.setName(name);
        user.setEmail(email.toLowerCase());
        user.setPassword(password);

        UserDAO dao = new UserDAO();
        try {
            if (dao.addUser(user)) {
                WebUtils.success(request, "Account created. Please sign in.");
                response.sendRedirect("login.jsp");
            } else {
                WebUtils.error(request, "Could not create your account. Please try again.");
                response.sendRedirect("register.jsp");
            }
        } catch (UserDAO.EmailAlreadyExistsException e) {
            WebUtils.error(request, e.getMessage());
            response.sendRedirect("register.jsp");
        }
    }

    /** Returns a message describing the first problem found, or {@code null} when valid. */
    private String validate(String name, String email, String password) {
        if (name == null) {
            return "Please enter your full name.";
        }
        if (name.length() > MAX_NAME_LENGTH) {
            return "Name must be " + MAX_NAME_LENGTH + " characters or fewer.";
        }
        if (!WebUtils.looksLikeEmail(email)) {
            return "Please enter a valid email address.";
        }
        if (email.length() > MAX_EMAIL_LENGTH) {
            return "Email must be " + MAX_EMAIL_LENGTH + " characters or fewer.";
        }
        if (password == null || password.length() < MIN_PASSWORD_LENGTH) {
            return "Password must be at least " + MIN_PASSWORD_LENGTH + " characters.";
        }
        return null;
    }
}
