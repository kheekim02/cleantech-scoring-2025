module.exports = async (req, res) => {
  return res.status(410).json({ error: 'This endpoint is retired. Use /api/auth-login.' });
};
