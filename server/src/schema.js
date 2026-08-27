import { execute, queryOne } from './db.js';

/**
 * Brings the database up to the shape the application expects, at startup.
 *
 * Every statement is idempotent, so this is safe to run on every boot: a fresh
 * database gets created and an existing one is left untouched.
 */

const log = (message) => console.log(`[Inkwell schema] ${message}`);

export async function initialiseSchema() {
  await createTables();
  await purgeExpiredRegistrations();
  await ensureAnAdminExists();
  log('schema is up to date');
}

async function createTables() {
  await execute(`
    CREATE TABLE IF NOT EXISTS user (
      id INT AUTO_INCREMENT PRIMARY KEY,
      full_name VARCHAR(100) NOT NULL,
      email VARCHAR(190) NOT NULL,
      -- Plain text, by explicit project choice. See the Security section of
      -- the README before deploying this anywhere real.
      password VARCHAR(255) NOT NULL,
      role ENUM('USER','ADMIN') NOT NULL DEFAULT 'USER',
      created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
      -- Stops two accounts sharing one email, which would let a duplicate
      -- registration silently shadow an existing login.
      CONSTRAINT uq_user_email UNIQUE (email)
    ) ENGINE=InnoDB
  `);

  // A signup that has not confirmed its email lives here, not in `user`, so an
  // unverified address never becomes a real account and never occupies the
  // email someone else may be entitled to register.
  await execute(`
    CREATE TABLE IF NOT EXISTS pending_registration (
      id INT AUTO_INCREMENT PRIMARY KEY,
      full_name VARCHAR(100) NOT NULL,
      email VARCHAR(190) NOT NULL,
      -- Plain text, matching the user table's deliberate choice.
      password VARCHAR(255) NOT NULL,
      otp_code VARCHAR(12) NOT NULL,
      otp_expires DATETIME NOT NULL,
      attempts INT NOT NULL DEFAULT 0,
      last_sent_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
      created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
      -- One pending signup per address; re-registering replaces it.
      CONSTRAINT uq_pending_email UNIQUE (email)
    ) ENGINE=InnoDB
  `);

  await execute(`
    CREATE TABLE IF NOT EXISTS post (
      id INT AUTO_INCREMENT PRIMARY KEY,
      title VARCHAR(200) NOT NULL,
      content TEXT NOT NULL,
      pinned BOOLEAN NOT NULL DEFAULT FALSE,
      uid INT NOT NULL,
      created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
      updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
      INDEX idx_post_uid (uid),
      -- Supports the default "pinned first, newest first" listing.
      INDEX idx_post_uid_pinned_created (uid, pinned DESC, created_at DESC),
      -- Deleting a user removes their notes with them.
      CONSTRAINT fk_post_user FOREIGN KEY (uid) REFERENCES user (id)
        ON DELETE CASCADE ON UPDATE CASCADE
    ) ENGINE=InnoDB
  `);
}

/** Clears abandoned signups so the table does not grow without bound. */
async function purgeExpiredRegistrations() {
  const result = await execute('DELETE FROM pending_registration WHERE otp_expires < NOW()');
  if (result.affectedRows > 0) {
    log(`removed ${result.affectedRows} expired pending registration(s)`);
  }
}

/**
 * Guarantees the instance is administrable.
 *
 * Without this, a database whose only admin was deleted would leave nobody able
 * to reach the admin area. The longest-standing account is promoted, and only
 * when there is no admin already, so this never quietly changes an established
 * setup.
 */
async function ensureAnAdminExists() {
  const admin = await queryOne("SELECT id FROM user WHERE role = 'ADMIN' LIMIT 1");
  if (admin) return;

  const oldest = await queryOne('SELECT id, email FROM user ORDER BY id ASC LIMIT 1');
  if (!oldest) return; // Empty install: the first account to register becomes admin.

  await execute("UPDATE user SET role = 'ADMIN' WHERE id = ?", [oldest.id]);
  log(`no admin existed; promoted the first account (${oldest.email}) to ADMIN`);
}
