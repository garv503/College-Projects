package com.Db;

import java.io.IOException;
import java.io.InputStream;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.SQLException;
import java.util.Properties;

public class DBConnect {
    private static final String DEFAULT_URL = "jdbc:mysql://localhost:3306/enotes?useSSL=false&serverTimezone=UTC";
    private static final String DEFAULT_USERNAME = "root";
    private static Connection conn;

    /**
     * Returns the shared application connection. Settings are read in this order:
     * JVM system properties, environment variables, then WEB-INF/classes/db.properties.
     */
    public static synchronized Connection getconn() {
        try {
            if (conn == null || conn.isClosed()) {
                Class.forName("com.mysql.cj.jdbc.Driver");
                Properties properties = loadProperties();
                String url = setting("enotes.db.url", "ENOTES_DB_URL", "db.url", DEFAULT_URL, properties);
                String username = setting("enotes.db.username", "ENOTES_DB_USERNAME", "db.username", DEFAULT_USERNAME, properties);
                String password = setting("enotes.db.password", "ENOTES_DB_PASSWORD", "db.password", "", properties);

                conn = DriverManager.getConnection(url, username, password);
            }
            return conn;
        } catch (ClassNotFoundException | SQLException e) {
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
