const { pool } = require('./_db');

/**
 * Serverless deliverable viewer endpoint.
 * Serves ingested PDF deliverable binaries directly from PostgreSQL.
 * Supports inline browser preview, HTTP caching, and conditional ETags.
 */
module.exports = async (req, res) => {
  if (req.method !== 'GET' && req.method !== 'HEAD') {
    res.setHeader('Allow', 'GET, HEAD');
    return res.status(405).json({ error: 'Method Not Allowed' });
  }

  const query = req.query || {};
  let startupId = query.startup_id || query.id;
  let filename = query.file || query.filename;

  if (!startupId || !filename) {
    return res.status(400).json({ error: 'Missing required parameters: startup_id and file are required.' });
  }

  // Normalize / sanitize parameters
  try {
    startupId = decodeURIComponent(startupId).trim();
    filename = decodeURIComponent(filename).trim();
  } catch (e) {
    return res.status(400).json({ error: 'Malformed URI encoding in parameters.' });
  }

  // Prevent directory traversal or poison bytes
  if (filename.includes('..') || filename.includes('/') || filename.includes('\\') || filename.includes('\0')) {
    return res.status(400).json({ error: 'Invalid filename parameter.' });
  }

  // Provide alias tolerance for em-dash vs hyphen
  const startupAlias = startupId.replace(/\u2014/g, '-');
  const startupWithDash = startupId.replace(/-/g, '\u2014');

  try {
    const result = await pool.query(
      `
      SELECT file_bytes, mime_type, file_size_bytes, sha256, updated_at
      FROM startup_deliverable_files
      WHERE (startup_id = $1 OR startup_id = $2 OR startup_id = $3)
        AND filename = $4
      LIMIT 1;
      `,
      [startupId, startupAlias, startupWithDash, filename]
    );

    if (result.rows.length === 0) {
      return res.status(404).json({
        error: 'Deliverable not found.',
        startup_id: startupId,
        filename,
      });
    }

    const row = result.rows[0];
    const etag = `"${row.sha256}"`;

    res.setHeader('Content-Type', row.mime_type || 'application/pdf');
    res.setHeader('Content-Length', row.file_size_bytes);
    res.setHeader('Content-Disposition', `inline; filename="${encodeURIComponent(filename)}"`);
    res.setHeader('Cache-Control', 'public, max-age=86400, stale-while-revalidate=604800');
    res.setHeader('ETag', etag);
    res.setHeader('Accept-Ranges', 'none');

    // Handle conditional GET (304 Not Modified)
    const clientEtag = req.headers['if-none-match'];
    if (clientEtag && (clientEtag === etag || clientEtag === `W/${etag}`)) {
      return res.status(304).end();
    }

    if (req.method === 'HEAD') {
      return res.status(200).end();
    }

    return res.status(200).send(row.file_bytes);
  } catch (err) {
    console.error('[Deliverable API] Database query error:', err);
    return res.status(500).json({ error: 'Database error retrieving deliverable: ' + err.message });
  }
};
