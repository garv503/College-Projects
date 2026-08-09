package com.api;

import java.io.IOException;
import java.util.Map;
import javax.servlet.ServletException;
import javax.servlet.annotation.WebServlet;
import javax.servlet.http.HttpServlet;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;

import com.DAO.PostDAO;
import com.User.UserDetails;
import com.util.Json;
import com.util.WebUtils;

/** Dashboard counters: {@code GET /api/stats}. */
@WebServlet("/api/stats")
public class StatsApi extends HttpServlet {

    private static final long serialVersionUID = 1L;

    private final PostDAO notes = new PostDAO();

    @Override
    protected void doGet(HttpServletRequest request, HttpServletResponse response)
            throws ServletException, IOException {

        UserDetails user = WebUtils.currentUser(request);

        Map<String, Object> stats = Json.map();
        stats.put("totalNotes", notes.countNotes(user.getId()));
        stats.put("pinnedNotes", notes.countPinned(user.getId()));
        Json.ok(response, stats);
    }
}
