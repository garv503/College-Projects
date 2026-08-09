import mysql from 'mysql2/promise';
import { config } from './config.js';

/**
 * Shared MySQL connection pool.
 *
 * Same role HikariCP played in the Java version: every query borrows a
 * connection and returns it, rather than sharing one long-lived connection
 * across concurrent requests.
 */
export const pool = mysql.createPool({
  host: config.db.host,
  port: config.db.port,
  user: config.db.user,
  password: config.db.password,
  database: config.db.database,
  waitForConnections: true,
  connectionLimit: 10,
  queueLimit: 0,
  charset: 'utf8mb4',
  // Keeps DATETIME/TIMESTAMP values as JS Dates so routes can send epoch millis.
  dateStrings: false,
});

/** Runs a query and returns just the rows. */
export async function query(sql, params = []) {
  const [rows] = await pool.execute(sql, params);
  return rows;
}

/** Runs a write and returns the result metadata (affectedRows, insertId). */
export async function execute(sql, params = []) {
  const [result] = await pool.execute(sql, params);
  return result;
}

/** Convenience for single-row reads. */
export async function queryOne(sql, params = []) {
  const rows = await query(sql, params);
  return rows.length ? rows[0] : null;
}
