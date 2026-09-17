# -*- coding: utf-8 -*-

"""
Performance Profiler ve Optimizasyon Aracı
AYEC Pro Teknik Servis Yonetim Sistemi

Bu modül, uygulama performansını izler ve bottleneck'leri tespit eder.
"""

import time
import functools
import logging
from datetime import datetime
import threading
from collections import defaultdict

logger = logging.getLogger('PerformanceProfiler')


def _interruptible_sleep(delay):
    threading.Event().wait(delay)

class PerformanceProfiler:
    """
    Performans izleme ve profiling sınıfı
    """
    
    def __init__(self):
        self.metrics = defaultdict(list)
        self.lock = threading.Lock()
        self.enabled = True
    
    def record_metric(self, function_name, execution_time, args_count=0):
        """
        Bir metriği kaydeder
        
        Args:
            function_name: Fonksiyon adı
            execution_time: Çalışma süresi (saniye)
            args_count: Argüman sayısı
        """
        if not self.enabled:
            return
        
        with self.lock:
            self.metrics[function_name].append({
                'time': execution_time,
                'timestamp': datetime.now(),
                'args_count': args_count
            })
    
    def get_stats(self, function_name=None):
        """
        İstatistikleri döndürür
        
        Args:
            function_name: Spesifik fonksiyon (None ise tümü)
        
        Returns:
            dict: İstatistikler
        """
        with self.lock:
            if function_name:
                if function_name not in self.metrics:
                    return None
                
                times = [m['time'] for m in self.metrics[function_name]]
                return {
                    'function': function_name,
                    'call_count': len(times),
                    'total_time': sum(times),
                    'avg_time': sum(times) / len(times) if times else 0,
                    'min_time': min(times) if times else 0,
                    'max_time': max(times) if times else 0
                }
            else:
                # Tüm fonksiyonlar için
                stats = {}
                for func_name, metrics in self.metrics.items():
                    times = [m['time'] for m in metrics]
                    stats[func_name] = {
                        'call_count': len(times),
                        'total_time': sum(times),
                        'avg_time': sum(times) / len(times) if times else 0,
                        'min_time': min(times) if times else 0,
                        'max_time': max(times) if times else 0
                    }
                return stats
    
    def get_slowest_functions(self, limit=10):
        """
        En yavaş fonksiyonları döndürür
        
        Args:
            limit: Kaç tane
        
        Returns:
            list: [(function_name, avg_time), ...]
        """
        stats = self.get_stats()
        sorted_funcs = sorted(
            stats.items(),
            key=lambda x: x[1]['avg_time'],
            reverse=True
        )
        return [(name, data['avg_time']) for name, data in sorted_funcs[:limit]]
    
    def get_most_called_functions(self, limit=10):
        """
        En çok çağrılan fonksiyonları döndürür
        
        Args:
            limit: Kaç tane
        
        Returns:
            list: [(function_name, call_count), ...]
        """
        stats = self.get_stats()
        sorted_funcs = sorted(
            stats.items(),
            key=lambda x: x[1]['call_count'],
            reverse=True
        )
        return [(name, data['call_count']) for name, data in sorted_funcs[:limit]]
    
    def clear_metrics(self):
        """
        Tüm metrikleri temizler
        """
        with self.lock:
            self.metrics.clear()
            logger.info("Performance metrics cleared")
    
    def generate_report(self):
        """
        Detaylı performans raporu oluşturur
        
        Returns:
            str: Rapor metni
        """
        stats = self.get_stats()
        
        report = []
        report.append("="*80)
        report.append("PERFORMANCE PROFILING REPORT")
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("="*80)
        report.append("")
        
        # En yavaş fonksiyonlar
        report.append("SLOWEST FUNCTIONS (Top 10)")
        report.append("-"*80)
        for func_name, avg_time in self.get_slowest_functions(10):
            report.append(f"  {func_name:50s} {avg_time*1000:8.2f} ms")
        report.append("")
        
        # En çok çağrılan fonksiyonlar
        report.append("MOST CALLED FUNCTIONS (Top 10)")
        report.append("-"*80)
        for func_name, call_count in self.get_most_called_functions(10):
            report.append(f"  {func_name:50s} {call_count:8d} calls")
        report.append("")
        
        # Detaylı istatistikler
        report.append("DETAILED STATISTICS")
        report.append("-"*80)
        report.append(f"{'Function':<40} {'Calls':>8} {'Total':>10} {'Avg':>10} {'Min':>10} {'Max':>10}")
        report.append("-"*80)
        
        for func_name, data in sorted(stats.items(), key=lambda x: x[1]['total_time'], reverse=True)[:20]:
            report.append(
                f"{func_name:<40} "
                f"{data['call_count']:>8d} "
                f"{data['total_time']:>10.3f}s "
                f"{data['avg_time']*1000:>9.2f}ms "
                f"{data['min_time']*1000:>9.2f}ms "
                f"{data['max_time']*1000:>9.2f}ms"
            )
        
        report.append("="*80)
        
        return "\n".join(report)
    
    def save_report(self, filename=None):
        """
        Raporu dosyaya kaydeder
        
        Args:
            filename: Dosya adı (None ise otomatik)
        """
        if filename is None:
            filename = f"performance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        report = self.generate_report()
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(report)
        
        logger.info(f"Performance report saved: {filename}")
        return filename

