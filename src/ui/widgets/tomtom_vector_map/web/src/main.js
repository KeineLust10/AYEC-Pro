import { LngLatBounds, Marker, NavigationControl, Popup } from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import { TomTomConfig } from '@tomtom-org/maps-sdk/core';
import { TomTomMap } from '@tomtom-org/maps-sdk/map';
import './style.css';

let mapInstance = null;
let apiKeyValue = '';
let bridge = null;
let trafficVisible = false;
let routeSourceReady = false;
let routePoints = [];
const personnelMarkers = new Map();
let centerMarker = null;
let selectedMarker = null;

function status(message, isError = false) {
  const element = document.getElementById('map-status');
  element.textContent = message;
  element.classList.toggle('error', isError);
  element.classList.add('visible');
  if (!isError && message === 'Harita hazir') {
    window.setTimeout(() => element.classList.remove('visible'), 1800);
  }
}

function markerElement(kind, label) {
  const element = document.createElement('div');
  element.className = `ayec-marker ayec-marker-${kind}`;
  element.title = label || '';
  element.innerHTML = '<span></span>';
  return element;
}

function addTrafficLayer() {
  if (!mapInstance || !mapInstance.isStyleLoaded() || mapInstance.getSource('ayec-tomtom-traffic')) return;
  const tile = `https://api.tomtom.com/maps/orbis/traffic/tile/flow/{z}/{x}/{y}.png?apiVersion=1&key=${encodeURIComponent(apiKeyValue)}`;
  mapInstance.addSource('ayec-tomtom-traffic', {
    type: 'raster',
    tiles: [tile],
    tileSize: 256,
    minzoom: 0,
    maxzoom: 20,
  });
  const firstSymbol = mapInstance.getStyle().layers.find((layer) => layer.type === 'symbol')?.id;
  mapInstance.addLayer({
    id: 'ayec-tomtom-traffic-flow',
    type: 'raster',
    source: 'ayec-tomtom-traffic',
    paint: { 'raster-opacity': 0.82 },
  }, firstSymbol);
}

function addRouteLayer() {
  if (!mapInstance || !mapInstance.isStyleLoaded() || routeSourceReady) return;
  mapInstance.addSource('ayec-field-route', {
    type: 'geojson',
    data: { type: 'FeatureCollection', features: [] },
  });
  mapInstance.addLayer({
    id: 'ayec-field-route-line',
    type: 'line',
    source: 'ayec-field-route',
    layout: { 'line-cap': 'round', 'line-join': 'round' },
    paint: { 'line-color': '#23c7ff', 'line-width': 5, 'line-opacity': 0.95 },
  });
  routeSourceReady = true;
}

function publishRoute(points, fit = false) {
  routePoints = points || [];
  addRouteLayer();
  if (!routeSourceReady) return;
  const coordinates = (points || []).map((point) => [Number(point[1]), Number(point[0])]);
  const feature = coordinates.length > 1 ? {
    type: 'Feature',
    properties: {},
    geometry: { type: 'LineString', coordinates },
  } : null;
  mapInstance.getSource('ayec-field-route').setData({
    type: 'FeatureCollection',
    features: feature ? [feature] : [],
  });
  if (fit && coordinates.length > 1) {
    const bounds = coordinates.reduce(
      (value, coordinate) => value.extend(coordinate),
      new LngLatBounds(coordinates[0], coordinates[0]),
    );
    mapInstance.fitBounds(bounds, { padding: 80, maxZoom: 17, duration: 500 });
  }
}

function connectBridge() {
  if (!window.qt || !window.qt.webChannelTransport || !window.QWebChannel) return;
  new window.QWebChannel(window.qt.webChannelTransport, (channel) => {
    bridge = channel.objects.fieldMapBridge;
    if (!mapInstance) return;
    mapInstance.on('click', (event) => {
      const point = [event.lngLat.lat, event.lngLat.lng];
      if (bridge && bridge.mapClicked) bridge.mapClicked(point[0], point[1]);
    });
  });
}

