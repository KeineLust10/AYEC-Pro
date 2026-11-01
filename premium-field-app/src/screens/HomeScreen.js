import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
    ActivityIndicator,
    Alert,
    Image,
    Linking,
    Modal,
    RefreshControl,
    SafeAreaView,
    ScrollView,
    StatusBar,
    StyleSheet,
    Switch,
    Text,
    TextInput,
    TouchableOpacity,
    View,
} from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import * as SecureStore from 'expo-secure-store';
import * as Location from 'expo-location';
import * as ImagePicker from 'expo-image-picker';
import NetInfo from '@react-native-community/netinfo';
import { Camera } from 'expo-camera';
import * as BarCodeScanner from 'expo-barcode-scanner';
import SignatureCanvas from 'react-native-signature-canvas';
import { WebView } from 'react-native-webview';
import { cacheBootstrap, cacheServiceDetail, enqueueRequest, readBootstrapCache, readServiceDetailCache, syncOutbox, tenantKeyForUser } from '../api/offlineStore';
import {
    AlertCircle,
    Camera as CameraIcon,
    CalendarDays,
    ChevronLeft,
    ChevronRight,
    ClipboardList,
    LayoutDashboard,
    LogOut,
    MapPin,
    Navigation,
    Menu,
    Package,
    RefreshCw,
    Search,
    Settings,
    Users,
    FileText,
    BarChart3,
    CircleHelp,
    UserRound,
    X,
} from 'lucide-react-native';
import client from '../api/client';
import { buildPortalAuthScript } from '../api/webPortalAuth';

const PAGE_SIZE = 10;

const tr = {
    ready: 'Haz\u0131r',
    onDuty: 'G\u00f6revde',
    busy: 'Me\u015fgul',
    break: 'Mola',
    permissionTitle: '\u0130zin Reddedildi',
    permissionBody: 'Konum izni olmadan takip yap\u0131lamaz.',
    error: 'Hata',
    statusError: 'Durum g\u00fcncellenemedi.',
    refreshError: 'Genel Bak\u0131\u015f verileri yenilenemedi.',
};

function text(value) {
    return String(value || '').toLocaleLowerCase('tr-TR');
}

function statusKey(device) {
    const value = text(device.status);
    if (/iptal|iade/.test(value)) return 'cancelled';
    if (/kargo|d\u0131\u015f servis/.test(value)) return 'cargo';
    if (/teslim/.test(value)) return 'done';
    if (/par\u00e7a|parca/.test(value)) return 'part';
    if (/tamam|bitti|test|kontrol/.test(value)) return 'completed';
    if (/tamir|servis|devam|i\u015flemde/.test(value)) return 'active';
    return 'waiting';
}

function displayServiceSource(device) {
    const source = String(device.service_source || device.service || '').trim();
    const labels = {
        cle_maintenance: 'Bak\u0131m / Servis',
        maintenance: 'Bak\u0131m / Servis',
        service: 'Servis',
        automotive: '\u0130\u015f Emri',
        web_automotive: 'Web Otomotiv',
        web_teknik_servis: 'Web Teknik Servis',
    };
    return labels[source.toLocaleLowerCase('tr-TR').replace(/[ -]+/g, '_')] || source || 'Servis';
}

function displayDeliveryState(device) {
    const value = device.exit_date || device.delivery || device.estimated_date;
    return value ? formatDate(value) : 'Teslim Edilmedi';
}

function displayServiceStatus(device) {
    const labels = {
        waiting: 'S\u0131raya Al\u0131nacak',
        active: 'Serviste',
        completed: 'Kontrol Tamamland\u0131',
        done: 'Teslim Edildi',
        part: 'Par\u00e7a Bekliyor',
        cargo: 'D\u0131\u015f Serviste',
        cancelled: '\u0130ptal / \u0130ade',
    };
    return labels[statusKey(device)] || device.status || 'Bekliyor';
}

function moneyNumber(value) {
    if (value === null || value === undefined || value === '') return 0;
    if (typeof value === 'number') return Number.isFinite(value) ? value : 0;
    let text = String(value).trim().replace(/[\s\u00a0]/g, '').replace(/[^0-9,.-]/g, '');
    if (text.includes(',') && text.includes('.')) {
        text = text.lastIndexOf(',') > text.lastIndexOf('.')
            ? text.replace(/\./g, '').replace(',', '.')
            : text.replace(/,/g, '');
    } else if (text.includes(',')) {
        const fraction = text.split(',').pop();
        text = fraction.length <= 2 ? text.replace(/\./g, '').replace(',', '.') : text.replace(/,/g, '');
    } else if ((text.match(/\./g) || []).length > 1 || (/\.\d{3}$/.test(text) && text.split('.').length === 2)) {
        text = text.replace(/\./g, '');
    }
    const amount = Number(text);
    return Number.isFinite(amount) ? amount : 0;
}

function formatMoney(value) {
    const amount = moneyNumber(value);
    return `${amount.toLocaleString('tr-TR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} \u20ba`;
}

function formatQuantity(value) {
    return Math.trunc(Number(value || 0)).toLocaleString('tr-TR', { maximumFractionDigits: 0 });
}

function formatDate(value) {
    if (!value) return '-';
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? String(value).slice(0, 10) : date.toLocaleDateString('tr-TR');
}

