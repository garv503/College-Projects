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

/** Updates a note the signed-in user owns. */
@WebServlet("/NoteEditServlet")
public class NoteEditServlet extends HttpServlet {

    private static final long serialVersionUID = 1L;

    @Override
    protected void doPost(HttpServletRequest request, HttpServletResponse response)
            throws ServletException, IOException {

        UserDetails user = WebUtils.currentUser(request);
        if (user == null) {
            response.sendRedirect("login.jsp");
            return;
        }

        int noteId = WebUtils.intParam(request, "noteid", -1);
        if (noteId < 1) {
            WebUtils.error(request, "That note could not be found.");
            response.sendRedirect("showNotes.jsp");
            return;
        }

        String title = WebUtils.trimmed(request, "title");
        String content = WebUtils.trimmed(request, "content");

        String problem = AddNotesServlet.validate(title, content);
        if (problem != null) {
            WebUtils.error(request, problem);
            response.sendRedirect("edit.jsp?note_id=" + noteId);
            return;
        }

        // Scoped by owner: editing someone else's note updates no rows and is
        // reported as not found, rather than succeeding.
        if (new PostDAO().updateNote(noteId, user.getId(), title, content)) {
            WebUtils.success(request, "Note updated.");
        } else {
            WebUtils.error(request, "That note could not be found.");
        }

        response.sendRedirect("showNotes.jsp");
    }
}
