# -*- coding: utf-8 -*-

"""
Cloud Backup Manager
AYEC Pro Teknik Servis Yonetim Sistemi

AWS S3, Google Drive ve Dropbox entegrasyonu
"""

import os
import shutil
import logging
from datetime import datetime
from pathlib import Path
import json
import sqlite3
import threading

logger = logging.getLogger('CloudBackup')


def _retry_pause(seconds):
    """Interrupt-friendly retry pause."""
    threading.Event().wait(seconds)

class CloudBackupManager:
    """
    Cloud backup yöneticisi - Çoklu cloud provider desteği
    """
    
    def __init__(self, db_path='ayecpro.db', config_file='cloud_config.json'):
        self.db_path = db_path
        self.config_file = config_file
        self.config = self.load_config()
        
        # Provider'ları başlat
        self.providers = {}
        self._init_providers()
    
    def get_db_setting(self, key, default=None):
        """Database'den ayar oku"""
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            cur.execute("SELECT value FROM settings WHERE key=?", (key,))
            row = cur.fetchone()
            conn.close()
            return row[0] if row else default
        except Exception:
            return default
    
    def checkpoint(self):
        """WAL modundaki veritabanını ana dosyaya işle (Flush)"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            conn.close()
            logger.info("Database checkpoint completed")
        except Exception as e:
            logger.warning(f"Checkpoint failed: {e}")

    def load_config(self):

        """Yapılandırma dosyasını yükle"""
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f:
                return json.load(f)
        else:
            # Varsayılan yapılandırma
            default_config = {
                'aws_s3': {
                    'enabled': False,
                    'bucket_name': 'ayecpro-backups',
                    'region': 'eu-central-1',
                    'access_key': '',
                    'secret_key': ''
                },
                'google_drive': {
                    'enabled': False,
                    'folder_id': '',
                    'credentials_file': 'google_credentials.json'
                },
                'dropbox': {
                    'enabled': False,
                    'access_token': '',
                    'folder_path': '/AYECPro/Backups'
                },
                'remote_server': {
                    'enabled': True,
                    'url': 'http://85.117.239.60:8000/api/backup/upload',
                    'auth_token': ''
                }
            }
            
            # Kaydet
            with open(self.config_file, 'w') as f:
                json.dump(default_config, f, indent=4)
            
            return default_config
    
    def _init_providers(self):
        """Cloud provider'ları başlat"""
        # AWS S3
        if self.config['aws_s3']['enabled']:
            try:
                from .cloud_providers.aws_s3 import S3Provider
                self.providers['s3'] = S3Provider(self.config['aws_s3'])
                logger.info("AWS S3 provider initialized")
            except ImportError:
                logger.warning("AWS S3 provider not available (boto3 not installed)")
            except Exception as e:
                logger.error(f"AWS S3 init error: {e}")
        
        # Google Drive
        if self.config['google_drive']['enabled']:
            try:
                from .cloud_providers.google_drive import GoogleDriveProvider
                self.providers['gdrive'] = GoogleDriveProvider(self.config['google_drive'])
                logger.info("Google Drive provider initialized")
            except ImportError:
                logger.warning("Google Drive provider not available")
            except Exception as e:
                logger.error(f"Google Drive init error: {e}")
        
        # Dropbox
        if self.config['dropbox']['enabled']:
            try:
                from .cloud_providers.dropbox_provider import DropboxProvider
                self.providers['dropbox'] = DropboxProvider(self.config['dropbox'])
                logger.info("Dropbox provider initialized")
            except ImportError:
                logger.warning("Dropbox provider not available")
            except Exception as e:
                logger.error(f"Dropbox init error: {e}")
        
        # Remote Server
        remote_server = (self.config or {}).get('remote_server') or {}
        if remote_server.get('enabled'):
            self.providers['remote'] = RemoteProvider(self.config['remote_server'], parent=self)
            logger.info("Remote Server provider initialized")
    
    def upload_backup(self, backup_file, provider_name=None, customer_name=None):
        """
        Yedek dosyasını cloud'a yükle
        
        Args:
            backup_file: Yedek dosya yolu
            provider_name: Spesifik provider (None ise tümü)
            customer_name: Opsiyonel müşteri adı (Klasörleleme için)
        
        Returns:
            dict: Yükleme sonuçları
        """
        if not os.path.exists(backup_file):
            logger.error(f"Backup file not found: {backup_file}")
            return {'success': False, 'error': 'File not found'}
        
        results = {}
        
        # Spesifik provider
        if provider_name:
            if provider_name in self.providers:
                results[provider_name] = self.providers[provider_name].upload(backup_file, customer_name=customer_name)
            else:
                results[provider_name] = {'success': False, 'error': 'Provider not available'}
        else:
            # Tüm provider'lara yükle
            for name, provider in self.providers.items():
                try:
                    results[name] = provider.upload(backup_file, customer_name=customer_name)
                except Exception as e:
                    results[name] = {'success': False, 'error': str(e)}
        
        return results
    
    def download_backup(self, backup_name, provider_name, destination=None):
        """
        Cloud'dan yedek indir
        
        Args:
            backup_name: Yedek dosya adı
            provider_name: Provider adı
            destination: İndirilecek konum
        
        Returns:
            str: İndirilen dosya yolu
        """
        if provider_name not in self.providers:
            logger.error(f"Provider not available: {provider_name}")
            return None
        
        if destination is None:
            destination = f'downloaded_{backup_name}'
        
        try:
            return self.providers[provider_name].download(backup_name, destination)
        except Exception as e:
            logger.error(f"Download error: {e}")
            return None
    
    def list_backups(self, provider_name):
        """
        Cloud'daki yedekleri listele
        
        Args:
            provider_name: Provider adı
        
        Returns:
            list: Yedek listesi
        """
        if provider_name not in self.providers:
            return []
        
        try:
            return self.providers[provider_name].list_backups()
        except Exception as e:
            logger.error(f"List backups error: {e}")
            return []
    
    def delete_backup(self, backup_name, provider_name):
        """
        Cloud'dan yedek sil
        
        Args:
            backup_name: Yedek dosya adı
            provider_name: Provider adı
        
        Returns:
            bool: Başarılı mı?
        """
        if provider_name not in self.providers:
            return False
        
        try:
            return self.providers[provider_name].delete(backup_name)
        except Exception as e:
            logger.error(f"Delete backup error: {e}")
            return False
    
    def sync_all(self, customer_name=None, provider_name=None):
        """
        Tüm provider'lara veya belirli bir provider'a senkronize yedekleme yap
        
        Returns:
            dict: Senkronizasyon sonuçları
        """
        # Önce lokal yedek al
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Dosya adı formatı: [MüşteriAdi]_Backup_[Tarih].db veya Backup_[Tarih].db
        if customer_name:
            # Geçersiz karakterleri temizle
            safe_name = "".join([c for c in customer_name if c.isalnum() or c in (' ', '_', '-')]).strip().replace(' ', '_')
            filename = f"{safe_name}_{timestamp}.db"
        else:
            filename = f"cloud_sync_{timestamp}.db"
            
        from src.utils.path_helper import PathHelper
        backups_dir = os.path.join(PathHelper.get_app_data_dir(), "backups")
        os.makedirs(backups_dir, exist_ok=True)
        backup_file = os.path.join(backups_dir, filename)
        
        # Database'i işle (WAL -> Main)
        self.checkpoint()
        
        # Database'i kopyala

        try:
            shutil.copy2(self.db_path, backup_file)
            logger.info(f"Local backup created: {backup_file}")
        except Exception as e:
            logger.error(f"Local backup failed: {e}")
            return {'success': False, 'error': str(e)}
        
        # Cloud'a yükle
        results = self.upload_backup(backup_file, provider_name=provider_name, customer_name=customer_name)
        
        # Lokal dosyayı sil (opsiyonel - sunucuya attıktan sonra yerelde kalmasını istiyoruz, silmiyoruz)
        # os.remove(backup_file)
        
        success = any(r.get('success', False) for r in results.values())
        
        # Aggregate errors if failed
        error_msg = None
        if not success:
            errors = []
            for p, res in results.items():
                if not res.get('success'):
                    errors.append(f"{p}: {res.get('error', 'Unknown')}")
            error_msg = "; ".join(errors) if errors else "Unknown backup error"

        return {
            'success': success,
            'error': error_msg,
            'results': results,
            'backup_file': backup_file
        }

