package com.Db;

import java.sql.Connection;
import java.sql.DatabaseMetaData;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Statement;
import javax.servlet.ServletContext;
import javax.servlet.ServletContextEvent;
import javax.servlet.ServletContextListener;
import javax.servlet.annotation.WebListener;

/**
 * Brings the database up to the shape the application expects, at startup.
 *
 * <p>Every step is idempotent and guarded by an existence check, so this is safe
 * to run on each boot: a fresh database gets created, an older one gets
 * upgraded in place, and an already-current one is left untouched.
 *
 * <p>Also disposes of the connection pool on shutdown so redeploys do not leak
 * connections.
 */
@WebListener
public class DatabaseInitializer implements ServletContextListener {

    /** Set on startup so messages land in the container log, not a hidden console. */
    private ServletContext servletContext;

    @Override
    public void contextInitialized(ServletContextEvent event) {
        this.servletContext = event.getServletContext();

        try (Connection conn = DBConnect.getConnection()) {
            createTables(conn);
            migrateUserTable(conn);
            migratePostTable(conn);
            log("schema is up to date");
        } catch (SQLException | RuntimeException e) {
            // Deliberately not fatal: if MySQL is down the app should still
            // deploy and render a readable error rather than failing to start.
            log("could not verify schema - " + e.getMessage());
        }
    }

    @Override
    public void contextDestroyed(ServletContextEvent event) {
        DBConnect.shutdown();
    }

    private void createTables(Connection conn) throws SQLException {
        try (Statement st = conn.createStatement()) {
            st.executeUpdate(
                    "CREATE TABLE IF NOT EXISTS user ("
                            + "id INT AUTO_INCREMENT PRIMARY KEY,"
                            + "full_name VARCHAR(100) NOT NULL,"
                            + "email VARCHAR(190) NOT NULL,"
                            + "password VARCHAR(255) NOT NULL,"
                            + "created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,"
                            + "CONSTRAINT uq_user_email UNIQUE (email)"
                            + ") ENGINE=InnoDB");

            st.executeUpdate(
                    "CREATE TABLE IF NOT EXISTS post ("
                            + "id INT AUTO_INCREMENT PRIMARY KEY,"
                            + "title VARCHAR(200) NOT NULL,"
                            + "content TEXT NOT NULL,"
                            + "pinned BOOLEAN NOT NULL DEFAULT FALSE,"
                            + "uid INT NOT NULL,"
                            + "created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,"
                            + "updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP "
                            + "ON UPDATE CURRENT_TIMESTAMP,"
                            + "INDEX idx_post_uid (uid),"
                            + "CONSTRAINT fk_post_user FOREIGN KEY (uid) REFERENCES user (id) "
                            + "ON DELETE CASCADE ON UPDATE CASCADE"
                            + ") ENGINE=InnoDB");
        }
    }

    private void migrateUserTable(Connection conn) throws SQLException {
        // Widened because the column now holds a PBKDF2 hash, not a raw password.
        if (columnLength(conn, "user", "password") < 255) {
            execute(conn, "ALTER TABLE user MODIFY COLUMN password VARCHAR(255) NOT NULL",
                    "widened user.password for hashed values");
        }

        // 190 keeps the column inside InnoDB's index-length limit under utf8mb4.
        if (columnLength(conn, "user", "email") < 190) {
            execute(conn, "ALTER TABLE user MODIFY COLUMN email VARCHAR(190) NOT NULL",
                    "widened user.email");
        }

        if (!columnExists(conn, "user", "created_at")) {
            execute(conn, "ALTER TABLE user ADD COLUMN created_at TIMESTAMP NOT NULL "
                            + "DEFAULT CURRENT_TIMESTAMP",
                    "added user.created_at");
        }

        if (!indexExists(conn, "user", "uq_user_email")) {
            if (hasDuplicateEmails(conn)) {
                // Refuse to guess which duplicate to delete - that is the
                // operator's call, so report it and leave the data alone.
                log("WARNING: duplicate emails in user table; unique constraint not added. "
                        + "Remove duplicates, then restart to finish the upgrade.");
            } else {
                execute(conn, "ALTER TABLE user ADD CONSTRAINT uq_user_email UNIQUE (email)",
                        "added unique constraint on user.email");
            }
        }
    }