# Global profiler instance
_profiler = PerformanceProfiler()

def profile(func):
    """
    Decorator: Fonksiyon performansını ölçer
    
    Usage:
        @profile
        def my_function():
            ...
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        
        execution_time = end_time - start_time
        
        # Metriği kaydet
        _profiler.record_metric(
            f"{func.__module__}.{func.__name__}",
            execution_time,
            len(args) + len(kwargs)
        )
        
        # Eğer çok yavaşsa uyar
        if execution_time > 1.0:  # 1 saniyeden uzun
            logger.warning(
                f"Slow function detected: {func.__name__} took {execution_time:.2f}s"
            )
        
        return result
    
    return wrapper

def get_profiler():
    """
    Global profiler instance'ını döndürür
    """
    return _profiler

class QueryOptimizer:
    """
    SQL sorgu optimizasyon önerileri
    """
    
    @staticmethod
    def analyze_query(query):
        """
        SQL sorgusunu analiz eder ve öneriler sunar
        
        Args:
            query: SQL sorgusu
        
        Returns:
            list: Öneriler
        """
        suggestions = []
        
        query_lower = query.lower()
        
        # SELECT * kontrolü
        if 'select *' in query_lower:
            suggestions.append({
                'type': 'WARNING',
                'message': 'SELECT * kullanımı performansı düşürür. Sadece gerekli sütunları seçin.',
                'severity': 'MEDIUM'
            })
        
        # WHERE clause kontrolü
        if 'where' not in query_lower and 'select' in query_lower:
            suggestions.append({
                'type': 'WARNING',
                'message': 'WHERE clause olmadan tüm kayıtlar çekilecek. Filtre eklemeyi düşünün.',
                'severity': 'HIGH'
            })
        
        # JOIN kontrolü
        join_count = query_lower.count('join')
        if join_count > 3:
            suggestions.append({
                'type': 'WARNING',
                'message': f'{join_count} JOIN kullanılıyor. Çok fazla JOIN performansı düşürür.',
                'severity': 'HIGH'
            })
        
        # LIKE %...% kontrolü
        if "like '%" in query_lower or 'like "%' in query_lower:
            suggestions.append({
                'type': 'WARNING',
                'message': 'LIKE ile başlayan wildcard (%...) index kullanımını engeller.',
                'severity': 'MEDIUM'
            })
        
        # ORDER BY kontrolü
        if 'order by' in query_lower and 'limit' not in query_lower:
            suggestions.append({
                'type': 'INFO',
                'message': 'ORDER BY kullanılıyor ama LIMIT yok. Tüm kayıtlar sıralanacak.',
                'severity': 'LOW'
            })
        
        # Subquery kontrolü
        if query_lower.count('select') > 1:
            suggestions.append({
                'type': 'INFO',
                'message': 'Subquery kullanılıyor. JOIN ile değiştirilebilir mi kontrol edin.',
                'severity': 'LOW'
            })
        
        return suggestions

if __name__ == '__main__':
    # Test
    logger.info("Performance Profiler - Test")
    
    @profile
    def test_function(n):
        _interruptible_sleep(0.1)
        return sum(range(n))
    
    # Test çağrıları
    for i in range(5):
        test_function(1000)
    
    # Rapor
    profiler = get_profiler()
    logger.info("%s", profiler.generate_report())
    
    # Query optimizer test
    optimizer = QueryOptimizer()
    test_query = "SELECT * FROM customers WHERE name LIKE '%test%'"
    suggestions = optimizer.analyze_query(test_query)
    
    logger.info("Query Optimization Suggestions:")
    for sug in suggestions:
        logger.info("[%s] %s", sug["severity"], sug["message"])
