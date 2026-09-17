import React, { useState } from 'react';
import {
    View, Text, TextInput, TouchableOpacity, StyleSheet,
    KeyboardAvoidingView, Platform, Image, Alert, ActivityIndicator
} from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import client from '../api/client';
import { User, Lock, ChevronRight } from 'lucide-react-native';

export default function LoginScreen({ route, navigation }) {
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [invitationCode, setInvitationCode] = useState('');
    const [licenseRequired, setLicenseRequired] = useState(false);
    const [loading, setLoading] = useState(false);
    const { onLogin } = route.params;

    const handleLogin = async () => {
        if (!username || !password) {
            Alert.alert('Hata', 'Lütfen tüm alanları doldurun.');
            return;
        }

        if (licenseRequired && !invitationCode.trim()) {
            Alert.alert('Davet kodu gerekli', 'Devam etmek icin yonetici tarafindan verilen davet kodunu girin.');
            return;
        }

        setLoading(true);
        try {
            if (licenseRequired) {
                await client.post('/license/activate', {
                    identifier: username,
                    password,
                    invitation_code: invitationCode,
                });
            }
            const response = await client.post('/auth/login', { identifier: username, password, remember: true });
            const token = response.data.access_token || response.data.token;
            const { user } = response.data;

            if (!token || !user) throw new Error('Invalid login response');

            if (user.type !== 'personnel' && user.role !== 'Admin') {
                // Allow Admin login for testing too
            }

            await AsyncStorage.setItem('userToken', token);
            await AsyncStorage.setItem('userData', JSON.stringify(user));

            onLogin(token);
        } catch (error) {
            console.error(error);
            const message = String(error?.response?.data?.error || error?.message || '');
            const status = Number(error?.response?.status || 0);
            if (status === 403 || /deneme|lisans/i.test(message)) {
                setLicenseRequired(true);
                Alert.alert('\u0130zin gerekli', message || 'Davet kodu veya lisans bilgisi gereklidir.');
                return;
            }
            Alert.alert('Giriş Başarısız', 'Geçersiz kullanıcı adı veya şifre.');
        } finally {
            setLoading(false);
        }
    };

    return (
        <KeyboardAvoidingView
            behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
            style={styles.container}
        >
            <View style={styles.topSection}>
                <View style={styles.logoContainer}>
                    {/* Logo placeholder */}
                    <View style={styles.circle}>
                        <Text style={styles.logoText}>PB</Text>
                    </View>
                </View>
                <Text style={styles.welcomeText}>Saha Takip</Text>
                <Text style={styles.subText}>Premium Bulut Teknik Servis</Text>
            </View>

            <View style={styles.formSection}>
                <View style={styles.inputWrapper}>
                    <User size={20} color="#94a3b8" style={styles.inputIcon} />
                    <TextInput
                        style={styles.input}
                        placeholder="Kullanıcı Adı / E-posta"
                        placeholderTextColor="#94a3b8"
                        value={username}
                        onChangeText={setUsername}
                        autoCapitalize="none"
                    />
                </View>

                <View style={styles.inputWrapper}>
                    <Lock size={20} color="#94a3b8" style={styles.inputIcon} />
                    <TextInput
                        style={styles.input}
                        placeholder="Şifre"
                        placeholderTextColor="#94a3b8"
                        secureTextEntry
                        value={password}
                        onChangeText={setPassword}
                    />
                </View>

                {licenseRequired && (
                    <View style={styles.inputWrapper}>
                        <TextInput
                            style={styles.input}
                            placeholder="Davet kodu"
                            placeholderTextColor="#94a3b8"
                            value={invitationCode}
                            onChangeText={setInvitationCode}
                            autoCapitalize="characters"
                            autoCorrect={false}
                        />
                    </View>
                )}

                <TouchableOpacity
                    style={styles.loginButton}
                    onPress={handleLogin}
                    disabled={loading}
                >
                    {loading ? (
                        <ActivityIndicator color="#fff" />
                    ) : (
                        <>
                            <Text style={styles.loginButtonText}>Giriş Yap</Text>
                            <ChevronRight size={20} color="#fff" />
                        </>
                    )}
                </TouchableOpacity>
            </View>

            <Text style={styles.footerText}>© 2026 BulutTech Bilişim</Text>
        </KeyboardAvoidingView>
    );
}

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: '#fff',
        padding: 24,
    },
    topSection: {
        marginTop: 80,
        alignItems: 'center',
        marginBottom: 40,
    },
    logoContainer: {
        marginBottom: 20,
    },
    circle: {
        width: 80,
        height: 80,
        borderRadius: 40,
        backgroundColor: '#3b82f6',
        justifyContent: 'center',
        alignItems: 'center',
        elevation: 4,
        shadowColor: '#3b82f6',
        shadowOffset: { width: 0, height: 4 },
        shadowOpacity: 0.3,
        shadowRadius: 8,
    },
    logoText: {
        color: '#fff',
        fontSize: 32,
        fontWeight: 'bold',
    },
    welcomeText: {
        fontSize: 28,
        fontWeight: 'bold',
        color: '#1e293b',
    },
    subText: {
        fontSize: 16,
        color: '#64748b',
        marginTop: 4,
    },
    formSection: {
        marginTop: 20,
    },
    inputWrapper: {
        flexDirection: 'row',
        alignItems: 'center',
        backgroundColor: '#f8fafc',
        borderWidth: 1,
        borderColor: '#e2e8f0',
        borderRadius: 12,
        marginBottom: 16,
        paddingHorizontal: 16,
        height: 56,
    },
    inputIcon: {
        marginRight: 12,
    },
    input: {
        flex: 1,
        fontSize: 16,
        color: '#1e293b',
    },
    loginButton: {
        backgroundColor: '#3b82f6',
        height: 56,
        borderRadius: 12,
        flexDirection: 'row',
        justifyContent: 'center',
        alignItems: 'center',
        marginTop: 10,
        elevation: 2,
        shadowColor: '#3b82f6',
        shadowOffset: { width: 0, height: 2 },
        shadowOpacity: 0.2,
        shadowRadius: 4,
    },
    loginButtonText: {
        color: '#fff',
        fontSize: 18,
        fontWeight: 'bold',
        marginRight: 8,
    },
    footerText: {
        position: 'absolute',
        bottom: 40,
        alignSelf: 'center',
        color: '#94a3b8',
        fontSize: 12,
    }
});