export default function HomeScreen({ route }) {
    const [userData, setUserData] = useState(null);
    const [devices, setDevices] = useState([]);
    const [appointments, setAppointments] = useState([]);
    const [offers, setOffers] = useState([]);
    const [stockLocations, setStockLocations] = useState([]);
    const [customers, setCustomers] = useState([]);
    const [stockItems, setStockItems] = useState([]);
    const [activeModule, setActiveModule] = useState('');
    const [portalToken, setPortalToken] = useState('');
    const [portalLoading, setPortalLoading] = useState(false);
    const [showAppointments, setShowAppointments] = useState(false);
    const [summary, setSummary] = useState(null);
    const [loading, setLoading] = useState(true);
    const [refreshing, setRefreshing] = useState(false);
    const [error, setError] = useState('');
    const [query, setQuery] = useState('');
    const [filter, setFilter] = useState('all');
    const [page, setPage] = useState(1);
    const [fieldPanelOpen, setFieldPanelOpen] = useState(false);
    const [scannerOpen, setScannerOpen] = useState(false);
    const [cameraPermission, setCameraPermission] = useState(null);
    const [serviceModalOpen, setServiceModalOpen] = useState(false);
    const [signatureOpen, setSignatureOpen] = useState(false);
    const [selectedService, setSelectedService] = useState(null);
    const [serviceDetail, setServiceDetail] = useState(null);
    const [serviceStatus, setServiceStatus] = useState('waiting');
    const [faultDraft, setFaultDraft] = useState('');
    const [repairDraft, setRepairDraft] = useState('');
    const [serviceSaving, setServiceSaving] = useState(false);
    const [evidenceToken, setEvidenceToken] = useState('');
    const [localEvidence, setLocalEvidence] = useState([]);
    const signatureRef = useRef(null);
    const [menuOpen, setMenuOpen] = useState(false);
    const [menuQuery, setMenuQuery] = useState('');
    const [isTracking, setIsTracking] = useState(false);
    const [personnelStatus, setPersonnelStatus] = useState(tr.ready);
    const [lastLocation, setLastLocation] = useState(null);
    const trackingInterval = useRef(null);
    const onLogout = route?.params?.onLogout;

    const sectorValue = text(userData?.sector || userData?.industry || userData?.current_sector || process.env.EXPO_PUBLIC_SECTOR);
    const automotive = sectorValue.includes('otomotiv');

    const stopTracking = useCallback(() => {
        if (trackingInterval.current) {
            clearInterval(trackingInterval.current);
            trackingInterval.current = null;
        }
    }, []);

    const sendLocation = useCallback(async () => {
        try {
            const location = await Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.Balanced });
            const { latitude, longitude } = location.coords;
            setLastLocation({ latitude, longitude });
            await client.post('/mobile/personnel/location', { lat: latitude, lng: longitude });
        } catch (locationError) {
            console.error('Location update failed', locationError);
        }
    }, []);

    const loadData = useCallback(async (quiet = false) => {
        if (!quiet) setLoading(true);
        setError('');
        try {
            const storedUser = await AsyncStorage.getItem('userData');
            const parsedUser = storedUser ? JSON.parse(storedUser) : null;
            if (parsedUser) setUserData(parsedUser);

            const tenantId = tenantKeyForUser(parsedUser);
            const response = await client.get('/desktop/bootstrap');
            const source = response.data || {};
            await cacheBootstrap(tenantId, source);
            setDevices(Array.isArray(source.devices) ? source.devices : []);
            setAppointments(Array.isArray(source.appointments) ? source.appointments : []);
            setOffers(Array.isArray(source.offers) ? source.offers : []);
            setStockLocations(Array.isArray(source.stock_locations) ? source.stock_locations : []);
            setCustomers(Array.isArray(source.customers) ? source.customers : []);
            setStockItems(Array.isArray(source.stock) ? source.stock : []);
            setSummary({
                total_receivables: 0,
                counts: source.counts || {},
                stock_location_summary: source.stock_location_summary || {},
            });
            setPersonnelStatus(tr.ready);
        } catch (loadError) {
            console.error('Dashboard load failed', loadError);
            try {
                const storedUser = await AsyncStorage.getItem('userData');
                const tenantId = tenantKeyForUser(storedUser ? JSON.parse(storedUser) : null);
                const cached = await readBootstrapCache(tenantId);
                if (cached) {
                    setDevices(Array.isArray(cached.devices) ? cached.devices : []);
                    setAppointments(Array.isArray(cached.appointments) ? cached.appointments : []);
                    setOffers(Array.isArray(cached.offers) ? cached.offers : []);
                    setStockLocations(Array.isArray(cached.stock_locations) ? cached.stock_locations : []);
                    setCustomers(Array.isArray(cached.customers) ? cached.customers : []);
                    setStockItems(Array.isArray(cached.stock) ? cached.stock : []);
                    setSummary({ total_receivables: 0, counts: cached.counts || {}, stock_location_summary: cached.stock_location_summary || {} });
                    setError('Cevrimdisi mod: son kaydedilen veriler gosteriliyor.');
                } else {
                    setError(tr.refreshError);
                }
            } catch (_) {
                setError(tr.refreshError);
            }
        } finally {
            setLoading(false);
            setRefreshing(false);
        }
    }, []);

    useEffect(() => {
        loadData();
        return stopTracking;
    }, [loadData, stopTracking]);

    useEffect(() => {
        if (activeModule !== 'portal') return;
        let mounted = true;
        setPortalLoading(true);
        SecureStore.getItemAsync('userToken').then((token) => {
            if (mounted) { setPortalToken(token || ''); setPortalLoading(Boolean(token)); }
        }).catch((tokenError) => {
            console.error('Portal token could not be loaded', tokenError);
            if (mounted) { setPortalToken(''); setPortalLoading(false); }
        });
        return () => { mounted = false; };
    }, [activeModule]);

    useEffect(() => NetInfo.addEventListener(async (state) => {
        if (!state.isConnected || state.isInternetReachable === false) return;
        try {
            const storedUser = await AsyncStorage.getItem('userData');
            const tenantId = tenantKeyForUser(storedUser ? JSON.parse(storedUser) : null);
            await syncOutbox(tenantId, client);
        } catch (syncError) {
            console.error('Offline sync failed', syncError);
        }
    }), []);

    const toggleTracking = useCallback(async (value) => {
        if (!value) {
            setIsTracking(false);
            stopTracking();
            return;
        }
        const permission = await Location.requestForegroundPermissionsAsync();
        if (permission.status !== 'granted') {
            Alert.alert(tr.permissionTitle, tr.permissionBody);
            return;
        }
        setIsTracking(true);
        await sendLocation();
        trackingInterval.current = setInterval(sendLocation, 120000);
    }, [sendLocation, stopTracking]);

    const updateStatus = useCallback(async (nextStatus) => {
        try {
            await client.post('/mobile/personnel/status', { status: nextStatus });
            setPersonnelStatus(nextStatus);
        } catch (statusError) {
            if (!statusError?.response) {
                try {
                    const storedUser = await AsyncStorage.getItem('userData');
                    const tenantId = tenantKeyForUser(storedUser ? JSON.parse(storedUser) : null);
                    await enqueueRequest(tenantId, 'post', '/mobile/personnel/status', { status: nextStatus });
                    setPersonnelStatus(nextStatus);
                    Alert.alert('Cevrimdisi kaydedildi', 'Baglanti gelince durum degisikligi eszamanlanacak.');
                    return;
                } catch (queueError) {
                    console.error('Offline status queue failed', queueError);
                }
            }
            Alert.alert(tr.error, tr.statusError);
        }
    }, []);

    const handleLogout = useCallback(async () => {
        stopTracking();
        await SecureStore.deleteItemAsync('userToken');
        await AsyncStorage.removeItem('userData');
        if (onLogout) onLogout();
    }, [onLogout, stopTracking]);

    const openService = useCallback(async (device) => {
        const trackingNo = String(device?.tracking_no || '').trim();
        if (!trackingNo) return;
        setSelectedService(device);
        setServiceDetail({ device, used_parts: [], evidence: [] });
        setFaultDraft(String(device.fault_description || ''));
        setRepairDraft(String(device.repair_details || ''));
        const currentStatus = statusKey(device);
        setServiceStatus(['waiting', 'active', 'completed'].includes(currentStatus) ? currentStatus : '');
        setLocalEvidence([]);
        setServiceModalOpen(true);
        let tenantId = null;
        try {
            const storedUser = await AsyncStorage.getItem('userData');
            tenantId = tenantKeyForUser(storedUser ? JSON.parse(storedUser) : null);
            const token = await SecureStore.getItemAsync('userToken');
            setEvidenceToken(token || '');
            const response = await client.get('/mobile/service/detail', { params: { tracking_no: trackingNo } });
            setServiceDetail(response.data || { device, used_parts: [], evidence: [] });
            await cacheServiceDetail(tenantId, trackingNo, response.data || { device, used_parts: [], evidence: [] });
            setFaultDraft(String(response.data?.device?.fault_description || ''));
            setRepairDraft(String(response.data?.device?.repair_details || ''));
            const fetchedStatus = statusKey(response.data?.device || device);
            setServiceStatus(['waiting', 'active', 'completed'].includes(fetchedStatus) ? fetchedStatus : '');
        } catch (detailError) {
            if (detailError?.response) {
                Alert.alert('Servis detayi alinamadi', 'Bu servis kaydina erisim izniniz olmayabilir.');
            } else {
                try {
                    const cached = await readServiceDetailCache(tenantId, trackingNo);
                    if (cached) {
                        setServiceDetail(cached);
                        setFaultDraft(String(cached.device?.fault_description || ''));
                        setRepairDraft(String(cached.device?.repair_details || ''));
                        const cachedStatus = statusKey(cached.device || device);
                        setServiceStatus(['waiting', 'active', 'completed'].includes(cachedStatus) ? cachedStatus : '');
                    }
                } catch (cacheError) {
                    console.error('Offline service detail could not be read', cacheError);
                }
            }
        }
    }, []);

    const saveServiceChanges = useCallback(async () => {
        if (!selectedService?.tracking_no) return;
        setServiceSaving(true);
        const payload = {
            tracking_no: selectedService.tracking_no,
            fault_description: faultDraft,
            repair_details: repairDraft,
        };
        if (serviceStatus) payload.status = serviceStatus;
        try {
            await client.post('/mobile/service/update', payload);
            setDevices((items) => items.map((item) => item.tracking_no === selectedService.tracking_no
                ? { ...item, fault_description: faultDraft, repair_details: repairDraft, status: serviceStatus ? (serviceStatus === 'active' ? '\u0130\u015flemde' : serviceStatus === 'completed' ? 'Kontrol Tamamland\u0131' : 'Bekliyor') : item.status }
                : item));
            setServiceDetail((current) => ({ ...current, device: { ...current?.device, ...payload } }));
            try {
                const storedUser = await AsyncStorage.getItem('userData');
                const tenantId = tenantKeyForUser(storedUser ? JSON.parse(storedUser) : null);
                await cacheServiceDetail(tenantId, selectedService.tracking_no, {
                    ...serviceDetail,
                    device: { ...serviceDetail?.device, ...payload },
                });
            } catch (cacheError) {
                console.error('Updated service detail could not be cached', cacheError);
            }
            Alert.alert('Kaydedildi', 'Servis bilgileri merkezi kayda yazildi.');
        } catch (saveError) {
            if (!saveError?.response) {
                try {
                    const storedUser = await AsyncStorage.getItem('userData');
                    const tenantId = tenantKeyForUser(storedUser ? JSON.parse(storedUser) : null);
                    await enqueueRequest(tenantId, 'post', '/mobile/service/update', payload);
                    setServiceDetail((current) => ({ ...current, device: { ...current?.device, ...payload } }));
                    Alert.alert('Cevrimdisi kaydedildi', 'Degisiklikler baglanti kurulunca gonderilecek.');
                } catch (queueError) {
                    console.error('Service update could not be queued', queueError);
                    Alert.alert('Kaydedilemedi', 'Cevrimdisi kuyruk icin tenant bilgisi bulunamadi.');
                }
            } else {
                Alert.alert('Kaydedilemedi', String(saveError.response.data?.error || 'Servis degisikligi reddedildi.'));
            }
        } finally {
            setServiceSaving(false);
        }
    }, [faultDraft, repairDraft, selectedService, serviceDetail, serviceStatus]);

    const saveEvidence = useCallback(async (evidenceType, imageBase64, uri = '') => {
        if (!selectedService?.tracking_no || !imageBase64) return;
        const payload = {
            tracking_no: selectedService.tracking_no,
            evidence_type: evidenceType,
            client_id: `mob-${Date.now()}-${Math.random().toString(36).slice(2, 12)}`,
            image_base64: imageBase64,
        };
        try {
            const response = await client.post('/mobile/service/evidence', payload, { timeout: 60000 });
            const record = { id: response.data.id, evidence_type: evidenceType, mime_type: evidenceType === 'signature' ? 'image/png' : 'image/jpeg' };
            const nextDetail = { ...serviceDetail, evidence: [record, ...(serviceDetail?.evidence || [])] };
            setServiceDetail(nextDetail);
            try {
                const storedUser = await AsyncStorage.getItem('userData');
                const tenantId = tenantKeyForUser(storedUser ? JSON.parse(storedUser) : null);
                await cacheServiceDetail(tenantId, selectedService.tracking_no, nextDetail);
            } catch (cacheError) {
                console.error('Uploaded evidence metadata could not be cached', cacheError);
            }
            Alert.alert('Kanita eklendi', 'Gorsel servis kaydina yuklendi.');
        } catch (uploadError) {
            if (!uploadError?.response) {
                try {
                    const storedUser = await AsyncStorage.getItem('userData');
                    const tenantId = tenantKeyForUser(storedUser ? JSON.parse(storedUser) : null);
                    await enqueueRequest(tenantId, 'post', '/mobile/service/evidence', payload);
                    setLocalEvidence((items) => [{ evidence_type: evidenceType, uri, pending: true }, ...items]);
                    Alert.alert('Cevrimdisi kaydedildi', 'Gorsel yerel kuyruga eklendi ve baglanti gelince gonderilecek.');
                } catch (queueError) {
                    console.error('Service evidence could not be queued', queueError);
                    Alert.alert('Kanita eklenemedi', 'Cevrimdisi kuyruk icin tenant bilgisi bulunamadi.');
                }
            } else {
                Alert.alert('Yukleme basarisiz', String(uploadError.response.data?.error || 'Gorsel servis kaydina eklenemedi.'));
            }
        }
    }, [selectedService, serviceDetail]);

    const captureEvidence = useCallback(async (evidenceType) => {
        const permission = await ImagePicker.requestCameraPermissionsAsync();
        if (!permission.granted) {
            Alert.alert('Kamera izni gerekli', 'Servis fotografi almak icin kamera izni verin.');
            return;
        }
        const result = await ImagePicker.launchCameraAsync({
            mediaTypes: ImagePicker.MediaTypeOptions.Images,
            base64: true,
            quality: 0.65,
            exif: false,
        });
        if (result.canceled || !result.assets?.[0]?.base64) return;
        await saveEvidence(evidenceType, result.assets[0].base64, result.assets[0].uri || '');
    }, [saveEvidence]);

    const saveSignature = useCallback((dataUrl) => {
        const encoded = String(dataUrl || '').trim();
        setSignatureOpen(false);
        if (encoded) saveEvidence('signature', encoded);
    }, [saveEvidence]);

    const openServiceAddress = useCallback(async () => {
        const device = serviceDetail?.device || selectedService || {};
        const address = String(device.customer_address || device.address || device.installation_address || '').trim();
        if (!address) {
            Alert.alert('Adres bulunamadi', 'Servis kaydinda yonlendirilecek bir adres yok.');
            return;
        }
        const url = `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(address)}`;
        try {
            await Linking.openURL(url);
        } catch (_) {
            Alert.alert('Harita acilamadi', 'Adres icin harita uygulamasi baslatilamadi.');
        }
    }, [selectedService, serviceDetail]);

    const countFor = useCallback((key) => devices.filter((device) => statusKey(device) === key).length, [devices]);
    const cards = useMemo(() => [
        { key: 'completed', title: automotive ? 'KONTROL\u00dc TAMAMLANAN' : 'TAM\u0130R ED\u0130LENLER', color: '#05a85b', icon: 'T' },
        { key: 'active', title: automotive ? 'SERV\u0130STEK\u0130 ARA\u00c7LAR' : 'TAM\u0130RDE OLANLAR', color: '#f59e0b', icon: 'D' },
        { key: 'waiting', title: automotive ? 'SIRAYA ALINACAKLAR' : '\u0130\u015eLEME ALINACAKLAR', color: '#1e88e5', icon: 'I' },
        { key: 'cancelled', title: '\u0130PTAL / \u0130ADE', color: '#ef4444', icon: 'X' },
        { key: 'cargo', title: automotive ? 'DI\u015e SERV\u0130SE G\u0130DENLER' : 'KARGOYA VER\u0130LENLER', color: '#d41462', icon: 'K' },
        { key: 'done', title: automotive ? 'TESL\u0130M ED\u0130LEN ARA\u00c7LAR' : 'TESL\u0130M ED\u0130LENLER', color: '#0891b2', icon: 'E' },
        { key: 'part', title: 'PAR\u00c7A BEKLEYENLER', color: '#0e7ab4', icon: 'P' },
        { key: 'debt', title: 'BEKLEYEN ALACAK', color: '#625da8', icon: 'B', value: Number(summary?.total_receivables || 0), money: true },
    ], [automotive, summary]);

    const filteredDevices = useMemo(() => {
        const needle = text(query);
        return devices.filter((device) => {
            const matchesFilter = filter === 'all' || statusKey(device) === filter;
            const haystack = text([
                device.tracking_no,
                device.customer_name,
                device.device_type,
                device.brand,
                device.model,
                device.status,
            ].join(' '));
            return matchesFilter && (!needle || haystack.includes(needle));
        });
    }, [devices, filter, query]);

    const appointmentRows = useMemo(() => appointments.map((appointment) => {
        const offerId = Number(appointment.offer_id || appointment.quote_id || 0);
        const offer = offers.find((item) => Number(item.id) === offerId);
        const planItems = Array.isArray(appointment.plan_items) && appointment.plan_items.length
            ? appointment.plan_items
            : (Array.isArray(offer?.items) ? offer.items : []);
        return { ...appointment, planItems };
    }), [appointments, offers]);

    const vehicleLocations = useMemo(
        () => stockLocations.filter((location) => location.location_type === 'vehicle'),
        [stockLocations],
    );
    const vehicleQuantity = useMemo(
        () => vehicleLocations.reduce((total, location) => total + Number(location.quantity || 0), 0),
        [vehicleLocations],
    );

    const pageCount = Math.max(1, Math.ceil(filteredDevices.length / PAGE_SIZE));
    const safePage = Math.min(page, pageCount);
    const pageRows = filteredDevices.slice((safePage - 1) * PAGE_SIZE, safePage * PAGE_SIZE);

    const setActiveFilter = useCallback((nextFilter) => {
        setFilter(nextFilter);
        setPage(1);
    }, []);

    const mobileMenuGroups = useMemo(() => [
        {
            key: 'workspace', title: 'İş Alanı', icon: LayoutDashboard,
            items: [
                { key: 'all', title: 'Genel Bakış', description: `${devices.length} aktif servis kaydi`, color: '#60a5fa' },
                { key: 'appointments', title: 'Randevu Takvimi', description: `${appointmentRows.length} planlı randevu`, color: '#a78bfa' },
                { key: 'module:customers', title: 'Müşteriler', description: `${customers.length} müşteri kaydı`, color: '#34d399' },
                { key: 'module:offers', title: 'Teklifler', description: `${offers.length} açık teklif`, color: '#fbbf24' },
                { key: 'portal', title: 'AYEC Pro Tüm Program Menüleri', description: 'Tüm program modülleri, akıllı içe aktarma ve kütüphaneler', color: '#818cf8' },
            ],
        },
        {
            key: 'services', title: 'Teknik Servis', icon: ClipboardList,
            items: [
                ...cards.filter((card) => !card.money).map((card) => ({ key: card.key, title: card.title, description: `${countFor(card.key)} servis kaydi`, color: card.color })),
                { key: 'scan', title: 'Barkod / QR Tara', description: 'Cihaz seri numarasıyla kayıt bul', color: '#22d3ee' },
                { key: 'field', title: 'Personel ve Saha', description: isTracking ? 'Konum takibi açık' : 'Durum ve konum takibi', color: '#fb7185' },
            ],
        },
        {
            key: 'operations', title: 'Operasyon', icon: Package,
            items: [
                { key: 'module:stock', title: 'Stok ve Araç Deposu', description: `${stockItems.length} stok kalemi / ${stockLocations.length} konum`, color: '#38bdf8' },
                { key: 'module:reports', title: 'Servis Raporları', description: 'Durum, iş yük ve saha ozeti', color: '#c084fc' },
                { key: 'sync', title: 'Senkronizasyon', description: error ? 'Çevrimdışı veriler' : 'Sunucu verisini yenile', color: '#4ade80' },
            ],
        },
        {
            key: 'support', title: 'Hesap ve Yardım', icon: Settings,
            items: [
                { key: 'module:profile', title: 'Hesap Bilgileri', description: userData?.company_name || userData?.username || 'Oturum ve şirket bilgisi', color: '#94a3b8' },
                { key: 'module:help', title: 'Kullanım Kılavuzu', description: 'Saha uygulaması hızlı başlangıç', color: '#fda4af' },
            ],
        },
    ], [appointmentRows.length, cards, countFor, customers.length, devices.length, error, isTracking, offers.length, stockItems.length, stockLocations.length, userData]);

    const filteredMenuGroups = useMemo(() => {
        const needle = text(menuQuery).trim();
        if (!needle) return mobileMenuGroups;
        return mobileMenuGroups.map((group) => ({
            ...group,
            items: group.items.filter((item) => text(`${group.title} ${item.title} ${item.description}`).includes(needle)),
        })).filter((group) => group.items.length);
    }, [menuQuery, mobileMenuGroups]);

    const handleMenuAction = useCallback((key) => {
        if (key === 'appointments') {
            setShowAppointments(true);
            setActiveModule('');
        } else if (key === 'field') {
            setFieldPanelOpen(true);
            setActiveModule('');
        } else if (key === 'scan') {
            setScannerOpen(true);
            setActiveModule('');
        } else if (key === 'sync') {
            loadData(true);
        } else if (key === 'portal') {
            setActiveModule('portal');
        } else if (key.startsWith('module:')) {
            setActiveModule(key.slice(7));
        } else {
            setActiveFilter(key);
            setActiveModule('');
        }
        setMenuOpen(false);
        setMenuQuery('');
    }, [loadData, setActiveFilter]);

    const activeService = serviceDetail?.device || selectedService || {};
    const serviceEvidence = serviceDetail?.evidence || [];

    if (loading) {
        return <View style={styles.center}><ActivityIndicator size="large" color="#3b82f6" /></View>;
    }

    return (
        <SafeAreaView style={styles.container}>
            <StatusBar barStyle="light-content" backgroundColor="#071525" />
            <Modal visible={Boolean(activeModule)} animationType="slide" onRequestClose={() => setActiveModule('')}>
                <SafeAreaView style={{ flex: 1, backgroundColor: '#06111f' }}>
                    <View style={styles.moduleHeader}>
                        <View style={{ flex: 1 }}>
                            <Text style={styles.moduleEyebrow}>AYEC PRO / SAHA ÇALIŞMA ALANI</Text>
                            <Text style={styles.moduleTitle}>{({ portal: 'AYEC Pro Full Program', customers: 'Müşteri Defteri', offers: 'Teklif Merkezi', stock: 'Stok ve Araç Deposu', reports: 'Servis Raporları', profile: 'Hesap Bilgileri', help: 'Saha Hızlı Kılavuzu' })[activeModule] || 'Modul'}</Text>
                        </View>
                        <TouchableOpacity onPress={() => setActiveModule('')} style={styles.headerButton}><X size={19} color="#dbeafe" /></TouchableOpacity>
                    </View>
                    {activeModule === 'portal' ? (
                        (() => {
                            const baseUrl = String(client.defaults.baseURL || 'https://panel.ayecpro.com/api').replace(/\/api\/?$/, '');
                            const origin = new URL(baseUrl).origin;
                            return (
                                <View style={styles.portalContainer}>
                                    {portalLoading ? <View style={styles.portalLoading}><ActivityIndicator color="#60a5fa" /><Text style={styles.moduleRowMeta}>AYEC Pro modulleri yukleniyor...</Text></View> : null}
                                    {portalToken ? <WebView
                                        source={{ uri: `${baseUrl}/?page=dashboard` }}
                                        originWhitelist={[`${origin}/*`]}
                                        injectedJavaScriptBeforeContentLoaded={buildPortalAuthScript(portalToken)}
                                        injectedJavaScript={buildPortalAuthScript(portalToken)}
                                        injectedJavaScriptBeforeContentLoadedForMainFrameOnly={false}
                                        javaScriptEnabled
                                        domStorageEnabled
                                        sharedCookiesEnabled
                                        thirdPartyCookiesEnabled
                                        setSupportMultipleWindows={false}
                                        onMessage={(event) => { if (event.nativeEvent.data === 'AYEC_AUTH_EXPIRED') handleLogout(); }}
                                        onLoadStart={() => setPortalLoading(true)}
                                        onLoadEnd={() => setPortalLoading(false)}
                                        onError={() => { setPortalLoading(false); Alert.alert('Moduller acilamadi', 'AYEC Pro web servisine baglanilamadi. Baglantiyi kontrol edip tekrar deneyin.'); }}
                                        onShouldStartLoadWithRequest={(request) => request.url.startsWith(`${origin}/`) || request.url === origin || request.url.startsWith(`blob:${origin}/`) || request.url.startsWith('data:')}
                                        allowsBackForwardNavigationGestures
                                        style={{ flex: 1, backgroundColor: '#fff' }}
                                    /> : <View style={styles.portalError}><Text style={styles.moduleRowTitle}>Guvenli oturum bulunamadi</Text><Text style={styles.moduleRowMeta}>Tum AYEC Pro modulleri icin once saha hesabinla giris yap.</Text></View>}
                                </View>
                            );
                        })()
                    ) : (
                    <ScrollView contentContainerStyle={styles.moduleContent}>
                        {activeModule === 'customers' && (
                            <>
                                <View style={styles.moduleSummary}><Users size={20} color="#34d399" /><View style={{ flex: 1 }}><Text style={styles.moduleSummaryValue}>{customers.length}</Text><Text style={styles.moduleSummaryLabel}>Kayıtlı müşteri</Text></View></View>
                                {customers.slice(0, 200).map((item, index) => (
                                    <View key={String(item.id || index)} style={styles.moduleRow}>
                                        <View style={styles.moduleAvatar}><Text style={styles.moduleAvatarText}>{String(item.name || item.customer_name || '?').slice(0, 1).toUpperCase()}</Text></View>
                                        <View style={{ flex: 1 }}><Text style={styles.moduleRowTitle}>{item.name || item.customer_name || item.title || 'Müşteri'}</Text><Text style={styles.moduleRowMeta}>{item.phone || item.mobile || item.email || item.address || 'İletişim bilgisi yok'}</Text></View>
                                        <Text style={styles.moduleChevron}>›</Text>
                                    </View>
                                ))}
                                {!customers.length && <Text style={styles.moduleEmpty}>Müşteri kaydı bulunamadı.</Text>}
                            </>
                        )}
                        {activeModule === 'offers' && (
                            <>
                                <View style={styles.moduleSummary}><FileText size={20} color="#fbbf24" /><View style={{ flex: 1 }}><Text style={styles.moduleSummaryValue}>{offers.length}</Text><Text style={styles.moduleSummaryLabel}>Teklif kaydı</Text></View></View>
                                {offers.slice(0, 200).map((item, index) => (
                                    <View key={String(item.id || index)} style={styles.moduleRow}><View style={{ flex: 1 }}><Text style={styles.moduleRowTitle}>{item.title || item.offer_no || item.customer_name || `Teklif ${index + 1}`}</Text><Text style={styles.moduleRowMeta}>{[item.customer_name, item.status, formatDate(item.created_at || item.date)].filter(Boolean).join('  /  ') || 'Teklif kaydı'}</Text></View><Text style={styles.moduleRowAmount}>{formatQuantity(item.total || item.grand_total || item.amount || 0)} TL</Text></View>
                                ))}
                                {!offers.length && <Text style={styles.moduleEmpty}>Teklif kaydı bulunamadı.</Text>}
                            </>
                        )}
                        {activeModule === 'stock' && (
                            <>
                                <View style={styles.moduleSummary}><Package size={20} color="#38bdf8" /><View style={{ flex: 1 }}><Text style={styles.moduleSummaryValue}>{stockItems.length}</Text><Text style={styles.moduleSummaryLabel}>Stok kalemi / {stockLocations.length} depo ve araç konumu</Text></View></View>
                                {stockLocations.slice(0, 100).map((item, index) => <View key={String(item.id || index)} style={styles.moduleRow}><View style={{ flex: 1 }}><Text style={styles.moduleRowTitle}>{item.name || item.location_name || item.title || 'Stok konumu'}</Text><Text style={styles.moduleRowMeta}>{item.location_type || item.type || 'Depo'}</Text></View><Text style={styles.moduleRowAmount}>{formatQuantity(item.quantity || item.total_quantity || 0)}</Text></View>)}
                                {!stockLocations.length && stockItems.slice(0, 100).map((item, index) => <View key={String(item.id || index)} style={styles.moduleRow}><View style={{ flex: 1 }}><Text style={styles.moduleRowTitle}>{item.name || item.product_name || item.title || 'Stok kalemi'}</Text><Text style={styles.moduleRowMeta}>{item.code || item.sku || item.category || 'Stok'}</Text></View><Text style={styles.moduleRowAmount}>{formatQuantity(item.quantity || item.stock_quantity || 0)}</Text></View>)}
                                {!stockItems.length && !stockLocations.length && <Text style={styles.moduleEmpty}>Stok bilgisi bulunamadı.</Text>}
                            </>
                        )}
                        {activeModule === 'reports' && (
                            <>
                                <View style={styles.moduleSummary}><BarChart3 size={20} color="#c084fc" /><View style={{ flex: 1 }}><Text style={styles.moduleSummaryValue}>Servis performansi</Text><Text style={styles.moduleSummaryLabel}>Güncel tenant verisine göre</Text></View></View>
                                {cards.filter((card) => !card.money).map((card) => <View key={card.key} style={styles.moduleMetricRow}><View style={[styles.moduleMetricDot, { backgroundColor: card.color }]} /><Text style={styles.moduleRowTitle}>{card.title}</Text><Text style={styles.moduleMetricValue}>{countFor(card.key)}</Text></View>)}
                                <View style={styles.moduleFootnote}><Text style={styles.moduleFootnoteText}>Raporlar yalnizca oturum acik sirketin servis kayitlarini kapsar.</Text></View>
                            </>
                        )}
                        {activeModule === 'profile' && (
                            <View style={styles.moduleInfoCard}><UserRound size={24} color="#93c5fd" /><Text style={styles.moduleRowTitle}>{userData?.full_name || userData?.name || userData?.username || 'Saha kullanıcısı'}</Text><Text style={styles.moduleRowMeta}>{userData?.company_name || 'AYEC Pro Şirket hesabı'}</Text><Text style={styles.moduleFootnoteText}>Oturum ve servis verileri şirket izolasyonu ile korunur.</Text></View>
                        )}
                        {activeModule === 'help' && (
                            <View style={styles.moduleInfoCard}><CircleHelp size={24} color="#fda4af" /><Text style={styles.moduleRowTitle}>Saha servis akışı</Text><Text style={styles.moduleRowMeta}>Servis listesinden bir kayıt seçin; cihaz ve müşteri bilgisini inceleyin, durumu güncelleyin, fotoğraf veya müşteri imzası ekleyin. Bağlantı yoksa işlemler tenant bazlı güvenli kuyruğa alınır.</Text><TouchableOpacity onPress={() => { setActiveModule(''); setScannerOpen(true); }} style={styles.modulePrimaryButton}><Text style={styles.modulePrimaryText}>Barkod veya QR tara</Text></TouchableOpacity></View>
                        )}
                    </ScrollView>
                    )}
                </SafeAreaView>
            </Modal>
            <Modal visible={serviceModalOpen} animationType="slide" onRequestClose={() => setServiceModalOpen(false)}>
                <SafeAreaView style={{ flex: 1, backgroundColor: '#071525' }}>
                    <View style={{ paddingHorizontal: 16, paddingVertical: 12, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', borderBottomWidth: 1, borderBottomColor: '#244766' }}>
                        <View style={{ flex: 1, paddingRight: 12 }}>
                            <Text style={{ color: '#f8fafc', fontSize: 18, fontWeight: '800' }}>Servis kaydi</Text>
                            <Text numberOfLines={1} style={{ color: '#93c5fd', marginTop: 3 }}>{activeService.tracking_no || '-'}</Text>
                        </View>
                        <TouchableOpacity onPress={() => setServiceModalOpen(false)} style={styles.headerButton}><X size={20} color="#dbeafe" /></TouchableOpacity>
                    </View>
                    <ScrollView contentContainerStyle={{ padding: 16, paddingBottom: 24 }} keyboardShouldPersistTaps="handled">
                        <View style={styles.detailCard}>
                            <Text style={styles.detailSectionTitle}>Müşteri ve cihaz</Text>
                            <Text style={styles.detailPrimary}>{activeService.customer_name || activeService.customer || '-'}</Text>
                            <Text style={styles.detailText}>{[activeService.device_type, activeService.brand || activeService.device_brand, activeService.model || activeService.device_model].filter(Boolean).join(' / ') || '-'}</Text>
                            <Text style={styles.detailText}>Seri no: {activeService.serial_no || activeService.serial_number || '-'}</Text>
                            <Text style={styles.detailText}>Telefon: {activeService.customer_phone || activeService.customer_contact || '-'}</Text>
                            <TouchableOpacity onPress={openServiceAddress} style={styles.detailLink}>
                                <Navigation size={16} color="#60a5fa" />
                                <Text style={styles.detailLinkText}>{activeService.customer_address || activeService.address || activeService.installation_address || 'Haritada a\u00e7'}</Text>
                            </TouchableOpacity>
                        </View>

                        <View style={styles.detailCard}>
                            <Text style={styles.detailSectionTitle}>Durum ve ariza</Text>
                            <View style={styles.detailStatusRow}>
                                {[
                                    { key: 'waiting', label: 'Sirada' },
                                    { key: 'active', label: '\u0130\u015flemde' },
                                    { key: 'completed', label: 'Kontrol tamam' },
                                ].map((item) => (
                                    <TouchableOpacity key={item.key} onPress={() => setServiceStatus(item.key)} style={[styles.detailStatusChip, serviceStatus === item.key && styles.detailStatusChipActive]}>
                                        <Text style={styles.detailStatusText}>{item.label}</Text>
                                    </TouchableOpacity>
                                ))}
                            </View>
                            <Text style={styles.detailFieldLabel}>Müşteri bildirimi / ariza</Text>
                            <TextInput value={faultDraft} onChangeText={setFaultDraft} multiline placeholder="Ariza aciklamasi" placeholderTextColor="#64748b" style={styles.serviceInput} />
                            <Text style={styles.detailFieldLabel}>Yapilan islemler</Text>
                            <TextInput value={repairDraft} onChangeText={setRepairDraft} multiline placeholder="Teshis, onarim ve test sonucu" placeholderTextColor="#64748b" style={styles.serviceInput} />
                        </View>

                        <View style={styles.detailCard}>
                            <View style={styles.detailSectionRow}>
                                <Text style={styles.detailSectionTitle}>Kullanilan parcalar</Text>
                                <Text style={styles.detailCount}>{(serviceDetail?.used_parts || []).length}</Text>
                            </View>
                            {(serviceDetail?.used_parts || []).length ? serviceDetail.used_parts.map((part, index) => (
                                <View key={String(part.id || index)} style={styles.partLine}>
                                    <Text style={styles.detailText}>{part.part_name || part.name || part.item_name || part.description || 'Par\u00e7a'}</Text>
                                    <Text style={styles.detailText}>x {part.quantity ?? part.qty ?? 1}</Text>
                                </View>
                            )) : <Text style={styles.detailMuted}>Bu servis icin parca kaydi yok.</Text>}
                        </View>

                        <View style={styles.detailCard}>
                            <Text style={styles.detailSectionTitle}>Servis kanitlari</Text>
                            <View style={styles.detailEvidenceActions}>
                                <TouchableOpacity onPress={() => captureEvidence('before')} style={styles.detailActionButton}><CameraIcon size={16} color="#dbeafe" /><Text style={styles.detailActionText}>Oncesi fotograf</Text></TouchableOpacity>
                                <TouchableOpacity onPress={() => captureEvidence('after')} style={styles.detailActionButton}><CameraIcon size={16} color="#dbeafe" /><Text style={styles.detailActionText}>Sonrasi fotograf</Text></TouchableOpacity>
                            </View>
                            <TouchableOpacity onPress={() => setSignatureOpen(true)} style={[styles.detailActionButton, { alignSelf: 'flex-start', marginTop: 8 }]}>
                                <Text style={styles.detailActionText}>Müşteri imzasi al</Text>
                            </TouchableOpacity>
                            {localEvidence.map((item, index) => item.uri ? (
                                <View key={`local-${index}`} style={styles.evidenceRow}>
                                    <Image source={{ uri: item.uri }} style={styles.evidenceImage} />
                                    <Text style={styles.detailText}>{item.evidence_type === 'before' ? '\u00d6ncesi' : item.evidence_type === 'after' ? 'Sonras\u0131' : 'Imza'} - bekleyen yukleme</Text>
                                </View>
                            ) : null)}
                            {serviceEvidence.map((item) => (
                                <View key={`remote-${item.id}`} style={styles.evidenceRow}>
                                    <Image
                                        source={{ uri: `${String(client.defaults.baseURL || '').replace(/\/$/, '')}/mobile/service/evidence?id=${item.id}`, headers: evidenceToken ? { Authorization: `Bearer ${evidenceToken}` } : {} }}
                                        style={styles.evidenceImage}
                                    />
                                    <Text style={styles.detailText}>{item.evidence_type === 'before' ? '\u00d6ncesi' : item.evidence_type === 'after' ? 'Sonras\u0131' : 'M\u00fc\u015fteri imzas\u0131'} - {formatDate(item.created_at)}</Text>
                                </View>
                            ))}
                            {!localEvidence.length && !serviceEvidence.length ? <Text style={styles.detailMuted}>Bu kayda henuz fotograf veya imza eklenmedi.</Text> : null}
                        </View>
                    </ScrollView>
                    <View style={styles.detailFooter}>
                        <TouchableOpacity disabled={serviceSaving} onPress={saveServiceChanges} style={[styles.detailSaveButton, serviceSaving && { opacity: 0.65 }]}>
                            {serviceSaving ? <ActivityIndicator color="#fff" /> : <Text style={styles.detailSaveText}>Servis kaydini kaydet</Text>}
                        </TouchableOpacity>
                    </View>
                </SafeAreaView>
            </Modal>
            <Modal visible={signatureOpen} animationType="slide" onRequestClose={() => setSignatureOpen(false)}>
                <SafeAreaView style={{ flex: 1, backgroundColor: '#f8fafc' }}>
                    <View style={{ padding: 16, flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }}>
                        <Text style={{ color: '#0f172a', fontSize: 18, fontWeight: '800' }}>Müşteri imzasi</Text>
                        <TouchableOpacity onPress={() => setSignatureOpen(false)}><Text style={{ color: '#1d4ed8' }}>Iptal</Text></TouchableOpacity>
                    </View>
                    <Text style={{ color: '#475569', paddingHorizontal: 16 }}>Servis islemi tamamlandigini onaylayarak imzalayin.</Text>
                    <View style={{ flex: 1, margin: 12, borderRadius: 12, overflow: 'hidden', borderWidth: 1, borderColor: '#cbd5e1' }}>
                        <SignatureCanvas
                            ref={signatureRef}
                            onOK={saveSignature}
                            onEmpty={() => Alert.alert('\u0130mza gerekli', 'Kaydetmeden \u00f6nce imza alan\u0131n\u0131 doldurun.')}
                            descriptionText="Imza"
                            clearText="Temizle"
                            confirmText="Imzayi kaydet"
                            imageType="image/png"
                            webStyle=".m-signature-pad--footer { display:flex; justify-content:space-around; } .m-signature-pad { box-shadow:none; border:0; } body,html { width:100%; height:100%; }"
                        />
                    </View>
                </SafeAreaView>
            </Modal>
            <Modal
                visible={menuOpen}
                transparent
                animationType="slide"
                onRequestClose={() => setMenuOpen(false)}
            >
                <View style={styles.menuModal}>
                    <TouchableOpacity
                        activeOpacity={1}
                        style={styles.menuBackdrop}
                        onPress={() => setMenuOpen(false)}
                    />
                    <View style={styles.menuDrawer}>
                        <View style={styles.menuDrawerHeader}>
                            <View>
                                <Text style={styles.menuDrawerTitle}>H\u0131zl\u0131 Gezinti</Text>
                                <Text style={styles.menuDrawerHint}>Mod\u00fcl ve durum kuyruklar\u0131</Text>
                            </View>
                            <TouchableOpacity onPress={() => setMenuOpen(false)} style={styles.menuCloseButton}>
                                <X size={19} color="#dbeafe" />
                            </TouchableOpacity>
                        </View>
                        <View style={styles.menuSearchBox}>
                            <Search size={16} color="#64748b" />
                            <TextInput
                                value={menuQuery}
                                onChangeText={setMenuQuery}
                                placeholder="Men\u00fcde ara..."
                                placeholderTextColor="#64748b"
                                style={styles.menuSearchInput}
                                autoFocus
                            />
                        </View>
                        <ScrollView contentContainerStyle={styles.menuScrollContent} keyboardShouldPersistTaps="handled">
                            {filteredMenuGroups.map((group) => {
                                const GroupIcon = group.icon;
                                return (
                                    <View key={group.key} style={styles.menuGroup}>
                                        <View style={styles.menuGroupTitleRow}>
                                            <GroupIcon size={14} color="#93c5fd" />
                                            <Text style={styles.menuGroupTitle}>{group.title}</Text>
                                        </View>
                                        {group.items.map((item) => (
                                            <TouchableOpacity
                                                key={item.key}
                                                onPress={() => handleMenuAction(item.key)}
                                                style={[styles.menuItem, filter === item.key && styles.menuItemActive]}
                                            >
                                                <View style={[styles.menuItemDot, item.color ? { backgroundColor: item.color } : null]} />
                                                <View style={styles.menuItemBody}>
                                                    <Text style={styles.menuItemTitle}>{item.title}</Text>
                                                    <Text style={styles.menuItemDescription}>{item.description}</Text>
                                                </View>
                                                {filter === item.key ? <Text style={styles.menuItemSelected}>Aktif</Text> : null}
                                            </TouchableOpacity>
                                        ))}
                                    </View>
                                );
                            })}
                            {!filteredMenuGroups.length ? <Text style={styles.menuEmpty}>E\u015fle\u015fen men\u00fc bulunamad\u0131.</Text> : null}
                        </ScrollView>
                    </View>
                </View>
            </Modal>
            <Modal visible={scannerOpen} animationType="slide" onRequestClose={() => setScannerOpen(false)}>
                <SafeAreaView style={{ flex: 1, backgroundColor: '#071525' }}>
                    <View style={{ padding: 16, flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }}>
                        <Text style={{ color: '#f8fafc', fontSize: 18, fontWeight: '700' }}>Cihaz kodunu tara</Text>
                        <TouchableOpacity onPress={() => setScannerOpen(false)}><Text style={{ color: '#93c5fd' }}>Kapat</Text></TouchableOpacity>
                    </View>
                    {cameraPermission?.granted ? (
                        <Camera
                            style={{ flex: 1, margin: 16, borderRadius: 16, overflow: 'hidden' }}
                            type={Camera.Constants.Type.back}
                            barCodeScannerSettings={{ barCodeTypes: [BarCodeScanner.Constants.BarCodeType.qr, BarCodeScanner.Constants.BarCodeType.code128, BarCodeScanner.Constants.BarCodeType.ean13, BarCodeScanner.Constants.BarCodeType.code39] }}
                            onBarCodeScanned={({ data }) => {
                                setQuery(String(data || '').trim());
                                setPage(1);
                                setScannerOpen(false);
                            }}
                        />
                    ) : <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center', padding: 24 }}>
                        <Text style={{ color: '#cbd5e1', textAlign: 'center', marginBottom: 16 }}>Barkod ve QR kod taramak icin kamera izni gereklidir.</Text>
                        <TouchableOpacity onPress={async () => setCameraPermission(await Camera.requestCameraPermissionsAsync())} style={styles.refreshButton}><Text style={{ color: '#dbeafe' }}>Kamera izni ver</Text></TouchableOpacity>
                    </View>}
                </SafeAreaView>
            </Modal>
            <View style={styles.header}>
                <View style={styles.headerIdentity}>
                    <TouchableOpacity onPress={() => setMenuOpen(true)} style={[styles.headerButton, styles.menuToggleButton]}>
                        <Menu size={20} color="#dbeafe" />
                    </TouchableOpacity>
                    <View style={styles.brandMark}><Text style={styles.brandText}>AP</Text></View>
                    <View>
                        <Text style={styles.headerTitle}>AYEC Pro</Text>
                        <Text style={styles.headerSubTitle}>{automotive ? 'Otomotiv Genel Bak\u0131\u015f' : 'Servis Genel Bak\u0131\u015f'}</Text>
                    </View>
                </View>
                <View style={styles.headerActions}>
                    <TouchableOpacity onPress={() => setFieldPanelOpen((value) => !value)} style={styles.headerButton}>
                        <Settings size={19} color="#dbeafe" />
                    </TouchableOpacity>
                    <TouchableOpacity onPress={handleLogout} style={styles.headerButton}>
                        <LogOut size={19} color="#fecaca" />
                    </TouchableOpacity>
                </View>
            </View>

            <ScrollView
                contentContainerStyle={styles.scrollContent}
                refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); loadData(true); }} tintColor="#3b82f6" />}
            >
                {fieldPanelOpen && (
                    <View style={[styles.panel, isTracking && styles.panelActive]}>
                        <View style={styles.panelHeader}>
                            <Navigation size={22} color={isTracking ? '#3b82f6' : '#94a3b8'} />
                            <View style={styles.panelTitleArea}>
                                <Text style={styles.panelTitle}>Saha Takibi</Text>
                                <Text style={styles.panelSubTitle}>{isTracking ? 'Konum merkeze g\u00f6nderiliyor' : 'Takip kapal\u0131'}</Text>
                            </View>
                            <Switch value={isTracking} onValueChange={toggleTracking} trackColor={{ false: '#334155', true: '#1d4ed8' }} />
                        </View>
                        {lastLocation && <View style={styles.locationRow}><MapPin size={14} color="#94a3b8" /><Text style={styles.locationText}>{lastLocation.latitude.toFixed(5)}, {lastLocation.longitude.toFixed(5)}</Text></View>}
                        <View style={styles.stockSummary}>
                            <View>
                                <Text style={styles.stockSummaryTitle}>Ara\u00e7 Stogu</Text>
                                <Text style={styles.stockSummaryHint}>{vehicleLocations.length} aktif arac konumu</Text>
                            </View>
                            <Text style={styles.stockSummaryValue}>{formatQuantity(vehicleQuantity)} adet</Text>
                        </View>
                        <View style={styles.personnelStatusRow}>
                            {[tr.ready, tr.onDuty, tr.busy, tr.break].map((item) => (
                                <TouchableOpacity key={item} onPress={() => updateStatus(item)} style={[styles.personnelStatusButton, personnelStatus === item && styles.personnelStatusButtonActive]}>
                                    <Text style={styles.personnelStatusText}>{item}</Text>
                                </TouchableOpacity>
                            ))}
                        </View>
                    </View>
                )}

                <View style={styles.titleRow}>
                    <View>
                        <Text style={styles.pageTitle}>Genel Bak\u0131\u015f</Text>
                        <Text style={styles.pageDescription}>{devices.length} aktif kay\u0131t canl\u0131 veriden y\u00fcklendi.</Text>
                    </View>
                    <TouchableOpacity onPress={() => loadData(true)} style={styles.refreshButton}>
                        <RefreshCw size={18} color="#60a5fa" />
                    </TouchableOpacity>
                </View>

                {error ? <View style={styles.errorBox}><AlertCircle size={18} color="#f87171" /><Text style={styles.errorText}>{error}</Text></View> : null}

                {showAppointments && (
                    <View style={styles.appointmentPanel}>
                        <View style={styles.listHeader}>
                            <View>
                                <Text style={styles.listTitle}>Randevu Merkezi</Text>
                                <Text style={styles.appointmentHint}>Montaj oncesi malzeme ve hizmet kontrolu</Text>
                            </View>
                            <Text style={styles.listCount}>{appointmentRows.length} randevu</Text>
                        </View>
                        {appointmentRows.length ? appointmentRows.map((appointment) => (
                            <View key={String(appointment.id)} style={styles.appointmentCard}>
                                <View style={styles.serviceCardTop}>
                                    <Text numberOfLines={1} style={styles.trackingNo}>{appointment.title || appointment.type || 'Randevu'}</Text>
                                    <Text style={styles.statusBadge}>{appointment.status || 'Planlandi'}</Text>
                                </View>
                                <Text style={styles.customerName}>{appointment.customer_name || appointment.customer || '-'}</Text>
                                <Text style={styles.deviceName}>{[formatDate(appointment.date), appointment.time].filter(Boolean).join('  /  ')}</Text>
                                <View style={styles.planDivider} />
                                <Text style={styles.planTitle}>Yukleme kontrol listesi</Text>
                                {appointment.planItems.length ? appointment.planItems.slice(0, 5).map((item, index) => (
                                    <Text key={`${appointment.id}-${index}`} numberOfLines={1} style={styles.planItem}>
                                        {`${item.name || item.description || item.service || 'Kalem'} x ${formatQuantity(item.planned_qty || item.quantity || item.qty || 1)}`}
                                    </Text>
                                )) : <Text style={styles.planItem}>Planlanmis kalem yok</Text>}
                            </View>
                        )) : <View style={styles.appointmentEmpty}><Text style={styles.emptyText}>Planlanmis randevu bulunamadi.</Text></View>}
                    </View>
                )}

                <View style={styles.metricGrid}>
                    {cards.map((card) => {
                        const value = card.value === undefined ? countFor(card.key) : card.value;
                        const percent = card.money ? 0 : (devices.length && typeof value === 'number' ? Math.round((value / devices.length) * 100) : 0);
                        return (
                            <TouchableOpacity key={card.key} onPress={() => setActiveFilter(card.key)} style={[styles.metricCard, { borderLeftColor: card.color }, filter === card.key && styles.metricCardActive]}>
                                <View style={[styles.metricIcon, { backgroundColor: `${card.color}22` }]}><Text style={[styles.metricIconText, { color: card.color }]}>{card.icon}</Text></View>
                                <View style={styles.metricBody}>
                                    <Text numberOfLines={2} style={styles.metricTitle}>{card.title}</Text>
                                    <Text style={styles.metricValue}>{card.money ? formatMoney(value) : `${value} ADET`}</Text>
                                    <Text style={[styles.metricPercent, { color: card.color }]}>{card.money ? 'TRY' : `${percent}%`}</Text>
                                </View>
                            </TouchableOpacity>
                        );
                    })}
                </View>

                <View style={styles.searchBox}>
                    <Search size={17} color="#64748b" />
                    <TextInput
                        value={query}
                        onChangeText={(value) => { setQuery(value); setPage(1); }}
                        placeholder={automotive ? 'Plaka, m\u00fc\u015fteri veya ara\u00e7 ara...' : 'Takip no, m\u00fc\u015fteri veya cihaz ara...'}
                        placeholderTextColor="#64748b"
                        style={styles.searchInput}
                    />
                    <TouchableOpacity onPress={async () => {
                        if (!cameraPermission?.granted) {
                            const permission = await Camera.requestCameraPermissionsAsync();
                            setCameraPermission(permission);
                            if (!permission.granted) {
                                setScannerOpen(true);
                                return;
                            }
                        }
                        setScannerOpen(true);
                    }} style={{ padding: 8 }} accessibilityLabel="Barkod tara">
                        <CameraIcon size={18} color="#60a5fa" />
                    </TouchableOpacity>
                </View>

                <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.filterRow}>
                    <TouchableOpacity onPress={() => setActiveFilter('all')} style={[styles.filterChip, filter === 'all' && styles.filterChipActive]}><Text style={styles.filterChipText}>T\u00fcm\u00fc</Text></TouchableOpacity>
                    {cards.slice(0, 7).map((card) => (
                        <TouchableOpacity key={card.key} onPress={() => setActiveFilter(card.key)} style={[styles.filterChip, filter === card.key && styles.filterChipActive]}>
                            <Text style={styles.filterChipText}>{card.title}</Text>
                        </TouchableOpacity>
                    ))}
                </ScrollView>

                <View style={styles.listHeader}>
                    <Text style={styles.listTitle}>{automotive ? 'Ara\u00e7 Servis Listesi' : 'Servis Listesi'}</Text>
                    <Text style={styles.listCount}>{filteredDevices.length} kay\u0131t</Text>
                </View>

                {pageRows.length ? pageRows.map((device) => (
                    <TouchableOpacity key={String(device.id || device.tracking_no)} onPress={() => openService(device)} style={styles.serviceCard}>
                        <View style={styles.serviceCardTop}>
                            <Text numberOfLines={1} style={styles.trackingNo}>{device.tracking_no || '-'}</Text>
                            <Text style={styles.statusBadge}>{automotive ? displayServiceStatus(device) : (device.status || 'Bekliyor')}</Text>
                        </View>
                        <Text numberOfLines={1} style={styles.customerName}>{device.customer_name || '-'}</Text>
                        <Text numberOfLines={2} style={styles.deviceName}>{[device.device_type, device.brand, device.model].filter(Boolean).join(' / ') || '-'}</Text>
                        <View style={styles.serviceMeta}>
                            <Text style={styles.serviceMetaText}>{automotive ? displayDeliveryState(device) : formatDate(device.entry_date)}</Text>
                            <Text style={styles.serviceMetaText}>{formatMoney(moneyNumber(device.price) + moneyNumber(device.labor_cost))}</Text>
                        </View>
                        {automotive && <Text numberOfLines={1} style={styles.serviceSource}>{displayServiceSource(device)}</Text>}
                    </TouchableOpacity>
                )) : (
                    <View style={styles.emptyState}>
                        <Package size={34} color="#64748b" />
                        <Text style={styles.emptyTitle}>Kay\u0131t bulunamad\u0131</Text>
                        <Text style={styles.emptyText}>Aramay\u0131 veya durum filtresini temizleyin.</Text>
                    </View>
                )}
            </ScrollView>

            <View style={styles.bottomNav}>
                <TouchableOpacity disabled={safePage <= 1} onPress={() => setPage((value) => Math.max(1, value - 1))} style={[styles.bottomButton, safePage <= 1 && styles.bottomButtonDisabled]}>
                    <ChevronLeft size={17} color="#cbd5e1" /><Text style={styles.bottomButtonText}>Geri</Text>
                </TouchableOpacity>
                <TouchableOpacity onPress={() => setActiveFilter('all')} style={styles.bottomButton}>
                    <Search size={17} color="#cbd5e1" /><Text style={styles.bottomButtonText}>Ara</Text>
                </TouchableOpacity>
                <TouchableOpacity onPress={() => setMenuOpen(true)} style={[styles.bottomButton, styles.bottomPrimary]}>
                    <Menu size={17} color="#111827" /><Text style={styles.bottomPrimaryText}>\u0130\u015flemler</Text>
                </TouchableOpacity>
                <View style={styles.pageBadge}><Text style={styles.pageBadgeText}>{safePage}/{pageCount}</Text></View>
                <TouchableOpacity disabled={safePage >= pageCount} onPress={() => setPage((value) => Math.min(pageCount, value + 1))} style={[styles.bottomButton, safePage >= pageCount && styles.bottomButtonDisabled]}>
                    <Text style={styles.bottomButtonText}>\u0130leri</Text><ChevronRight size={17} color="#cbd5e1" />
                </TouchableOpacity>
            </View>
        </SafeAreaView>
    );
}

