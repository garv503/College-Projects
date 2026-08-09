import { Router } from 'express';
import { execute, query, queryOne } from '../db.js';

/**
 * Note endpoints.
 *
 * Every statement is scoped by owner id. A note id belonging to someone else
 * therefore matches no rows and is reported as "not found", which is also the
 * response for a note that does not exist - the two are deliberately
 * indistinguishable, so the API cannot be used to discover which ids exist.
 */
const router = Router();

const MAX_TITLE_LENGTH = 200;
const MAX_CONTENT_LENGTH = 20_000;
const COLUMNS = 'id, title, content, pinned, uid, created_at, updated_at';

const trimmed = (value) => (typeof value === 'string' && value.trim() ? value.trim() : null);

function view(note) {
  const createdAt = note.created_at ? new Date(note.created_at).getTime() : null;
  const updatedAt = note.updated_at ? new Date(note.updated_at).getTime() : null;
  return {
    id: note.id,
    title: note.title,
    content: note.content,
    pinned: Boolean(note.pinned),
    edited: Boolean(createdAt && updatedAt && updatedAt > createdAt),
    createdAt,
    updatedAt,
  };
}

function validate(title, content) {
  if (!title) return 'Please enter a title.';
  if (title.length > MAX_TITLE_LENGTH) return `Title must be ${MAX_TITLE_LENGTH} characters or fewer.`;
  if (!content) return 'Please enter some content.';
  if (content.length > MAX_CONTENT_LENGTH) return `Content must be ${MAX_CONTENT_LENGTH} characters or fewer.`;
  return null;
}

const notFound = (res) => res.status(404).json({ error: 'That note could not be found.' });

/** Parses a route id, returning null for anything that is not a positive integer. */
function noteId(raw) {
  const id = Number(raw);
  return Number.isInteger(id) && id > 0 ? id : null;
}

router.get('/', async (req, res, next) => {
  try {
    const uid = req.session.user.id;
    const search = trimmed(req.query.q);

    let rows;
    if (search) {
      // Escape LIKE's own wildcards so a literal % or _ searches for itself.
      const pattern = `%${search.replace(/!/g, '!!').replace(/%/g, '!%').replace(/_/g, '!_')}%`;
      rows = await query(
        `SELECT ${COLUMNS} FROM post
         WHERE uid = ? AND (title LIKE ? ESCAPE '!' OR content LIKE ? ESCAPE '!')
         ORDER BY pinned DESC, created_at DESC`,
        [uid, pattern, pattern],
      );
    } else {
      rows = await query(
        `SELECT ${COLUMNS} FROM post WHERE uid = ? ORDER BY pinned DESC, created_at DESC`,
        [uid],
      );
    }

    res.json({ notes: rows.map(view) });
  } catch (error) {
    next(error);
  }
});

router.post('/', async (req, res, next) => {
  try {
    const title = trimmed(req.body?.title);
    const content = trimmed(req.body?.content);

    const problem = validate(title, content);
    if (problem) return res.status(400).json({ error: problem });

    // The author is the signed-in user, never a value from the request body.
    await execute('INSERT INTO post (title, content, uid) VALUES (?, ?, ?)',
      [title, content, req.session.user.id]);

    return res.status(201).json({ message: 'Note added.' });
  } catch (error) {
    return next(error);
  }
});

router.get('/:id', async (req, res, next) => {
  try {
    const id = noteId(req.params.id);
    if (!id) return notFound(res);

    const note = await queryOne(`SELECT ${COLUMNS} FROM post WHERE id = ? AND uid = ?`,
      [id, req.session.user.id]);

    return note ? res.json({ note: view(note) }) : notFound(res);
  } catch (error) {
    return next(error);
  }
});

router.put('/:id', async (req, res, next) => {
  try {
    const id = noteId(req.params.id);
    if (!id) return notFound(res);

    const title = trimmed(req.body?.title);
    const content = trimmed(req.body?.content);

    const problem = validate(title, content);
    if (problem) return res.status(400).json({ error: problem });

    const result = await execute(
      'UPDATE post SET title = ?, content = ? WHERE id = ? AND uid = ?',
      [title, content, id, req.session.user.id],
    );

    return result.affectedRows === 1
      ? res.json({ message: 'Note updated.' })
      : notFound(res);
  } catch (error) {
    return next(error);
  }
});

router.delete('/:id', async (req, res, next) => {
  try {
    const id = noteId(req.params.id);
    if (!id) return notFound(res);

    const result = await execute('DELETE FROM post WHERE id = ? AND uid = ?',
      [id, req.session.user.id]);

    return result.affectedRows === 1
      ? res.json({ message: 'Note deleted.' })
      : notFound(res);
  } catch (error) {
    return next(error);
  }
});

router.post('/:id/pin', async (req, res, next) => {
  try {
    const id = noteId(req.params.id);
    if (!id) return notFound(res);

    const uid = req.session.user.id;
    const result = await execute('UPDATE post SET pinned = NOT pinned WHERE id = ? AND uid = ?',
      [id, uid]);

    if (result.affectedRows !== 1) return notFound(res);

    const note = await queryOne(`SELECT ${COLUMNS} FROM post WHERE id = ? AND uid = ?`, [id, uid]);
    return res.json({ note: view(note) });
  } catch (error) {
    return next(error);
  }
});

export default router;
