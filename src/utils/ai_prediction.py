# -*- coding: utf-8 -*-

"""
AI-Powered Prediction System
AYEC Pro Teknik Servis Yonetim Sistemi

Machine Learning tabanlı tahminleme:
- Stok tahmini
- Gelir tahmini
- Müşteri davranış analizi
- Servis süresi tahmini
"""

import numpy as np
from datetime import datetime, timedelta
import logging
import json

logger = logging.getLogger('AIPrediction')

class AIPredictionEngine:
    """
    AI tahminleme motoru
    """
    
    def __init__(self, db):
        self.db = db
        self.models = {}
        self._init_models()
    
    def _init_models(self):
        """Modelleri başlat"""
        logger.info("AI Prediction Engine initializing...")
        
        # Basit tahminleme modelleri (gerçek ML kütüphaneleri olmadan)
        # Üretim ortamında scikit-learn, tensorflow vb. kullanılabilir
        self.models = {
            'stock': SimpleStockPredictor(),
            'revenue': SimpleRevenuePredictor(),
            'customer': SimpleCustomerPredictor(),
            'service_time': SimpleServiceTimePredictor()
        }
        
        logger.info("AI models loaded")
    
    def predict_stock_demand(self, part_id, days_ahead=30):
        """
        Stok talebi tahmini
        
        Args:
            part_id: Parça ID
            days_ahead: Kaç gün sonrası için tahmin
        
        Returns:
            dict: Tahmin sonuçları
        """
        try:
            # Geçmiş kullanım verilerini al
            history = self._get_stock_usage_history(part_id, days=90)
            
            if not history:
                return {
                    'predicted_demand': 0,
                    'confidence': 0,
                    'recommendation': 'Yetersiz veri'
                }
            
            # Tahmin yap
            prediction = self.models['stock'].predict(history, days_ahead)
            
            # Öneri oluştur
            current_stock = self._get_current_stock(part_id)
            recommendation = self._generate_stock_recommendation(
                current_stock, 
                prediction['predicted_demand']
            )
            
            return {
                'part_id': part_id,
                'current_stock': current_stock,
                'predicted_demand': prediction['predicted_demand'],
                'confidence': prediction['confidence'],
                'recommendation': recommendation,
                'days_ahead': days_ahead
            }
            
        except Exception as e:
            logger.error(f"Stock prediction error: {e}")
            return {'error': str(e)}
    
    def predict_revenue(self, months_ahead=3):
        """
        Gelir tahmini
        
        Args:
            months_ahead: Kaç ay sonrası için tahmin
        
        Returns:
            dict: Tahmin sonuçları
        """
        try:
            # Geçmiş gelir verilerini al
            history = self._get_revenue_history(months=12)
            
            if not history:
                return {
                    'predicted_revenue': 0,
                    'confidence': 0,
                    'trend': 'unknown'
                }
            
            # Tahmin yap
            prediction = self.models['revenue'].predict(history, months_ahead)
            
            # Trend analizi
            trend = self._analyze_revenue_trend(history)
            
            return {
                'predicted_revenue': prediction['predicted_revenue'],
                'confidence': prediction['confidence'],
                'trend': trend,
                'months_ahead': months_ahead,
                'breakdown': prediction.get('breakdown', {})
            }
            
        except Exception as e:
            logger.error(f"Revenue prediction error: {e}")
            return {'error': str(e)}
    
    def predict_customer_churn(self, customer_id):
        """
        Müşteri kaybı riski tahmini
        
        Args:
            customer_id: Müşteri ID
        
        Returns:
            dict: Risk analizi
        """
        try:
            # Müşteri aktivite verilerini al
            activity = self._get_customer_activity(customer_id)
            
            if not activity:
                return {
                    'churn_risk': 'unknown',
                    'confidence': 0,
                    'recommendation': 'Yetersiz veri'
                }
            
            # Risk tahmini
            prediction = self.models['customer'].predict_churn(activity)
            
            # Öneri oluştur
            recommendation = self._generate_retention_recommendation(prediction['churn_risk'])
            
            return {
                'customer_id': customer_id,
                'churn_risk': prediction['churn_risk'],
                'risk_score': prediction['risk_score'],
                'confidence': prediction['confidence'],
                'recommendation': recommendation,
                'factors': prediction.get('factors', [])
            }
            
        except Exception as e:
            logger.error(f"Churn prediction error: {e}")
            return {'error': str(e)}
    
    def predict_service_duration(self, device_type, problem_description):
        """
        Servis süresi tahmini
        
        Args:
            device_type: Cihaz tipi
            problem_description: Problem açıklaması
        
        Returns:
            dict: Süre tahmini
        """
        try:
            # Benzer servis geçmişini al
            similar_services = self._get_similar_services(device_type, problem_description)
            
            if not similar_services:
                return {
                    'estimated_hours': 24,
                    'confidence': 0.3,
                    'note': 'Varsayılan tahmin (benzer servis bulunamadı)'
                }
            
            # Tahmin yap
            prediction = self.models['service_time'].predict(similar_services)
            
            return {
                'device_type': device_type,
                'estimated_hours': prediction['estimated_hours'],
                'estimated_days': prediction['estimated_hours'] / 8,
                'confidence': prediction['confidence'],
                'similar_services_count': len(similar_services)
            }
            
        except Exception as e:
            logger.error(f"Service duration prediction error: {e}")
            return {'error': str(e)}
    
    def get_insights(self):
        """
        Genel iş zekası önerileri
        
        Returns:
            dict: İçgörüler ve öneriler
        """
        insights = {
            'stock_alerts': [],
            'revenue_forecast': {},
            'customer_risks': [],
            'operational_insights': []
        }
        
        try:
            # Kritik stok uyarıları
            critical_parts = self.db.check_critical_stock()
            for part in critical_parts[:5]:  # İlk 5 kritik parça
                part_id = part[0]
                prediction = self.predict_stock_demand(part_id, days_ahead=30)
                if prediction.get('recommendation'):
                    insights['stock_alerts'].append({
                        'part_id': part_id,
                        'part_name': part[1],
                        'current_stock': part[2],
                        'prediction': prediction
                    })
            
            # Gelir tahmini
            insights['revenue_forecast'] = self.predict_revenue(months_ahead=3)
            
            # Operasyonel içgörüler
            insights['operational_insights'] = self._generate_operational_insights()
            
        except Exception as e:
            logger.error(f"Insights generation error: {e}")
        
        return insights
    
    # ========================================================================
    # HELPER METHODS
    # ========================================================================
    
    def _get_stock_usage_history(self, part_id, days=90):
        """Parça kullanım geçmişini al"""
        try:
            # stock_history tablosundan veri çek
            query = """
                SELECT date, amount 
                FROM stock_history 
                WHERE part_id = ? AND type = 'OUT'
                ORDER BY date DESC 
                LIMIT ?
            """
            self.db.cursor.execute(query, (part_id, days))
            rows = self.db.cursor.fetchall()
            
            return [{'date': row[0], 'amount': abs(row[1])} for row in rows]
        except Exception as e:
            logger.debug(f"AI prediction stock usage history fallback: {e}")
            return []
    
    def _get_current_stock(self, part_id):
        """Mevcut stok miktarını al"""
        try:
            self.db.cursor.execute("SELECT stock FROM parts WHERE id = ?", (part_id,))
            row = self.db.cursor.fetchone()
            return row[0] if row else 0
        except Exception as e:
            logger.debug(f"AI prediction current stock fallback: {e}")
            return 0
    
    def _get_revenue_history(self, months=12):
        """Gelir geçmişini al"""
        try:
            query = """
                SELECT date, amount 
                FROM accounting 
                WHERE type = 'Gelir'
                ORDER BY date DESC
            """
            self.db.cursor.execute(query)
            rows = self.db.cursor.fetchall()
            
            # Aylık toplam
            monthly = {}
            for row in rows:
                try:
                    # date strings are usually YYYY-MM-DD HH:MM:SS or just YYYY-MM-DD
                    date_str = str(row[0])
                    if ' ' in date_str:
                        date_obj = datetime.strptime(date_str.split(' ')[0], '%Y-%m-%d')
                    else:
                        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                    month_key = date_obj.strftime('%Y-%m')
                    monthly[month_key] = monthly.get(month_key, 0) + row[1]
                except Exception:
                    continue
            
            return [{'month': k, 'revenue': v} for k, v in sorted(monthly.items())][-months:]
        except Exception as e:
            logger.debug(f"AI prediction revenue history fallback: {e}")
            return []
    
    def _get_customer_activity(self, customer_id):
        """Müşteri aktivite verilerini al"""
        try:
            # Son 6 ay içindeki servisler
            query = """
                SELECT created_at, status 
                FROM devices 
                WHERE customer_id = ?
                ORDER BY created_at DESC
            """
            self.db.cursor.execute(query, (customer_id,))
            rows = self.db.cursor.fetchall()
            
            return {
                'total_services': len(rows),
                'recent_services': rows[:10],
                'last_service_date': rows[0][0] if rows else None
            }
        except Exception as e:
            logger.debug(f"AI prediction customer activity fallback: {e}")
            return {}
    
    def _get_similar_services(self, device_type, problem_description):
        """Benzer servisleri bul"""
        try:
            query = """
                SELECT created_at, completed_at 
                FROM devices 
                WHERE device_type = ? AND status = 'Teslim Edildi'
                LIMIT 50
            """
            self.db.cursor.execute(query, (device_type,))
            rows = self.db.cursor.fetchall()
            
            services = []
            for row in rows:
                try:
                    # date strings: YYYY-MM-DD HH:MM:SS
                    def parse_dt(dt_str):
                        if not dt_str: return None
                        fmt = "%Y-%m-%d %H:%M:%S" if ' ' in str(dt_str) else "%Y-%m-%d"
                        return datetime.strptime(str(dt_str), fmt)

                    start = parse_dt(row[0])
                    end = parse_dt(row[1])
                    if start and end:
                        duration = (end - start).total_seconds() / 3600  # Saat
                        services.append({'duration_hours': duration})
                except Exception as e:
                    logger.debug(f"Date parse error in similar services: {e}")
                    continue
            
            return services
        except Exception as e:
            logger.debug(f"AI prediction similar services fallback: {e}")
            return []
    
    def _generate_stock_recommendation(self, current_stock, predicted_demand):
        """Stok önerisi oluştur"""
        if predicted_demand > current_stock * 2:
            return f"ACİL: {int(predicted_demand - current_stock)} adet sipariş verin"
        elif predicted_demand > current_stock:
            return f"UYARI: {int(predicted_demand - current_stock)} adet sipariş önerilir"
        else:
            return "Stok yeterli"
    
    def _analyze_revenue_trend(self, history):
        """Gelir trendi analizi"""
        if len(history) < 3:
            return 'unknown'
        
        recent = [h['revenue'] for h in history[-3:]]
        avg_recent = sum(recent) / len(recent)
        
        older = [h['revenue'] for h in history[:-3]]
        avg_older = sum(older) / len(older) if older else avg_recent
        
        if avg_recent > avg_older * 1.1:
            return 'increasing'
        elif avg_recent < avg_older * 0.9:
            return 'decreasing'
        else:
            return 'stable'
    
    def _generate_retention_recommendation(self, churn_risk):
        """Müşteri elde tutma önerisi"""
        if churn_risk == 'high':
            return "ACİL: Müşteriyle iletişime geçin, özel indirim sunun"
        elif churn_risk == 'medium':
            return "UYARI: Müşteri memnuniyeti anketi gönderin"
        else:
            return "Müşteri ilişkisi iyi durumda"
    
    def _generate_operational_insights(self):
        """Operasyonel içgörüler"""
        insights = []
        
        try:
            # Bekleyen servis sayısı
            self.db.cursor.execute("SELECT COUNT(*) FROM devices WHERE status = 'Beklemede'")
            pending = self.db.cursor.fetchone()[0]
            
            if pending > 10:
                insights.append({
                    'type': 'warning',
                    'message': f'{pending} bekleyen servis var. Kapasite artırımı düşünün.'
                })
            
            # Parça bekleyen servisler
            self.db.cursor.execute("SELECT COUNT(*) FROM devices WHERE status = 'Parça Bekliyor'")
            waiting_parts = self.db.cursor.fetchone()[0]
            
            if waiting_parts > 5:
                insights.append({
                    'type': 'warning',
                    'message': f'{waiting_parts} servis parça bekliyor. Tedarik sürecini hızlandırın.'
                })
        except Exception as e:
            logger.debug(f"AI prediction operational insights fallback: {e}")
        
        return insights

