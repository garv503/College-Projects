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

/** Pins or unpins a note, so it sorts to the top of the list. */
@WebServlet("/PinServlet")
public class PinServlet extends HttpServlet {

    private static final long serialVersionUID = 1L;

    @Override
    protected void doPost(HttpServletRequest request, HttpServletResponse response)
            throws ServletException, IOException {

        UserDetails user = WebUtils.currentUser(request);
        if (user == null) {
            response.sendRedirect("login.jsp");
            return;
        }

        int noteId = WebUtils.intParam(request, "note_id", -1);

        if (noteId < 1 || !new PostDAO().togglePin(noteId, user.getId())) {
            WebUtils.error(request, "That note could not be found.");
        }

        // Preserve an active search so pinning from search results keeps context.
        String search = WebUtils.trimmed(request, "q");
        response.sendRedirect(search == null
                ? "showNotes.jsp"
                : "showNotes.jsp?q=" + java.net.URLEncoder.encode(search, "UTF-8"));
    }
}
