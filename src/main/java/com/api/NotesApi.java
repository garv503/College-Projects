package com.api;

import java.io.IOException;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import javax.servlet.ServletException;
import javax.servlet.annotation.WebServlet;
import javax.servlet.http.HttpServlet;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;

import com.DAO.PostDAO;
import com.User.Post;
import com.User.UserDetails;
import com.fasterxml.jackson.databind.JsonNode;
import com.util.Json;
import com.util.WebUtils;

/**
 * Note endpoints under {@code /api/notes}.
 *
 * <pre>
 *   GET    /api/notes          list (optional ?q= search)
 *   POST   /api/notes          create
 *   GET    /api/notes/{id}     fetch one
 *   PUT    /api/notes/{id}     update
 *   DELETE /api/notes/{id}     delete
 *   POST   /api/notes/{id}/pin toggle pinned
 * </pre>
 *
 * <p>Every call resolves the owner from the session and passes it to the DAO, so
 * a note id belonging to someone else affects no rows and reads as "not found".
 * The DAO layer is used exactly as the JSP version used it - unchanged.
 */
@WebServlet("/api/notes/*")
public class NotesApi extends HttpServlet {

    private static final long serialVersionUID = 1L;
    static final int MAX_TITLE_LENGTH = 200;
    static final int MAX_CONTENT_LENGTH = 20_000;

    private final PostDAO notes = new PostDAO();

    @Override
    protected void doGet(HttpServletRequest request, HttpServletResponse response)
            throws ServletException, IOException {

        UserDetails user = WebUtils.currentUser(request);
        String path = path(request);

        if (path.isEmpty()) {
            String search = WebUtils.trimmed(request, "q");
            List<Post> found = search == null
                    ? notes.getNotes(user.getId())
                    : notes.searchNotes(user.getId(), search);

            List<Map<String, Object>> items = new ArrayList<>();
            for (Post note : found) {
                items.add(view(note));
            }
            Json.ok(response, Map.of("notes", items));
            return;
        }

        int id = idFrom(path);
        Post note = id < 1 ? null : notes.getNoteById(id, user.getId());
        if (note == null) {
            notFound(response);
            return;
        }
        Json.ok(response, Map.of("note", view(note)));
    }

    @Override
    protected void doPost(HttpServletRequest request, HttpServletResponse response)
            throws ServletException, IOException {

        UserDetails user = WebUtils.currentUser(request);
        String path = path(request);

        if (path.endsWith("/pin")) {
            int id = idFrom(path.substring(0, path.length() - "/pin".length()));
            if (id < 1 || !notes.togglePin(id, user.getId())) {
                notFound(response);
                return;
            }
            Post updated = notes.getNoteById(id, user.getId());
            Json.ok(response, Map.of("note", view(updated)));
            return;
        }

        if (!path.isEmpty()) {
            Json.error(response, HttpServletResponse.SC_NOT_FOUND, "Unknown endpoint.");
            return;
        }

        JsonNode body = Json.read(request);
        String title = Json.text(body, "title");
        String content = Json.text(body, "content");

        String problem = validate(title, content);
        if (problem != null) {
            Json.error(response, HttpServletResponse.SC_BAD_REQUEST, problem);
            return;
        }

        if (!notes.addNote(title, content, user.getId())) {
            Json.error(response, HttpServletResponse.SC_INTERNAL_SERVER_ERROR,
                    "Could not save your note. Please try again.");
            return;
        }
        Json.write(response, HttpServletResponse.SC_CREATED, Map.of("message", "Note added."));
    }

    @Override
    protected void doPut(HttpServletRequest request, HttpServletResponse response)
            throws ServletException, IOException {

        UserDetails user = WebUtils.currentUser(request);
        int id = idFrom(path(request));
        if (id < 1) {
            notFound(response);
            return;
        }

        JsonNode body = Json.read(request);
        String title = Json.text(body, "title");
        String content = Json.text(body, "content");

        String problem = validate(title, content);
        if (problem != null) {
            Json.error(response, HttpServletResponse.SC_BAD_REQUEST, problem);
            return;
        }

        if (!notes.updateNote(id, user.getId(), title, content)) {
            notFound(response);
            return;
        }
        Json.ok(response, Map.of("message", "Note updated."));
    }

    @Override
    protected void doDelete(HttpServletRequest request, HttpServletResponse response)
            throws ServletException, IOException {

        UserDetails user = WebUtils.currentUser(request);
        int id = idFrom(path(request));

        if (id < 1 || !notes.deleteNote(id, user.getId())) {
            notFound(response);
            return;
        }
        Json.ok(response, Map.of("message", "Note deleted."));
    }

    /** Path after {@code /api/notes}, normalised to "" for the collection itself. */
    private String path(HttpServletRequest request) {
        String info = request.getPathInfo();
        if (info == null || "/".equals(info)) {
            return "";
        }
        return info;
    }

    /** Parses "/12" into 12; returns -1 for anything that is not a positive id. */
    private int idFrom(String path) {
        String raw = path.startsWith("/") ? path.substring(1) : path;
        try {
            int id = Integer.parseInt(raw);
            return id < 1 ? -1 : id;
        } catch (NumberFormatException e) {
            return -1;
        }
    }

    /**
     * The same response for a missing note and for someone else's note, so the
     * API cannot be used to discover which note ids exist.
     */
    private void notFound(HttpServletResponse response) throws IOException {
        Json.error(response, HttpServletResponse.SC_NOT_FOUND, "That note could not be found.");
    }

    private Map<String, Object> view(Post note) {
        Map<String, Object> view = Json.map();
        view.put("id", note.getId());
        view.put("title", note.getTitle());
        view.put("content", note.getContent());
        view.put("pinned", note.isPinned());
        view.put("edited", note.isEdited());
        // Epoch millis: unambiguous over the wire, formatted in the browser's
        // own locale and timezone by the client.
        view.put("createdAt", note.getCreatedAt() == null ? null : note.getCreatedAt().getTime());
        view.put("updatedAt", note.getUpdatedAt() == null ? null : note.getUpdatedAt().getTime());
        return view;
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