const styles = StyleSheet.create({
    container: { flex: 1, backgroundColor: '#06111f' },
    center: { flex: 1, alignItems: 'center', justifyContent: 'center', backgroundColor: '#06111f' },
    header: { minHeight: 68, paddingHorizontal: 16, paddingVertical: 10, backgroundColor: '#071525', borderBottomWidth: 1, borderBottomColor: '#1e3a56', flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
    headerIdentity: { flexDirection: 'row', alignItems: 'center' },
    menuToggleButton: { marginRight: 9 },
    brandMark: { width: 38, height: 38, borderRadius: 12, backgroundColor: '#2563eb', alignItems: 'center', justifyContent: 'center', marginRight: 10 },
    brandText: { color: '#fff', fontWeight: '900', fontSize: 13 },
    headerTitle: { color: '#fff', fontSize: 18, fontWeight: '800' },
    headerSubTitle: { color: '#93c5fd', fontSize: 11, marginTop: 2 },
    headerActions: { flexDirection: 'row', gap: 7 },
    headerButton: { width: 38, height: 38, borderRadius: 19, backgroundColor: '#10263c', borderWidth: 1, borderColor: '#244766', alignItems: 'center', justifyContent: 'center' },
    portalContainer: { flex: 1, backgroundColor: '#ffffff' },
    portalLoading: { position: 'absolute', zIndex: 5, alignSelf: 'center', top: 18, flexDirection: 'row', gap: 9, alignItems: 'center', padding: 12, borderRadius: 14, backgroundColor: '#071525' },
    portalError: { flex: 1, alignItems: 'center', justifyContent: 'center', gap: 10, padding: 28 },
    moduleHeader: { minHeight: 84, paddingHorizontal: 18, paddingVertical: 14, flexDirection: 'row', alignItems: 'center', borderBottomWidth: 1, borderBottomColor: '#1e3a56', backgroundColor: '#071525' },
    moduleEyebrow: { color: '#60a5fa', fontSize: 9, fontWeight: '900', letterSpacing: 1.2 },
    moduleTitle: { color: '#f8fafc', fontSize: 20, fontWeight: '900', marginTop: 5 },
    moduleContent: { padding: 16, paddingBottom: 32 },
    moduleSummary: { minHeight: 82, padding: 16, borderRadius: 16, backgroundColor: '#0b1f33', borderWidth: 1, borderColor: '#244766', flexDirection: 'row', alignItems: 'center', gap: 13, marginBottom: 12 },
    moduleSummaryValue: { color: '#f8fafc', fontSize: 20, fontWeight: '900' },
    moduleSummaryLabel: { color: '#94a3b8', fontSize: 11, marginTop: 3 },
    moduleRow: { minHeight: 66, paddingHorizontal: 12, paddingVertical: 10, marginBottom: 7, borderRadius: 12, backgroundColor: '#0b1f33', borderWidth: 1, borderColor: '#1e3a56', flexDirection: 'row', alignItems: 'center', gap: 10 },
    moduleAvatar: { width: 36, height: 36, borderRadius: 12, backgroundColor: '#123d3d', alignItems: 'center', justifyContent: 'center' },
    moduleAvatarText: { color: '#6ee7b7', fontSize: 15, fontWeight: '900' },
    moduleRowTitle: { color: '#e2e8f0', fontSize: 13, fontWeight: '800' },
    moduleRowMeta: { color: '#94a3b8', fontSize: 10, marginTop: 4, lineHeight: 15 },
    moduleRowAmount: { color: '#bae6fd', fontSize: 11, fontWeight: '800' },
    moduleChevron: { color: '#64748b', fontSize: 22 },
    moduleEmpty: { color: '#94a3b8', fontSize: 12, textAlign: 'center', paddingVertical: 30 },
    moduleMetricRow: { minHeight: 52, paddingHorizontal: 14, marginBottom: 7, borderRadius: 12, backgroundColor: '#0b1f33', flexDirection: 'row', alignItems: 'center', gap: 10 },
    moduleMetricDot: { width: 8, height: 8, borderRadius: 4 },
    moduleMetricValue: { color: '#f8fafc', marginLeft: 'auto', fontSize: 15, fontWeight: '900' },
    moduleFootnote: { marginTop: 12, padding: 13, borderRadius: 12, backgroundColor: '#0b1f33' },
    moduleFootnoteText: { color: '#94a3b8', fontSize: 11, lineHeight: 17, textAlign: 'center' },
    moduleInfoCard: { alignItems: 'center', padding: 24, gap: 12, borderRadius: 18, backgroundColor: '#0b1f33', borderWidth: 1, borderColor: '#244766' },
    modulePrimaryButton: { alignSelf: 'stretch', alignItems: 'center', padding: 14, borderRadius: 12, backgroundColor: '#2563eb', marginTop: 6 },
    modulePrimaryText: { color: '#ffffff', fontWeight: '800', fontSize: 12 },
    menuModal: { flex: 1, flexDirection: 'row', backgroundColor: 'rgba(2, 8, 18, 0.48)' },
    menuBackdrop: { flex: 1 },
    menuDrawer: { width: '84%', maxWidth: 340, height: '100%', backgroundColor: '#071525', borderLeftWidth: 1, borderLeftColor: '#244766', paddingTop: 14 },
    menuDrawerHeader: { minHeight: 58, paddingHorizontal: 15, paddingBottom: 12, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', borderBottomWidth: 1, borderBottomColor: '#1e3a56' },
    menuDrawerTitle: { color: '#f8fafc', fontSize: 17, fontWeight: '900' },
    menuDrawerHint: { color: '#94a3b8', fontSize: 10, marginTop: 3 },
    menuCloseButton: { width: 36, height: 36, borderRadius: 18, backgroundColor: '#10263c', borderWidth: 1, borderColor: '#244766', alignItems: 'center', justifyContent: 'center' },
    menuSearchBox: { height: 42, marginHorizontal: 14, marginVertical: 12, borderWidth: 1, borderColor: '#244766', borderRadius: 10, backgroundColor: '#0b1f33', flexDirection: 'row', alignItems: 'center', paddingHorizontal: 10 },
    menuSearchInput: { flex: 1, color: '#f8fafc', fontSize: 12, marginLeft: 7 },
    menuScrollContent: { paddingHorizontal: 12, paddingBottom: 28 },
    menuGroup: { marginBottom: 14 },
    menuGroupTitleRow: { flexDirection: 'row', alignItems: 'center', gap: 7, paddingHorizontal: 5, paddingVertical: 7 },
    menuGroupTitle: { color: '#93c5fd', fontSize: 10, fontWeight: '900', letterSpacing: 0.7, textTransform: 'uppercase' },
    menuItem: { minHeight: 55, backgroundColor: '#0b1f33', borderWidth: 1, borderColor: '#1e3a56', borderRadius: 11, paddingHorizontal: 10, marginBottom: 6, flexDirection: 'row', alignItems: 'center' },
    menuItemActive: { backgroundColor: '#132d47', borderColor: '#3b82f6' },
    menuItemDot: { width: 9, height: 9, borderRadius: 5, backgroundColor: '#60a5fa', marginRight: 10 },
    menuItemBody: { flex: 1, minWidth: 0 },
    menuItemTitle: { color: '#e2e8f0', fontSize: 12, fontWeight: '800' },
    menuItemDescription: { color: '#94a3b8', fontSize: 10, marginTop: 3 },
    menuItemSelected: { color: '#86efac', fontSize: 9, fontWeight: '900' },
    menuEmpty: { color: '#94a3b8', fontSize: 12, textAlign: 'center', paddingVertical: 30 },
    detailCard: { backgroundColor: '#0b1f33', borderWidth: 1, borderColor: '#244766', borderRadius: 14, padding: 13, marginBottom: 12 },
    detailSectionRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
    detailSectionTitle: { color: '#bfdbfe', fontSize: 13, fontWeight: '900', marginBottom: 9 },
    detailPrimary: { color: '#f8fafc', fontSize: 15, fontWeight: '800', marginBottom: 4 },
    detailText: { color: '#cbd5e1', fontSize: 11, lineHeight: 17, flexShrink: 1 },
    detailMuted: { color: '#94a3b8', fontSize: 11, lineHeight: 17 },
    detailCount: { color: '#93c5fd', fontSize: 11, fontWeight: '800' },
    detailLink: { flexDirection: 'row', alignItems: 'center', gap: 7, marginTop: 9 },
    detailLinkText: { color: '#60a5fa', fontSize: 11, flex: 1 },
    detailStatusRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 6, marginBottom: 11 },
    detailStatusChip: { borderWidth: 1, borderColor: '#244766', backgroundColor: '#071525', borderRadius: 999, paddingHorizontal: 10, paddingVertical: 7 },
    detailStatusChipActive: { borderColor: '#60a5fa', backgroundColor: '#1d4ed8' },
    detailStatusText: { color: '#dbeafe', fontSize: 10, fontWeight: '800' },
    detailFieldLabel: { color: '#93c5fd', fontSize: 10, fontWeight: '800', marginBottom: 5, marginTop: 7 },
    serviceInput: { minHeight: 80, color: '#f8fafc', fontSize: 12, textAlignVertical: 'top', backgroundColor: '#071525', borderWidth: 1, borderColor: '#244766', borderRadius: 10, padding: 10 },
    partLine: { flexDirection: 'row', justifyContent: 'space-between', gap: 10, paddingVertical: 5, borderBottomWidth: 1, borderBottomColor: '#1e3a56' },
    detailEvidenceActions: { flexDirection: 'row', flexWrap: 'wrap', gap: 7 },
    detailActionButton: { minHeight: 38, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 7, borderRadius: 10, borderWidth: 1, borderColor: '#3b82f6', backgroundColor: '#102c48', paddingHorizontal: 10 },
    detailActionText: { color: '#dbeafe', fontSize: 10, fontWeight: '800' },
    evidenceRow: { flexDirection: 'row', alignItems: 'center', gap: 10, marginTop: 10, paddingTop: 9, borderTopWidth: 1, borderTopColor: '#1e3a56' },
    evidenceImage: { width: 58, height: 58, borderRadius: 9, backgroundColor: '#071525' },
    detailFooter: { padding: 12, borderTopWidth: 1, borderTopColor: '#244766', backgroundColor: '#071525' },
    detailSaveButton: { minHeight: 46, borderRadius: 12, backgroundColor: '#2563eb', alignItems: 'center', justifyContent: 'center' },
    detailSaveText: { color: '#fff', fontSize: 13, fontWeight: '900' },
    scrollContent: { padding: 12, paddingBottom: 92 },
    panel: { backgroundColor: '#0b1f33', borderWidth: 1, borderColor: '#244766', borderRadius: 14, padding: 13, marginBottom: 12 },
    panelActive: { borderColor: '#3b82f6' },
    panelHeader: { flexDirection: 'row', alignItems: 'center' },
    panelTitleArea: { flex: 1, marginLeft: 10 },
    panelTitle: { color: '#f8fafc', fontSize: 15, fontWeight: '800' },
    panelSubTitle: { color: '#94a3b8', fontSize: 11, marginTop: 2 },
    locationRow: { flexDirection: 'row', alignItems: 'center', marginTop: 10, paddingTop: 10, borderTopWidth: 1, borderTopColor: '#1e3a56' },
    locationText: { color: '#94a3b8', fontSize: 11, marginLeft: 5 },
    stockSummary: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginTop: 10, paddingTop: 10, borderTopWidth: 1, borderTopColor: '#1e3a56' },
    stockSummaryTitle: { color: '#dbeafe', fontSize: 11, fontWeight: '800' },
    stockSummaryHint: { color: '#94a3b8', fontSize: 10, marginTop: 2 },
    stockSummaryValue: { color: '#86efac', fontSize: 14, fontWeight: '900' },
    personnelStatusRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 6, marginTop: 10 },
    personnelStatusButton: { borderWidth: 1, borderColor: '#244766', borderRadius: 999, paddingHorizontal: 10, paddingVertical: 7 },
    personnelStatusButtonActive: { backgroundColor: '#1d4ed8', borderColor: '#60a5fa' },
    personnelStatusText: { color: '#dbeafe', fontSize: 11, fontWeight: '700' },
    titleRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginBottom: 11 },
    pageTitle: { color: '#f8fafc', fontSize: 22, fontWeight: '900' },
    pageDescription: { color: '#94a3b8', fontSize: 11, marginTop: 3 },
    refreshButton: { width: 38, height: 38, borderRadius: 10, borderWidth: 1, borderColor: '#244766', backgroundColor: '#0b1f33', alignItems: 'center', justifyContent: 'center' },
    errorBox: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#3f1720', borderWidth: 1, borderColor: '#7f1d1d', borderRadius: 10, padding: 10, marginBottom: 10 },
    errorText: { color: '#fecaca', fontSize: 12, marginLeft: 7, flex: 1 },
    appointmentPanel: { backgroundColor: '#0b1f33', borderWidth: 1, borderColor: '#244766', borderRadius: 14, padding: 11, marginBottom: 12 },
    appointmentCard: { backgroundColor: '#10263c', borderWidth: 1, borderColor: '#244766', borderRadius: 11, padding: 10, marginTop: 8 },
    appointmentHint: { color: '#94a3b8', fontSize: 10, marginTop: 2 },
    appointmentEmpty: { paddingVertical: 18, alignItems: 'center' },
    planDivider: { height: 1, backgroundColor: '#1e3a56', marginTop: 8, marginBottom: 7 },
    planTitle: { color: '#bfdbfe', fontSize: 10, fontWeight: '800', marginBottom: 4 },
    planItem: { color: '#cbd5e1', fontSize: 11, lineHeight: 17 },
    metricGrid: { flexDirection: 'row', flexWrap: 'wrap', justifyContent: 'space-between', gap: 8 },
    metricCard: { width: '48.8%', minHeight: 88, borderWidth: 1, borderLeftWidth: 4, borderColor: '#244766', borderRadius: 12, backgroundColor: '#0b1f33', padding: 9, flexDirection: 'row', alignItems: 'center' },
    metricCardActive: { backgroundColor: '#132d47', borderColor: '#3b82f6' },
    metricIcon: { width: 32, height: 32, borderRadius: 16, alignItems: 'center', justifyContent: 'center', marginRight: 8 },
    metricIconText: { fontWeight: '900', fontSize: 13 },
    metricBody: { flex: 1, minWidth: 0 },
    metricTitle: { color: '#bfdbfe', fontSize: 9, fontWeight: '800', lineHeight: 12 },
    metricValue: { color: '#fff', fontSize: 15, fontWeight: '900', marginTop: 3 },
    metricPercent: { fontSize: 10, fontWeight: '800', marginTop: 2 },
    searchBox: { height: 44, borderWidth: 1, borderColor: '#244766', borderRadius: 11, backgroundColor: '#0b1f33', flexDirection: 'row', alignItems: 'center', paddingHorizontal: 12, marginTop: 12 },
    searchInput: { flex: 1, color: '#f8fafc', marginLeft: 8, fontSize: 13 },
    filterRow: { paddingVertical: 10, gap: 7 },
    filterChip: { borderWidth: 1, borderColor: '#244766', borderRadius: 999, backgroundColor: '#0b1f33', paddingHorizontal: 12, paddingVertical: 8 },
    filterChipActive: { backgroundColor: '#2563eb', borderColor: '#60a5fa' },
    filterChipText: { color: '#dbeafe', fontSize: 10, fontWeight: '700' },
    listHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 7 },
    listTitle: { color: '#f8fafc', fontSize: 16, fontWeight: '800' },
    listCount: { color: '#93c5fd', fontSize: 11 },
    serviceCard: { backgroundColor: '#0b1f33', borderWidth: 1, borderColor: '#244766', borderRadius: 12, padding: 11, marginBottom: 8 },
    serviceCardTop: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', gap: 8 },
    trackingNo: { color: '#fff', fontSize: 13, fontWeight: '900', flex: 1 },
    statusBadge: { color: '#bfdbfe', backgroundColor: '#173a5b', borderRadius: 999, paddingHorizontal: 8, paddingVertical: 4, fontSize: 9, fontWeight: '800' },
    customerName: { color: '#e2e8f0', fontSize: 13, fontWeight: '700', marginTop: 7 },
    deviceName: { color: '#94a3b8', fontSize: 11, lineHeight: 15, marginTop: 3 },
    serviceMeta: { flexDirection: 'row', justifyContent: 'space-between', borderTopWidth: 1, borderTopColor: '#1e3a56', paddingTop: 8, marginTop: 8 },
    serviceMetaText: { color: '#93c5fd', fontSize: 10, fontWeight: '700' },
    serviceSource: { color: '#94a3b8', fontSize: 10, fontWeight: '700', marginTop: 7 },
    emptyState: { alignItems: 'center', justifyContent: 'center', minHeight: 180, backgroundColor: '#0b1f33', borderWidth: 1, borderColor: '#244766', borderRadius: 12 },
    emptyTitle: { color: '#f8fafc', fontSize: 16, fontWeight: '800', marginTop: 8 },
    emptyText: { color: '#94a3b8', fontSize: 11, marginTop: 4 },
    bottomNav: { minHeight: 62, paddingHorizontal: 8, paddingVertical: 7, backgroundColor: '#071525', borderTopWidth: 1, borderTopColor: '#244766', flexDirection: 'row', alignItems: 'center', gap: 5 },
    bottomButton: { flex: 1, minHeight: 43, borderRadius: 999, backgroundColor: '#0b1f33', borderWidth: 1, borderColor: '#244766', flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 3, paddingHorizontal: 5 },
    bottomButtonDisabled: { opacity: 0.42 },
    bottomButtonText: { color: '#cbd5e1', fontSize: 10, fontWeight: '700' },
    bottomPrimary: { flex: 1.25, backgroundColor: '#f59e0b', borderColor: '#fbbf24' },
    bottomPrimaryText: { color: '#111827', fontSize: 10, fontWeight: '900' },
    pageBadge: { minWidth: 42, minHeight: 42, borderRadius: 21, backgroundColor: '#10263c', alignItems: 'center', justifyContent: 'center' },
    pageBadgeText: { color: '#fff', fontSize: 10, fontWeight: '900' },
});