# ============================================================================
# CLOUD PROVIDER BASE CLASS
# ============================================================================

class CloudProvider:
    """Base class for cloud providers"""
    
    def __init__(self, config):
        self.config = config
    
    def upload(self, file_path, customer_name=None):
        """Upload file to cloud"""
        raise NotImplementedError
    
    def download(self, file_name, destination):
        """Download file from cloud"""
        raise NotImplementedError
    
    def list_backups(self):
        """List all backups in cloud"""
        raise NotImplementedError
    
    def delete(self, file_name):
        """Delete file from cloud"""
        raise NotImplementedError

# ============================================================================
# AWS S3 PROVIDER (Örnek implementasyon)
# ============================================================================

class S3Provider(CloudProvider):
    """AWS S3 provider"""
    
    def __init__(self, config):
        super().__init__(config)
        
        try:
            import boto3
            self.s3_client = boto3.client(
                's3',
                region_name=config['region'],
                aws_access_key_id=config['access_key'],
                aws_secret_access_key=config['secret_key']
            )
            self.bucket_name = config['bucket_name']
        except ImportError:
            raise ImportError("boto3 not installed. Run: pip install boto3")
    
    def upload(self, file_path, customer_name=None):
        """S3'e yükle"""
        try:
            file_name = os.path.basename(file_path)
            
            target_key = f'backups/{file_name}'
            if customer_name:
                target_key = f'backups/{customer_name}/{file_name}'
            
            self.s3_client.upload_file(
                file_path,
                self.bucket_name,
                target_key
            )
            
            logger.info(f"Uploaded to S3: {file_name}")
            
            return {
                'success': True,
                'provider': 's3',
                'file_name': file_name,
                'url': f's3://{self.bucket_name}/{target_key}'
            }
            
        except Exception as e:
            logger.error(f"S3 upload error: {e}")
            return {'success': False, 'error': str(e)}
    
    def download(self, file_name, destination):
        """S3'ten indir"""
        try:
            self.s3_client.download_file(
                self.bucket_name,
                f'backups/{file_name}',
                destination
            )
            
            logger.info(f"Downloaded from S3: {file_name}")
            return destination
            
        except Exception as e:
            logger.error(f"S3 download error: {e}")
            return None
    
    def list_backups(self):
        """S3'teki yedekleri listele"""
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix='backups/'
            )
            
            backups = []
            for obj in response.get('Contents', []):
                backups.append({
                    'name': obj['Key'].replace('backups/', ''),
                    'size': obj['Size'],
                    'last_modified': obj['LastModified'].isoformat()
                })
            
            return backups
            
        except Exception as e:
            logger.error(f"S3 list error: {e}")
            return []
    
    def delete(self, file_name):
        """S3'ten sil"""
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=f'backups/{file_name}'
            )
            
            logger.info(f"Deleted from S3: {file_name}")
            return True
            
        except Exception as e:
            logger.error(f"S3 delete error: {e}")
            return False

