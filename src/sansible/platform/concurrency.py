"""
Cross-platform concurrency utilities.

Provides portable concurrency primitives that work correctly on both Windows and Unix,
avoiding fork-based assumptions that don't work on Windows.
"""

import concurrent.futures
import threading
import queue
from typing import TypeVar, Callable, Iterable, Optional, Any
from dataclasses import dataclass

from . import IS_WINDOWS


T = TypeVar("T")
R = TypeVar("R")


@dataclass
class TaskResult:
    """Result of a parallel task execution."""
    success: bool
    value: Any
    error: Optional[Exception]
    task_id: Any


def run_parallel_threads(
    func: Callable[[T], R],
    items: Iterable[T],
    max_workers: Optional[int] = None,
) -> list[TaskResult]:
    """
    Run a function in parallel using threads.
    
    This is the safest option for Windows compatibility as it avoids
    process-based parallelism which has limitations on Windows.
    
    Args:
        func: Function to call for each item
        items: Items to process
        max_workers: Maximum number of worker threads (default: min(32, cpu_count + 4))
    
    Returns:
        List of TaskResult objects in same order as input items
    """
    items_list = list(items)
    results: list[TaskResult] = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_idx = {
            executor.submit(func, item): idx
            for idx, item in enumerate(items_list)
        }
        
        # Pre-allocate results list
        results = [None] * len(items_list)  # type: ignore
        
        for future in concurrent.futures.as_completed(future_to_idx):
            idx = future_to_idx[future]
            try:
                value = future.result()
                results[idx] = TaskResult(
                    success=True,
                    value=value,
                    error=None,
                    task_id=idx,
                )
            except Exception as e:
                results[idx] = TaskResult(
                    success=False,
                    value=None,
                    error=e,
                    task_id=idx,
                )
    
    return results


def run_parallel_processes(
    func: Callable[[T], R],
    items: Iterable[T],
    max_workers: Optional[int] = None,
) -> list[TaskResult]:
    """
    Run a function in parallel using processes.
    
    NOTE: On Windows, the function and items must be picklable.
    The main module must be protected with if __name__ == "__main__".
    
    Prefer run_parallel_threads unless you need to bypass the GIL.
    
    Args:
        func: Function to call for each item (must be picklable)
        items: Items to process (must be picklable)
        max_workers: Maximum number of worker processes
    
    Returns:
        List of TaskResult objects in same order as input items
    """
    items_list = list(items)
    results: list[TaskResult] = []
    
    # Use spawn context on all platforms for consistency
    # This is the only option on Windows anyway
    with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
        future_to_idx = {
            executor.submit(func, item): idx
            for idx, item in enumerate(items_list)
        }
        
        results = [None] * len(items_list)  # type: ignore
        
        for future in concurrent.futures.as_completed(future_to_idx):
            idx = future_to_idx[future]
            try:
                value = future.result()
                results[idx] = TaskResult(
                    success=True,
                    value=value,
                    error=None,
                    task_id=idx,
                )
            except Exception as e:
                results[idx] = TaskResult(
                    success=False,
                    value=None,
                    error=e,
                    task_id=idx,
                )
    
    return results


class WorkerPool:
    """
    A thread-based worker pool for running tasks.
    
    This provides more control than run_parallel_threads for
    long-running task processing.
    """
    
    def __init__(self, num_workers: int = 4):
        self.num_workers = num_workers
        self._task_queue: queue.Queue = queue.Queue()
        self._result_queue: queue.Queue = queue.Queue()
        self._workers: list[threading.Thread] = []
        self._shutdown = threading.Event()
        self._started = False
    
    def start(self) -> None:
        """Start the worker threads."""
        if self._started:
            return
        
        self._shutdown.clear()
        for i in range(self.num_workers):
            worker = threading.Thread(
                target=self._worker_loop,
                name=f"WorkerPool-{i}",
                daemon=True,
            )
            worker.start()
            self._workers.append(worker)
        
        self._started = True
    
    def submit(self, func: Callable, *args, **kwargs) -> None:
        """Submit a task to the pool."""
        if not self._started:
            self.start()
        self._task_queue.put((func, args, kwargs))
    
    def get_result(self, timeout: Optional[float] = None) -> TaskResult:
        """Get a result from the pool (blocking)."""
        return self._result_queue.get(timeout=timeout)
    
    def shutdown(self, wait: bool = True) -> None:
        """Shutdown the worker pool."""
        self._shutdown.set()
        
        # Send poison pills to workers
        for _ in self._workers:
            self._task_queue.put(None)
        
        if wait:
            for worker in self._workers:
                worker.join()
        
        self._workers.clear()
        self._started = False
    
    def _worker_loop(self) -> None:
        """Main loop for worker threads."""
        while not self._shutdown.is_set():
            try:
                task = self._task_queue.get(timeout=0.1)
            except queue.Empty:
                continue
            
            if task is None:  # Poison pill
                break
            
            func, args, kwargs = task
            try:
                result = func(*args, **kwargs)
                self._result_queue.put(TaskResult(
                    success=True,
                    value=result,
                    error=None,
                    task_id=id(task),
                ))
            except Exception as e:
                self._result_queue.put(TaskResult(
                    success=False,
                    value=None,
                    error=e,
                    task_id=id(task),
                ))
    
    def __enter__(self) -> "WorkerPool":
        self.start()
        return self
    
    def __exit__(self, *args) -> None:
        self.shutdown()


# Default parallel execution function - use threads for Windows safety
run_parallel = run_parallel_threads