# ============================================================================
# SIMPLE PREDICTION MODELS (ML kütüphaneleri olmadan basit tahminleme)
# ============================================================================

class SimpleStockPredictor:
    """Basit stok tahmini"""
    
    def predict(self, history, days_ahead):
        if not history:
            return {'predicted_demand': 0, 'confidence': 0}
        
        # Ortalama günlük kullanım
        total_usage = sum(h['amount'] for h in history)
        avg_daily = total_usage / len(history)
        
        # Tahmin
        predicted = avg_daily * days_ahead
        
        # Güven skoru (veri miktarına göre)
        confidence = min(len(history) / 90, 1.0)
        
        return {
            'predicted_demand': int(predicted),
            'confidence': confidence
        }

class SimpleRevenuePredictor:
    """Basit gelir tahmini"""
    
    def predict(self, history, months_ahead):
        if not history:
            return {'predicted_revenue': 0, 'confidence': 0}
        
        # Ortalama aylık gelir
        total_revenue = sum(h['revenue'] for h in history)
        avg_monthly = total_revenue / len(history)
        
        # Trend faktörü
        if len(history) >= 3:
            recent_avg = sum(h['revenue'] for h in history[-3:]) / 3
            trend_factor = recent_avg / avg_monthly if avg_monthly > 0 else 1.0
        else:
            trend_factor = 1.0
        
        # Tahmin
        predicted = avg_monthly * trend_factor * months_ahead
        
        return {
            'predicted_revenue': predicted,
            'confidence': min(len(history) / 12, 0.9),
            'breakdown': {
                'avg_monthly': avg_monthly,
                'trend_factor': trend_factor
            }
        }