# ============================================================================
# MOCK PROVIDERS (Gerçek implementasyon için placeholder)
# ============================================================================

class GoogleDriveProvider(CloudProvider):
    """Google Drive provider (Mock)"""
    
    def upload(self, file_path, customer_name=None):
        logger.info("Google Drive upload (mock)")
        return {'success': True, 'provider': 'gdrive', 'note': 'Mock implementation'}
    
    def download(self, file_name, destination):
        logger.info("Google Drive download (mock)")
        return destination
    
    def list_backups(self):
        return []
    
    def delete(self, file_name):
        return True

class DropboxProvider(CloudProvider):
    """Dropbox provider (Mock)"""
    
    def upload(self, file_path, customer_name=None):
        logger.info("Dropbox upload (mock)")
        return {'success': True, 'provider': 'dropbox', 'note': 'Mock implementation'}
    
    def download(self, file_name, destination):
        logger.info("Dropbox download (mock)")
        return destination
    
    def list_backups(self):
        return []
    
    def delete(self, file_name):
        return True

class RemoteProvider(CloudProvider):
    """Custom Remote Server provider (REST API)"""
    
    def __init__(self, config, parent=None):
        super().__init__(config)
        self.parent = parent # CloudBackupManager instance

    def upload(self, file_path, customer_name=None):
        import requests
        try:
            file_name = os.path.basename(file_path)
            
            # Müşteri adı parametresi boşsa, dosya adından çıkarmayı dene
            if not customer_name:
                try:
                    # Örnek: Musteri_20260309_103636.db -> Musteri
                    customer_name = file_name.split('_')[0]
                except IndexError:
                    customer_name = "Bilinmeyen"

            # Dinamik IP kontrolü
            ip = "85.117.239.60:8000"
            if self.parent:
                ip = self.parent.get_db_setting("backup_server_ip", ip)
            
            # URL'yi dinamik oluştur
            if ip:
                # Port kontrolü (8000 yoksa ekle)
                # Basit ipv4 kontrolü
                clean_ip = ip.replace("http://", "").replace("https://", "").rstrip("/")
                if ":" not in clean_ip:
                    ip = f"{clean_ip}:8000"
                
                # Basic normalization
                if not ip.startswith("http"):
                     # Check if user entered IP:PORT without scheme
                    base_url = f"http://{ip}"
                else:
                    base_url = ip
                
                # Check if it has the path, if not append it
                if "/api/backup/upload" not in base_url:
                     # Remove trailing slash if any
                    base_url = base_url.rstrip("/")
                    url = f"{base_url}/api/backup/upload"
                else:
                    url = base_url
            else:
                 # Fallback to config only if NO IP found
                url = self.config['url']
            
            logger.info(f"Target Upload URL: {url}")

            headers = {}
            if self.config.get('auth_token'):
                headers['Authorization'] = f"Bearer {self.config['auth_token']}"
            
            data = {}
            if customer_name:
                data['customer_name'] = customer_name
            
            # Retry logic
            import time
            max_retries = 3
            last_error = None
            
            for attempt in range(max_retries):
                try:
                    with open(file_path, 'rb') as f:
                        files = {'file': (file_name, f)}
                        # Increased timeout to 120s
                        response = requests.post(url, headers=headers, files=files, data=data, timeout=120)
                        
                    if response.status_code == 200:
                        data_res = response.json()
                        if data_res.get('success'):
                            logger.info(f"Uploaded to Remote Server: {file_name} (Customer: {customer_name})")
                            return {'success': True, 'provider': 'remote', 'file_name': file_name}
                        else:
                            return {'success': False, 'error': data_res.get('message', 'Unknown server error')}
                    else:
                        last_error = f"HTTP {response.status_code}: {response.text}"
                        logger.warning(f"Attempt {attempt+1} failed: {last_error}")
                        
                except requests.exceptions.ConnectionError as ce:
                    last_error = f"Connection Error: {ce}"
                    logger.warning(f"Connection attempt {attempt+1} failed: {ce}")
                    _retry_pause(2)
                except Exception as e:
                    last_error = str(e)
                    logger.warning(f"Attempt {attempt+1} unexpected error: {e}")
                    _retry_pause(1)

            return {'success': False, 'error': f"Failed after {max_retries} attempts. Last error: {last_error}"}
            
        except Exception as e:
            logger.error(f"Remote upload initialization error: {e}")
            return {'success': False, 'error': str(e)}

    def list_backups(self):
        # Optional: Implement if server supports listing
        return []

    def download(self, file_name, destination):
        """Download the live database from the remote server"""
        import requests
        try:
            # Dinamik IP kontrolü
            ip = "85.117.239.60:8000"
            if self.parent:
                ip = self.parent.get_db_setting("backup_server_ip", ip)
            
            # URL'yi dinamik oluştur
            if ip:
                clean_ip = ip.replace("http://", "").replace("https://", "").rstrip("/")
                if ":" not in clean_ip:
                    ip = f"{clean_ip}:8000"
                
                if not ip.startswith("http"):
                    base_url = f"http://{ip}"
                else:
                    base_url = ip
                
                if "/api/backup/download" not in base_url:
                    base_url = base_url.rstrip("/")
                    url = f"{base_url}/api/backup/download"
                else:
                    url = base_url
            else:
                url = self.config.get('url', '').replace('/upload', '/download')
            
            logger.info(f"Target Download URL: {url}")

            # Auth header
            headers = {}
            if self.config.get('auth_token'):
                headers['Authorization'] = f"Bearer {self.config['auth_token']}"
            
            # Token from DB settings (if available)
            if self.parent:
                token = self.parent.get_db_setting("web_auth_token", None)
                if token:
                    headers['Authorization'] = f"Bearer {token}"
            
            # Download with retry
            max_retries = 3
            last_error = None
            
            for attempt in range(max_retries):
                try:
                    response = requests.get(url, headers=headers, timeout=120, stream=True)
                    
                    if response.status_code == 200:
                        # Save to destination
                        with open(destination, 'wb') as f:
                            for chunk in response.iter_content(chunk_size=8192):
                                f.write(chunk)
                        
                        logger.info(f"Downloaded from Remote Server to: {destination}")
                        return destination
                    else:
                        last_error = f"HTTP {response.status_code}: {response.text}"
                        logger.warning(f"Download attempt {attempt+1} failed: {last_error}")
                        
                except requests.exceptions.ConnectionError as ce:
                    last_error = f"Connection Error: {ce}"
                    logger.warning(f"Connection attempt {attempt+1} failed: {ce}")
                    _retry_pause(2)
                except Exception as e:
                    last_error = str(e)
                    logger.warning(f"Attempt {attempt+1} unexpected error: {e}")
                    _retry_pause(1)

            logger.error(f"Download failed after {max_retries} attempts. Last error: {last_error}")
            return None
            
        except Exception as e:
            logger.error(f"Remote download initialization error: {e}")
            return None

# Global instance
_cloud_backup_manager = None

def get_cloud_backup_manager(db_path='ayecpro.db'):
    """Global cloud backup manager instance"""
    global _cloud_backup_manager
    if _cloud_backup_manager is None:
        _cloud_backup_manager = CloudBackupManager(db_path)
    return _cloud_backup_manager

if __name__ == '__main__':
    # Test
    logger.info("Cloud Backup Manager - Test")
    
    manager = CloudBackupManager()
    logger.info("Yapılandırma:")
    logger.info(json.dumps(manager.config, indent=2, ensure_ascii=False))
    
    logger.info("Aktif provider'lar:")
    for name in manager.providers.keys():
        logger.info("  - %s", name)
    logger.info("Cloud backup manager hazır")
