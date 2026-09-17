import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
    ActivityIndicator,
    Alert,
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
import * as Location from 'expo-location';
import {
    AlertCircle,
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
    X,
} from 'lucide-react-native';
import client from '../api/client';

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
    const [showAppointments, setShowAppointments] = useState(false);
    const [summary, setSummary] = useState(null);
    const [loading, setLoading] = useState(true);
    const [refreshing, setRefreshing] = useState(false);
    const [error, setError] = useState('');
    const [query, setQuery] = useState('');
    const [filter, setFilter] = useState('all');
    const [page, setPage] = useState(1);
    const [fieldPanelOpen, setFieldPanelOpen] = useState(false);
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

            const response = await client.get('/desktop/bootstrap');
            const source = response.data || {};
            setDevices(Array.isArray(source.devices) ? source.devices : []);
            setAppointments(Array.isArray(source.appointments) ? source.appointments : []);
            setOffers(Array.isArray(source.offers) ? source.offers : []);
            setStockLocations(Array.isArray(source.stock_locations) ? source.stock_locations : []);
            setSummary({
                total_receivables: 0,
                counts: source.counts || {},
                stock_location_summary: source.stock_location_summary || {},
            });
            setPersonnelStatus(tr.ready);
        } catch (loadError) {
            console.error('Dashboard load failed', loadError);
            setError(tr.refreshError);
        } finally {
            setLoading(false);
            setRefreshing(false);
        }
    }, []);

    useEffect(() => {
        loadData();
        return stopTracking;
    }, [loadData, stopTracking]);

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
            Alert.alert(tr.error, tr.statusError);
        }
    }, []);

    const handleLogout = useCallback(async () => {
        stopTracking();
        await AsyncStorage.multiRemove(['userToken', 'userData']);
        if (onLogout) onLogout();
    }, [onLogout, stopTracking]);

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
            key: 'overview',
            title: 'Genel Bak\u0131\u015f',
            icon: LayoutDashboard,
            items: [
                { key: 'all', title: 'T\u00fcm Kay\u0131tlar', description: 'Servis listesi ve durum \u00f6zeti' },
            ],
        },
        {
            key: 'services',
            title: 'Servis \u0130\u015flemleri',
            icon: ClipboardList,
            items: cards.filter((card) => !card.money).map((card) => ({
                key: card.key,
                title: card.title,
                description: `${countFor(card.key)} kay\u0131t`,
                color: card.color,
            })),
        },
        {
            key: 'quick',
            title: 'H\u0131zl\u0131 \u0130\u015flemler',
            icon: CalendarDays,
            items: [
                { key: 'appointments', title: 'Randevular', description: `${appointmentRows.length} plan` },
                { key: 'field', title: 'Saha Takibi', description: isTracking ? 'Takip a\u00e7\u0131k' : 'Takip kapal\u0131' },
                { key: 'refresh', title: 'Verileri Yenile', description: 'Canl\u0131 veriyi tekrar y\u00fckle' },
            ],
        },
    ], [appointmentRows.length, cards, countFor, isTracking]);

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
        } else if (key === 'field') {
            setFieldPanelOpen(true);
        } else if (key === 'refresh') {
            loadData(true);
        } else {
            setActiveFilter(key);
        }
        setMenuOpen(false);
        setMenuQuery('');
    }, [loadData, setActiveFilter]);

    if (loading) {
        return <View style={styles.center}><ActivityIndicator size="large" color="#3b82f6" /></View>;
    }

    return (
        <SafeAreaView style={styles.container}>
            <StatusBar barStyle="light-content" backgroundColor="#071525" />
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
                    <TouchableOpacity key={String(device.id || device.tracking_no)} style={styles.serviceCard}>
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
