"""
Advanced Analytics Engine

Provides detailed analytics and insights on query patterns,
performance metrics, and usage trends.
"""
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Tuple
from collections import Counter, defaultdict

from crawler.history_manager import HistoryManager, QueryRecord


class AnalyticsEngine:
    """
    Advanced analytics for query history

    Features:
    - Performance metrics (execution time, confidence, success rate)
    - Usage patterns (peak hours, popular products, language preferences)
    - Trend analysis (query volume over time)
    - Parsing accuracy tracking
    - Comparative analytics
    """

    def __init__(self, history_manager: HistoryManager = None):
        """Initialize analytics engine"""
        self.history_manager = history_manager or HistoryManager()

    def get_performance_metrics(self) -> Dict:
        """
        Calculate performance metrics

        Returns:
            dict: Performance statistics
        """
        history = self.history_manager.history

        if not history:
            return self._empty_metrics()

        # Execution time stats
        exec_times = [r.execution_time for r in history]
        avg_exec_time = sum(exec_times) / len(exec_times)
        min_exec_time = min(exec_times)
        max_exec_time = max(exec_times)

        # Confidence stats
        confidences = [r.confidence for r in history]
        avg_confidence = sum(confidences) / len(confidences)
        high_confidence = sum(1 for c in confidences if c >= 0.9)
        low_confidence = sum(1 for c in confidences if c < 0.7)

        # Results stats
        results = [r.results_count for r in history]
        avg_results = sum(results) / len(results)
        zero_results = sum(1 for r in results if r == 0)

        # Success rate (queries with >0 results)
        success_rate = (len(history) - zero_results) / len(history) if history else 0

        return {
            'execution_time': {
                'avg': avg_exec_time,
                'min': min_exec_time,
                'max': max_exec_time,
                'median': sorted(exec_times)[len(exec_times) // 2]
            },
            'confidence': {
                'avg': avg_confidence,
                'high_count': high_confidence,
                'low_count': low_confidence,
                'high_percentage': high_confidence / len(history) * 100
            },
            'results': {
                'avg': avg_results,
                'zero_results': zero_results,
                'success_rate': success_rate * 100
            }
        }

    def get_usage_patterns(self) -> Dict:
        """
        Analyze usage patterns

        Returns:
            dict: Usage pattern statistics
        """
        history = self.history_manager.history

        if not history:
            return {}

        # Parse timestamps
        hours = []
        days_of_week = []
        dates = []

        for record in history:
            try:
                dt = datetime.fromisoformat(record.timestamp)
                hours.append(dt.hour)
                days_of_week.append(dt.weekday())  # 0=Monday
                dates.append(dt.date())
            except:
                continue

        # Peak hours
        hour_counts = Counter(hours)
        peak_hour = hour_counts.most_common(1)[0] if hour_counts else (0, 0)

        # Peak day
        day_counts = Counter(days_of_week)
        day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        peak_day = day_counts.most_common(1)[0] if day_counts else (0, 0)

        # Active days
        unique_dates = set(dates)
        total_days = (max(dates) - min(dates)).days + 1 if dates else 0
        active_days = len(unique_dates)

        # Most popular products
        product_counts = Counter(r.product for r in history)
        popular_products = product_counts.most_common(5)

        # Most popular languages
        lang_counts = Counter(r.language for r in history)
        popular_languages = lang_counts.most_common()

        return {
            'peak_hour': {
                'hour': peak_hour[0],
                'count': peak_hour[1],
                'time_range': f"{peak_hour[0]:02d}:00-{peak_hour[0]:02d}:59"
            },
            'peak_day': {
                'day': day_names[peak_day[0]] if peak_day[0] < 7 else 'Unknown',
                'count': peak_day[1]
            },
            'activity': {
                'total_days': total_days,
                'active_days': active_days,
                'activity_rate': active_days / total_days * 100 if total_days > 0 else 0
            },
            'popular_products': popular_products,
            'popular_languages': popular_languages
        }

    def get_trend_analysis(self, days: int = 7) -> Dict:
        """
        Analyze query trends over time

        Args:
            days: Number of days to analyze

        Returns:
            dict: Trend statistics
        """
        history = self.history_manager.history

        if not history:
            return {}

        # Filter to recent days
        cutoff_date = datetime.now() - timedelta(days=days)
        recent_queries = []

        for record in history:
            try:
                dt = datetime.fromisoformat(record.timestamp)
                if dt >= cutoff_date:
                    recent_queries.append((dt.date(), record))
            except:
                continue

        if not recent_queries:
            return {'period': days, 'queries': 0}

        # Group by date
        queries_by_date = defaultdict(list)
        for date, record in recent_queries:
            queries_by_date[date].append(record)

        # Calculate daily stats
        daily_stats = {}
        for date, records in sorted(queries_by_date.items()):
            daily_stats[date.isoformat()] = {
                'count': len(records),
                'avg_confidence': sum(r.confidence for r in records) / len(records),
                'avg_results': sum(r.results_count for r in records) / len(records),
                'methods': Counter(r.method for r in records)
            }

        # Overall trend
        total_queries = len(recent_queries)
        avg_per_day = total_queries / days

        # Growth trend
        first_half = len([r for date, r in recent_queries if date < datetime.now().date() - timedelta(days=days//2)])
        second_half = len([r for date, r in recent_queries if date >= datetime.now().date() - timedelta(days=days//2)])

        if first_half > 0:
            growth_rate = ((second_half - first_half) / first_half) * 100
        else:
            growth_rate = 0

        return {
            'period_days': days,
            'total_queries': total_queries,
            'avg_per_day': avg_per_day,
            'growth_rate': growth_rate,
            'daily_stats': daily_stats
        }

    def get_parsing_accuracy(self) -> Dict:
        """
        Analyze parsing method performance

        Returns:
            dict: Parsing accuracy metrics
        """
        history = self.history_manager.history

        if not history:
            return {}

        # Group by parsing method
        by_method = defaultdict(list)
        for record in history:
            by_method[record.method].append(record)

        # Calculate metrics per method
        method_metrics = {}
        for method, records in by_method.items():
            confidences = [r.confidence for r in records]
            results = [r.results_count for r in records]
            exec_times = [r.execution_time for r in records]

            method_metrics[method] = {
                'count': len(records),
                'avg_confidence': sum(confidences) / len(confidences),
                'avg_results': sum(results) / len(results),
                'avg_exec_time': sum(exec_times) / len(exec_times),
                'success_rate': sum(1 for r in results if r > 0) / len(results) * 100
            }

        return method_metrics

    def get_comparative_analysis(self) -> Dict:
        """
        Compare metrics across different dimensions

        Returns:
            dict: Comparative statistics
        """
        history = self.history_manager.history

        if not history:
            return {}

        # By language comparison
        by_language = defaultdict(list)
        for record in history:
            by_language[record.language].append(record)

        lang_comparison = {}
        for lang, records in by_language.items():
            lang_comparison[lang] = {
                'count': len(records),
                'avg_confidence': sum(r.confidence for r in records) / len(records),
                'avg_results': sum(r.results_count for r in records) / len(records),
                'methods': Counter(r.method for r in records)
            }

        # By product comparison
        by_product = defaultdict(list)
        for record in history:
            by_product[record.product].append(record)

        product_comparison = {}
        for product, records in by_product.items():
            product_comparison[product] = {
                'count': len(records),
                'avg_confidence': sum(r.confidence for r in records) / len(records),
                'avg_results': sum(r.results_count for r in records) / len(records),
                'languages': Counter(r.language for r in records)
            }

        return {
            'by_language': lang_comparison,
            'by_product': product_comparison
        }

    def get_query_complexity_analysis(self) -> Dict:
        """
        Analyze query complexity patterns

        Returns:
            dict: Complexity metrics
        """
        history = self.history_manager.history

        if not history:
            return {}

        # Classify queries by complexity
        simple_queries = []  # Direct IMS or high confidence rules
        medium_queries = []  # Rules with medium confidence
        complex_queries = []  # LLM fallback or low confidence

        for record in history:
            if record.method == 'direct' or (record.method == 'rules' and record.confidence >= 0.9):
                simple_queries.append(record)
            elif record.method == 'llm' or record.confidence < 0.7:
                complex_queries.append(record)
            else:
                medium_queries.append(record)

        total = len(history)

        return {
            'simple': {
                'count': len(simple_queries),
                'percentage': len(simple_queries) / total * 100 if total > 0 else 0,
                'avg_exec_time': sum(r.execution_time for r in simple_queries) / len(simple_queries) if simple_queries else 0
            },
            'medium': {
                'count': len(medium_queries),
                'percentage': len(medium_queries) / total * 100 if total > 0 else 0,
                'avg_exec_time': sum(r.execution_time for r in medium_queries) / len(medium_queries) if medium_queries else 0
            },
            'complex': {
                'count': len(complex_queries),
                'percentage': len(complex_queries) / total * 100 if total > 0 else 0,
                'avg_exec_time': sum(r.execution_time for r in complex_queries) / len(complex_queries) if complex_queries else 0
            }
        }

    def generate_report(self, output_file: Path = None) -> Dict:
        """
        Generate comprehensive analytics report

        Args:
            output_file: Optional file to save report

        Returns:
            dict: Complete analytics report
        """
        report = {
            'generated_at': datetime.now().isoformat(),
            'total_queries': len(self.history_manager.history),
            'performance': self.get_performance_metrics(),
            'usage_patterns': self.get_usage_patterns(),
            'trends_7d': self.get_trend_analysis(days=7),
            'trends_30d': self.get_trend_analysis(days=30),
            'parsing_accuracy': self.get_parsing_accuracy(),
            'comparative': self.get_comparative_analysis(),
            'complexity': self.get_query_complexity_analysis()
        }

        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)

        return report

    def _empty_metrics(self) -> Dict:
        """Return empty metrics structure"""
        return {
            'execution_time': {'avg': 0, 'min': 0, 'max': 0, 'median': 0},
            'confidence': {'avg': 0, 'high_count': 0, 'low_count': 0, 'high_percentage': 0},
            'results': {'avg': 0, 'zero_results': 0, 'success_rate': 0}
        }
