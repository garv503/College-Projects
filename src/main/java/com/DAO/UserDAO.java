package com.DAO;

import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.SQLIntegrityConstraintViolationException;

import com.Db.DBConnect;
import com.User.UserDetails;

/**
 * User persistence: registration and credential checking.
 *
 * <p><strong>Passwords are stored as plain text, by explicit project choice.</strong>
 * Anyone who can read the {@code user} table can therefore read every account's
 * real password, and because people reuse passwords, that exposure is not
 * limited to this application. Hashing them instead is a one-line change in
 * {@link #addUser} and {@link #loginUser}; see the Security section of the
 * README before deploying this anywhere real.
 *
 * <p>Connections are borrowed per operation and returned by the
 * try-with-resources blocks, rather than sharing one long-lived connection.
 */
public class UserDAO {

    /** Thrown when a registration collides with an existing account. */
    public static class EmailAlreadyExistsException extends Exception {
        private static final long serialVersionUID = 1L;

        public EmailAlreadyExistsException(String message) {
            super(message);
        }
    }

    /**
     * Creates a user, storing the password exactly as supplied.
     *
     * @throws EmailAlreadyExistsException if the email is already registered
     */
    public boolean addUser(UserDetails us) throws EmailAlreadyExistsException {
        String query = "INSERT INTO user (full_name, email, password) VALUES (?, ?, ?)";

        try (Connection conn = DBConnect.getConnection();
                PreparedStatement ps = conn.prepareStatement(query)) {

            ps.setString(1, us.getName());
            ps.setString(2, us.getEmail());
            ps.setString(3, us.getPassword());

            return ps.executeUpdate() == 1;

        } catch (SQLIntegrityConstraintViolationException e) {
            // The unique index on email is what actually enforces this; catching
            // it here avoids a check-then-insert race between two signups.
            throw new EmailAlreadyExistsException("An account with that email already exists.");
        } catch (SQLException e) {
            e.printStackTrace();
            return false;
        }
    }

    /**
     * Verifies credentials and returns the matching user, or {@code null} when
     * the email is unknown or the password is wrong.
     */
    public UserDetails loginUser(UserDetails us) {
        String query = "SELECT id, full_name, email, password, created_at FROM user WHERE email = ?";

        try (Connection conn = DBConnect.getConnection();
                PreparedStatement ps = conn.prepareStatement(query)) {

            ps.setString(1, us.getEmail());

            try (ResultSet rs = ps.executeQuery()) {
                if (!rs.next()) {
                    return null;
                }

                String stored = rs.getString("password");
                if (stored == null || !stored.equals(us.getPassword())) {
                    return null;
                }

                UserDetails user = map(rs);
                // Not carried into the session; nothing in the UI needs it.
                user.setPassword(null);
                return user;
            }

        } catch (SQLException e) {
            e.printStackTrace();
            return null;
        }
    }

    /** Reports whether an email is already registered (used for friendly form errors). */
    public boolean emailExists(String email) {
        String query = "SELECT 1 FROM user WHERE email = ? LIMIT 1";

        try (Connection conn = DBConnect.getConnection();
                PreparedStatement ps = conn.prepareStatement(query)) {

            ps.setString(1, email);
            try (ResultSet rs = ps.executeQuery()) {
                return rs.next();
            }

        } catch (SQLException e) {
            e.printStackTrace();
            return false;
        }
    }

    private UserDetails map(ResultSet rs) throws SQLException {
        UserDetails user = new UserDetails();
        user.setId(rs.getInt("id"));
        user.setName(rs.getString("full_name"));
        user.setEmail(rs.getString("email"));
        user.setCreatedAt(rs.getTimestamp("created_at"));
        return user;
    }
}