class SimpleCustomerPredictor:
    """Basit müşteri davranış tahmini"""
    
    def predict_churn(self, activity):
        total_services = activity.get('total_services', 0)
        last_service = activity.get('last_service_date')
        
        if total_services == 0:
            return {
                'churn_risk': 'unknown',
                'risk_score': 0,
                'confidence': 0,
                'factors': []
            }
        
        # Son servis tarihi kontrolü
        risk_score = 0
        factors = []
        
        if last_service:
            try:
                # date format: YYYY-MM-DD HH:MM:SS
                fmt = "%Y-%m-%d %H:%M:%S" if ' ' in str(last_service) else "%Y-%m-%d"
                last_date = datetime.strptime(str(last_service), fmt)
                days_since = (datetime.now() - last_date).days
                
                if days_since > 180:
                    risk_score += 0.5
                    factors.append('6 aydan uzun süredir servis yok')
                elif days_since > 90:
                    risk_score += 0.3
                    factors.append('3 aydan uzun süredir servis yok')
            except Exception as e:
                logger.debug(f"AI prediction churn date parse fallback: {e}")
        
        # Servis sayısı
        if total_services < 3:
            risk_score += 0.2
            factors.append('Az sayıda servis geçmişi')
        
        # Risk kategorisi
        if risk_score > 0.6:
            churn_risk = 'high'
        elif risk_score > 0.3:
            churn_risk = 'medium'
        else:
            churn_risk = 'low'
        
        return {
            'churn_risk': churn_risk,
            'risk_score': risk_score,
            'confidence': 0.7,
            'factors': factors
        }

class SimpleServiceTimePredictor:
    """Basit servis süresi tahmini"""
    
    def predict(self, similar_services):
        if not similar_services:
            return {'estimated_hours': 24, 'confidence': 0.3}
        
        # Ortalama süre
        durations = [s['duration_hours'] for s in similar_services]
        avg_duration = sum(durations) / len(durations)
        
        # Güven skoru
        confidence = min(len(similar_services) / 20, 0.9)
        
        return {
            'estimated_hours': avg_duration,
            'confidence': confidence
        }

# Global instance
_ai_engine = None

def get_ai_engine(db):
    """Global AI engine instance"""
    global _ai_engine
    if _ai_engine is None:
        _ai_engine = AIPredictionEngine(db)
    return _ai_engine

if __name__ == '__main__':
    logger.info("AI Prediction Engine - Test Mode")
    logger.info("Bu modül database bağlantısı gerektirir.")