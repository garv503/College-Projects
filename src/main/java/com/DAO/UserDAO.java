package com.DAO;

import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.SQLIntegrityConstraintViolationException;

import com.Db.DBConnect;
import com.User.UserDetails;
import com.util.PasswordHasher;

/**
 * User persistence: registration and credential checking.
 *
 * <p>Connections are borrowed per operation and returned by the
 * try-with-resources blocks, rather than sharing one long-lived connection.
 */
public class UserDAO {

    /** Thrown when a registration collides with an existing account. */
    public static class EmailAlreadyExistsException extends Exception {
        public EmailAlreadyExistsException(String message) {
            super(message);
        }
    }

    /**
     * Creates a user, storing a PBKDF2 hash of the password.
     *
     * @throws EmailAlreadyExistsException if the email is already registered
     */
    public boolean addUser(UserDetails us) throws EmailAlreadyExistsException {
        String query = "INSERT INTO user (full_name, email, password) VALUES (?, ?, ?)";

        try (Connection conn = DBConnect.getConnection();
                PreparedStatement ps = conn.prepareStatement(query)) {

            ps.setString(1, us.getName());
            ps.setString(2, us.getEmail());
            ps.setString(3, PasswordHasher.hash(us.getPassword()));

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
     *
     * <p>Accounts created before hashing existed still hold a raw password. Those
     * are detected, verified against the raw value once, and then transparently
     * re-saved as a hash, so old accounts keep working and self-heal on first
     * successful login.
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
                String supplied = us.getPassword();
                boolean legacyPlaintext = !PasswordHasher.isHashed(stored);

                boolean valid = legacyPlaintext
                        ? stored.equals(supplied)
                        : PasswordHasher.matches(supplied, stored);

                if (!valid) {
                    return null;
                }

                UserDetails user = map(rs);

                if (legacyPlaintext) {
                    upgradeStoredPassword(user.getId(), supplied);
                }

                // Never carry the credential around in the session object.
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

    /** Replaces a legacy plaintext password with a hash of the same value. */
    private void upgradeStoredPassword(int userId, String rawPassword) {
        String query = "UPDATE user SET password = ? WHERE id = ?";

        try (Connection conn = DBConnect.getConnection();
                PreparedStatement ps = conn.prepareStatement(query)) {

            ps.setString(1, PasswordHasher.hash(rawPassword));
            ps.setInt(2, userId);
            ps.executeUpdate();

        } catch (SQLException e) {
            // A failed upgrade must not fail the login itself; it will be
            // retried on the user's next successful sign-in.
            e.printStackTrace();
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
