package com.api;

import java.io.IOException;
import java.util.Map;
import javax.servlet.ServletException;
import javax.servlet.annotation.WebServlet;
import javax.servlet.http.HttpServlet;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;
import javax.servlet.http.HttpSession;

import com.DAO.UserDAO;
import com.User.UserDetails;
import com.fasterxml.jackson.databind.JsonNode;
import com.util.Csrf;
import com.util.Json;
import com.util.WebUtils;

/**
 * Account endpoints: {@code /api/auth/session|register|login|logout}.
 *
 * <p>Replaces the servlets that used to redirect between JSPs. Authentication is
 * still the container session cookie, so the CSRF protection and the ownership
 * rules behind it are unchanged - only the response format moved to JSON.
 */
@WebServlet("/api/auth/*")
public class AuthApi extends HttpServlet {

    private static final long serialVersionUID = 1L;
    private static final int MIN_PASSWORD_LENGTH = 8;
    private static final int MAX_NAME_LENGTH = 100;
    private static final int MAX_EMAIL_LENGTH = 190;

    private final UserDAO users = new UserDAO();

    @Override
    protected void doGet(HttpServletRequest request, HttpServletResponse response)
            throws ServletException, IOException {

        if (!"/session".equals(request.getPathInfo())) {
            Json.error(response, HttpServletResponse.SC_NOT_FOUND, "Unknown endpoint.");
            return;
        }

        // Always 200, even when signed out: the front end calls this on load to
        // decide what to render, and "nobody is signed in" is a normal answer.
        UserDetails user = WebUtils.currentUser(request);
        Map<String, Object> body = Json.map();
        body.put("user", user == null ? null : publicView(user));
        body.put("csrfToken", Csrf.token(request));
        Json.ok(response, body);
    }

    @Override
    protected void doPost(HttpServletRequest request, HttpServletResponse response)
            throws ServletException, IOException {

        String action = request.getPathInfo() == null ? "" : request.getPathInfo();

        switch (action) {
            case "/register":
                register(request, response);
                break;
            case "/login":
                login(request, response);
                break;
            case "/logout":
                logout(request, response);
                break;
            default:
                Json.error(response, HttpServletResponse.SC_NOT_FOUND, "Unknown endpoint.");
        }
    }

    private void register(HttpServletRequest request, HttpServletResponse response) throws IOException {
        JsonNode body = Json.read(request);
        String name = Json.text(body, "name");
        String email = Json.text(body, "email");
        String password = body == null || !body.hasNonNull("password") ? null : body.get("password").asText();

        String problem = validateRegistration(name, email, password);
        if (problem != null) {
            Json.error(response, HttpServletResponse.SC_BAD_REQUEST, problem);
            return;
        }

        UserDetails user = new UserDetails();
        user.setName(name);
        user.setEmail(email.toLowerCase());
        user.setPassword(password);

        try {
            if (users.addUser(user)) {
                Json.write(response, HttpServletResponse.SC_CREATED,
                        Map.of("message", "Account created. Please sign in."));
            } else {
                Json.error(response, HttpServletResponse.SC_INTERNAL_SERVER_ERROR,
                        "Could not create your account. Please try again.");
            }
        } catch (UserDAO.EmailAlreadyExistsException e) {
            Json.error(response, HttpServletResponse.SC_CONFLICT, e.getMessage());
        }
    }

    private void login(HttpServletRequest request, HttpServletResponse response) throws IOException {
        JsonNode body = Json.read(request);
        String email = Json.text(body, "email");
        String password = body == null || !body.hasNonNull("password") ? null : body.get("password").asText();

        if (email == null || password == null || password.isEmpty()) {
            Json.error(response, HttpServletResponse.SC_BAD_REQUEST,
                    "Please enter both your email and password.");
            return;
        }

        UserDetails credentials = new UserDetails();
        credentials.setEmail(email.toLowerCase());
        credentials.setPassword(password);

        UserDetails user = users.loginUser(credentials);
        if (user == null) {
            // One message for both unknown email and wrong password, so the
            // response cannot be used to discover which emails are registered.
            Json.error(response, HttpServletResponse.SC_UNAUTHORIZED, "Invalid email or password.");
            return;
        }

        // Issue a new session id on sign-in, so a session id planted before
        // login cannot be reused afterwards (session fixation).
        HttpSession existing = request.getSession(false);
        if (existing != null) {
            existing.invalidate();
        }

        HttpSession session = request.getSession(true);
        session.setAttribute("userD", user);
        session.setMaxInactiveInterval(60 * 60);

        Map<String, Object> result = Json.map();
        result.put("user", publicView(user));
        // The new session needs a matching token before the client can write.
        result.put("csrfToken", Csrf.token(request));
        Json.ok(response, result);
    }

    private void logout(HttpServletRequest request, HttpServletResponse response) throws IOException {
        HttpSession session = request.getSession(false);
        if (session != null) {
            session.invalidate();
        }
        Json.ok(response, Map.of("message", "You have been signed out."));
    }

    /** The user fields the client is allowed to see. Never includes the password. */
    private Map<String, Object> publicView(UserDetails user) {
        Map<String, Object> view = Json.map();
        view.put("id", user.getId());
        view.put("name", user.getName());
        view.put("email", user.getEmail());
        view.put("initial", user.getInitial());
        view.put("createdAt", user.getCreatedAt() == null ? null : user.getCreatedAt().getTime());
        return view;
    }

    private String validateRegistration(String name, String email, String password) {
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
