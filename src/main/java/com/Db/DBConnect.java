package com.Db;

import java.io.IOException;
import java.io.InputStream;
import java.sql.Connection;
import java.sql.SQLException;
import java.util.Properties;
import javax.sql.DataSource;

import com.zaxxer.hikari.HikariConfig;
import com.zaxxer.hikari.HikariDataSource;

/**
 * Owns the application's JDBC connection pool.
 *
 * <p>This used to hand every request the same single static {@link Connection}.
 * A servlet container serves requests on many threads at once, so concurrent
 * users shared one connection and could interleave each other's statements and
 * results; a single dropped connection also took the whole app down until
 * redeploy. Each caller now borrows its own connection from a pool and returns
 * it by closing it, which is why every call site uses try-with-resources.
 */
public final class DBConnect {

    private static final String DEFAULT_URL =
            "jdbc:mysql://localhost:3306/enotes?useSSL=false&serverTimezone=UTC";
    private static final String DEFAULT_USERNAME = "root";

    private static volatile HikariDataSource dataSource;

    private DBConnect() {
    }

    /**
     * Returns the shared pool, creating it on first use. Settings are read in
     * this order: JVM system properties, environment variables, then
     * {@code db.properties} on the classpath.
     */
    public static DataSource getDataSource() {
        HikariDataSource local = dataSource;
        if (local == null) {
            synchronized (DBConnect.class) {
                local = dataSource;
                if (local == null) {
                    local = build();
                    dataSource = local;
                }
            }
        }
        return local;
    }

    /**
     * Borrows a connection from the pool. Callers must close it (ideally via
     * try-with-resources), which returns it to the pool rather than dropping it.
     */
    public static Connection getConnection() throws SQLException {
        return getDataSource().getConnection();
    }

    /** Releases the pool. Called on context shutdown so redeploys do not leak connections. */
    public static synchronized void shutdown() {
        if (dataSource != null) {
            dataSource.close();
            dataSource = null;
        }
    }

    private static HikariDataSource build() {
        Properties properties = loadProperties();

        HikariConfig config = new HikariConfig();
        config.setJdbcUrl(setting("enotes.db.url", "ENOTES_DB_URL", "db.url", DEFAULT_URL, properties));
        config.setUsername(setting("enotes.db.username", "ENOTES_DB_USERNAME", "db.username",
                DEFAULT_USERNAME, properties));
        config.setPassword(setting("enotes.db.password", "ENOTES_DB_PASSWORD", "db.password", "", properties));
        config.setDriverClassName("com.mysql.cj.jdbc.Driver");
        config.setPoolName("enotes-pool");
        config.setMaximumPoolSize(10);
        config.setMinimumIdle(2);
        config.setConnectionTimeout(10_000);
        // Recycle connections well inside MySQL's default 8-hour wait_timeout so
        // the pool never hands out one the server has already dropped.
        config.setMaxLifetime(600_000);
        config.setConnectionTestQuery("SELECT 1");

        try {
            return new HikariDataSource(config);
        } catch (RuntimeException e) {
            throw new IllegalStateException(
                    "Unable to connect to the enotes database. Check db.properties or ENOTES_DB_* settings.", e);
        }
    }

    private static Properties loadProperties() {
        Properties properties = new Properties();
        try (InputStream input = DBConnect.class.getClassLoader().getResourceAsStream("db.properties")) {
            if (input != null) {
                properties.load(input);
            }
        } catch (IOException e) {
            throw new IllegalStateException("Could not read db.properties.", e);
        }
        return properties;
    }

    private static String setting(String systemProperty, String environmentVariable, String propertyKey,
            String defaultValue, Properties properties) {
        String value = System.getProperty(systemProperty);
        if (isBlank(value)) {
            value = System.getenv(environmentVariable);
        }
        if (isBlank(value)) {
            value = properties.getProperty(propertyKey);
        }
        return isBlank(value) ? defaultValue : value;
    }

    private static boolean isBlank(String value) {
        return value == null || value.trim().isEmpty();
    }
}
