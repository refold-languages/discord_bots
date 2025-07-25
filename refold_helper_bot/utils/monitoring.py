"""
Monitoring and performance tracking system for Refold Helper Bot.
Provides performance metrics, health checks, and operational insights.
"""

import asyncio
import time
import psutil
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field

from .logger import get_logger, log_performance, log_health_check


@dataclass
class PerformanceMetric:
    """Data class for performance metrics."""
    operation: str
    duration_ms: float
    timestamp: datetime
    success: bool
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class HealthCheckResult:
    """Data class for health check results."""
    name: str
    healthy: bool
    message: str
    timestamp: datetime
    duration_ms: float
    context: Dict[str, Any] = field(default_factory=dict)


class PerformanceMonitor:
    """Performance monitoring and metrics collection system."""
    
    def __init__(self, max_metrics: int = 1000):
        self.logger = get_logger('bot.performance')
        self.metrics: deque = deque(maxlen=max_metrics)
        self.operation_stats: Dict[str, Dict] = defaultdict(lambda: {
            'count': 0,
            'total_duration': 0.0,
            'min_duration': float('inf'),
            'max_duration': 0.0,
            'success_count': 0,
            'error_count': 0
        })
        self.start_time = datetime.utcnow()
    
    @asynccontextmanager
    async def track(self, operation: str, **context):
        """
        Context manager for tracking operation performance.
        
        Args:
            operation: Name of the operation
            context: Additional context to include in metrics
        
        Usage:
            async with performance_monitor.track("database_query", table="users"):
                result = await database.query("SELECT * FROM users")
        """
        start_time = time.perf_counter()
        success = False
        error = None
        
        try:
            yield
            success = True
        except Exception as e:
            error = str(e)
            raise
        finally:
            end_time = time.perf_counter()
            duration_ms = (end_time - start_time) * 1000
            
            # Record metric
            metric = PerformanceMetric(
                operation=operation,
                duration_ms=duration_ms,
                timestamp=datetime.utcnow(),
                success=success,
                context={**context, 'error': error} if error else context
            )
            self.record_metric(metric)
    
    def record_metric(self, metric: PerformanceMetric):
        """Record a performance metric."""
        self.metrics.append(metric)
        
        # Update operation statistics
        stats = self.operation_stats[metric.operation]
        stats['count'] += 1
        stats['total_duration'] += metric.duration_ms
        stats['min_duration'] = min(stats['min_duration'], metric.duration_ms)
        stats['max_duration'] = max(stats['max_duration'], metric.duration_ms)
        
        if metric.success:
            stats['success_count'] += 1
        else:
            stats['error_count'] += 1
        
        # Log the performance metric
        log_performance(
            metric.operation,
            metric.duration_ms,
            success=metric.success,
            **metric.context
        )
    
    def get_operation_stats(self, operation: str = None) -> Dict[str, Any]:
        """
        Get performance statistics for operations.
        
        Args:
            operation: Specific operation to get stats for, or None for all
            
        Returns:
            Dictionary of performance statistics
        """
        if operation:
            if operation not in self.operation_stats:
                return {}
            
            stats = self.operation_stats[operation].copy()
            if stats['count'] > 0:
                stats['avg_duration'] = stats['total_duration'] / stats['count']
                stats['success_rate'] = stats['success_count'] / stats['count']
                stats['error_rate'] = stats['error_count'] / stats['count']
            return stats
        
        # Return all operations
        result = {}
        for op_name, stats in self.operation_stats.items():
            op_stats = stats.copy()
            if op_stats['count'] > 0:
                op_stats['avg_duration'] = op_stats['total_duration'] / op_stats['count']
                op_stats['success_rate'] = op_stats['success_count'] / op_stats['count']
                op_stats['error_rate'] = op_stats['error_count'] / op_stats['count']
            result[op_name] = op_stats
        
        return result
    
    def get_recent_metrics(self, minutes: int = 10) -> List[PerformanceMetric]:
        """Get metrics from the last N minutes."""
        cutoff = datetime.utcnow() - timedelta(minutes=minutes)
        return [m for m in self.metrics if m.timestamp >= cutoff]
    
    def get_slow_operations(self, threshold_ms: float = 1000) -> List[PerformanceMetric]:
        """Get operations that took longer than threshold."""
        return [m for m in self.metrics if m.duration_ms >= threshold_ms]
    
    def clear_metrics(self):
        """Clear all stored metrics and reset statistics."""
        self.metrics.clear()
        self.operation_stats.clear()
        self.start_time = datetime.utcnow()


