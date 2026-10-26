import {api, getToken, setToken} from './api.js';
import {categoryMap, escapeHtml, normalizeLocalPhone, relativeTime} from './utils.js';

const $ = s => document.querySelector(s);
const $$ = s => [...document.querySelectorAll(s)];
let metadata = {categories: [], quartiers: []}, profile, scope = 'quartier', category = '', selectedCategory = '';
let locationMap, locationMarker, selectedLocation = null, locationValidated = false;
let previousOrder = [], lastFeedSignature = '';
let previousStates = {}, currentQuartier = '';

function toast(message) { const el=$('#toast'); el.textContent=message; el.classList.add('show'); setTimeout(()=>el.classList.remove('show'),2600); }
function setView(authenticated) { $('#authView').hidden=authenticated; $('#feedView').hidden=!authenticated; $('#createButton').hidden=!authenticated; $('#profileButton').hidden=!authenticated; }
function options(select, selected='') { select.innerHTML=metadata.quartiers.map(q=>`<option ${q===selected?'selected':''}>${escapeHtml(q)}</option>`).join(''); }

async function boot() {
  metadata = await api('/metadata');
  $('#categoryFilters').innerHTML = `<button class="active" data-category="">Toutes</button>` + metadata.categories.map(c=>`<button data-category="${c.id}">${c.icone} ${escapeHtml(c.label)}</button>`).join('');
  $('#categoryGrid').innerHTML = metadata.categories.map(c=>`<button class="category-option" type="button" data-pick="${c.id}">${c.icone} ${escapeHtml(c.label)}</button>`).join('');
  options($('#quartierProfile'));
  if (!getToken()) return setView(false);
  try { profile=await api('/auth/profile'); setView(true); if(!profile.pseudo) openProfile(); else hydrateProfile(); await detectCurrentQuartier(); await loadAlerts(); }
  catch { setToken(null); setView(false); }
}

function hydrateProfile(){ $('#welcomeName').textContent=profile.pseudo||'voisin·e'; $('#pseudo').value=profile.pseudo||''; options($('#quartierProfile'),profile.quartier_defaut); $('#adminLink').hidden=!profile.is_admin; $('#workLink').hidden=!(profile.groupes||[]).length; }
function openProfile(){ hydrateProfile(); $('#profileView').hidden=false; }
function closeSheets(){ $$('.sheet').forEach(el=>el.hidden=true); }

function geolocationErrorMessage(error) {
  if (!window.isSecureContext) return "La géolocalisation exige HTTPS ou une ouverture depuis localhost.";
  if (!error) return "La géolocalisation n'est pas disponible sur cet appareil.";
  if (error.code === 1) return "Localisation refusée. Autorisez-la dans les réglages du navigateur, puis réessayez.";
  if (error.code === 2) return "Position indisponible. Vérifiez que le service de localisation macOS est activé.";
  if (error.code === 3) return "La localisation prend trop de temps. Vous pouvez placer le repère manuellement sur la carte.";
  return "Impossible d'obtenir votre position. Placez le repère manuellement sur la carte.";
}

function getCurrentPosition() {
  if (!window.isSecureContext) return Promise.reject({message: geolocationErrorMessage()});
  if (!navigator.geolocation) return Promise.reject({message: geolocationErrorMessage()});
  return new Promise((resolve,reject)=>navigator.geolocation.getCurrentPosition(resolve,error=>reject({code:error.code,message:geolocationErrorMessage(error)}),{enableHighAccuracy:false,timeout:15000,maximumAge:300000}));
}

function setLocation(latitude, longitude, center = false) {
  selectedLocation = {latitude: Number(latitude), longitude: Number(longitude)};
  locationValidated = false;
  if (!locationMarker) {
    locationMarker = L.marker([latitude, longitude], {draggable: true}).addTo(locationMap);
    locationMarker.on('dragend', event => {
      const point = event.target.getLatLng();
      setLocation(point.lat, point.lng);
    });
  } else locationMarker.setLatLng([latitude, longitude]);
  if (center) locationMap.setView([latitude, longitude], 17);
  $('#coordinatesLabel').textContent = 'Vérification de la position…';
  $('#clearLocationButton').hidden = false;
  resolveLocation();
}

