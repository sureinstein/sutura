export const categoryMap = categories => Object.fromEntries(categories.map(c => [c.id, c]));

export function relativeTime(iso, now = new Date()) {
  const minutes = Math.max(0, Math.floor((now - new Date(iso)) / 60000));
  if (minutes < 1) return "À l'instant";
  if (minutes < 60) return `Il y a ${minutes} min`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `Il y a ${hours} h`;
  return `Il y a ${Math.floor(hours / 24)} j`;
}

export function escapeHtml(value = "") {
  return String(value).replace(/[&<>'"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));
}

export function normalizeLocalPhone(value) {
  return String(value).replace(/\D/g, '').replace(/^221/, '').slice(0, 9);
}

