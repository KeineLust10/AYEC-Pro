# -*- coding: utf-8 -*-

"""
Asenkron İşlem Yöneticisi
AYEC Pro Teknik Servis Yonetim Sistemi

Bu modül, uzun süren işlemleri arka planda çalıştırır.
"""

import threading
import queue
import logging
import time
from datetime import datetime
from functools import wraps

logger = logging.getLogger('AsyncManager')


def _interruptible_sleep(delay):
    threading.Event().wait(delay)

class AsyncTaskManager:
    """
    Asenkron görev yöneticisi
    """
    
    def __init__(self, max_workers=5):
        self.max_workers = max_workers
        self.task_queue = queue.Queue()
        self.workers = []
        self.running = False
        self.completed_tasks = []
        self.failed_tasks = []
    
    def start(self):
        """
        Worker thread'lerini başlatır
        """
        if self.running:
            logger.warning("AsyncTaskManager already running")
            return
        
        self.running = True
        
        for i in range(self.max_workers):
            worker = threading.Thread(
                target=self._worker,
                name=f"AsyncWorker-{i}",
                daemon=True
            )
            worker.start()
            self.workers.append(worker)
        
        logger.info(f"AsyncTaskManager started with {self.max_workers} workers")
    
    def stop(self):
        """
        Worker thread'lerini durdurur
        """
        self.running = False
        
        # Tüm worker'ların bitmesini bekle
        for worker in self.workers:
            worker.join(timeout=5)
        
        logger.info("AsyncTaskManager stopped")
    
    def _worker(self):
        """
        Worker thread fonksiyonu
        """
        while self.running:
            try:
                # Queue'dan görev al (timeout ile)
                task = self.task_queue.get(timeout=1)
                
                if task is None:
                    break
                
                task_id, func, args, kwargs, callback = task
                
                try:
                    # Görevi çalıştır
                    logger.debug(f"Executing task {task_id}: {func.__name__}")
                    start_time = datetime.now()
                    
                    result = func(*args, **kwargs)
                    
                    end_time = datetime.now()
                    duration = (end_time - start_time).total_seconds()
                    
                    # Başarılı görev
                    self.completed_tasks.append({
                        'task_id': task_id,
                        'function': func.__name__,
                        'start_time': start_time,
                        'end_time': end_time,
                        'duration': duration,
                        'result': result
                    })
                    
                    logger.info(f"Task {task_id} completed in {duration:.2f}s")
                    
                    # Callback varsa çağır
                    if callback:
                        try:
                            callback(result)
                        except Exception as e:
                            logger.error(f"Callback error for task {task_id}: {str(e)}")
                
                except Exception as e:
                    # Başarısız görev
                    logger.error(f"Task {task_id} failed: {str(e)}")
                    
                    self.failed_tasks.append({
                        'task_id': task_id,
                        'function': func.__name__,
                        'error': str(e),
                        'timestamp': datetime.now()
                    })
                
                finally:
                    self.task_queue.task_done()
            
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Worker error: {str(e)}")
    
    def submit_task(self, func, *args, callback=None, **kwargs):
        """
        Bir görevi queue'ya ekler
        
        Args:
            func: Çalıştırılacak fonksiyon
            *args: Fonksiyon argümanları
            callback: Tamamlandığında çağrılacak fonksiyon
            **kwargs: Fonksiyon keyword argümanları
        
        Returns:
            str: Task ID
        """
        task_id = f"task_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        
        self.task_queue.put((task_id, func, args, kwargs, callback))
        
        logger.debug(f"Task {task_id} submitted: {func.__name__}")
        
        return task_id
    
    def get_queue_size(self):
        """
        Queue'daki bekleyen görev sayısını döndürür
        """
        return self.task_queue.qsize()
    
    def get_completed_count(self):
        """
        Tamamlanan görev sayısını döndürür
        """
        return len(self.completed_tasks)
    
    def get_failed_count(self):
        """
        Başarısız görev sayısını döndürür
        """
        return len(self.failed_tasks)
    
    def get_stats(self):
        """
        İstatistikleri döndürür
        """
        return {
            'queue_size': self.get_queue_size(),
            'completed': self.get_completed_count(),
            'failed': self.get_failed_count(),
            'workers': len(self.workers),
            'running': self.running
        }

# Global task manager
_task_manager = None

def get_task_manager(max_workers=5):
    """
    Global task manager instance'ını döndürür
    """
    global _task_manager
    if _task_manager is None:
        _task_manager = AsyncTaskManager(max_workers)
        _task_manager.start()
    return _task_manager

def async_task(callback=None):
    """
    Decorator: Fonksiyonu asenkron çalıştırır
    
    Usage:
        @async_task
        def long_running_function():
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            task_manager = get_task_manager()
            return task_manager.submit_task(func, *args, callback=callback, **kwargs)
        return wrapper
    return decorator

class BackgroundTask:
    """
    Arka plan görevi için yardımcı sınıf
    """
    
    def __init__(self, func, *args, **kwargs):
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self.thread = None
        self.result = None
        self.error = None
        self.completed = False
    
    def start(self):
        """
        Görevi başlatır
        """
        self.thread = threading.Thread(
            target=self._run,
            daemon=True
        )
        self.thread.start()
        return self
    
    def _run(self):
        """
        Görevi çalıştırır
        """
        try:
            self.result = self.func(*self.args, **self.kwargs)
        except Exception as e:
            self.error = e
            logger.error(f"Background task error: {str(e)}")
        finally:
            self.completed = True
    
    def wait(self, timeout=None):
        """
        Görevin bitmesini bekler
        
        Args:
            timeout: Maksimum bekleme süresi (saniye)
        
        Returns:
            result: Görev sonucu
        """
        if self.thread:
            self.thread.join(timeout=timeout)
        
        if self.error:
            raise self.error
        
        return self.result
    
    def is_completed(self):
        """
        Görev tamamlandı mı?
        """
        return self.completed

def run_in_background(func, *args, **kwargs):
    """
    Bir fonksiyonu arka planda çalıştırır
    
    Args:
        func: Fonksiyon
        *args: Argümanlar
        **kwargs: Keyword argümanlar
    
    Returns:
        BackgroundTask: Görev nesnesi
    """
    task = BackgroundTask(func, *args, **kwargs)
    return task.start()

if __name__ == '__main__':
    # Test

    logger.info("Async Task Manager - Test")
    
    def test_task(n, delay=0.5):
        """Test görevi"""
        logger.info("Task %s started", n)
        _interruptible_sleep(delay)
        logger.info("Task %s completed", n)
        return f"Result {n}"
    
    def on_complete(result):
        """Callback fonksiyonu"""
        logger.info("Callback: %s", result)
    
    # Task manager'ı başlat
    manager = get_task_manager(max_workers=3)
    
    # Görevleri gönder
    logger.info("Submitting tasks...")
    for i in range(5):
        manager.submit_task(test_task, i, delay=0.3, callback=on_complete)
    
    # Bekle
    logger.info("Waiting for tasks to complete...")
    _interruptible_sleep(3)
    
    # İstatistikler
    stats = manager.get_stats()
    logger.info("Stats: %s", stats)
    
    # Background task test
    logger.info("Background Task Test:")
    bg_task = run_in_background(test_task, 99, delay=1.0)
    logger.info("Background task started, doing other work...")
    _interruptible_sleep(0.5)
    logger.info("Waiting for background task...")
    result = bg_task.wait()
    logger.info("Background task result: %s", result)
    
    # Cleanup
    manager.stop()
    logger.info("Test completed")