    private void migratePostTable(Connection conn) throws SQLException {
        if (columnLength(conn, "post", "title") < 200) {
            execute(conn, "ALTER TABLE post MODIFY COLUMN title VARCHAR(200) NOT NULL",
                    "widened post.title");
        }

        // The original VARCHAR(45) silently truncated almost every real note.
        if (!"text".equalsIgnoreCase(columnType(conn, "post", "content"))) {
            execute(conn, "ALTER TABLE post MODIFY COLUMN content TEXT NOT NULL",
                    "converted post.content to TEXT (was truncating at 45 characters)");
        }

        if (!columnExists(conn, "post", "pinned")) {
            execute(conn, "ALTER TABLE post ADD COLUMN pinned BOOLEAN NOT NULL DEFAULT FALSE",
                    "added post.pinned");
        }

        // The original column was named `date`; keep the data and rename it.
        if (!columnExists(conn, "post", "created_at")) {
            if (columnExists(conn, "post", "date")) {
                execute(conn, "ALTER TABLE post CHANGE COLUMN `date` created_at TIMESTAMP NOT NULL "
                                + "DEFAULT CURRENT_TIMESTAMP",
                        "renamed post.date to post.created_at");
            } else {
                execute(conn, "ALTER TABLE post ADD COLUMN created_at TIMESTAMP NOT NULL "
                                + "DEFAULT CURRENT_TIMESTAMP",
                        "added post.created_at");
            }
        }

        if (!columnExists(conn, "post", "updated_at")) {
            execute(conn, "ALTER TABLE post ADD COLUMN updated_at TIMESTAMP NOT NULL "
                            + "DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP",
                    "added post.updated_at");
        }

        if (!indexExists(conn, "post", "idx_post_uid_pinned_created")) {
            execute(conn, "ALTER TABLE post ADD INDEX idx_post_uid_pinned_created "
                            + "(uid, pinned DESC, created_at DESC)",
                    "added listing index on post");
        }
    }

    private boolean hasDuplicateEmails(Connection conn) throws SQLException {
        String sql = "SELECT 1 FROM user GROUP BY email HAVING COUNT(*) > 1 LIMIT 1";
        try (Statement st = conn.createStatement(); ResultSet rs = st.executeQuery(sql)) {
            return rs.next();
        }
    }

    private boolean columnExists(Connection conn, String table, String column) throws SQLException {
        DatabaseMetaData meta = conn.getMetaData();
        try (ResultSet rs = meta.getColumns(conn.getCatalog(), null, table, column)) {
            return rs.next();
        }
    }

    /** Returns the declared character length of a column, or 0 when unknown. */
    private int columnLength(Connection conn, String table, String column) throws SQLException {
        String sql = "SELECT CHARACTER_MAXIMUM_LENGTH FROM information_schema.COLUMNS "
                + "WHERE TABLE_SCHEMA = ? AND TABLE_NAME = ? AND COLUMN_NAME = ?";
        try (PreparedStatement ps = conn.prepareStatement(sql)) {
            ps.setString(1, conn.getCatalog());
            ps.setString(2, table);
            ps.setString(3, column);
            try (ResultSet rs = ps.executeQuery()) {
                return rs.next() ? rs.getInt(1) : 0;
            }
        }
    }

    /** Returns the column's data type (for example {@code varchar}, {@code text}). */
    private String columnType(Connection conn, String table, String column) throws SQLException {
        String sql = "SELECT DATA_TYPE FROM information_schema.COLUMNS "
                + "WHERE TABLE_SCHEMA = ? AND TABLE_NAME = ? AND COLUMN_NAME = ?";
        try (PreparedStatement ps = conn.prepareStatement(sql)) {
            ps.setString(1, conn.getCatalog());
            ps.setString(2, table);
            ps.setString(3, column);
            try (ResultSet rs = ps.executeQuery()) {
                return rs.next() ? rs.getString(1) : "";
            }
        }
    }

    private boolean indexExists(Connection conn, String table, String indexName) throws SQLException {
        String sql = "SELECT 1 FROM information_schema.STATISTICS "
                + "WHERE TABLE_SCHEMA = ? AND TABLE_NAME = ? AND INDEX_NAME = ? LIMIT 1";
        try (PreparedStatement ps = conn.prepareStatement(sql)) {
            ps.setString(1, conn.getCatalog());
            ps.setString(2, table);
            ps.setString(3, indexName);
            try (ResultSet rs = ps.executeQuery()) {
                return rs.next();
            }
        }
    }

    private void execute(Connection conn, String sql, String description) throws SQLException {
        try (Statement st = conn.createStatement()) {
            st.executeUpdate(sql);
            log(description);
        }
    }

    private void log(String message) {
        String line = "[E-Notes schema] " + message;
        if (servletContext != null) {
            servletContext.log(line);
        } else {
            System.out.println(line);
        }
    }
}
