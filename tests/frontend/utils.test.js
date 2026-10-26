import {describe,expect,it} from 'vitest';
import {categoryMap,escapeHtml,normalizeLocalPhone,relativeTime} from '../../app/static/js/utils.js';

describe('utilitaires du frontend',()=>{
  it('protège le HTML injecté par un utilisateur',()=>expect(escapeHtml('<img onerror="x">')).toBe('&lt;img onerror=&quot;x&quot;&gt;'));
  it('normalise un numéro local',()=>expect(normalizeLocalPhone('+221 77 123-45-67')).toBe('771234567'));
  it('calcule un temps relatif lisible',()=>expect(relativeTime('2026-09-08T11:48:00Z',new Date('2026-09-08T12:00:00Z'))).toBe('Il y a 12 min'));
  it('indexe les catégories',()=>expect(categoryMap([{id:'eau',label:'Eau'}]).eau.label).toBe('Eau'));
});