window.initAyecTomTomMap = (key, latitude, longitude) => {
  apiKeyValue = String(key || '').trim();
  if (!apiKeyValue) {
    status('TomTom Maps API anahtari bulunamadi.', true);
    return false;
  }
  try {
    const probeCanvas = document.createElement('canvas');
    const webgl2 = probeCanvas.getContext('webgl2', { failIfMajorPerformanceCaveat: false });
    if (!webgl2) {
      const message = 'WebGL2 kullanilamiyor. Qt WebEngine GPU/WebGL destegini etkinlestirin.';
      status(message, true);
      if (bridge && bridge.reportMapError) bridge.reportMapError(message);
      return false;
    }
    webgl2.getExtension('WEBGL_lose_context')?.loseContext();
    TomTomConfig.instance.put({ apiKey: apiKeyValue, language: 'tr-TR' });
    const sdkMap = new TomTomMap({
      mapLibre: {
        container: 'map',
        center: [Number(longitude), Number(latitude)],
        zoom: 14,
        pitch: 52,
        maxZoom: 20,
        attributionControl: true,
      },
    });
    mapInstance = sdkMap.mapLibreMap;
    mapInstance.addControl(new NavigationControl({ showCompass: true, visualizePitch: true }), 'bottom-right');
    mapInstance.on('load', () => {
      addRouteLayer();
      if (routePoints.length) publishRoute(routePoints);
      if (trafficVisible) addTrafficLayer();
      centerMarker = new Marker({ element: markerElement('center', 'Varsayilan merkez') })
        .setLngLat([Number(longitude), Number(latitude)]).addTo(mapInstance);
      status('Harita hazir');
      if (bridge && bridge.reportMapLoaded) bridge.reportMapLoaded();
      window.dispatchEvent(new Event('ayec-map-ready'));
    });
    mapInstance.on('style.load', () => {
      routeSourceReady = false;
      addRouteLayer();
      if (routePoints.length) publishRoute(routePoints);
      if (trafficVisible) addTrafficLayer();
    });
    mapInstance.on('error', (event) => {
      const message = event?.error?.message || 'Harita verisi yuklenemedi.';
      status(message, true);
      if (bridge && bridge.reportMapError) bridge.reportMapError(message);
      window.dispatchEvent(new CustomEvent('ayec-map-error', { detail: message }));
    });
    connectBridge();
    return true;
  } catch (error) {
    status(error?.message || 'TomTom vektor haritasi baslatilamadi.', true);
    window.dispatchEvent(new CustomEvent('ayec-map-error', { detail: error?.message || 'Map startup failed' }));
    return false;
  }
};

window.ayecTomTomMap = {
  setPitch(value) { if (mapInstance) mapInstance.easeTo({ pitch: Number(value), duration: 450 }); },
  flyTo(latitude, longitude, zoom = 15) {
    if (mapInstance) mapInstance.flyTo({ center: [Number(longitude), Number(latitude)], zoom: Number(zoom), essential: true });
  },
  setTraffic(active) {
    trafficVisible = Boolean(active);
    if (!mapInstance || !mapInstance.isStyleLoaded()) return;
    if (trafficVisible) addTrafficLayer();
    else if (mapInstance.getLayer('ayec-tomtom-traffic-flow')) mapInstance.removeLayer('ayec-tomtom-traffic-flow');
  },
  setPersonnel(records) {
    if (!mapInstance) return;
    for (const marker of personnelMarkers.values()) marker.remove();
    personnelMarkers.clear();
    (records || []).forEach((record) => {
      const latitude = Number(record.lat);
      const longitude = Number(record.lng);
      if (!Number.isFinite(latitude) || !Number.isFinite(longitude)) return;
      const element = markerElement('personnel', record.name || 'Teknisyen');
      const marker = new Marker({ element }).setLngLat([longitude, latitude]);
      if (record.name) marker.setPopup(new Popup({ offset: 18 }).setText(String(record.name)));
      marker.addTo(mapInstance);
      personnelMarkers.set(String(record.id ?? personnelMarkers.size), marker);
    });
  },
  setRoute(points) { publishRoute(points, true); },
  clearRoute() { publishRoute([]); },
  select(latitude, longitude) {
    if (!mapInstance) return;
    selectedMarker?.remove();
    selectedMarker = new Marker({ element: markerElement('selected', 'Secilen konum') })
      .setLngLat([Number(longitude), Number(latitude)]).addTo(mapInstance);
  },
  refresh() {
    if (!mapInstance) return;
    mapInstance.resize();
    mapInstance.setStyle(mapInstance.getStyle());
  },
};