async function resolveLocation() {
  const point = selectedLocation;
  try {
    const result = await api(`/geo/reverse?lat=${point.latitude}&lon=${point.longitude}`);
    if (point !== selectedLocation) return;
    locationValidated = true;
    selectedLocation.countryCode = 'sn';
    selectedLocation.commune = result.commune || '';
    selectedLocation.region = result.region || '';
    const quartier = result.quartier || result.commune;
    $('#quartierAlert').value = quartier || result.commune || '';
    $('#coordinatesLabel').classList.add('detected');
    $('#coordinatesLabel').textContent = `Quartier détecté : ${quartier || result.commune || 'localité au Sénégal'} · ${point.latitude.toFixed(6)}, ${point.longitude.toFixed(6)}`;
  } catch (error) {
    if (point !== selectedLocation) return;
    selectedLocation = null; locationValidated = false;
    $('#quartierAlert').value = '';
    if (locationMarker) { locationMap.removeLayer(locationMarker); locationMarker = null; }
    $('#clearLocationButton').hidden = true;
    $('#coordinatesLabel').textContent = error.message;
    $('#coordinatesLabel').classList.remove('detected');
    toast(error.message);
  }
}

function initLocationMap() {
  if (locationMap || !window.L) return;
  locationMap = L.map('locationMap').setView([14.7167, -17.4677], 12);
  L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
  }).addTo(locationMap);
  locationMap.on('click', event => setLocation(event.latlng.lat, event.latlng.lng));
}

function openCreate() {
  $('#createView').hidden = false;
  initLocationMap();
  setTimeout(() => locationMap?.invalidateSize(), 50);
}

async function detectCurrentQuartier() {
  currentQuartier = profile?.quartier_defaut || '';
  if (!navigator.geolocation) { $('#currentArea').textContent=`📍 ${currentQuartier} · quartier du profil`; return; }
  try {
    const position = await getCurrentPosition();
    const place = await api(`/geo/reverse?lat=${position.coords.latitude}&lon=${position.coords.longitude}`);
    currentQuartier = place.quartier || place.commune || currentQuartier;
    $('#currentArea').textContent=`📍 ${currentQuartier} · position actuelle`;
  } catch (error) {
    $('#currentArea').textContent=`📍 ${currentQuartier} · quartier du profil — ${error.message || 'position indisponible'}`;
  }
}

async function loadAlerts(live = false){
  const key=`sutura_alerts_${scope}_${currentQuartier}_${category}`; const query=new URLSearchParams({scope}); if(scope==='quartier'&&currentQuartier)query.set('quartier',currentQuartier); if(category)query.set('categorie',category);
  try { const data=await api(`/alerts?${query}`); const signature=data.items.map(a=>`${a.id}:${a.date_modification}:${a.statut_traitement}`).join('|'); if(!live||signature!==lastFeedSignature){localStorage.setItem(key,JSON.stringify(data.items));renderAlerts(data.items,live);lastFeedSignature=signature} $('#offlineBanner').hidden=true; }
  catch(e){ const cached=JSON.parse(localStorage.getItem(key)||'[]'); renderAlerts(cached); $('#offlineBanner').hidden=navigator.onLine; if(navigator.onLine)toast(e.message); }
}