class HealthCheck:
    """Health checking system for monitoring bot components."""
    
    def __init__(self):
        self.logger = get_logger('bot.health')
        self.checks: Dict[str, Callable] = {}
        self.last_results: Dict[str, HealthCheckResult] = {}
        self.check_intervals: Dict[str, int] = {}  # seconds
        self._running_checks: Dict[str, asyncio.Task] = {}
    
    def register_check(self, name: str, check_func: Callable, interval_seconds: int = 300):
        """
        Register a health check function.
        
        Args:
            name: Name of the health check
            check_func: Async function that returns (healthy: bool, message: str, context: dict)
            interval_seconds: How often to run this check (default 5 minutes)
        """
        self.checks[name] = check_func
        self.check_intervals[name] = interval_seconds
    
    async def run_check(self, name: str) -> HealthCheckResult:
        """
        Run a specific health check.
        
        Args:
            name: Name of the health check to run
            
        Returns:
            HealthCheckResult with the check results
        """
        if name not in self.checks:
            return HealthCheckResult(
                name=name,
                healthy=False,
                message=f"Health check '{name}' not found",
                timestamp=datetime.utcnow(),
                duration_ms=0.0
            )
        
        start_time = time.perf_counter()
        try:
            healthy, message, context = await self.checks[name]()
            duration_ms = (time.perf_counter() - start_time) * 1000
            
            result = HealthCheckResult(
                name=name,
                healthy=healthy,
                message=message,
                timestamp=datetime.utcnow(),
                duration_ms=duration_ms,
                context=context or {}
            )
            
            self.last_results[name] = result
            log_health_check(name, healthy, duration_ms=duration_ms, **context)
            
            return result
            
        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            self.logger.exception(f"Health check '{name}' failed", check_name=name, error=str(e))
            
            result = HealthCheckResult(
                name=name,
                healthy=False,
                message=f"Check failed: {str(e)}",
                timestamp=datetime.utcnow(),
                duration_ms=duration_ms,
                context={'error': str(e)}
            )
            
            self.last_results[name] = result
            return result
    
    async def run_all_checks(self) -> Dict[str, HealthCheckResult]:
        """Run all registered health checks."""
        results = {}
        
        # Run all checks concurrently
        tasks = {name: self.run_check(name) for name in self.checks.keys()}
        completed = await asyncio.gather(*tasks.values(), return_exceptions=True)
        
        for name, result in zip(tasks.keys(), completed):
            if isinstance(result, Exception):
                results[name] = HealthCheckResult(
                    name=name,
                    healthy=False,
                    message=f"Check execution failed: {str(result)}",
                    timestamp=datetime.utcnow(),
                    duration_ms=0.0
                )
            else:
                results[name] = result
        
        return results
    
    def get_health_summary(self) -> Dict[str, Any]:
        """Get overall health summary."""
        if not self.last_results:
            return {
                'overall_healthy': True,
                'total_checks': 0,
                'healthy_checks': 0,
                'unhealthy_checks': 0,
                'last_check_time': None,
                'checks': {}
            }
        
        healthy_count = sum(1 for r in self.last_results.values() if r.healthy)
        total_count = len(self.last_results)
        overall_healthy = healthy_count == total_count
        
        return {
            'overall_healthy': overall_healthy,
            'total_checks': total_count,
            'healthy_checks': healthy_count,
            'unhealthy_checks': total_count - healthy_count,
            'last_check_time': max(r.timestamp for r in self.last_results.values()),
            'checks': {name: {
                'healthy': result.healthy,
                'message': result.message,
                'timestamp': result.timestamp,
                'duration_ms': result.duration_ms
            } for name, result in self.last_results.items()}
        }
    
    def start_periodic_checks(self):
        """Start running periodic health checks."""
        for name, interval in self.check_intervals.items():
            if name not in self._running_checks:
                task = asyncio.create_task(self._periodic_check_loop(name, interval))
                self._running_checks[name] = task
    
    def stop_periodic_checks(self):
        """Stop all periodic health checks."""
        for task in self._running_checks.values():
            task.cancel()
        self._running_checks.clear()
    
    async def _periodic_check_loop(self, name: str, interval: int):
        """Run a health check periodically."""
        while True:
            try:
                await self.run_check(name)
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Periodic health check loop failed", check_name=name, error=str(e))
                await asyncio.sleep(60)  # Wait a minute before retrying


def create_system_health_checks(health_checker: HealthCheck):
    """Create standard system health checks."""
    
    async def memory_usage_check():
        """Check memory usage."""
        memory = psutil.virtual_memory()
        usage_percent = memory.percent
        
        # Consider unhealthy if using more than 85% memory
        healthy = usage_percent < 85
        message = f"Memory usage: {usage_percent:.1f}%"
        context = {
            'memory_percent': usage_percent,
            'memory_available_gb': memory.available / (1024**3),
            'memory_total_gb': memory.total / (1024**3)
        }
        
        return healthy, message, context
    
    async def disk_usage_check():
        """Check disk usage."""
        disk = psutil.disk_usage('/')
        usage_percent = (disk.used / disk.total) * 100
        
        # Consider unhealthy if using more than 90% disk
        healthy = usage_percent < 90
        message = f"Disk usage: {usage_percent:.1f}%"
        context = {
            'disk_percent': usage_percent,
            'disk_free_gb': disk.free / (1024**3),
            'disk_total_gb': disk.total / (1024**3)
        }
        
        return healthy, message, context
    
    async def cpu_usage_check():
        """Check CPU usage."""
        # Get average CPU usage over 1 second
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # Consider unhealthy if using more than 80% CPU consistently
        healthy = cpu_percent < 80
        message = f"CPU usage: {cpu_percent:.1f}%"
        context = {
            'cpu_percent': cpu_percent,
            'cpu_count': psutil.cpu_count()
        }
        
        return healthy, message, context
    
    # Register the checks
    health_checker.register_check('memory_usage', memory_usage_check, interval_seconds=300)
    health_checker.register_check('disk_usage', disk_usage_check, interval_seconds=600)
    health_checker.register_check('cpu_usage', cpu_usage_check, interval_seconds=300)


# Global instances
performance_monitor = PerformanceMonitor()
health_check = HealthCheck()

# Initialize system health checks
create_system_health_checks(health_check)