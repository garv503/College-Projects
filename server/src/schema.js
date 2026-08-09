import { config } from './config.js';
import { execute, query, queryOne } from './db.js';

/**
 * Brings the database up to the shape the application expects, at startup.
 *
 * Port of the Java DatabaseInitializer, with the same contract: every step is
 * guarded by an existence check, so this is safe to run on every boot. A fresh
 * database gets created, an older one gets upgraded in place, and an
 * already-current one is left untouched.
 */

const log = (message) => console.log(`[Inkwell schema] ${message}`);

export async function initialiseSchema() {
  await createTables();
  await migrateUserTable();
  await migratePostTable();
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
      -- NULL for accounts created through Google that have not set one yet.
      password VARCHAR(255) NULL,
      role ENUM('USER','ADMIN') NOT NULL DEFAULT 'USER',
      -- Google's stable account identifier ("sub"), set for Google signups.
      google_id VARCHAR(64) NULL,
      -- Emails arriving from Google are already verified by Google.
      email_verified BOOLEAN NOT NULL DEFAULT FALSE,
      -- One-time token behind the "set your password" link in the setup email.
      setup_token VARCHAR(64) NULL,
      setup_token_expires DATETIME NULL,
      created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
      CONSTRAINT uq_user_email UNIQUE (email),
      CONSTRAINT uq_user_google_id UNIQUE (google_id),
      INDEX idx_user_setup_token (setup_token)
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
      CONSTRAINT fk_post_user FOREIGN KEY (uid) REFERENCES user (id)
        ON DELETE CASCADE ON UPDATE CASCADE
    ) ENGINE=InnoDB
  `);
}

async function migrateUserTable() {
  if ((await columnLength('user', 'password')) < 255) {
    await step('ALTER TABLE user MODIFY COLUMN password VARCHAR(255) NOT NULL',
      'widened user.password');
  }

  // 190 keeps the column inside InnoDB's index-length limit under utf8mb4.
  if ((await columnLength('user', 'email')) < 190) {
    await step('ALTER TABLE user MODIFY COLUMN email VARCHAR(190) NOT NULL',
      'widened user.email');
  }

  if (!(await columnExists('user', 'created_at'))) {
    await step('ALTER TABLE user ADD COLUMN created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP',
      'added user.created_at');
  }

  if (!(await columnExists('user', 'role'))) {
    await step(
      "ALTER TABLE user ADD COLUMN role ENUM('USER','ADMIN') NOT NULL DEFAULT 'USER'",
      'added user.role',
    );
  }

  // Google accounts have no password until the holder sets one from the setup
  // email, so the column has to allow NULL.
  if (!(await columnIsNullable('user', 'password'))) {
    await step('ALTER TABLE user MODIFY COLUMN password VARCHAR(255) NULL',
      'made user.password nullable (for Google accounts)');
  }

  if (!(await columnExists('user', 'google_id'))) {
    await step('ALTER TABLE user ADD COLUMN google_id VARCHAR(64) NULL',
      'added user.google_id');
  }

  if (!(await indexExists('user', 'uq_user_google_id'))) {
    await step('ALTER TABLE user ADD CONSTRAINT uq_user_google_id UNIQUE (google_id)',
      'added unique constraint on user.google_id');
  }

  if (!(await columnExists('user', 'email_verified'))) {
    await step('ALTER TABLE user ADD COLUMN email_verified BOOLEAN NOT NULL DEFAULT FALSE',
      'added user.email_verified');
  }

  if (!(await columnExists('user', 'setup_token'))) {
    await step('ALTER TABLE user ADD COLUMN setup_token VARCHAR(64) NULL',
      'added user.setup_token');
  }

  if (!(await columnExists('user', 'setup_token_expires'))) {
    await step('ALTER TABLE user ADD COLUMN setup_token_expires DATETIME NULL',
      'added user.setup_token_expires');
  }

  if (!(await indexExists('user', 'idx_user_setup_token'))) {
    await step('ALTER TABLE user ADD INDEX idx_user_setup_token (setup_token)',
      'added index on user.setup_token');
  }

  if (!(await indexExists('user', 'uq_user_email'))) {
    const duplicate = await queryOne(
      'SELECT email FROM user GROUP BY email HAVING COUNT(*) > 1 LIMIT 1',
    );
    if (duplicate) {
      // Refuse to guess which duplicate to delete - that is the operator's call.
      log('WARNING: duplicate emails in user table; unique constraint not added. '
        + 'Remove duplicates, then restart to finish the upgrade.');
    } else {
      await step('ALTER TABLE user ADD CONSTRAINT uq_user_email UNIQUE (email)',
        'added unique constraint on user.email');
    }
  }
}

async function migratePostTable() {
  if ((await columnLength('post', 'title')) < 200) {
    await step('ALTER TABLE post MODIFY COLUMN title VARCHAR(200) NOT NULL',
      'widened post.title');
  }

  if ((await columnType('post', 'content')).toLowerCase() !== 'text') {
    await step('ALTER TABLE post MODIFY COLUMN content TEXT NOT NULL',
      'converted post.content to TEXT');
  }

  if (!(await columnExists('post', 'pinned'))) {
    await step('ALTER TABLE post ADD COLUMN pinned BOOLEAN NOT NULL DEFAULT FALSE',
      'added post.pinned');
  }

  // The original column was named `date`; keep the data and rename it.
  if (!(await columnExists('post', 'created_at'))) {
    if (await columnExists('post', 'date')) {
      await step(
        'ALTER TABLE post CHANGE COLUMN `date` created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP',
        'renamed post.date to post.created_at',
      );
    } else {
      await step('ALTER TABLE post ADD COLUMN created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP',
        'added post.created_at');
    }
  }

  if (!(await columnExists('post', 'updated_at'))) {
    await step(
      'ALTER TABLE post ADD COLUMN updated_at TIMESTAMP NOT NULL '
      + 'DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP',
      'added post.updated_at',
    );
  }

  if (!(await indexExists('post', 'idx_post_uid_pinned_created'))) {
    await step(
      'ALTER TABLE post ADD INDEX idx_post_uid_pinned_created (uid, pinned DESC, created_at DESC)',
      'added listing index on post',
    );
  }
}

/**
 * Guarantees the instance is administrable.
 *
 * Without this an upgraded database would have no admin at all (every existing
 * row defaults to USER) and nobody could reach the admin area. The
 * longest-standing account is promoted, and only when there is no admin
 * already, so this never quietly changes an established setup.
 */
async function ensureAnAdminExists() {
  const admin = await queryOne("SELECT id FROM user WHERE role = 'ADMIN' LIMIT 1");
  if (admin) return;

  const oldest = await queryOne('SELECT id, email FROM user ORDER BY id ASC LIMIT 1');
  if (!oldest) return; // Empty install: the first account to register becomes admin.

  await execute("UPDATE user SET role = 'ADMIN' WHERE id = ?", [oldest.id]);
  log(`no admin existed; promoted the first account (${oldest.email}) to ADMIN`);
}

/* ---------------------------------------------------------------- helpers */

async function columnExists(table, column) {
  const row = await queryOne(
    'SELECT 1 AS present FROM information_schema.COLUMNS '
    + 'WHERE TABLE_SCHEMA = ? AND TABLE_NAME = ? AND COLUMN_NAME = ?',
    [config.db.database, table, column],
  );
  return Boolean(row);
}

async function columnLength(table, column) {
  const row = await queryOne(
    'SELECT CHARACTER_MAXIMUM_LENGTH AS len FROM information_schema.COLUMNS '
    + 'WHERE TABLE_SCHEMA = ? AND TABLE_NAME = ? AND COLUMN_NAME = ?',
    [config.db.database, table, column],
  );
  return row?.len ?? 0;
}

async function columnIsNullable(table, column) {
  const row = await queryOne(
    'SELECT IS_NULLABLE AS nullable FROM information_schema.COLUMNS '
    + 'WHERE TABLE_SCHEMA = ? AND TABLE_NAME = ? AND COLUMN_NAME = ?',
    [config.db.database, table, column],
  );
  return row?.nullable === 'YES';
}

async function columnType(table, column) {
  const row = await queryOne(
    'SELECT DATA_TYPE AS type FROM information_schema.COLUMNS '
    + 'WHERE TABLE_SCHEMA = ? AND TABLE_NAME = ? AND COLUMN_NAME = ?',
    [config.db.database, table, column],
  );
  return row?.type ?? '';
}

async function indexExists(table, indexName) {
  const rows = await query(
    'SELECT 1 FROM information_schema.STATISTICS '
    + 'WHERE TABLE_SCHEMA = ? AND TABLE_NAME = ? AND INDEX_NAME = ? LIMIT 1',
    [config.db.database, table, indexName],
  );
  return rows.length > 0;
}

async function step(sql, description) {
  await execute(sql);
  log(description);
}