function renderAlerts(items, live = false){
  const cats=categoryMap(metadata.categories); $('#emptyState').hidden=items.length>0;
  const statuses={nouveau:'Nouveau',qualifie:'Qualifié',assigne:'Assigné',en_cours:'En cours',traite:'Traité',rejete:'Rejeté'};
  const oldPositions=Object.fromEntries(previousOrder.map((id,index)=>[id,index]));
  $('#alertList').innerHTML=items.map((a,index)=>{const old=oldPositions[a.id],changed=live&&previousStates[a.id]&&previousStates[a.id]!==`${a.date_modification}:${a.statut_traitement}`,movement=live&&old!==undefined?(index<old?'move-up':index>old?'move-down':changed?'live-change':''):'';return `<article class="alert-card ${a.statut} ${movement}" data-feed-id="${a.id}">${a.photo_url?`<img class="alert-photo" src="${escapeHtml(a.photo_url)}" alt="Photo de l'alerte" loading="lazy">`:''}<div class="alert-body"><div class="alert-meta"><span class="badge">${cats[a.categorie]?.icone||'⚠️'} ${escapeHtml(cats[a.categorie]?.label||a.categorie)}</span><span class="time">Mis à jour ${relativeTime(a.date_modification||a.date_publication).toLowerCase()}</span></div><p>${escapeHtml(a.description)}</p><div class="location">📍 ${escapeHtml(a.quartier)} · par ${escapeHtml(a.auteur.pseudo)}</div>${a.latitude!==null&&a.longitude!==null?`<a class="map-link" href="https://www.openstreetmap.org/?mlat=${a.latitude}&mlon=${a.longitude}#map=18/${a.latitude}/${a.longitude}" target="_blank" rel="noopener">Voir la position exacte ↗</a>`:''}</div><div class="card-actions"><span class="status-chip status-${a.statut_traitement}">${statuses[a.statut_traitement]||escapeHtml(a.statut_traitement)}</span>${a.auteur.id!==profile.id?`<button data-confirm="${a.id}" ${a.confirmee_par_moi?'disabled':''}>${a.confirmee_par_moi?'✓ Confirmé':'Je confirme'} <sup class="confirm-count" aria-label="${a.compteur_confirmations} confirmations">${a.compteur_confirmations}</sup></button>`:`<span class="author-confirmations">Confirmé par <sup class="confirm-count" aria-label="${a.compteur_confirmations} confirmations">${a.compteur_confirmations}</sup></span>`}</div></article>`}).join('');
  previousOrder=items.map(a=>a.id);
  previousStates=Object.fromEntries(items.map(a=>[a.id,`${a.date_modification}:${a.statut_traitement}`]));
}

