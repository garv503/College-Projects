package com.DAO;

import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.ArrayList;
import java.util.List;

import com.Db.DBConnect;
import com.User.Post;

/**
 * Note persistence.
 *
 * <p>Every read and write is scoped by owner id. Previously a note could be
 * fetched, edited, or deleted by id alone, so any signed-in user could act on
 * another user's notes just by changing the number in the URL. Passing the
 * owner into the {@code WHERE} clause means a mismatched id simply affects zero
 * rows instead of touching someone else's data.
 */
public class PostDAO {

    private static final String COLUMNS =
            "id, title, content, pinned, uid, created_at, updated_at";

    /** Creates a note owned by {@code uid}. */
    public boolean addNote(String title, String content, int uid) {
        String query = "INSERT INTO post (title, content, uid) VALUES (?, ?, ?)";

        try (Connection conn = DBConnect.getConnection();
                PreparedStatement ps = conn.prepareStatement(query)) {

            ps.setString(1, title);
            ps.setString(2, content);
            ps.setInt(3, uid);

            return ps.executeUpdate() == 1;

        } catch (SQLException e) {
            e.printStackTrace();
            return false;
        }
    }

    /** Returns every note owned by {@code uid}, pinned first, then newest first. */
    public List<Post> getNotes(int uid) {
        String query = "SELECT " + COLUMNS + " FROM post WHERE uid = ? "
                + "ORDER BY pinned DESC, created_at DESC";

        try (Connection conn = DBConnect.getConnection();
                PreparedStatement ps = conn.prepareStatement(query)) {

            ps.setInt(1, uid);
            return mapAll(ps);

        } catch (SQLException e) {
            e.printStackTrace();
            return new ArrayList<>();
        }
    }

    /**
     * Returns the user's notes whose title or content matches {@code term}.
     *
     * <p>The term is bound as a parameter and the wildcards are added around the
     * bound value, so a term containing SQL syntax is still just text.
     */
    public List<Post> searchNotes(int uid, String term) {
        String query = "SELECT " + COLUMNS + " FROM post "
                + "WHERE uid = ? AND (title LIKE ? ESCAPE '!' OR content LIKE ? ESCAPE '!') "
                + "ORDER BY pinned DESC, created_at DESC";

        // Escape LIKE's own wildcards so a literal % or _ searches for itself.
        String pattern = "%" + term.replace("!", "!!")
                                   .replace("%", "!%")
                                   .replace("_", "!_") + "%";

        try (Connection conn = DBConnect.getConnection();
                PreparedStatement ps = conn.prepareStatement(query)) {

            ps.setInt(1, uid);
            ps.setString(2, pattern);
            ps.setString(3, pattern);
            return mapAll(ps);

        } catch (SQLException e) {
            e.printStackTrace();
            return new ArrayList<>();
        }
    }

    /**
     * Returns a single note, but only if {@code uid} owns it.
     *
     * @return the note, or {@code null} when it does not exist or belongs to
     *         someone else - the caller cannot tell those apart, which avoids
     *         confirming that another user's note id exists
     */
    public Post getNoteById(int noteId, int uid) {
        String query = "SELECT " + COLUMNS + " FROM post WHERE id = ? AND uid = ?";

        try (Connection conn = DBConnect.getConnection();
                PreparedStatement ps = conn.prepareStatement(query)) {

            ps.setInt(1, noteId);
            ps.setInt(2, uid);

            try (ResultSet rs = ps.executeQuery()) {
                return rs.next() ? map(rs) : null;
            }

        } catch (SQLException e) {
            e.printStackTrace();
            return null;
        }
    }

    /** Updates a note the caller owns. Returns false if they do not own it. */
    public boolean updateNote(int noteId, int uid, String title, String content) {
        String query = "UPDATE post SET title = ?, content = ? WHERE id = ? AND uid = ?";

        try (Connection conn = DBConnect.getConnection();
                PreparedStatement ps = conn.prepareStatement(query)) {

            ps.setString(1, title);
            ps.setString(2, content);
            ps.setInt(3, noteId);
            ps.setInt(4, uid);

            return ps.executeUpdate() == 1;

        } catch (SQLException e) {
            e.printStackTrace();
            return false;
        }
    }

    /** Deletes a note the caller owns. Returns false if they do not own it. */
    public boolean deleteNote(int noteId, int uid) {
        String query = "DELETE FROM post WHERE id = ? AND uid = ?";

        try (Connection conn = DBConnect.getConnection();
                PreparedStatement ps = conn.prepareStatement(query)) {

            ps.setInt(1, noteId);
            ps.setInt(2, uid);

            return ps.executeUpdate() == 1;

        } catch (SQLException e) {
            e.printStackTrace();
            return false;
        }
    }

    /** Flips the pinned flag on a note the caller owns. */
    public boolean togglePin(int noteId, int uid) {
        String query = "UPDATE post SET pinned = NOT pinned WHERE id = ? AND uid = ?";

        try (Connection conn = DBConnect.getConnection();
                PreparedStatement ps = conn.prepareStatement(query)) {

            ps.setInt(1, noteId);
            ps.setInt(2, uid);

            return ps.executeUpdate() == 1;

        } catch (SQLException e) {
            e.printStackTrace();
            return false;
        }
    }

    /** Counts the user's notes, for the dashboard. */
    public int countNotes(int uid) {
        return count("SELECT COUNT(*) FROM post WHERE uid = ?", uid);
    }

    /** Counts the user's pinned notes, for the dashboard. */
    public int countPinned(int uid) {
        return count("SELECT COUNT(*) FROM post WHERE uid = ? AND pinned = TRUE", uid);
    }

    private int count(String query, int uid) {
        try (Connection conn = DBConnect.getConnection();
                PreparedStatement ps = conn.prepareStatement(query)) {

            ps.setInt(1, uid);
            try (ResultSet rs = ps.executeQuery()) {
                return rs.next() ? rs.getInt(1) : 0;
            }

        } catch (SQLException e) {
            e.printStackTrace();
            return 0;
        }
    }

    private List<Post> mapAll(PreparedStatement ps) throws SQLException {
        List<Post> notes = new ArrayList<>();
        try (ResultSet rs = ps.executeQuery()) {
            while (rs.next()) {
                notes.add(map(rs));
            }
        }
        return notes;
    }

    private Post map(ResultSet rs) throws SQLException {
        Post post = new Post();
        post.setId(rs.getInt("id"));
        post.setTitle(rs.getString("title"));
        post.setContent(rs.getString("content"));
        post.setPinned(rs.getBoolean("pinned"));
        post.setUid(rs.getInt("uid"));
        post.setCreatedAt(rs.getTimestamp("created_at"));
        post.setUpdatedAt(rs.getTimestamp("updated_at"));
        return post;
    }
}
