package com.Servlet;

import java.io.IOException;
import javax.servlet.ServletException;
import javax.servlet.annotation.WebServlet;
import javax.servlet.http.HttpServlet;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;

import com.DAO.PostDAO;
import com.User.UserDetails;
import com.util.WebUtils;

/** Creates a note for the signed-in user. */
@WebServlet("/AddNotesServlet")
public class AddNotesServlet extends HttpServlet {

    private static final long serialVersionUID = 1L;
    static final int MAX_TITLE_LENGTH = 200;
    static final int MAX_CONTENT_LENGTH = 20_000;

    @Override
    protected void doPost(HttpServletRequest request, HttpServletResponse response)
            throws ServletException, IOException {

        // The author is the signed-in user. It used to come from a hidden form
        // field, so anyone could post a note into another account by editing it.
        UserDetails user = WebUtils.currentUser(request);
        if (user == null) {
            response.sendRedirect("login.jsp");
            return;
        }

        String title = WebUtils.trimmed(request, "title");
        String content = WebUtils.trimmed(request, "content");

        String problem = validate(title, content);
        if (problem != null) {
            WebUtils.error(request, problem);
            response.sendRedirect("addNotes.jsp");
            return;
        }

        if (new PostDAO().addNote(title, content, user.getId())) {
            WebUtils.success(request, "Note added.");
            response.sendRedirect("showNotes.jsp");
        } else {
            WebUtils.error(request, "Could not save your note. Please try again.");
            response.sendRedirect("addNotes.jsp");
        }
    }

    static String validate(String title, String content) {
        if (title == null) {
            return "Please enter a title.";
        }
        if (title.length() > MAX_TITLE_LENGTH) {
            return "Title must be " + MAX_TITLE_LENGTH + " characters or fewer.";
        }
        if (content == null) {
            return "Please enter some content.";
        }
        if (content.length() > MAX_CONTENT_LENGTH) {
            return "Content must be " + MAX_CONTENT_LENGTH + " characters or fewer.";
        }
        return null;
    }
}