$('#phoneForm').addEventListener('submit',async e=>{e.preventDefault();const local=normalizeLocalPhone($('#telephone').value);if(local.length!==9)return toast('Saisissez 9 chiffres');try{const r=await api('/auth/request-otp',{method:'POST',body:JSON.stringify({telephone:`+221${local}`})});$('#phoneForm').hidden=true;$('#otpForm').hidden=false;$('#devHint').textContent=r.dev_code?`Mode développement : code ${r.dev_code}`:'';}catch(err){toast(err.message)}});
$('#otpForm').addEventListener('submit',async e=>{e.preventDefault();try{const local=normalizeLocalPhone($('#telephone').value);const r=await api('/auth/verify-otp',{method:'POST',body:JSON.stringify({telephone:`+221${local}`,code:$('#otp').value})});setToken(r.token);profile=r.user;setView(true);openProfile();}catch(err){toast(err.message)}});
$('#profileForm').addEventListener('submit',async e=>{e.preventDefault();try{profile=await api('/auth/profile',{method:'PATCH',body:JSON.stringify({pseudo:$('#pseudo').value,quartier_defaut:$('#quartierProfile').value})});hydrateProfile();closeSheets();await loadAlerts();toast('Profil enregistré');}catch(err){toast(err.message)}});
$('#alertForm').addEventListener('submit',async e=>{e.preventDefault();if(!selectedCategory)return toast('Choisissez une catégorie');if(!selectedLocation||!locationValidated)return toast('Sélectionnez une position au Sénégal pour détecter le quartier');const fd=new FormData();fd.set('categorie',selectedCategory);fd.set('quartier',$('#quartierAlert').value);fd.set('description',$('#description').value);fd.set('option_whatsapp',$('#whatsapp').checked);fd.set('latitude',selectedLocation.latitude);fd.set('longitude',selectedLocation.longitude);fd.set('country_code',selectedLocation.countryCode);fd.set('commune',selectedLocation.commune);fd.set('region',selectedLocation.region);if($('#photo').files[0])fd.set('photo',$('#photo').files[0]);try{await api('/alerts',{method:'POST',body:fd});e.target.reset();selectedCategory='';selectedLocation=null;locationValidated=false;if(locationMarker){locationMap.removeLayer(locationMarker);locationMarker=null}$('#coordinatesLabel').textContent='Aucune position précise sélectionnée';$('#coordinatesLabel').classList.remove('detected');$('#clearLocationButton').hidden=true;$$('[data-pick]').forEach(x=>x.classList.remove('active'));closeSheets();await loadAlerts();toast('Alerte publiée');}catch(err){toast(err.message)}});
$('#categoryFilters').addEventListener('click',e=>{const b=e.target.closest('[data-category]');if(!b)return;category=b.dataset.category;$$('[data-category]').forEach(x=>x.classList.toggle('active',x===b));loadAlerts()});
$('#categoryGrid').addEventListener('click',e=>{const b=e.target.closest('[data-pick]');if(!b)return;selectedCategory=b.dataset.pick;$$('[data-pick]').forEach(x=>x.classList.toggle('active',x===b))});
$('#alertList').addEventListener('click',async e=>{const confirm=e.target.closest('[data-confirm]'),resolve=e.target.closest('[data-resolve]');try{if(confirm)await api(`/alerts/${confirm.dataset.confirm}/confirm`,{method:'POST'});if(resolve)await api(`/alerts/${resolve.dataset.resolve}/resolve`,{method:'POST'});if(confirm||resolve)await loadAlerts();}catch(err){toast(err.message)}});
$$('[data-scope]').forEach(b=>b.addEventListener('click',()=>{scope=b.dataset.scope;previousOrder=[];lastFeedSignature='';$$('[data-scope]').forEach(x=>x.classList.toggle('active',x===b));loadAlerts()}));
$('#description').addEventListener('input',e=>$('#charCount').textContent=`${e.target.value.length}/280`);
$('#telephone').addEventListener('input',e=>e.target.value=normalizeLocalPhone(e.target.value));
$('#profileButton').addEventListener('click',openProfile);$('#createButton').addEventListener('click',openCreate);$$('[data-close]').forEach(x=>x.addEventListener('click',closeSheets));
$('#myAlertsButton').addEventListener('click',()=>{scope='mine';category='';previousOrder=[];lastFeedSignature='';$$('[data-scope],[data-category]').forEach(x=>x.classList.remove('active'));closeSheets();loadAlerts();toast('Affichage de vos alertes déclarées')});
$('#locateButton').addEventListener('click',async()=>{try{const position=await getCurrentPosition();setLocation(position.coords.latitude,position.coords.longitude,true)}catch(error){toast(error.message||geolocationErrorMessage(error))}});
$('#clearLocationButton').addEventListener('click',()=>{selectedLocation=null;locationValidated=false;$('#quartierAlert').value='';if(locationMarker){locationMap.removeLayer(locationMarker);locationMarker=null}$('#coordinatesLabel').textContent='Aucune position précise sélectionnée';$('#coordinatesLabel').classList.remove('detected');$('#clearLocationButton').hidden=true});
$('#logoutButton').addEventListener('click',()=>{setToken(null);location.reload()});window.addEventListener('online',loadAlerts);window.addEventListener('offline',()=>$('#offlineBanner').hidden=false);
if('serviceWorker' in navigator)navigator.serviceWorker.register('/static/service-worker.js');
boot().catch(e=>toast(e.message));
setInterval(()=>{if(getToken()&&!$('#feedView').hidden&&document.visibilityState==='visible')loadAlerts(true)},8000);
